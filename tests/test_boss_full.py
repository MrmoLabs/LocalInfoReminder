import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.boss_manager import BossManager


class TestBossFull(unittest.TestCase):
    def setUp(self):
        self.config = {
            "enable_boss_settings": True,
            "boss_detection": {
                "targets": [
                    {
                        "id": "target_a",
                        "display_name": "\u76ee\u6807A",
                        "match_names": ["Target A", "\u76ee\u6807A"],
                        "ocr_keywords": ["\u76ee\u6807A"],
                        "time_windows": [{"start": "27:10", "end": "24:30"}],
                        "kill_window_seconds": 180,
                        "kill_keywords": ["\u5b8c\u6210"],
                        "faction_match": "distinguish",
                        "ignore_keywords": ["\u5373\u5c06"],
                        "spawn_sound": "",
                        "kill_sound": "",
                        "buff_duration": 120,
                    },
                    {
                        "id": "target_b",
                        "display_name": "\u76ee\u6807B",
                        "match_names": ["Target B", "\u76ee\u6807B"],
                        "ocr_keywords": ["\u76ee\u6807B"],
                        "time_windows": [{"start": "17:20", "end": "14:30"}],
                        "kill_window_seconds": 150,
                        "kill_keywords": ["\u5b8c\u6210"],
                        "faction_match": "ignore",
                        "ignore_keywords": ["\u63d0\u793a"],
                        "spawn_sound": "target_b_spawn.mp3",
                        "kill_sound": "target_b_kill.mp3",
                        "buff_duration": 300,
                    },
                ],
            }
        }
        self.bm = BossManager(self.config)

    def test_notification_windows(self):
        spawn_targets = self.bm.get_spawn_targets(1500)
        self.assertEqual([target["id"] for target in spawn_targets], ["target_a"])
        self.assertFalse(self.bm.get_spawn_targets(1400))
        self.assertEqual([target["id"] for target in self.bm.get_spawn_targets(900)], ["target_b"])

    def test_auto_reset_flags(self):
        self.bm.notification_state["target_a_window_1"] = True
        self.bm.info['active'] = True
        self.bm.get_spawn_targets(1650)
        self.assertFalse(self.bm.notification_state["target_a_window_1"])
        self.assertFalse(self.bm.info['active'])

    def test_prediction_logic(self):
        target = self.bm.predict_appearance(1500)
        self.assertTrue(target % 30 == 0)
        self.assertTrue(1440 <= target <= 1460)

    def test_kill_logic_durations(self):
        self.bm.handle_kill_detected("ally", "Target A")
        self.assertEqual(self.bm.info['buff_duration'], 120)

        self.bm.handle_kill_detected("enemy", "Target B")
        self.assertEqual(self.bm.info['buff_duration'], 300)

    def test_spawn_label_clears_after_countdown_reaches_zero(self):
        self.bm.handle_spawn_detected("Target A", 1500)
        spawn_abs = self.bm.info["spawn_time_abs"]
        self.bm.update_info_state(spawn_abs)
        self.assertEqual(self.bm.info["spawn_str"], "")

    def test_display_name_and_sound_come_from_target_config(self):
        self.assertEqual(self.bm._display_target_name("Target A"), "\u76ee\u6807A")
        self.assertEqual(self.bm.get_spawn_sound("Target B"), "target_b_spawn.mp3")
        self.assertEqual(self.bm.get_kill_sound("Target B"), "target_b_kill.mp3")


if __name__ == '__main__':
    unittest.main()
