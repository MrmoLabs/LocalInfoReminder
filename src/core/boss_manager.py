import time
from typing import Any, Dict, List, Optional, TypedDict

from core.config_loader import ConfigLoader
from core.logger import setup_logger


logger = setup_logger()


class BossWindow(TypedDict):
    id: str
    name: str
    start: int
    end: int


class BossInfo(TypedDict, total=False):
    active: bool
    name: str
    spawn_time: int
    spawn_str: str
    target_id: Optional[str]
    spawn_time_abs: int
    location: str
    kill_status: Optional[str]
    kill_detected_time: float
    buff_duration: int


class BossManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.notification_state: Dict[str, bool] = self._build_notification_state()
        self.info: BossInfo = {
            "active": False,
            "name": "",
            "spawn_time": 0,
            "spawn_str": "",
        }
        self.pending_kill_check_start_time = 0.0
        self.current_target_id: Optional[str] = None
        self.pending_kill_target_id: Optional[str] = None

    def _boss_detection_config(self) -> Dict[str, Any]:
        return ConfigLoader.normalize_boss_detection(
            self.config.get("boss_detection", {}),
            {},
        )

    def _targets(self) -> List[Dict[str, Any]]:
        return self._boss_detection_config().get("targets", [])

    def get_target_by_id(self, target_id: str) -> Optional[Dict[str, Any]]:
        target_id = str(target_id or "").strip()
        for target in self._targets():
            if str(target.get("id", "")).strip() == target_id:
                return target
        return None

    def get_target_by_name(self, boss_name: str) -> Optional[Dict[str, Any]]:
        normalized_name = str(boss_name or "")
        lowered = normalized_name.lower()
        for target in self._targets():
            aliases = list(target.get("match_names", [])) + list(target.get("ocr_keywords", [])) + [
                target.get("display_name", ""),
                target.get("id", ""),
            ]
            for alias in aliases:
                alias_text = str(alias or "").strip()
                if not alias_text:
                    continue
                if alias_text.lower() in lowered or alias_text in normalized_name:
                    return target
        return None

    def _get_time_windows(self, target: Dict[str, Any]) -> List[BossWindow]:
        parsed: List[BossWindow] = []
        for idx, window in enumerate(ConfigLoader._normalize_time_windows(target.get("time_windows", []))):
            start_seconds = ConfigLoader.parse_time_str(window.get("start", "00:00"))
            end_seconds = ConfigLoader.parse_time_str(window.get("end", "00:00"))
            if start_seconds < end_seconds:
                start_seconds, end_seconds = end_seconds, start_seconds
            parsed.append({
                "id": f"{target.get('id', 'target')}_window_{idx + 1}",
                "name": f"{target.get('display_name', target.get('id', 'target'))} window {idx + 1}",
                "start": start_seconds,
                "end": end_seconds,
            })
        return parsed

    def _build_notification_state(self) -> Dict[str, bool]:
        state: Dict[str, bool] = {}
        for target in self._targets():
            for window in self._get_time_windows(target):
                state[window["id"]] = False
        return state

    def _find_active_window(self, target: Dict[str, Any], current_seconds: int) -> Optional[BossWindow]:
        for window in self._get_time_windows(target):
            if window["end"] <= current_seconds <= window["start"]:
                return window
        return None

    def get_spawn_targets(self, current_seconds: int) -> List[Dict[str, Any]]:
        if not self.config.get("enable_boss_settings", True):
            return []

        available_targets: List[Dict[str, Any]] = []
        for target in self._targets():
            for window in self._get_time_windows(target):
                state_key = window["id"]
                if state_key not in self.notification_state:
                    self.notification_state[state_key] = False
                reset_threshold = window["start"] + 10
                if current_seconds > reset_threshold and self.notification_state.get(state_key):
                    logger.info(f"[BossManager] Resetting notification flag for {state_key}")
                    self.notification_state[state_key] = False
                    self.info["active"] = False

            active_window = self._find_active_window(target, current_seconds)
            if active_window and not self.notification_state.get(active_window["id"], False):
                available_targets.append(target)

        return available_targets

    def check_notification_windows(self, current_seconds: int) -> bool:
        return bool(self.get_spawn_targets(current_seconds))

    def predict_appearance(self, broadcast_time: int) -> int:
        start_t = broadcast_time - 60
        end_t = broadcast_time - 40

        best_target = start_t
        candidates = []
        for t in range(end_t, start_t - 1, -1):
            if t % 30 == 0:
                candidates.append(t)

        if candidates:
            best_target = candidates[0]
            logger.info(f"[BossManager] Prediction: broadcast {broadcast_time} -> target {best_target} (delay {broadcast_time - best_target}s)")
        else:
            logger.warning(f"[BossManager] Prediction failed: no XX:00/30 found in [{start_t}, {end_t}]. Using T-60.")
            best_target = start_t

        return best_target

    def _display_target_name(self, boss_name: str) -> str:
        target = self.get_target_by_name(boss_name)
        if target:
            display_name = target.get("display_name") or target.get("id") or ""
            return str(display_name)
        return boss_name or "\u672a\u77e5\u76ee\u6807"

    def get_active_target(self) -> Optional[Dict[str, Any]]:
        if self.current_target_id:
            return self.get_target_by_id(self.current_target_id)
        return None

    def handle_spawn_detected(self, boss_name: str, current_seconds: int):
        target = self.get_target_by_name(boss_name)
        logger.info(f"[BossManager] Event notification received: {self._display_target_name(boss_name)}")

        if target:
            active_window = self._find_active_window(target, current_seconds)
            if active_window:
                self.notification_state[active_window["id"]] = True
                logger.info(f"[BossManager] {active_window['name']} detected.")
            self.current_target_id = str(target.get("id", "") or "") or None
            self.pending_kill_target_id = str(target.get("id", "") or "") or None

        spawn_time_abs = self.predict_appearance(current_seconds)
        location_str = ""
        time_to_spawn = current_seconds - spawn_time_abs
        if time_to_spawn < 0:
            time_to_spawn = 0

        self.info.update({
            "active": True,
            "name": boss_name,
            "target_id": target.get("id") if target else None,
            "spawn_time_abs": spawn_time_abs,
            "spawn_time": time_to_spawn,
            "spawn_str": ConfigLoader.format_time_str(time_to_spawn),
            "location": location_str,
            "kill_status": None,
            "kill_detected_time": 0,
            "buff_duration": 0,
        })

        logger.info(f"[BossManager] Event info updated: {self._display_target_name(boss_name)} appearing at {spawn_time_abs} ({self.info['spawn_str']}) Loc: {location_str}")
        self.pending_kill_check_start_time = time.time() + time_to_spawn + 58
        return time_to_spawn

    def handle_kill_detected(self, faction: str, boss_name: str) -> int:
        target = self.get_target_by_name(boss_name) or self.get_active_target()
        buff_duration = 0
        if target:
            try:
                buff_duration = int(target.get("buff_duration", 0))
            except Exception:
                buff_duration = 0
            self.current_target_id = str(target.get("id", "") or "") or None

        logger.info(f"[BossManager] Event completed by {faction}: {self._display_target_name(boss_name)} - Duration: {buff_duration}s")
        self.pending_kill_check_start_time = 0
        self.pending_kill_target_id = None

        self.info.update({
            "active": True,
            "name": boss_name,
            "target_id": target.get("id") if target else None,
            "spawn_time": 0,
            "spawn_str": "",
            "kill_status": faction,
            "kill_detected_time": time.time(),
            "buff_duration": buff_duration,
        })

        return buff_duration

    def check_delayed_kill_enable(self):
        if self.pending_kill_check_start_time > 0:
            if time.time() >= self.pending_kill_check_start_time:
                logger.info("[BossManager] Executing delayed event completion check enable")
                self.pending_kill_check_start_time = 0.0
                return True
        return False

    def get_pending_kill_target(self) -> Optional[Dict[str, Any]]:
        if self.pending_kill_target_id:
            return self.get_target_by_id(self.pending_kill_target_id)
        return self.get_active_target()

    def get_kill_target_for_time(self, current_seconds: int) -> Optional[Dict[str, Any]]:
        pending = self.get_pending_kill_target()
        if pending:
            return pending

        for target in self._targets():
            if self._find_active_window(target, current_seconds):
                return target
        return None

    def get_spawn_sound(self, boss_name: str) -> str:
        target = self.get_target_by_name(boss_name)
        return str((target or {}).get("spawn_sound", "") or "")

    def get_kill_sound(self, boss_name: str) -> str:
        target = self.get_target_by_name(boss_name) or self.get_active_target()
        return str((target or {}).get("kill_sound", "") or "")

    def update_info_state(self, current_seconds: int):
        if not self.info["active"]:
            return

        if "spawn_time_abs" in self.info:
            time_to_spawn = current_seconds - int(self.info["spawn_time_abs"])
            self.info["spawn_time"] = time_to_spawn

            if time_to_spawn > 0:
                self.info["spawn_str"] = ConfigLoader.format_time_str(time_to_spawn)
            else:
                self.info["spawn_str"] = ""

        if self.info.get("kill_status"):
            kill_time = float(self.info.get("kill_detected_time", 0.0))
            buff_dur = int(self.info.get("buff_duration", 0))
            if (time.time() - kill_time) > buff_dur:
                logger.info("[BossManager] Auto-hiding event info (duration expired)")
                self.info["active"] = False
        else:
            if "spawn_time_abs" in self.info:
                if (int(self.info["spawn_time_abs"]) - current_seconds) > 240:
                    logger.info("[BossManager] Auto-hiding event info (4 mins post-appearance timeout)")
                    self.info["active"] = False
