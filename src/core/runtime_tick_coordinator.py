import time
from typing import Callable, Dict, Optional

from core.audio_manager import AudioManager
from core.logger import setup_logger

logger = setup_logger()


class RuntimeTickCoordinator:
    def __init__(
        self,
        *,
        input_manager,
        time_manager,
        boss_manager,
        class_control_service,
        command_manager,
        audio: AudioManager,
        screen_monitor=None,
        config: Optional[Dict] = None,
        auto_sync_interval: float,
        last_time_check: float,
        last_auto_sync_time: float,
        trigger_time_sync: Callable[[bool], None],
        emit_time_update: Callable[[str], None],
        emit_state: Callable[[bool], None],
    ):
        self.input_manager = input_manager
        self.time_manager = time_manager
        self.boss_manager = boss_manager
        self.class_control_service = class_control_service
        self.command_manager = command_manager
        self.audio = audio
        self.screen_monitor = screen_monitor
        self.config = config or {}
        self.auto_sync_interval = auto_sync_interval
        self.last_time_check = last_time_check
        self.last_auto_sync_time = last_auto_sync_time
        self.trigger_time_sync = trigger_time_sync
        self.emit_time_update = emit_time_update
        self.emit_state = emit_state

    def update_config(self, config: Dict) -> None:
        self.config = config

    def process_tick(self, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else now

        self.input_manager.poll_holds(now)

        delta = now - self.last_time_check
        self.last_time_check = now

        if now - self.last_auto_sync_time > self.auto_sync_interval:
            self.trigger_time_sync(True)
            self.last_auto_sync_time = now

        self._update_boss_checks()
        self._update_time(delta)
        self.class_control_service.build_class_states(now)

        if self.boss_manager.info['active']:
            self.boss_manager.update_info_state(self.time_manager.current_seconds)

        for sound_file in self.command_manager.collect_due_audio_notifications(now):
            self.audio.play(sound_file, AudioManager.CHANNEL_SFX)

        self.emit_state(False)
        return True

    def _update_boss_checks(self) -> None:
        if self.screen_monitor is None:
            return

        spawn_targets = self.boss_manager.get_spawn_targets(self.time_manager.current_seconds)
        self.screen_monitor.set_boss_check_enabled(bool(spawn_targets), spawn_targets)

        if self.boss_manager.check_delayed_kill_enable():
            self.screen_monitor.set_boss_kill_check_enabled(
                True,
                self.boss_manager.get_kill_target_for_time(self.time_manager.current_seconds),
            )

    def _update_time(self, delta: float) -> None:
        time_str = self.time_manager.update(delta)
        if not time_str:
            return

        self.emit_time_update(time_str)

        if not self.config.get('enable_global_events', True):
            return

        for event in self.config.get('global_events', []):
            if not event.get('is_enabled', True):
                continue
            if event.get('time') != time_str:
                continue

            logger.info(f"[RuntimeTickCoordinator] Global Event: {event.get('name')}")
            sound_file = event.get('sound', '')
            if sound_file and not event.get('is_muted', False):
                self.audio.play(sound_file, AudioManager.CHANNEL_HIGH)
            break
