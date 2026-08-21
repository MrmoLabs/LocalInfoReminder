import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.verify_release_version import verify


class TestReleasePackaging(unittest.TestCase):
    def test_release_tag_matches_project_version(self):
        self.assertEqual(verify("v1.0.0"), "1.0.0")

    def test_invalid_release_tag_is_rejected(self):
        with self.assertRaises(ValueError):
            verify("1.0.0")


if __name__ == "__main__":
    unittest.main()
