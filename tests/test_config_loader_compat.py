import json
import os
import sys
import tempfile
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from core.config_loader import ConfigLoader


class TestConfigLoaderCompat(unittest.TestCase):
    def test_legacy_enemy_keys_migrate_to_command_keys(self):
        legacy_config = {
            "enemy_skills": [
                {
                    "id": "legacy",
                    "name": "Legacy Skill",
                    "sound": "enemy_skills/legacy.mp3",
                    "ocr_color": "red",
                    "ocr_keywords": ["Legacy"],
                }
            ],
            "enable_enemy_skills": False,
            "ocr_enemy_skills": False,
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(legacy_config, tmp, ensure_ascii=False)
            tmp_path = tmp.name

        try:
            loaded = ConfigLoader.load_config(tmp_path)
        finally:
            os.unlink(tmp_path)

        self.assertIn("command_skills", loaded)
        self.assertNotIn("enemy_skills", loaded)
        self.assertFalse(loaded["enable_command_skills"])
        self.assertFalse(loaded["ocr_command_skills"])
        self.assertEqual(loaded["command_skills"][0]["sound"], "command_skills/legacy.mp3")

    def test_bare_sound_filename_gets_command_folder_prefix(self):
        config = {
            "command_skills": [
                {
                    "id": "quick",
                    "name": "Quick",
                    "sound": "quick.mp3",
                }
            ]
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(config, tmp, ensure_ascii=False)
            tmp_path = tmp.name

        try:
            loaded = ConfigLoader.load_config(tmp_path)
        finally:
            os.unlink(tmp_path)

        self.assertEqual(loaded["command_skills"][0]["sound"], "command_skills/quick.mp3")


    def test_command_cd_notice_defaults_and_sound_prefix(self):
        config = {
            "command_skills": [
                {
                    "id": "quick",
                    "name": "Quick",
                    "cd_sound": "ready.mp3",
                }
            ]
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(config, tmp, ensure_ascii=False)
            tmp_path = tmp.name

        try:
            loaded = ConfigLoader.load_config(tmp_path)
        finally:
            os.unlink(tmp_path)

        skill = loaded["command_skills"][0]
        self.assertEqual(skill["cd_sound"], "command_skills/ready.mp3")
        self.assertEqual(skill["cd_threshold"], 0)
        self.assertFalse(skill["cd_flash"])


if __name__ == "__main__":
    unittest.main()
