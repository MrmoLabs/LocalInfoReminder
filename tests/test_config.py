import unittest
import sys
import os
from pathlib import Path

# Add src to path so we can import ConfigLoader
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.config_loader import ConfigLoader

class TestConfigLoader(unittest.TestCase):
    def test_time_conversion(self):
        self.assertEqual(ConfigLoader.parse_time_str("20:00"), 1200)
        self.assertEqual(ConfigLoader.parse_time_str("00:30"), 30)
        self.assertEqual(ConfigLoader.parse_time_str("01:01"), 61)
        
        self.assertEqual(ConfigLoader.format_time_str(1200), "20:00")
        self.assertEqual(ConfigLoader.format_time_str(30), "00:30")
        self.assertEqual(ConfigLoader.format_time_str(61), "01:01")

    def test_load_config(self):
        config = ConfigLoader.load_config()
        self.assertIsNotNone(config)
        self.assertIn("global_events", config)
        self.assertIn("classes_template", config)
        self.assertIn("command_skills", config)
        self.assertIn("boss_detection", config)
        self.assertIn("targets", config["boss_detection"])
        
        found_event = any(
            event["time"] == "20:20" and event["name"] == "野怪刷新"
            for event in config["global_events"]
        )
        self.assertTrue(found_event, "Could not find expected 20:20 event")


    def test_primary_entry_alias_roundtrip(self):
        import json
        import tempfile

        payload = {
            "primary_entries": [{"id": "A", "name": "主条目A"}],
            "extended_entries": [{"id": "B", "name": "扩展条目B"}],
            "enable_primary_entries": False,
            "enable_extended_entries": True,
            "ocr_primary_entries": False
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(payload, tmp, ensure_ascii=False)
            load_path = tmp.name

        try:
            loaded = ConfigLoader.load_config(load_path)
            self.assertIn("command_skills", loaded)
            self.assertIn("miracle_skills", loaded)
            self.assertFalse(loaded["enable_command_skills"])
            self.assertTrue(loaded["enable_miracle_skills"])
            self.assertFalse(loaded["ocr_command_skills"])

            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as out_tmp:
                save_path = out_tmp.name

            try:
                self.assertTrue(ConfigLoader.save_config(loaded, save_path))
                saved = json.loads(Path(save_path).read_text(encoding="utf-8"))
                self.assertIn("primary_entries", saved)
                self.assertIn("extended_entries", saved)
                self.assertIn("enable_primary_entries", saved)
                self.assertIn("enable_extended_entries", saved)
                self.assertIn("ocr_primary_entries", saved)
                self.assertNotIn("command_skills", saved)
                self.assertNotIn("miracle_skills", saved)
                cached = ConfigLoader.get_config()
                self.assertIn("command_skills", cached)
                self.assertIn("miracle_skills", cached)
                self.assertFalse(cached["enable_command_skills"])
            finally:
                os.unlink(save_path)
        finally:
            os.unlink(load_path)

    def test_atomic_save_preserves_original_when_replace_fails(self):
        import tempfile
        from unittest.mock import patch

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write('{"original": true}')
            save_path = tmp.name

        try:
            with patch("core.config_loader.os.replace", side_effect=OSError("replace failed")):
                self.assertFalse(ConfigLoader.save_config({"replacement": True}, save_path))
            self.assertEqual(Path(save_path).read_text(encoding="utf-8"), '{"original": true}')
            leftovers = list(Path(save_path).parent.glob(f".{Path(save_path).name}.*.tmp"))
            self.assertEqual(leftovers, [])
        finally:
            os.unlink(save_path)

if __name__ == '__main__':
    unittest.main()
