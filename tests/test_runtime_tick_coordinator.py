import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.audio_manager import AudioManager
from core.runtime_tick_coordinator import RuntimeTickCoordinator


class TestRuntimeTickCoordinator(unittest.TestCase):
    def _make_coordinator(self):
        return RuntimeTickCoordinator(
            input_manager=MagicMock(),
            time_manager=MagicMock(),
            boss_manager=MagicMock(),
            class_control_service=MagicMock(),
            command_manager=MagicMock(),
            audio=MagicMock(spec=AudioManager),
            screen_monitor=MagicMock(),
            config={'enable_global_events': True, 'global_events': []},
            auto_sync_interval=60.0,
            last_time_check=100.0,
            last_auto_sync_time=0.0,
            trigger_time_sync=MagicMock(),
            emit_time_update=MagicMock(),
            emit_state=MagicMock(),
        )

    def test_process_tick_triggers_auto_sync_and_emits_state(self):
        coordinator = self._make_coordinator()
        coordinator.time_manager.update.return_value = None
        coordinator.boss_manager.info = {'active': False}
        coordinator.boss_manager.get_spawn_targets.return_value = []
        coordinator.boss_manager.check_delayed_kill_enable.return_value = False

        coordinator.process_tick(now=200.0)

        coordinator.trigger_time_sync.assert_called_once_with(True)
        coordinator.input_manager.poll_holds.assert_called_once_with(200.0)
        coordinator.class_control_service.build_class_states.assert_called_once_with(200.0)
        coordinator.screen_monitor.set_boss_check_enabled.assert_called_once_with(False, [])
        coordinator.emit_state.assert_called_once_with(False)

    def test_process_tick_plays_global_event_audio(self):
        coordinator = self._make_coordinator()
        coordinator.config = {
            'enable_global_events': True,
            'global_events': [
                {'time': '12:34', 'name': 'Event', 'sound': 'global.mp3', 'is_enabled': True, 'is_muted': False},
            ],
        }
        coordinator.time_manager.update.return_value = '12:34'
        coordinator.time_manager.current_seconds = 100
        coordinator.boss_manager.info = {'active': False}
        coordinator.boss_manager.get_spawn_targets.return_value = [{'id': 'boss_a'}]
        coordinator.boss_manager.check_delayed_kill_enable.return_value = True
        coordinator.boss_manager.get_kill_target_for_time.return_value = {'id': 'boss_a'}

        coordinator.process_tick(now=120.0)

        coordinator.emit_time_update.assert_called_once_with('12:34')
        coordinator.audio.play.assert_called_once_with('global.mp3', AudioManager.CHANNEL_HIGH)
        coordinator.screen_monitor.set_boss_check_enabled.assert_called_once_with(True, [{'id': 'boss_a'}])
        coordinator.screen_monitor.set_boss_kill_check_enabled.assert_called_once_with(True, {'id': 'boss_a'})

if __name__ == '__main__':
    unittest.main()
