import os
import sys
import types
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import main


class TestMainOcrPreload(unittest.TestCase):
    def test_preload_imports_rapidocr_on_main_thread(self):
        fake_ort = types.ModuleType("onnxruntime")
        fake_rapid = types.ModuleType("rapidocr_onnxruntime")
        fake_rapid.RapidOCR = object

        with patch('core.vision.performance.ensure_onnxruntime_dll_search_paths'), \
             patch('core.vision.performance.preload_onnxruntime_native_binaries'), \
             patch('core.vision.performance.apply_rapidocr_runtime_limits'), \
             patch.dict(sys.modules, {
                 'onnxruntime': fake_ort,
                 'rapidocr_onnxruntime': fake_rapid,
             }, clear=False):
            self.assertTrue(main.preload_ocr_runtime())


if __name__ == "__main__":
    unittest.main()
