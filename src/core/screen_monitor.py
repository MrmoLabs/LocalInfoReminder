import time
import os
import mss
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from core.vision.time_recognizer import TimeRecognizer
from core.vision.boss_detector import BossDetector
from core.vision.skill_detector import SkillDetector
from core.vision.performance import (
    apply_rapidocr_runtime_limits,
    ensure_onnxruntime_dll_search_paths,
    preload_onnxruntime_native_binaries,
)
from core.logger import setup_logger

logger = setup_logger()

class ScreenMonitor(QThread):
    # Signals
    trigger_skill_id = pyqtSignal(str)
    time_sync_result = pyqtSignal(str) # [RESTORED]
    
    # [NEW] Boss Signals
    boss_spawn_detected = pyqtSignal(str)
    boss_kill_detected = pyqtSignal(str, str) # faction, boss_name
    
    debug_regions_changed = pyqtSignal(dict) # [NEW] Signal for debug overlay

    def __init__(self, interval=0.5):
        super().__init__()
        self.interval = interval
        self.running = True
        self.paused = False
        self.sct = None
        
        # Initialize OCR lazily inside the worker thread to avoid blocking UI startup.
        self.ocr = None
        self.time_recognizer = None
        self.boss_detector = None
        self.skill_detector = None
        
        # Flags
        self.sync_requested = False
        self.regions_emitted = False
        self.preload_attempted = False
        self.ocr_init_failed = False
        self.ocr_init_error = ""
        
        # Initial Monitor Area (Fallback)
        self.monitor_area = {"top": 225, "left": 700, "width": 570, "height": 45}

    def _screen_interval_from_config(self):
        config = getattr(self, "config", {}) or {}
        try:
            return max(0.1, float(config.get("screen_monitor_interval_seconds", self.interval)))
        except Exception:
            return max(0.1, float(self.interval))


    @staticmethod
    def _merge_capture_regions(regions):
        if not regions:
            return None

        left = min(int(region["left"]) for region in regions)
        top = min(int(region["top"]) for region in regions)
        right = max(int(region["left"]) + int(region["width"]) for region in regions)
        bottom = max(int(region["top"]) + int(region["height"]) for region in regions)
        return {
            "left": left,
            "top": top,
            "width": max(1, right - left),
            "height": max(1, bottom - top),
        }

    def _build_shared_capture_region(self, monitor, should_sync_time, should_check_boss, should_check_skill):
        if not self._ensure_components():
            return None

        regions = []
        if should_sync_time and self.time_recognizer is not None:
            for item in self.time_recognizer.get_regions(monitor).values():
                regions.append({key: item[key] for key in ("left", "top", "width", "height")})

        if should_check_boss and self.boss_detector is not None:
            for item in self.boss_detector.get_regions(monitor).values():
                regions.append({key: item[key] for key in ("left", "top", "width", "height")})

        if should_check_skill and self.skill_detector is not None:
            for item in self.skill_detector.get_regions(monitor).values():
                regions.append({key: item[key] for key in ("left", "top", "width", "height")})

        return self._merge_capture_regions(regions)

    def trigger_debug_capture(self):
        if self.skill_detector is not None:
            self.skill_detector.trigger_debug_capture()

    def trigger_debug_boss_capture(self):
        if self.boss_detector is not None:
            self.boss_detector.trigger_debug_capture()

    def trigger_debug_prep_capture(self):
        if self.time_recognizer is not None:
            self.time_recognizer.trigger_debug_prep_capture()

    def trigger_sync(self):
        self.sync_requested = True

    def set_boss_check_enabled(self, enabled: bool, targets=None):
        if self.boss_detector is not None:
            self.boss_detector.set_spawn_check(enabled, targets)

    def set_boss_kill_check_enabled(self, enabled: bool, target=None):
        if self.boss_detector is not None:
            self.boss_detector.set_kill_check(enabled, target)

    def set_config(self, config):
        self.config = config
        self.interval = self._screen_interval_from_config()
        self.regions_emitted = False
        if self.time_recognizer is not None:
            self.time_recognizer.set_config(config)
        if self.skill_detector is not None:
            self.skill_detector.set_config(config)
        if self.boss_detector is not None:
            self.boss_detector.set_config(config)

    def _ocr_features_enabled(self):
        config = getattr(self, 'config', {}) or {}
        return (
            config.get("ocr_time_sync", True)
            or (config.get("enable_boss_settings", True) and config.get("ocr_boss_detection", True))
            or (config.get("enable_command_skills", True) and config.get("ocr_command_skills", True))
        )

    def _ensure_components(self):
        if self.ocr is not None:
            return True
        if self.ocr_init_failed:
            return False

        try:
            ensure_onnxruntime_dll_search_paths()
            preload_onnxruntime_native_binaries()
            apply_rapidocr_runtime_limits(getattr(self, "config", {}) or {})
            from rapidocr_onnxruntime import RapidOCR

            self.ocr = RapidOCR()
            self.time_recognizer = TimeRecognizer(self.ocr)
            self.boss_detector = BossDetector(self.ocr)
            self.skill_detector = SkillDetector(self.ocr)
            if hasattr(self, 'config'):
                self.time_recognizer.set_config(self.config)
                self.skill_detector.set_config(self.config)
                self.boss_detector.set_config(self.config)
            return True
        except Exception as e:
            self.ocr_init_failed = True
            self.ocr_init_error = str(e)
            logger.exception(f"[ScreenMonitor] Failed to initialize OCR components: {e}")
            logger.warning("[ScreenMonitor] OCR disabled for this session after initialization failure.")
            self.ocr = None
            self.time_recognizer = None
            self.boss_detector = None
            self.skill_detector = None
            return False

    def run(self):
        logger.info("[ScreenMonitor] Started (Modular)")
        try:
            # Reuse a single mss handle for the monitor thread lifetime.
            self.sct = mss.mss()

            if self._ocr_features_enabled():
                self.preload_attempted = True
                if not self._ensure_components():
                    logger.warning("[ScreenMonitor] OCR preload failed. Will retry lazily when needed.")

            while self.running:
                start_time = time.time()
                shared_capture_elapsed = 0.0
                time_sync_elapsed = 0.0
                boss_elapsed = 0.0
                skill_elapsed = 0.0

                try:
                    self.interval = self._screen_interval_from_config()
                    monitor = self.sct.monitors[1]

                    should_sync_time = self.sync_requested and self.config.get("ocr_time_sync", True)
                    should_check_boss = self.config.get("enable_boss_settings", True) and self.config.get("ocr_boss_detection", True)
                    should_check_skill = self.config.get("enable_command_skills", True) and self.config.get("ocr_command_skills", True)

                    shared_frame = None
                    shared_region = None
                    if should_sync_time or should_check_boss or should_check_skill:
                        if not self._ensure_components():
                            time.sleep(1.0)
                            continue

                        # [NEW] Emit Debug Regions ONCE (or periodically if monitor changes)
                        if not self.regions_emitted:
                            all_regions = {}
                            all_regions.update(self.time_recognizer.get_regions(monitor))
                            all_regions.update(self.skill_detector.get_regions(monitor))
                            self.debug_regions_changed.emit(all_regions)
                            self.regions_emitted = True

                        shared_region = self._build_shared_capture_region(
                            monitor,
                            should_sync_time,
                            should_check_boss,
                            should_check_skill,
                        )
                        if shared_region is not None:
                            shared_capture_start = time.time()
                            shared_frame = np.array(self.sct.grab(shared_region))
                            shared_capture_elapsed = time.time() - shared_capture_start

                    # 1. Time Sync
                    time_sync_processed = False
                    if should_sync_time and self.time_recognizer is not None:
                        time_sync_start = time.time()
                        time_str = self.time_recognizer.process(self.sct, monitor, True, frame_bgra=shared_frame, frame_region=shared_region)
                        time_sync_elapsed = time.time() - time_sync_start
                        if time_str:
                            self.time_sync_result.emit(time_str)
                        self.sync_requested = False
                        time_sync_processed = True

                    # Avoid stacking three OCR-heavy passes in one monitor loop.
                    skip_follow_up_ocr = time_sync_processed and (should_check_boss or should_check_skill)
                    if skip_follow_up_ocr:
                        logger.debug("[ScreenMonitor] Skipping boss/skill OCR this cycle after time sync to avoid OCR pile-up.")

                    # 2. Boss Detection (Spawn & Kill)
                    if (not skip_follow_up_ocr) and should_check_boss and self.boss_detector is not None:
                        boss_start = time.time()
                        boss_events = self.boss_detector.process(self.sct, monitor, frame_bgra=shared_frame, frame_region=shared_region)
                        boss_elapsed = time.time() - boss_start
                        for evt in boss_events:
                            if evt[0] == 'spawn':
                                self.boss_spawn_detected.emit(evt[1])
                            elif evt[0] == 'kill':
                                self.boss_kill_detected.emit(evt[1], evt[2])

                    # 3. Skill Detection
                    if (not skip_follow_up_ocr) and should_check_skill and self.skill_detector is not None:
                        skill_start = time.time()
                        skill_id = self.skill_detector.process(
                            self.sct,
                            monitor,
                            self.paused,
                            frame_bgra=shared_frame,
                            frame_region=shared_region,
                        )
                        skill_elapsed = time.time() - skill_start
                        if skill_id:
                            logger.debug(f"[ScreenMonitor] Emitting trigger_skill_id: {skill_id}")
                            self.trigger_skill_id.emit(skill_id)

                except Exception as e:
                    logger.exception(f"[ScreenMonitor] Critical Loop Error: {e}")
                    time.sleep(1.0)

                elapsed = time.time() - start_time
                if elapsed > max(1.0, self.interval * 2.0):
                    logger.warning(
                        "[ScreenMonitor] Slow OCR cycle detected: "
                        f"total={elapsed:.2f}s interval={self.interval:.2f}s "
                        f"shared_capture={shared_capture_elapsed:.2f}s "
                        f"time_sync={time_sync_elapsed:.2f}s "
                        f"boss={boss_elapsed:.2f}s "
                        f"skill={skill_elapsed:.2f}s"
                    )
                sleep_time = max(0.01, self.interval - elapsed)
                time.sleep(sleep_time)
        finally:
            if self.sct is not None:
                try:
                    self.sct.close()
                except Exception:
                    pass
                self.sct = None

    def stop(self, timeout_ms: int = 1500):
        self.running = False
        if self.isRunning():
            if not self.wait(timeout_ms):
                logger.warning(f"[ScreenMonitor] Stop timeout after {timeout_ms}ms; continuing shutdown.")
