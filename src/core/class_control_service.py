import time
from typing import Dict, Optional

from core.audio_manager import AudioManager
from core.group_controller import GroupController


class ClassControlService:
    def __init__(self, groups: Dict[str, GroupController], audio: AudioManager):
        self.groups = groups
        self.audio = audio

    def handle_gesture(self, group_id: str, gesture: str, player_id: Optional[object] = None) -> None:
        if group_id not in self.groups:
            return

        group = self.groups[group_id]
        is_muted = group.config.get('is_muted', False)
        is_independent_mode = (group.loop_mode == GroupController.MODE_INDEPENDENT)

        if gesture == 'strict_trigger':
            if not is_independent_mode:
                return
            pid = int(player_id) if player_id else 1
            sounds = group.trigger_independent(pid, time.time())
            self._play_sounds(sounds, AudioManager.CHANNEL_NORMAL)
            return

        if gesture == 'reset_independent':
            if not is_independent_mode:
                return
            pid = int(player_id) if player_id else 1
            group.reset_independent(pid)
            return

        if is_independent_mode:
            return

        if gesture == 'start':
            if group.state == GroupController.STATE_IDLE:
                group.start()
            return

        if gesture == 'resume':
            if group.state == GroupController.STATE_PAUSED:
                group.toggle_pause()
            return

        if gesture == 'single_tap':
            if group.state == GroupController.STATE_IDLE:
                group.start()
                return
            if group.state == GroupController.STATE_PAUSED:
                group.toggle_pause()
                return
            if group.state == GroupController.STATE_RUNNING:
                sounds = group.skip(time.time())
                if not is_muted:
                    self._play_sounds(sounds, AudioManager.CHANNEL_NORMAL)
                return

        if gesture == 'long_press':
            if group.state != GroupController.STATE_IDLE:
                group.stop()
            return

        if gesture == 'double_tap':
            if group.state in [GroupController.STATE_RUNNING, GroupController.STATE_PAUSED]:
                group.toggle_pause()
            return

        if gesture == 'skip_turn':
            if group.state == GroupController.STATE_RUNNING:
                sounds = group.skip(time.time())
                if not is_muted:
                    self._play_sounds(sounds, AudioManager.CHANNEL_NORMAL)
            return

        if gesture == 'skip_turn_consumed' and group.state == GroupController.STATE_RUNNING:
            sounds = group.skip_with_cooldown(time.time())
            if not is_muted:
                self._play_sounds(sounds, AudioManager.CHANNEL_SFX)

    def build_class_states(self, now: float):
        states = []
        for group in self.groups.values():
            sounds = group.update(now)
            if sounds and not group.config.get('is_muted', False):
                self._play_sounds(sounds, AudioManager.CHANNEL_NORMAL)
            states.append(group.get_ui_state(now))
        return states

    def stop_all_groups(self) -> None:
        for group in self.groups.values():
            if group.state != GroupController.STATE_IDLE:
                group.stop()

    def _play_sounds(self, sounds, channel: int) -> None:
        if not sounds:
            return
        for sound in sounds:
            self.audio.play(sound, channel)
