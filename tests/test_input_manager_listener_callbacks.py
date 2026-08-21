import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.input_manager import InputManager


class TestInputManagerListenerCallbacks(unittest.TestCase):
    def test_listener_direct_callbacks_are_wired(self):
        manager = InputManager({
            "enable_classes": False,
            "enable_command_skills": False,
            "enable_miracle_skills": False,
        })

        self.assertEqual(manager.listener.on_key_pressed.__func__, manager._on_press.__func__)
        self.assertIs(manager.listener.on_key_pressed.__self__, manager)
        self.assertEqual(manager.listener.on_key_released.__func__, manager._on_release.__func__)
        self.assertIs(manager.listener.on_key_released.__self__, manager)
        self.assertEqual(manager.listener.on_global_hotkey.__func__, manager._on_global_hotkey.__func__)
        self.assertIs(manager.listener.on_global_hotkey.__self__, manager)

    def test_direct_global_callback_dispatches_without_listener_qt_signal(self):
        manager = InputManager({
            "enable_classes": False,
            "enable_command_skills": False,
            "enable_miracle_skills": False,
        })
        events = []
        manager.overlay_toggled.connect(lambda: events.append("overlay"))

        manager.listener.on_global_hotkey("overlay")

        self.assertEqual(events, ["overlay"])


if __name__ == "__main__":
    unittest.main()
