import unittest
from unittest.mock import MagicMock
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.group_controller import GroupController

class TestGroupControllerFull(unittest.TestCase):
    def setUp(self):
        self.config = {"name": "Test", "players": [1, 2], "loop_mode": "step"}
        self.gc = GroupController("gc1", self.config)

    def test_state_machine(self):
        """Verify basic state transitions."""
        self.assertEqual(self.gc.state, "IDLE")
        
        self.gc.start()
        self.assertEqual(self.gc.state, "RUNNING")
        
        self.gc.toggle_pause()
        self.assertEqual(self.gc.state, "PAUSED")
        
        self.gc.toggle_pause()
        self.assertEqual(self.gc.state, "RUNNING")
        
        self.gc.stop()
        self.assertEqual(self.gc.state, "IDLE")

    def test_step_mode_pause(self):
        """Verify Step Mode auto-pauses after FIRE requires confirmation."""
        self.gc.start()
        # Mock scheduler to FIRE
        # Step Ready is True initially.
        self.gc.scheduler.get_next_action = MagicMock(return_value={'action_type': 'FIRE', 'player_id': 1})
        
        # First Update: Should FIRE and consume step_ready
        res = self.gc.update(100)
        self.assertIsNotNone(res) # Fired
        self.assertFalse(self.gc.step_ready) # Token consumed
        
        # Second Update: Scheduler wants to FIRE P2?
        # But step_ready is False. Should Auto-Pause.
        self.gc.scheduler.get_next_action = MagicMock(return_value={'action_type': 'FIRE', 'player_id': 2})
        res = self.gc.update(105)
        
        self.assertIsNone(res) # Blocked
        self.assertEqual(self.gc.state, "PAUSED") # Auto-paused
        
        # Verify Manual Resume re-enables step
        self.gc.toggle_pause()
        self.assertTrue(self.gc.step_ready)

if __name__ == '__main__':
    unittest.main()
