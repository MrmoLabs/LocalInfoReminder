import sys
from typing import TypedDict, List, Optional, Any

class TimeConstants:
    # Scheduler Defaults
    DEFAULT_BUFF_DURATION = 5.0
    DEFAULT_SKILL_COOLDOWN = 20.0
    SKIP_PENALTY_DURATION = 10.0
    
    # Tick Rates
    LOGIC_TICK_MS = 30
    SCREEN_MONITOR_INTERVAL = 0.5
    
    # Auto Sync
    AUTO_SYNC_INTERVAL = 60.0
    SYNC_MAX_DEVIATION = 10  # Seconds

class FilePaths:
    # Configuration
    CONFIG_JSON = "config.json"
    LAUNCHER_STATE = "state/launcher_state.json"
    DEV_CONFIG = "state/dev_config.json"
    LOGS_DIR = "logs"
    
    # Assets
    ASSETS_DIR = "assets"
    ICON_FILE = "LocalInfoReminder.ico"

class UIConstants:
    # Overlay
    DEFAULT_WIDTH = 360
    DEFAULT_HEIGHT = 420
    MIN_WIDTH = 180
    MIN_HEIGHT = 80
    
    # Colors (RGBA)
    BG_ALPHA_DEFAULT = 220
    BG_ALPHA_TRANSPARENT = 5
    
class AudioFiles:
    DRAGON_SPAWN = "dragon_spawn.mp3"
    PREPARE = "prepare.mp3"
    CANCEL = "cancel.mp3"


def allow_dev_config_overrides() -> bool:
    return not getattr(sys, 'frozen', False)

# --- Type Definitions for State Safety ---
class EnemyState(TypedDict):
    name: str
    remaining: float
    total_duration: float
    state: str # 'ACTIVE', 'COOLDOWN', 'READY'
    type: str # 'command', 'miracle'
    flash_threshold: float

class ClassState(TypedDict):
    id: str
    name: str # 'Display Name'
    state: str # 'IDLE', 'RUNNING', 'PAUSED'
    remaining_time: float # for current turn

class BossInfo(TypedDict, total=False):
    active: bool
    spawn_str: str # MM:SS
    kill_status: Optional[str] # 'ally' or 'enemy'
    kill_detected_time: float
    buff_duration: float

class GameState(TypedDict, total=False):
    """
    Defines the structure of the UI update payload.
    Keys are optional because updates can be partial.
    """
    time_str: str
    enemies: List[EnemyState]
    classes: List[ClassState]
    boss_info: BossInfo
