import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.ui_state_builder import UiStateBuilder


class TestUiStateBuilder(unittest.TestCase):
    def test_build_returns_expected_payload(self):
        builder = UiStateBuilder()
        group = MagicMock()
        group.get_ui_state.return_value = {'id': 'g1'}
        command_manager = MagicMock()
        command_manager.update.return_value = [{'id': 'c1'}]
        boss_manager = MagicMock()
        boss_manager.info = {'active': True}
        time_manager = MagicMock()
        time_manager.get_formatted_time.return_value = '12:34'
        screen_monitor = MagicMock()
        screen_monitor.paused = False

        with patch('core.ui_state_builder.time.time', return_value=100.0):
            payload = builder.build(
                time_manager=time_manager,
                groups={'g1': group},
                command_manager=command_manager,
                boss_manager=boss_manager,
                screen_monitor=screen_monitor,
            )

        self.assertEqual(payload['time_str'], '12:34')
        self.assertEqual(payload['classes'], [{'id': 'g1'}])
        self.assertEqual(payload['commands'], [{'id': 'c1'}])
        self.assertTrue(payload['ocr_active'])
