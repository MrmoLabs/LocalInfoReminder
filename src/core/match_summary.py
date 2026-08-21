import os
import sys
import threading
from datetime import datetime
from typing import Optional

from core.app_paths import match_summary_path
from core.config_loader import ConfigLoader


class MatchSummaryWriter:
    def __init__(
        self,
        output_path: Optional[str] = None,
        split_threshold_seconds: int = 300,
        boss_targets: Optional[list] = None,
    ):
        self.output_path = output_path or self._default_output_path()
        self.split_threshold_seconds = split_threshold_seconds
        self.boss_targets = boss_targets or ConfigLoader.default_boss_targets()
        self._lock = threading.RLock()
        self._last_countdown_seconds: Optional[int] = None
        self._match_index = 0
        self._pending_new_match = False
        self._current_match_started = False

    def update_countdown(self, countdown_seconds: int) -> None:
        with self._lock:
            current = max(0, int(countdown_seconds))
            if (
                self._current_match_started
                and self._last_countdown_seconds is not None
                and current - self._last_countdown_seconds >= self.split_threshold_seconds
            ):
                self._pending_new_match = True
            self._last_countdown_seconds = current

    def record_boss_spawn(
        self,
        boss_name: str,
        countdown_seconds: int,
        predicted_seconds: Optional[int],
        detected_at: Optional[datetime] = None,
    ) -> None:
        detected_at = detected_at or datetime.now()
        with self._lock:
            self.update_countdown(countdown_seconds)
            self._ensure_match_started(detected_at)
            display_name = self._boss_display_name(boss_name)
            category = self._boss_category(boss_name)
            self._append_row(
                category=category,
                event="\u4e8b\u4ef6\u63d0\u793a",
                target=display_name,
                faction="-",
                countdown=self._format_countdown(countdown_seconds),
                source="OCR",
                real_time=self._format_wall_time(detected_at),
            )
            predicted_time = self._format_countdown(predicted_seconds)
            if predicted_time:
                self._append_row(
                    category=category,
                    event="\u4e8b\u4ef6\u51fa\u73b0",
                    target=display_name,
                    faction="-",
                    countdown=predicted_time,
                    source="\u9884\u6d4b",
                    real_time=self._format_wall_time(detected_at),
                )

    def record_boss_kill(
        self,
        boss_name: str,
        faction: str,
        countdown_seconds: int,
        detected_at: Optional[datetime] = None,
    ) -> None:
        detected_at = detected_at or datetime.now()
        with self._lock:
            self.update_countdown(countdown_seconds)
            self._ensure_match_started(detected_at)
            self._append_row(
                category=self._boss_category(boss_name),
                event="\u4e8b\u4ef6\u5b8c\u6210",
                target=self._boss_display_name(boss_name),
                faction=self._format_faction(faction),
                countdown=self._format_countdown(countdown_seconds),
                source="OCR",
                real_time=self._format_wall_time(detected_at),
            )

    def record_command_skill(
        self,
        skill_name: str,
        countdown_seconds: int,
        source: str,
        faction: str = "-",
        detected_at: Optional[datetime] = None,
    ) -> None:
        detected_at = detected_at or datetime.now()
        with self._lock:
            self.update_countdown(countdown_seconds)
            self._ensure_match_started(detected_at)
            self._append_row(
                category="\u4e3b\u6280\u80fd",
                event="\u4f7f\u7528",
                target=skill_name,
                faction=faction,
                countdown=self._format_countdown(countdown_seconds),
                source=source,
                real_time=self._format_wall_time(detected_at),
            )

    def _ensure_match_started(self, detected_at: datetime) -> None:
        if self._current_match_started and not self._pending_new_match:
            return

        self._match_index += 1
        self._current_match_started = True
        self._pending_new_match = False

        file_exists = os.path.exists(self.output_path)
        self._ensure_parent_dir()
        with open(self.output_path, "a", encoding="utf-8", newline="\n") as handle:
            if not file_exists:
                handle.write("# \u5bf9\u5c40\u5173\u952e\u4fe1\u606f\u6c47\u603b\n\n")
            else:
                handle.write("\n")
            handle.write(
                f"## \u5bf9\u5c40 {self._match_index} "
                f"(\u5f00\u59cb\u65f6\u95f4 {self._format_wall_time(detected_at)})\n\n"
            )
            handle.write(
                "| \u7c7b\u522b | \u4e8b\u4ef6 | \u76ee\u6807 | \u5f52\u5c5e | \u672c\u5c40\u5012\u8ba1\u65f6 | \u6765\u6e90 | \u771f\u5b9e\u65f6\u95f4 |\n"
            )
            handle.write(
                "| --- | --- | --- | --- | --- | --- | --- |\n"
            )

    def _append_row(
        self,
        *,
        category: str,
        event: str,
        target: str,
        faction: str,
        countdown: str,
        source: str,
        real_time: str,
    ) -> None:
        self._ensure_parent_dir()
        values = [category, event, target, faction, countdown, source, real_time]
        row = "| " + " | ".join(self._escape_cell(value) for value in values) + " |\n"
        with open(self.output_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(row)

    def _ensure_parent_dir(self) -> None:
        parent = os.path.dirname(self.output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def _default_output_path(self) -> str:
        return match_summary_path()

    def _format_countdown(self, countdown_seconds: Optional[int]) -> str:
        if countdown_seconds is None:
            return ""
        return ConfigLoader.format_time_str(max(0, int(countdown_seconds)))

    def _format_wall_time(self, detected_at: datetime) -> str:
        return detected_at.strftime("%Y-%m-%d %H:%M:%S")

    def _find_target(self, boss_name: str):
        normalized_name = str(boss_name or "")
        lowered = normalized_name.lower()
        for target in self.boss_targets:
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

    def _boss_category(self, boss_name: str) -> str:
        target = self._find_target(boss_name)
        if target:
            return target.get("display_name", target.get("id", ""))
        return "\u76ee\u6807\u4e8b\u4ef6"

    def _boss_display_name(self, boss_name: str) -> str:
        target = self._find_target(boss_name)
        if target:
            return target.get("display_name", target.get("id", ""))
        return boss_name or "\u672a\u77e5\u76ee\u6807"

    def _format_faction(self, faction: str) -> str:
        if faction == "ally":
            return "\u672c\u65b9"
        if faction == "enemy":
            return "\u5bf9\u65b9"
        if faction in {"unknown", "ignore", "none"}:
            return "-"
        return faction or "-"

    def _escape_cell(self, value: str) -> str:
        text = str(value or "").replace("\r", " ").replace("\n", "<br>")
        return text.replace("|", "\\|")
