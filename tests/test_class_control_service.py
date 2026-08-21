import os
import sys
import time
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.audio_manager import AudioManager
from core.class_control_service import ClassControlService
from core.group_controller import GroupController


class TestClassControlService(unittest.TestCase):
    def _make_service(self):
        group = MagicMock()
        group.config = {'is_muted': False}
        group.loop_mode = 'loop'
        group.state = GroupController.STATE_IDLE
        audio = MagicMock(spec=AudioManager)
        service = ClassControlService({'g1': group}, audio)
        return service, group, audio

    def test_single_tap_starts_idle_group(self):
        service, group, _ = self._make_service()

        service.handle_gesture('g1', 'single_tap')

        group.start.assert_called_once()

    def test_skip_turn_consumed_plays_sfx(self):
        service, group, audio = self._make_service()
        group.state = GroupController.STATE_RUNNING
        group.skip_with_cooldown.return_value = ['a.mp3']

        service.handle_gesture('g1', 'skip_turn_consumed')

        group.skip_with_cooldown.assert_called_once()
        audio.play.assert_called_once_with('a.mp3', AudioManager.CHANNEL_SFX)

    def test_build_class_states_updates_groups_and_returns_states(self):
        service, group, audio = self._make_service()
        group.update.return_value = ['a.mp3']
        group.get_ui_state.return_value = {'id': 'g1'}

        states = service.build_class_states(time.time())

        self.assertEqual(states, [{'id': 'g1'}])
        audio.play.assert_called_once_with('a.mp3', AudioManager.CHANNEL_NORMAL)
