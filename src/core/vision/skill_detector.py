import cv2
import numpy as np
import time
import os
from core.vision.color_profile import default_color_profiles, match_ratio
from core.vision.vision_constants import (
    build_region_from_ratio,
    crop_bgra_region,
    default_detection_regions,
    default_detection_thresholds,
)
from core.vision.performance import downsample_region_for_processing

import logging

logger = logging.getLogger(__name__)


class SkillDetector:
    def __init__(self, ocr_instance):
        self.ocr = ocr_instance
        self.debug_capture_requested = False

        # Debounce
        self.last_trigger_time = 0
        self.trigger_cooldown = 1.0
        self.active_skills = {}

        # Config
        self.monitor_area = None
        self.config = {}

    def _skill_region_ratio(self):
        vision_detection = (self.config or {}).get("vision_detection", {})
        regions = vision_detection.get("regions", {})
        return dict(regions.get("skill_bar", default_detection_regions()["skill_bar"]))

    def _color_profile(self, key):
        vision_detection = (self.config or {}).get("vision_detection", {})
        profiles = vision_detection.get("color_profiles", {})
        return dict(profiles.get(key, default_color_profiles()[key]))

    def _skill_trigger_ratio(self):
        vision_detection = (self.config or {}).get("vision_detection", {})
        thresholds = vision_detection.get("thresholds", {})
        return float(thresholds.get("skill_trigger_ratio", default_detection_thresholds()["skill_trigger_ratio"]))

    def _skill_color_advantage_ratio(self):
        vision_detection = (self.config or {}).get("vision_detection", {})
        thresholds = vision_detection.get("thresholds", {})
        return float(thresholds.get("skill_color_advantage_ratio", default_detection_thresholds()["skill_color_advantage_ratio"]))

    def get_regions(self, monitor):
        """Returns the monitored regions for debug visualization."""
        skill_region = build_region_from_ratio(monitor, self._skill_region_ratio())
        return {
            "Command Skill": {**skill_region, "color": "#0000FF"}
        }

    def set_config(self, config):
        self.config = config or {}

    def process(self, sct, monitor, paused: bool, frame_bgra=None, frame_region=None):
        """
        Returns skill_id if triggered, else None.
        """
        if not hasattr(self, 'config') or not self.config:
            return None

        skill_region_ratio = self._skill_region_ratio()
        self.monitor_area = build_region_from_ratio(monitor, skill_region_ratio)

        if self.debug_capture_requested:
            self._save_debug(sct, self.monitor_area, "manual_debug_capture")
            self.debug_capture_requested = False

        if paused:
            return None

        try:
            now = time.time()
            expired_ids = [sid for sid, expiry in self.active_skills.items() if now > expiry]
            for sid in expired_ids:
                del self.active_skills[sid]

            command_skills = self.config.get('command_skills', [])

            if frame_bgra is not None and frame_region is not None:
                img_np = crop_bgra_region(frame_bgra, frame_region, self.monitor_area)
            else:
                img_np = np.array(sct.grab(self.monitor_area))
            if img_np.size == 0:
                return None
            img_np = downsample_region_for_processing(img_np, skill_region_ratio, self.config)
            img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGRA2RGB)

            total_pixels = img_np.shape[0] * img_np.shape[1]
            if total_pixels == 0:
                return None

            red_profile = self._color_profile("skill_red")
            blue_profile = self._color_profile("skill_blue")
            red_ratio, _ = match_ratio(img_rgb, red_profile)
            blue_ratio, _ = match_ratio(img_rgb, blue_profile)
            trigger_ratio = self._skill_trigger_ratio()
            advantage_ratio = self._skill_color_advantage_ratio()
            red_threshold = max(trigger_ratio, float(red_profile.get("min_ratio", trigger_ratio)))
            blue_threshold = max(trigger_ratio, float(blue_profile.get("min_ratio", trigger_ratio)))

            is_red = red_ratio > red_threshold
            is_blue = blue_ratio > blue_threshold
            red_advantage = red_ratio - blue_ratio
            blue_advantage = blue_ratio - red_ratio

            detected_colors = set()
            if is_red and red_advantage >= advantage_ratio:
                detected_colors.add('red')
            if is_blue and blue_advantage >= advantage_ratio:
                detected_colors.add('blue')

            if is_red and is_blue and not detected_colors:
                logger.debug(
                    f"[SkillDetector] Color gate ambiguous. red={red_ratio:.4f} blue={blue_ratio:.4f} advantage<{advantage_ratio:.4f}"
                )

            if not detected_colors:
                return None

            possible_skills = []

            for skill in command_skills:
                if not skill.get('is_enabled', True):
                    continue
                skill_color = skill.get('ocr_color', '').lower()
                if not skill_color or skill_color in detected_colors:
                    possible_skills.append(skill)

            if not possible_skills:
                return None

            result, _ = self.ocr(img_rgb)
            if not result:
                return None
            full_text = "".join([line[1] for line in result])

            if now - self.last_trigger_time > self.trigger_cooldown:
                for skill in possible_skills:
                    skill_id = skill.get('id')
                    expiry = self.active_skills.get(skill_id, 0)
                    if now < expiry:
                        continue

                    keywords = skill.get('ocr_keywords', [])
                    for kw in keywords:
                        if kw in full_text:
                            logger.info(f"[SkillDetector] Trigger ({skill.get('ocr_color')}): {skill.get('name')} (Text: {full_text})")
                            self.last_trigger_time = now

                            duration = float(skill.get('duration', 0))
                            if duration > 0:
                                self.active_skills[skill_id] = now + duration
                                logger.debug(f"[SkillDetector] Cooldown set for {skill.get('name')}: {duration}s")

                            return skill_id

        except Exception as e:
            logger.error(f"[SkillDetector] Error: {e}", exc_info=True)

        return None

    def trigger_debug_capture(self):
        self.debug_capture_requested = True

    def _save_debug(self, sct, region, prefix):
        try:
            img = np.array(sct.grab(region))
            if not os.path.exists("debug_imgs"):
                os.makedirs("debug_imgs")
            timestamp = int(time.time() * 1000)
            cv2.imwrite(f"debug_imgs/{prefix}_{timestamp}.png", img)
            logger.info(f"[SkillDetector] Saved debug image: {prefix}_{timestamp}.png")
        except Exception as e:
            logger.error(f"[SkillDetector] Failed to save debug: {e}")
