import unittest
from unittest.mock import MagicMock, patch
import os
import subprocess
import sys

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    from core.logic_engine import LogicEngine
except ImportError:
    # Handle the case where imports fail due to missing dlls or other env issues
    LogicEngine = None

class TestSmoke(unittest.TestCase):
    """
    Golden Path / Smoke Tests.
    Ensures the core application components can at least be instantiated
    and perform basic operations without crashing.
    """

    def setUp(self):
        if LogicEngine is None:
            self.fail("Could not import LogicEngine. Check environment/PYTHONPATH.")

        # Mock dependencies that might require UI or Hardware
        self.mock_config = {
            "classes_template": [{"id": "test_class", "name": "Test Class", "default_hotkey": "F1"}],
            "global_events": [],
            "command_skills": [],
            "miracle_skills": [],
            "ocr_time_sync": False,
            "enable_classes": True
        }

    @patch('core.logic_engine.ConfigLoader')
    def test_logic_engine_initialization(self, mock_loader):
        """
        Test that LogicEngine initializes correctly with valid config.
        """
        # Setup Mocks
        mock_loader_instance = mock_loader.return_value
        mock_loader_instance.load_config.return_value = self.mock_config
        
        # Instantiate
        engine = LogicEngine(self.mock_config)
        
        # Check basic state
        self.assertIsNotNone(engine)
        self.assertIsNone(engine.input_manager)
        self.assertIsNone(engine.boss_manager)
        self.assertIsInstance(engine.groups, dict)
        
        # Clean up
        engine.stop()

    def test_environment_sanity(self):
        """
        Test that critical libraries are importable.
        """
        modules = ["cv2", "numpy", "rapidocr_onnxruntime"]
        for module_name in modules:
            result = subprocess.run(
                [sys.executable, "-c", f"import {module_name}; print('ok')"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                self.fail(f"Environment Sanity Check Failed for {module_name}: {detail}")

if __name__ == '__main__':
    unittest.main()
