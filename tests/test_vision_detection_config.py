import os
import sys
import tempfile
import unittest
import json

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from core.config_loader import ConfigLoader
from core.vision.boss_detector import BossDetector
from core.vision.skill_detector import SkillDetector
from core.vision.time_recognizer import TimeRecognizer


class DummyOCR:
    def __call__(self, _img):
        return [], None


class TestVisionDetectionConfig(unittest.TestCase):
    def test_load_config_injects_vision_detection_defaults(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump({}, tmp, ensure_ascii=False)
            tmp_path = tmp.name

        try:
            loaded = ConfigLoader.load_config(tmp_path)
        finally:
            os.unlink(tmp_path)

        self.assertIn("vision_detection", loaded)
        self.assertIn("regions", loaded["vision_detection"])
        self.assertIn("thresholds", loaded["vision_detection"])
        self.assertIn("time_main", loaded["vision_detection"]["regions"])
        self.assertIn("skill_trigger_ratio", loaded["vision_detection"]["thresholds"])
        self.assertIn("color_profiles", loaded["vision_detection"])
        self.assertIn("skill_red", loaded["vision_detection"]["color_profiles"])
        self.assertIn("ocr_time_sync_interval_seconds", loaded)
        self.assertIn("screen_monitor_interval_seconds", loaded)
        self.assertIn("skill_color_advantage_ratio", loaded["vision_detection"]["thresholds"])

    def test_detectors_use_custom_region_ratios(self):
        config = {
            "vision_detection": {
                "regions": {
                    "time_main": {"left": 0.1, "top": 0.2, "width": 0.3, "height": 0.4},
                    "time_prep": {"left": 0.2, "top": 0.3, "width": 0.1, "height": 0.2},
                    "skill_bar": {"left": 0.4, "top": 0.5, "width": 0.2, "height": 0.1},
                    "boss_notification": {"left": 0.6, "top": 0.1, "width": 0.25, "height": 0.15},
                    "boss_kill": {"left": 0.7, "top": 0.2, "width": 0.22, "height": 0.12},
                },
                "thresholds": {
                    "skill_trigger_ratio": 0.123,
                    "skill_color_advantage_ratio": 0.034,
                    "boss_faction_ratio": 0.456,
                },
            },
            "boss_detection": {"targets": []},
            "boss_buff_durations": {},
            "command_skills": [],
        }
        monitor = {"top": 10, "left": 20, "width": 1000, "height": 500}

        time_recognizer = TimeRecognizer(DummyOCR())
        time_recognizer.set_config(config)
        time_regions = time_recognizer.get_regions(monitor)
        self.assertEqual(time_regions["Time Main"]["left"], 164)
        self.assertEqual(time_regions["Time Main"]["top"], 110)
        self.assertEqual(time_regions["Time Main"]["width"], 266)
        self.assertEqual(time_regions["Time Main"]["height"], 200)

        skill_detector = SkillDetector(DummyOCR())
        skill_detector.set_config(config)
        skill_regions = skill_detector.get_regions(monitor)
        self.assertEqual(skill_regions["Command Skill"]["left"], 431)
        self.assertEqual(skill_regions["Command Skill"]["top"], 260)
        self.assertAlmostEqual(skill_detector._skill_trigger_ratio(), 0.123)
        self.assertAlmostEqual(skill_detector._skill_color_advantage_ratio(), 0.034)

        boss_detector = BossDetector(DummyOCR())
        boss_detector.set_config(config)
        boss_regions = boss_detector.get_regions(monitor)
        self.assertEqual(boss_regions["Target Event Notification"]["left"], 609)
        self.assertEqual(boss_regions["Target Event Notification"]["top"], 60)
        self.assertEqual(boss_regions["Target Event Kill"]["left"], 698)
        self.assertEqual(boss_regions["Target Event Kill"]["top"], 110)
        self.assertAlmostEqual(boss_detector._boss_faction_ratio(), 0.456)

    def test_normalize_vision_detection_preserves_per_profile_min_ratio(self):
        normalized = ConfigLoader.normalize_vision_detection({
            "thresholds": {
                "skill_trigger_ratio": 0.01,
                "boss_faction_ratio": 0.03,
            },
            "color_profiles": {
                "skill_red": {"sample_color": [255, 70, 70], "tolerance": 120.0, "min_ratio": 0.015},
                "skill_blue": {"sample_color": [70, 130, 255], "tolerance": 90.0, "min_ratio": 0.022},
                "boss_red": {"sample_color": [255, 60, 60], "tolerance": 80.0, "min_ratio": 0.041},
                "boss_blue": {"sample_color": [70, 130, 255], "tolerance": 95.0, "min_ratio": 0.027},
            },
        })
        profiles = normalized["color_profiles"]
        self.assertAlmostEqual(profiles["skill_red"]["min_ratio"], 0.015)
        self.assertAlmostEqual(profiles["skill_blue"]["min_ratio"], 0.022)
        self.assertAlmostEqual(profiles["boss_red"]["min_ratio"], 0.041)
        self.assertAlmostEqual(profiles["boss_blue"]["min_ratio"], 0.027)


if __name__ == "__main__":
    unittest.main()
