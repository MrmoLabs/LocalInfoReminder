import time
from typing import Dict


class UiStateBuilder:
    def build(self, *, time_manager, groups, command_manager, boss_manager, screen_monitor) -> Dict:
        now = time.time()
        return {
            'time_str': time_manager.get_formatted_time(),
            'classes': [group.get_ui_state(now) for group in groups.values()],
            'commands': command_manager.update(now),
            'boss_info': boss_manager.info,
            'ocr_active': not screen_monitor.paused if screen_monitor is not None else False,
        }
