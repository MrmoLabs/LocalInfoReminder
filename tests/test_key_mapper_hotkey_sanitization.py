import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.input.key_mapper import KeyMapper


class TestKeyMapperHotkeySanitization(unittest.TestCase):
    def test_placeholder_hotkeys_are_ignored(self):
        mapper = KeyMapper({
            "enable_classes": True,
            "enable_command_skills": True,
            "enable_miracle_skills": True,
            "classes_template": [
                {
                    "id": "wind_wall",
                    "name": "风墙循环",
                    "default_hotkey": "Click to Set",
                    "skip_cd_hotkey": "Recording...",
                    "independent_hotkeys": ["num_1", "Click to Set", ""],
                }
            ],
            "command_skills": [
                {
                    "id": "quick_step",
                    "name": "主要条目A",
                    "default_hotkey": "Click to Set",
                }
            ],
            "miracle_skills": [
                {
                    "id": "spirit_vision",
                    "name": "扩展条目A",
                    "default_hotkey": " alt ",
                }
            ],
        })

        self.assertEqual(
            mapper.keypad_map,
            {
                "num_1": [{"cid": "wind_wall", "type": "strict_trigger", "pid": 1}],
            },
        )
        self.assertEqual(mapper.skip_map, {})
        self.assertEqual(set(mapper.skill_map.keys()), {"alt"})


if __name__ == "__main__":
    unittest.main()
