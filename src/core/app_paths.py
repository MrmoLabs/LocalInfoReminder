import os
import sys
from pathlib import Path


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    return ensure_dir(app_base_dir() / "logs")


def state_dir() -> Path:
    return ensure_dir(app_base_dir() / "state")


def state_file_path(filename: str) -> str:
    return os.fspath(state_dir() / filename)


def legacy_root_file_path(filename: str) -> str:
    return os.fspath(app_base_dir() / filename)


def preferred_state_path(filename: str) -> str:
    return state_file_path(filename)


def existing_state_path(filename: str) -> str:
    preferred = preferred_state_path(filename)
    if os.path.exists(preferred):
        return preferred
    legacy = legacy_root_file_path(filename)
    return legacy if os.path.exists(legacy) else preferred


def log_subdir(name: str) -> Path:
    return ensure_dir(logs_dir() / name)


def runtime_log_path(filename: str = "debug.log") -> str:
    return os.fspath(log_subdir("runtime") / filename)


def match_summary_path(filename: str = "match_summary.md") -> str:
    return os.fspath(logs_dir() / filename)


def build_log_path(filename: str) -> str:
    return os.fspath(log_subdir("build") / filename)
