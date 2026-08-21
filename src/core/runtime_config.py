from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class RuntimeConfig:
    start_seconds: int
    # class_id: {"count": int, "loop_mode": str}
    # loop_mode: "loop" or "once"
    class_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    show_ally_panel: bool = True
    show_command_monitor: bool = True
