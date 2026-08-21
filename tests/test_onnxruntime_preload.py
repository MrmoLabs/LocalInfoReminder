import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.vision.performance import preload_onnxruntime_native_binaries


class TestOnnxruntimePreload(unittest.TestCase):
    def test_preload_is_skipped_in_source_mode_on_windows(self):
        with patch('core.vision.performance.os.name', 'nt'), \
             patch('core.vision.performance.sys.frozen', False, create=True), \
             patch('core.vision.performance.ctypes.WinDLL') as win_dll:
            preload_onnxruntime_native_binaries()
            win_dll.assert_not_called()


if __name__ == "__main__":
    unittest.main()
