import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.vision.boss_detector import BossDetector


class DummyOCR:
    def __call__(self, *_args, **_kwargs):
        return [], None


class TestBossDetectorConfig(unittest.TestCase):
    def setUp(self):
        self.detector = BossDetector(DummyOCR())
        self.target_alpha = {
            "id": "alpha_boss",
            "display_name": "Alpha",
            "match_names": ["Alpha Boss", "\u7532\u76ee\u6807"],
            "ocr_keywords": ["AlphaBoss"],
            "time_windows": [{"start": "27:10", "end": "24:30"}],
            "kill_window_seconds": 95,
            "kill_keywords": ["EnemyFinal", "AllyFinal"],
            "faction_match": "ignore",
            "ignore_keywords": ["IgnoreThis"],
            "spawn_sound": "alpha_spawn.mp3",
            "kill_sound": "alpha_kill.mp3",
            "buff_duration": 120,
        }
        self.target_beta = {
            "id": "beta_boss",
            "display_name": "Beta",
            "match_names": ["Beta Boss", "Gamma Boss"],
            "ocr_keywords": ["BetaBoss", "GammaBoss"],
            "time_windows": [{"start": "17:20", "end": "14:30"}],
            "kill_window_seconds": 180,
            "kill_keywords": ["EnemyFinal"],
            "faction_match": "distinguish",
            "ignore_keywords": [],
            "spawn_sound": "beta_spawn.mp3",
            "kill_sound": "",
            "buff_duration": 300,
        }
        self.detector.set_config({
            "boss_detection": {
                "targets": [self.target_alpha, self.target_beta]
            }
        })
        self.detector.set_spawn_check(True, [self.target_alpha, self.target_beta])
        self.detector.set_kill_check(True, self.target_alpha)

    def test_spawn_keyword_mapping_comes_from_targets(self):
        self.assertEqual(self.detector._detect_spawn_name("xxxAlphaBossxxx"), "Alpha Boss")
        self.assertEqual(self.detector._detect_spawn_name("xxxGammaBossxxx"), "Beta Boss")
        self.assertIsNone(self.detector._detect_spawn_name("NoBoss"))

    def test_display_name_comes_from_target_config(self):
        self.assertEqual(self.detector._display_target_name("\u7532\u76ee\u6807\u5df2\u51fa\u73b0"), "Alpha")
        self.assertEqual(self.detector._display_target_name("Gamma Boss incoming"), "Beta")

    def test_kill_settings_come_from_active_target(self):
        self.assertEqual(self.detector._kill_timeout_seconds(), 95)
        self.assertEqual(self.detector._ignore_keywords(), ["IgnoreThis"])
        self.assertEqual(self.detector._kill_keywords(), ["EnemyFinal", "AllyFinal"])
        self.assertEqual(self.detector._faction_match_mode(), "ignore")


if __name__ == '__main__':
    unittest.main()
