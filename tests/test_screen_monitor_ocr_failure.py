import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.screen_monitor import ScreenMonitor


class TestScreenMonitorOcrFailure(unittest.TestCase):
    def test_ocr_init_failure_is_sticky_for_session(self):
        monitor = ScreenMonitor()
        monitor.config = {}

        with patch('core.screen_monitor.ensure_onnxruntime_dll_search_paths'), \
             patch('core.screen_monitor.preload_onnxruntime_native_binaries', side_effect=OSError(1114, 'dll init failed')), \
             patch('core.screen_monitor.apply_rapidocr_runtime_limits') as apply_limits:
            self.assertFalse(monitor._ensure_components())
            self.assertTrue(monitor.ocr_init_failed)
            self.assertFalse(monitor._ensure_components())
            apply_limits.assert_not_called()


if __name__ == "__main__":
    unittest.main()
