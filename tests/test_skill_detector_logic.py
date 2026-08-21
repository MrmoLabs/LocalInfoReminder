import os
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from core.vision.skill_detector import SkillDetector


class FakeScreenCapture:
    def __init__(self, bgr_color):
        self.bgra = np.zeros((40, 120, 4), dtype=np.uint8)
        self.bgra[:, :, 0] = bgr_color[0]
        self.bgra[:, :, 1] = bgr_color[1]
        self.bgra[:, :, 2] = bgr_color[2]
        self.bgra[:, :, 3] = 255

    def grab(self, region):
        return self.bgra.copy()


class TestSkillDetectorLogic(unittest.TestCase):
    def setUp(self):
        self.monitor = {"top": 0, "left": 0, "width": 1920, "height": 1080}

    def _build_detector(self, ocr_text, config):
        def fake_ocr(_img):
            return ([("box", ocr_text)], None)

        detector = SkillDetector(fake_ocr)
        detector.set_config(config)
        detector.trigger_cooldown = 0.0
        return detector

    def test_red_command_skill_triggers_on_matching_keyword(self):
        config = {
            "command_skills": [
                {
                    "id": "cmd_1",
                    "name": "Command One",
                    "ocr_color": "red",
                    "ocr_keywords": ["CommandOne"],
                    "duration": 5,
                }
            ],
            "miracle_skills": [],
        }
        detector = self._build_detector("CommandOne Ready", config)
        sct = FakeScreenCapture((0, 0, 255))

        with patch("core.vision.skill_detector.time.time", return_value=100.0):
            result = detector.process(sct, self.monitor, paused=False)

        self.assertEqual(result, "cmd_1")
        self.assertEqual(detector.active_skills["cmd_1"], 105.0)

    def test_color_filter_blocks_non_matching_command_skill(self):
        config = {
            "command_skills": [
                {
                    "id": "cmd_blue",
                    "name": "Blue Command",
                    "ocr_color": "blue",
                    "ocr_keywords": ["CommandBlue"],
                }
            ],
            "miracle_skills": [],
        }
        detector = self._build_detector("CommandBlue", config)
        sct = FakeScreenCapture((0, 0, 255))

        with patch("core.vision.skill_detector.time.time", return_value=200.0):
            result = detector.process(sct, self.monitor, paused=False)

        self.assertIsNone(result)

    def test_miracle_skills_are_not_part_of_ocr_detection(self):
        config = {
            "command_skills": [],
            "miracle_skills": [
                {
                    "id": "miracle_1",
                    "name": "Miracle One",
                    "ocr_color": "red",
                    "ocr_keywords": ["MiracleOne"],
                }
            ],
        }
        detector = self._build_detector("MiracleOne", config)
        sct = FakeScreenCapture((0, 0, 255))

        with patch("core.vision.skill_detector.time.time", return_value=300.0):
            result = detector.process(sct, self.monitor, paused=False)

        self.assertIsNone(result)

    def test_active_skill_is_not_retriggered_before_duration_expires(self):
        config = {
            "command_skills": [
                {
                    "id": "cmd_repeat",
                    "name": "Repeat Command",
                    "ocr_color": "red",
                    "ocr_keywords": ["Repeat"],
                    "duration": 10,
                }
            ],
            "miracle_skills": [],
        }
        detector = self._build_detector("Repeat", config)
        sct = FakeScreenCapture((0, 0, 255))

        with patch("core.vision.skill_detector.time.time", side_effect=[10.0, 12.0]):
            first = detector.process(sct, self.monitor, paused=False)
            second = detector.process(sct, self.monitor, paused=False)

        self.assertEqual(first, "cmd_repeat")
        self.assertIsNone(second)

    def test_ambiguous_color_gate_skips_ocr(self):
        config = {
            "command_skills": [
                {
                    "id": "cmd_red",
                    "name": "Red Command",
                    "ocr_color": "red",
                    "ocr_keywords": ["CommandRed"],
                }
            ],
            "vision_detection": {
                "thresholds": {
                    "skill_trigger_ratio": 0.05,
                    "skill_color_advantage_ratio": 0.02,
                }
            },
        }

        def fake_ocr(_img):
            raise AssertionError("OCR should not run when color gate is ambiguous")

        detector = SkillDetector(fake_ocr)
        detector.set_config(config)
        sct = FakeScreenCapture((120, 120, 120))

        with patch("core.vision.skill_detector.match_ratio", side_effect=[(0.081, np.ones((40, 120), dtype=bool)), (0.073, np.ones((40, 120), dtype=bool))]):
            with patch("core.vision.skill_detector.time.time", return_value=400.0):
                result = detector.process(sct, self.monitor, paused=False)

        self.assertIsNone(result)



if __name__ == "__main__":
    unittest.main()
