import cv2
import numpy as np
import os
import time

from core.config_loader import ConfigLoader
from core.constants import FilePaths, allow_dev_config_overrides
from core.logger import setup_logger
from core.vision.color_profile import default_color_profiles, match_ratio
from core.vision.vision_constants import (
    build_region_from_ratio,
    crop_bgra_region,
    default_detection_regions,
    default_detection_thresholds,
)
from core.vision.performance import downsample_region_for_processing


logger = setup_logger()


class BossDetector:
    DEFAULT_KILL_TIMEOUT = 180
    DEFAULT_SPAWN_HINT_KEYWORDS = (
        "即将",
        "出现",
        "出没",
        "刷新",
        "一分钟",
        "1分钟",
        "可大有",
    )

    def __init__(self, ocr_instance):
        self.ocr = ocr_instance
        self.config = {}
        self.boss_check_enabled = False
        self.boss_kill_check_enabled = False
        self.active_spawn_targets = []
        self.active_kill_target = None

        self.last_boss_trigger_time = 0
        self.last_boss_kill_check_time = 0
        self.last_kill_signal_time = 0
        self.boss_kill_check_start_ts = 0

        self.debug_boss_capture_requested = False
        self.debug_ocr_enabled = False
        self.debug_boss_capture_enabled = False
        if not allow_dev_config_overrides():
            logger.info("[BossDetector] Debug Mode disabled in frozen build.")
            return
        try:
            import json
            if os.path.exists(FilePaths.DEV_CONFIG):
                with open(FilePaths.DEV_CONFIG, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.debug_ocr_enabled = cfg.get("debug_ocr", False)
                    self.debug_boss_capture_enabled = cfg.get("debug_boss_capture", False)
            logger.info(f"[BossDetector] Debug Mode: OCR={self.debug_ocr_enabled}, Capture={self.debug_boss_capture_enabled}")
        except Exception as e:
            logger.error(f"[BossDetector] Failed to load dev_config: {e}")

    def set_config(self, config):
        self.config = config or {}

    def _boss_detection_config(self):
        return ConfigLoader.normalize_boss_detection(
            self.config.get("boss_detection", {}),
            {},
        )

    def _boss_region_ratio(self, key="boss_notification"):
        vision_detection = (self.config or {}).get("vision_detection", {})
        regions = vision_detection.get("regions", {})
        defaults = default_detection_regions()
        return dict(regions.get(key, defaults[key]))

    def _color_profile(self, key):
        vision_detection = (self.config or {}).get("vision_detection", {})
        profiles = vision_detection.get("color_profiles", {})
        return dict(profiles.get(key, default_color_profiles()[key]))

    def _boss_faction_ratio(self):
        vision_detection = (self.config or {}).get("vision_detection", {})
        thresholds = vision_detection.get("thresholds", {})
        return float(thresholds.get("boss_faction_ratio", default_detection_thresholds()["boss_faction_ratio"]))

    def _targets(self):
        return self._boss_detection_config().get("targets", [])

    def _candidate_spawn_targets(self):
        return self.active_spawn_targets or self._targets()

    def _candidate_kill_targets(self):
        return [self.active_kill_target] if self.active_kill_target else self._targets()

    def _target_aliases(self, target, include_ocr_keywords=False):
        aliases = list(target.get("match_names", [])) + [target.get("display_name", ""), target.get("id", "")]
        if include_ocr_keywords:
            aliases += list(target.get("ocr_keywords", []))
        return aliases

    def _match_target(self, text, candidates=None, include_ocr_keywords=False):
        normalized_text = str(text or "")
        lowered = normalized_text.lower()
        for target in candidates or []:
            for alias in self._target_aliases(target, include_ocr_keywords=include_ocr_keywords):
                alias_text = str(alias or "").strip()
                if not alias_text:
                    continue
                if alias_text.lower() in lowered or alias_text in normalized_text:
                    return target
        return None

    def _detect_spawn_name(self, clean_text):
        target = self._match_target(clean_text, self._candidate_spawn_targets(), include_ocr_keywords=True)
        if target:
            return target.get("match_names", [target.get("display_name", target.get("id", ""))])[0]
        return None

    def _detect_kill_name(self, txt):
        target = self._match_target(txt, self._candidate_kill_targets(), include_ocr_keywords=True)
        if target:
            return target.get("match_names", [target.get("display_name", target.get("id", ""))])[0]
        return "Unknown"

    def _display_target_name(self, boss_name: str) -> str:
        target = self._match_target(boss_name, self._targets(), include_ocr_keywords=True)
        if target:
            return target.get("display_name", target.get("id", ""))
        return boss_name or "\u672a\u77e5\u76ee\u6807"

    def _kill_timeout_seconds(self):
        target = self.active_kill_target or {}
        try:
            return int(target.get("kill_window_seconds", self.DEFAULT_KILL_TIMEOUT))
        except Exception:
            return self.DEFAULT_KILL_TIMEOUT

    def _kill_keywords(self):
        return list((self.active_kill_target or {}).get("kill_keywords", []))

    def _ignore_keywords(self):
        return list((self.active_kill_target or {}).get("ignore_keywords", []))

    def _spawn_hint_keywords(self):
        configured = self._ignore_keywords()
        merged = list(configured)
        for keyword in self.DEFAULT_SPAWN_HINT_KEYWORDS:
            if keyword not in merged:
                merged.append(keyword)
        return merged

    def _faction_match_mode(self):
        return str((self.active_kill_target or {}).get("faction_match", "distinguish") or "distinguish").lower()

    def set_spawn_check(self, enabled: bool, targets=None):
        if self.boss_check_enabled != enabled:
            logger.info(f"[BossDetector] Event check {'enabled' if enabled else 'disabled'}")
        self.boss_check_enabled = enabled
        self.active_spawn_targets = list(targets or []) if enabled else []

    def set_kill_check(self, enabled: bool, target=None):
        target_name = ""
        if target:
            target_name = str(target.get("display_name") or target.get("id") or "").strip()
        if enabled and not target:
            logger.info("[BossDetector] Completion check request ignored: no target provided.")
            self.boss_kill_check_enabled = False
            self.active_kill_target = None
            self.boss_kill_check_start_ts = 0
            return
        logger.info(
            f"[BossDetector] Completion check state: {enabled}"
            + (f" (target={target_name})" if target_name else "")
        )
        self.boss_kill_check_enabled = enabled
        self.active_kill_target = dict(target) if target else None
        if enabled:
            self.boss_kill_check_start_ts = time.time()
            self.last_boss_kill_check_time = 0
            logger.info(f"[BossDetector] Completion check started. Timeout in {self._kill_timeout_seconds()}s.")
        else:
            self.boss_kill_check_start_ts = 0

    def get_regions(self, monitor):
        notification_region = build_region_from_ratio(monitor, self._boss_region_ratio("boss_notification"))
        kill_region = build_region_from_ratio(monitor, self._boss_region_ratio("boss_kill"))
        return {
            "Target Event Notification": {**notification_region, "color": "#FF0000"},
            "Target Event Kill": {**kill_region, "color": "#FF8800"},
        }

    def _log_timing(self, phase, start_time, **segments):
        total_ms = (time.time() - start_time) * 1000.0
        segment_parts = [f"{name}={value * 1000.0:.1f}ms" for name, value in segments.items()]
        logger.info(
            f"[BossDetector] {phase} timing: total={total_ms:.1f}ms "
            + " ".join(segment_parts)
        )

    def process(self, sct, monitor, frame_bgra=None, frame_region=None):
        events = []
        now = time.time()
        notification_region_ratio = self._boss_region_ratio("boss_notification")
        kill_region_ratio = self._boss_region_ratio("boss_kill")
        notification_region = build_region_from_ratio(monitor, notification_region_ratio)
        kill_region = build_region_from_ratio(monitor, kill_region_ratio)

        if self.debug_boss_capture_requested:
            self._save_debug(sct, notification_region, "boss_region_debug")
            self.debug_boss_capture_requested = False

        if self.boss_check_enabled and (now - self.last_boss_trigger_time > 1.0):
            if now - self.last_boss_trigger_time > 60:
                try:
                    if frame_bgra is not None and frame_region is not None:
                        boss_img = crop_bgra_region(frame_bgra, frame_region, notification_region)
                    else:
                        boss_img = np.array(sct.grab(notification_region))
                    if boss_img.size == 0:
                        boss_img = None
                    if boss_img is not None:
                        boss_img = downsample_region_for_processing(boss_img, notification_region_ratio, self.config)
                        boss_rgb = cv2.cvtColor(boss_img, cv2.COLOR_BGRA2RGB)
                    else:
                        boss_rgb = None
                    if boss_rgb is None:
                        result = None
                    else:
                        result, _ = self.ocr(boss_rgb)
                    if result:
                        raw_text = " ".join([line[1] for line in result])
                        clean_text = raw_text.replace(" ", "").replace("\uff0c", "").replace("\u3002", "")
                        spawn_name = self._detect_spawn_name(clean_text)
                        if spawn_name:
                            logger.info(f"[BossDetector] TARGET EVENT DETECTED: {self._display_target_name(spawn_name)}")
                            self.last_boss_trigger_time = now
                            events.append(("spawn", spawn_name))
                except Exception:
                    logger.exception("[BossDetector] Spawn detection error")

        if self.boss_kill_check_enabled:
            if not self.active_kill_target:
                logger.info("[BossDetector] Completion check disabled: active target missing.")
                self.boss_kill_check_enabled = False
                return events
            kill_timeout = self._kill_timeout_seconds()
            if now - self.boss_kill_check_start_ts > kill_timeout:
                logger.info(f"[BossDetector] Completion check timed out ({kill_timeout}s). Auto-disabling.")
                self.boss_kill_check_enabled = False
            elif now - self.last_boss_kill_check_time > 1.0:
                self.last_boss_kill_check_time = now
                try:
                    timing_start = time.time()
                    capture_elapsed = 0.0
                    preprocess_elapsed = 0.0
                    color_elapsed = 0.0
                    ocr_elapsed = 0.0
                    parse_elapsed = 0.0

                    capture_start = time.time()
                    if frame_bgra is not None and frame_region is not None:
                        k_img = crop_bgra_region(frame_bgra, frame_region, kill_region)
                    else:
                        k_img = np.array(sct.grab(kill_region))
                    capture_elapsed = time.time() - capture_start
                    if k_img.size == 0:
                        self._log_timing("Completion scan skipped", timing_start, capture=capture_elapsed)
                        return events

                    preprocess_start = time.time()
                    k_img = downsample_region_for_processing(k_img, kill_region_ratio, self.config)
                    k_rgb = cv2.cvtColor(k_img, cv2.COLOR_BGRA2RGB)
                    preprocess_elapsed = time.time() - preprocess_start

                    color_start = time.time()
                    red_profile = self._color_profile("boss_red")
                    blue_profile = self._color_profile("boss_blue")
                    r_ratio, red_mask = match_ratio(k_rgb, red_profile)
                    b_ratio, blue_mask = match_ratio(k_rgb, blue_profile)
                    red_count = int(red_mask.sum()) if red_mask is not None else 0
                    blue_count = int(blue_mask.sum()) if blue_mask is not None else 0
                    faction_ratio = self._boss_faction_ratio()
                    red_min_ratio = max(faction_ratio, float(red_profile.get("min_ratio", faction_ratio)))
                    blue_min_ratio = max(faction_ratio, float(blue_profile.get("min_ratio", faction_ratio)))
                    color_elapsed = time.time() - color_start

                    faction = None
                    if r_ratio > red_min_ratio and red_count > blue_count * 2:
                        faction = "enemy"
                    elif b_ratio > blue_min_ratio and blue_count > red_count * 2:
                        faction = "ally"

                    faction_mode = self._faction_match_mode()
                    active_target_name = self._display_target_name(
                        (self.active_kill_target or {}).get("display_name", "") or (self.active_kill_target or {}).get("id", "")
                    )
                    logger.info(
                        "[BossDetector] Completion scan: "
                        f"target={active_target_name or 'unknown'} "
                        f"mode={faction_mode} "
                        f"red_ratio={r_ratio:.4f} blue_ratio={b_ratio:.4f} "
                        f"red_pixels={red_count} blue_pixels={blue_count} "
                        f"thresholds=({red_min_ratio:.4f},{blue_min_ratio:.4f}) "
                        f"faction={faction or 'undetermined'}"
                    )

                    # If the completion banner color signal is weak, skip OCR entirely.
                    # This avoids spending seconds on OCR when the region is clearly not showing a kill result.
                    if r_ratio < red_min_ratio and b_ratio < blue_min_ratio:
                        logger.debug("[BossDetector] Completion OCR skipped: color ratios below thresholds")
                        self._log_timing(
                            "Completion scan skipped",
                            timing_start,
                            capture=capture_elapsed,
                            preprocess=preprocess_elapsed,
                            color=color_elapsed,
                        )
                        return events

                    ocr_start = time.time()
                    res, _ = self.ocr(k_rgb)
                    ocr_elapsed = time.time() - ocr_start
                    if not res:
                        logger.debug("[BossDetector] Completion OCR returned no text")
                        self._log_timing(
                            "Completion OCR empty",
                            timing_start,
                            capture=capture_elapsed,
                            preprocess=preprocess_elapsed,
                            color=color_elapsed,
                            ocr=ocr_elapsed,
                        )
                    else:
                        parse_start = time.time()
                        full_text = " ".join([str(line[1]) for line in res])
                        txt = full_text.replace(" ", "")
                        logger.info(f"[BossDetector] Completion OCR text ({faction or 'unknown'}): {txt}")

                        boss_name = self._detect_kill_name(txt)
                        ignore_keywords = self._spawn_hint_keywords()
                        kill_keywords = self._kill_keywords()
                        is_kill_event = False

                        if any(k in txt for k in ignore_keywords):
                            logger.info("[BossDetector] Completion OCR ignored by ignore_keywords")
                        elif any(k in txt for k in kill_keywords):
                            if faction_mode == "ignore":
                                is_kill_event = True
                            elif faction in {"enemy", "ally"}:
                                is_kill_event = True
                            else:
                                logger.info("[BossDetector] Completion keywords matched but faction is still undetermined")
                        else:
                            logger.debug("[BossDetector] Completion OCR did not match any kill keywords")

                        if is_kill_event and boss_name == "Unknown":
                            logger.info(f"[BossDetector] Completion event ignored: unknown target name (Text: {txt})")
                            is_kill_event = False

                        if is_kill_event and now - self.last_kill_signal_time > 10:
                            final_faction = faction if faction_mode == "distinguish" else (faction or "unknown")
                            logger.info(f"[BossDetector] EVENT COMPLETED: {final_faction} - {self._display_target_name(boss_name)}")
                            self.last_kill_signal_time = now
                            events.append(("kill", final_faction, boss_name))
                        parse_elapsed = time.time() - parse_start
                        self._log_timing(
                            "Completion OCR processed",
                            timing_start,
                            capture=capture_elapsed,
                            preprocess=preprocess_elapsed,
                            color=color_elapsed,
                            ocr=ocr_elapsed,
                            parse=parse_elapsed,
                        )
                except Exception as e:
                    logger.exception(f"[BossDetector] Completion check error: {e}")

        return events

    def trigger_debug_capture(self):
        self.debug_boss_capture_requested = True

    def _save_debug(self, sct, region, prefix):
        try:
            img = np.array(sct.grab(region))
            if not os.path.exists("debug_imgs"):
                os.makedirs("debug_imgs")
            timestamp = int(time.time() * 1000)
            cv2.imwrite(f"debug_imgs/{prefix}_{timestamp}.png", img)
            logger.info(f"[BossDetector] Saved debug image: {prefix}_{timestamp}.png")
        except Exception as e:
            logger.error(f"[BossDetector] Failed to save debug: {e}")
