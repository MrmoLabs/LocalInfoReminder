import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

# Mock pygame before importing AudioManager
sys.modules['pygame'] = MagicMock()
sys.modules['pygame.mixer'] = MagicMock()

from core.audio_manager import AudioManager

class TestAudioManager(unittest.TestCase):
    def setUp(self):
        # Reset singleton for testing
        AudioManager._instance = None
        self.audio_manager = AudioManager()

    def test_initialization(self):
        # Check if mixer init was called
        sys.modules['pygame'].mixer.init.assert_called()
        sys.modules['pygame'].mixer.set_num_channels.assert_called_with(8)

    def test_play_sound(self):
        # Mock a loaded sound
        mock_sound = MagicMock()
        self.audio_manager.sounds["test.wav"] = mock_sound
        
        # Mock channel
        mock_channel = MagicMock()
        sys.modules['pygame'].mixer.Channel.return_value = mock_channel

        self.audio_manager.play("test.wav", AudioManager.CHANNEL_NORMAL)
        
        # Verify the requested priority channel is used.
        sys.modules['pygame'].mixer.Channel.assert_called_with(AudioManager.CHANNEL_NORMAL)
        mock_channel.play.assert_called_once_with(mock_sound)
        mock_sound.play.assert_not_called()

    def test_stop_all(self):
        self.audio_manager.stop_all()
        sys.modules['pygame'].mixer.stop.assert_called()

if __name__ == '__main__':
    unittest.main()
