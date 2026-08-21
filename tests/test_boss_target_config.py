import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.config_loader import ConfigLoader


class TestBossTargetNormalization(unittest.TestCase):
    def test_legacy_fields_migrate_to_targets(self):
        boss_detection = ConfigLoader.normalize_boss_detection(
            {
                "notification_windows": [
                    {"start": "27:10", "end": "24:30"},
                    {"start": "17:20", "end": "14:30"},
                ],
                "kill_check_timeout_seconds": 222,
                "spawn_keywords": {
                    "zhang_bao": ["AlphaBoss"],
                    "zhuye_gule": ["BetaBoss"],
                },
                "kill_keywords": {
                    "enemy": ["\u5b8c\u6210"],
                    "ally": ["\u83b7\u5f97"],
                },
                "ignore_keywords": ["\u5373\u5c06"],
            },
            {
                "zhang_bao": 111,
                "zhuye_gule": 333,
            },
        )

        self.assertEqual(set(boss_detection.keys()), {"targets"})
        targets = boss_detection["targets"]
        self.assertEqual(targets[0]["id"], "zhang_bao")
        self.assertEqual(targets[0]["ocr_keywords"], ["AlphaBoss"])
        self.assertEqual(targets[0]["time_windows"], [{"start": "27:10", "end": "24:30"}, {"start": "17:20", "end": "14:30"}])
        self.assertEqual(targets[0]["kill_window_seconds"], 222)
        self.assertEqual(targets[0]["kill_keywords"], ["\u5b8c\u6210", "\u83b7\u5f97"])
        self.assertEqual(targets[0]["ignore_keywords"], ["\u5373\u5c06"])
        self.assertEqual(targets[0]["buff_duration"], 111)
        self.assertEqual(targets[0]["spawn_sound"], "dragon_spawn.mp3")
        self.assertEqual(targets[1]["buff_duration"], 333)

    def test_time_window_string_is_normalized(self):
        boss_detection = ConfigLoader.normalize_boss_detection(
            {
                "targets": [
                    {
                        "id": "target_x",
                        "display_name": "\u76ee\u6807X",
                        "match_names": ["Target X"],
                        "ocr_keywords": ["\u76ee\u6807X"],
                        "time_windows": "27:10-24:30,17:20-14:30",
                        "kill_window_seconds": 180,
                        "kill_keywords": ["\u5b8c\u6210"],
                        "faction_match": "ignore",
                        "ignore_keywords": [],
                        "spawn_sound": "spawn.mp3",
                        "kill_sound": "kill.mp3",
                        "buff_duration": 60,
                    }
                ]
            },
            {},
        )
        self.assertEqual(
            boss_detection["targets"][0]["time_windows"],
            [{"start": "27:10", "end": "24:30"}, {"start": "17:20", "end": "14:30"}],
        )

    def test_targets_to_boss_durations(self):
        durations = ConfigLoader.targets_to_boss_durations([
            {"id": "target_a", "buff_duration": 30},
            {"id": "target_b", "buff_duration": 60},
        ])
        self.assertEqual(durations, {"target_a": 30, "target_b": 60})


if __name__ == '__main__':
    unittest.main()
