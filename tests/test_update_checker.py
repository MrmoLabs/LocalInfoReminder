import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from core.update_checker import (
    UpdateCheckError,
    check_github_update,
    is_newer_version,
    load_update_config,
    parse_version,
)
from core.version import __version__


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, *_args, **_kwargs):
        return json.dumps(self.payload).encode("utf-8")


class TestUpdateChecker(unittest.TestCase):
    def test_version_comparison(self):
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))
        self.assertTrue(is_newer_version("v1.0.1", "1.0.0"))
        self.assertFalse(is_newer_version("v1.0.0", "1.0.0"))
        self.assertFalse(is_newer_version("v0.9.9", "1.0.0"))

    def test_invalid_version_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_version("latest")

    def test_empty_repository_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "update_config.json")
            with open(path, "w", encoding="utf-8") as stream:
                json.dump({"github_repository": ""}, stream)
            with self.assertRaises(UpdateCheckError):
                load_update_config(path)

    @patch("core.update_checker.urllib.request.urlopen")
    def test_latest_release_is_parsed(self, mock_urlopen):
        mock_urlopen.return_value = _Response(
            {
                "tag_name": "v1.2.0",
                "name": "Version 1.2.0",
                "body": "Changes",
                "html_url": "https://github.com/example/project/releases/tag/v1.2.0",
            }
        )
        result = check_github_update("example/project", "1.0.0")
        self.assertTrue(result.update_available)
        self.assertEqual(result.latest_version, "1.2.0")

    def test_source_version_matches_project_metadata(self):
        import tomllib

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        with open(os.path.join(project_root, "pyproject.toml"), "rb") as stream:
            metadata = tomllib.load(stream)
        self.assertEqual(__version__, metadata["project"]["version"])


if __name__ == "__main__":
    unittest.main()
