import unittest
import sys
import os
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.config_loader import ConfigLoader
from core.audio_manager import AudioManager
from core.runtime_config import RuntimeConfig
from core.logic_engine import LogicEngine
from ui.launcher import LauncherWindow
from ui.overlay import OverlayWindow

class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance for UI tests
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_components_instantiation(self):
        # 1. Config
        config = ConfigLoader.get_config()
        self.assertIsNotNone(config)

        # 2. Audio
        audio = AudioManager()
        self.assertIsNotNone(audio)

        # 3. Runtime Config
        runtime_config = RuntimeConfig(start_seconds=1200)
        
        # 4. Logic Engine
        logic = LogicEngine(runtime_config)
        self.assertIsNotNone(logic)
        
        # 5. Launcher
        launcher = LauncherWindow()
        self.assertIsNotNone(launcher)
        
        # 6. Overlay
        overlay = OverlayWindow(logic)
        self.assertIsNotNone(overlay)

if __name__ == '__main__':
    unittest.main()
