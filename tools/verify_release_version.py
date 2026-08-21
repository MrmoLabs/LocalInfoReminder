"""Validate that a release tag matches every application version source."""

from __future__ import annotations

import argparse
import ast
import re
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")


def source_version() -> str:
    module = ast.parse((PROJECT_ROOT / "src/core/version.py").read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    value = ast.literal_eval(node.value)
                    if isinstance(value, str):
                        return value
    raise RuntimeError("src/core/version.py does not define a string __version__")


def project_version() -> str:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def verify(tag: str) -> str:
    match = TAG_RE.fullmatch(tag.strip())
    if not match:
        raise ValueError("Release tag must use the form v1.2.3")
    tag_version = match.group(1)
    versions = {
        "Git tag": tag_version,
        "pyproject.toml": project_version(),
        "src/core/version.py": source_version(),
    }
    if len(set(versions.values())) != 1:
        details = ", ".join(f"{name}={value}" for name, value in versions.items())
        raise ValueError(f"Release versions do not match: {details}")
    return tag_version


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag")
    args = parser.parse_args()
    print(verify(args.tag))


if __name__ == "__main__":
    main()
