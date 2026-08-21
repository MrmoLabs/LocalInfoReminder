import os
import sys
import unittest
from unittest.mock import MagicMock

from PyQt6.QtCore import QRecursiveMutex

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.logic_engine import LogicEngine


class TestLogicEngineDebugGates(unittest.TestCase):
    def _make_engine(self, enabled):
        engine = LogicEngine.__new__(LogicEngine)
        engine.enable_debug_hotkeys = enabled
        engine.mutex = QRecursiveMutex()
        engine.screen_monitor = MagicMock()
        return engine

    def test_debug_triggers_are_blocked_when_dev_flag_disabled(self):
        engine = self._make_engine(False)

        engine.trigger_debug_screenshot()
        engine.trigger_boss_debug()
        engine.trigger_prep_debug()

        engine.screen_monitor.trigger_debug_capture.assert_not_called()
        engine.screen_monitor.trigger_debug_boss_capture.assert_not_called()
        engine.screen_monitor.trigger_debug_prep_capture.assert_not_called()

    def test_debug_triggers_work_when_dev_flag_enabled(self):
        engine = self._make_engine(True)

        engine.trigger_debug_screenshot()
        engine.trigger_boss_debug()
        engine.trigger_prep_debug()

        engine.screen_monitor.trigger_debug_capture.assert_called_once()
        engine.screen_monitor.trigger_debug_boss_capture.assert_called_once()
        engine.screen_monitor.trigger_debug_prep_capture.assert_called_once()


if __name__ == '__main__':
    unittest.main()
