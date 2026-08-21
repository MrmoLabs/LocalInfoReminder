"""Read-only GitHub Releases update checks."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.version import __version__
from utils.resource_path import get_resource_path


_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


class UpdateCheckError(RuntimeError):
    """Raised when update metadata cannot be loaded or understood."""


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_name: str
    release_notes: str
    release_url: str
    update_available: bool


def parse_version(value: str) -> tuple[int, int, int]:
    match = _VERSION_RE.fullmatch((value or "").strip())
    if not match:
        raise ValueError(f"Unsupported version: {value!r}")
    return tuple(int(part) for part in match.groups())


def is_newer_version(candidate: str, current: str = __version__) -> bool:
    return parse_version(candidate) > parse_version(current)


def load_update_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else Path(get_resource_path("update_config.json"))
    try:
        with path.open("r", encoding="utf-8-sig") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateCheckError(f"无法读取更新配置：{exc}") from exc

    repository = str(data.get("github_repository", "")).strip().strip("/")
    if not repository or repository.count("/") != 1:
        raise UpdateCheckError("尚未配置 GitHub 仓库，请在 update_config.json 中填写 owner/repo。")
    return {**data, "github_repository": repository}


def check_github_update(
    repository: str,
    current_version: str = __version__,
    timeout: float = 8.0,
) -> UpdateInfo:
    api_url = f"https://api.github.com/repos/{repository}/releases/latest"
    request = urllib.request.Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"LocalInfoReminder/{current_version}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateCheckError("GitHub 仓库不存在，或尚未发布正式 Release。") from exc
        raise UpdateCheckError(f"GitHub 返回 HTTP {exc.code}。") from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise UpdateCheckError(f"无法连接 GitHub：{exc}") from exc

    tag_name = str(payload.get("tag_name", "")).strip()
    try:
        latest_version = ".".join(str(part) for part in parse_version(tag_name))
    except ValueError as exc:
        raise UpdateCheckError(f"Release 标签不是支持的版本号：{tag_name or '(空)'}") from exc

    release_url = str(payload.get("html_url", "")).strip()
    if not release_url.startswith("https://github.com/"):
        raise UpdateCheckError("GitHub Release 没有有效的页面地址。")

    return UpdateInfo(
        current_version=current_version,
        latest_version=latest_version,
        release_name=str(payload.get("name") or tag_name),
        release_notes=str(payload.get("body") or ""),
        release_url=release_url,
        update_available=is_newer_version(latest_version, current_version),
    )
