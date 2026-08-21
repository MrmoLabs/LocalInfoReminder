import cv2
import numpy as np
import os
import time

from core.vision.vision_constants import build_region_from_ratio, crop_bgra_region, default_detection_regions
from core.vision.performance import downsample_region_for_processing


class TimeRecognizer:
    def __init__(self, ocr_instance):
        self.ocr = ocr_instance
        self.debug_prep_capture_requested = False
        self.config = {}

    def set_config(self, config):
        self.config = config or {}

    def _region_ratios(self):
        vision_detection = (self.config or {}).get("vision_detection", {})
        regions = vision_detection.get("regions", {})
        defaults = default_detection_regions()
        return {
            "time_main": dict(regions.get("time_main", defaults["time_main"])),
            "time_prep": dict(regions.get("time_prep", defaults["time_prep"])),
        }

    def get_regions(self, monitor):
        """Returns the monitored regions for debug visualization."""
        regions = self._region_ratios()
        time_main_region = build_region_from_ratio(monitor, regions["time_main"])
        prep_region = build_region_from_ratio(monitor, regions["time_prep"])
        return {
            "Time Main": {**time_main_region, "color": "#00FF00"},
            "Time Prep": {**prep_region, "color": "#AAFF00"},
        }

    def process(self, sct, monitor, sync_requested: bool, frame_bgra=None, frame_region=None):
        """
        Attempts to find the game time.
        Returns a time string "MM:SS" if found, or None.
        """
        if not sync_requested:
            return None

        try:
            regions = self._region_ratios()
            time_region_ratio = regions["time_main"]
            time_region = build_region_from_ratio(monitor, time_region_ratio)

            if frame_bgra is not None and frame_region is not None:
                t_img = crop_bgra_region(frame_bgra, frame_region, time_region)
            else:
                t_img = np.array(sct.grab(time_region))
            if t_img.size == 0:
                return None
            t_img = downsample_region_for_processing(t_img, time_region_ratio, self.config)
            t_rgb = cv2.cvtColor(t_img, cv2.COLOR_BGRA2RGB)

            res, _ = self.ocr(t_rgb)
            has_digits = False

            # 1. Main Timer Check
            if res:
                full_text = " ".join([line[1] for line in res])
                has_digits = any(char.isdigit() for char in full_text)
                if has_digits:
                    print(f"[TimeRecognizer] Main Timer OCR: {full_text}")
                    return full_text
                print(f"[TimeRecognizer] Main Timer found text '{full_text}' but NO DIGITS. Trying Prep...")

            # 2. Prep Timer Fallback
            if not res or not has_digits:
                prep_region_ratio = regions["time_prep"]
                prep_region = build_region_from_ratio(monitor, prep_region_ratio)

                if self.debug_prep_capture_requested:
                    self._save_debug(sct, prep_region, "prep_debug_capture")
                    self.debug_prep_capture_requested = False

                if frame_bgra is not None and frame_region is not None:
                    p_img = crop_bgra_region(frame_bgra, frame_region, prep_region)
                else:
                    p_img = np.array(sct.grab(prep_region))
                if p_img.size == 0:
                    return None
                p_img = downsample_region_for_processing(p_img, prep_region_ratio, self.config)
                p_rgb = cv2.cvtColor(p_img, cv2.COLOR_BGRA2RGB)
                p_res, _ = self.ocr(p_rgb)

                if p_res:
                    p_text = " ".join([line[1] for line in p_res]).strip()
                    print(f"[TimeRecognizer] Prep Timer OCR: {p_text}")
                    return self._parse_prep_time(p_text)
                print("[TimeRecognizer] Prep Timer: No text found")

        except Exception as e:
            print(f"[TimeRecognizer] Error: {e}")

        return None

    def _parse_prep_time(self, p_text):
        mins = 0
        secs = 0
        valid_prep = False

        if ":" in p_text:
            parts = p_text.split(":")
            parts = [p.strip() for p in parts if p.strip().isdigit()]
            if len(parts) >= 2:
                mins = int(parts[0])
                secs = int(parts[1])
                valid_prep = True
        elif p_text.isdigit():
            val = int(p_text)
            if val < 60:
                mins = 0
                secs = val
                valid_prep = True

        if valid_prep:
            total_mins = mins + 30
            final_sync_str = f"{total_mins:02d}:{secs:02d}"
            print(f"[TimeRecognizer] Prep Logic: {p_text} -> Found {mins}m {secs}s -> Emitting {final_sync_str}")
            return final_sync_str

        return None

    def trigger_debug_prep_capture(self):
        self.debug_prep_capture_requested = True

    def _save_debug(self, sct, region, prefix):
        try:
            img = np.array(sct.grab(region))
            if not os.path.exists("debug_imgs"):
                os.makedirs("debug_imgs")
            timestamp = int(time.time() * 1000)
            cv2.imwrite(f"debug_imgs/{prefix}_{timestamp}.png", img)
            print(f"[TimeRecognizer] Saved debug image: {prefix}_{timestamp}.png")
        except Exception as e:
            print(f"[TimeRecognizer] Failed to save debug image: {e}")
