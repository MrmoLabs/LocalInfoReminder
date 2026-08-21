import unittest
from unittest.mock import MagicMock
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.group_controller import GroupController

class TestGroupController(unittest.TestCase):
    def setUp(self):
        self.config = {
            "name": "Test Group",
            "interval": 5.0,
            "cooldown": 10.0,
            "count": 2,
            "loop_mode": "loop"
        }
        self.gc = GroupController("test_group", self.config)

    def test_initial_state(self):
        self.assertEqual(self.gc.state, GroupController.STATE_IDLE)
        self.assertEqual(self.gc.loop_mode, "loop")

    def test_start_stop(self):
        self.gc.start()
        self.assertEqual(self.gc.state, GroupController.STATE_RUNNING)
        self.assertEqual(self.gc.current_player_id, 1)
        
        self.gc.stop()
        self.assertEqual(self.gc.state, GroupController.STATE_IDLE)

    def test_independent_mode_logic(self):
        """Test the Independent Mode trigger logic."""
        self.gc.loop_mode = GroupController.MODE_INDEPENDENT
        
        # Test Trigger
        # We need to mock scheduler.check_independent_fire because it depends on complex time logic
        self.gc.scheduler.check_independent_fire = MagicMock(return_value=(True, "OK"))
        self.gc.scheduler.fire_independent_player = MagicMock(return_value={'action_type': 'FIRE'})
        
        res = self.gc.trigger_independent(1, time.time())
        self.assertIsNotNone(res)
        self.assertIn("1.mp3", res[0])
        
        # Test Blocked
        self.gc.scheduler.check_independent_fire = MagicMock(return_value=(False, "Cooldown"))
        res = self.gc.trigger_independent(1, time.time())
        self.assertIsNone(res)

    def test_pause_toggle(self):
        self.gc.start()
        self.assertEqual(self.gc.state, GroupController.STATE_RUNNING)
        
        self.gc.toggle_pause()
        self.assertEqual(self.gc.state, GroupController.STATE_PAUSED)
        
        self.gc.toggle_pause()
        self.assertEqual(self.gc.state, GroupController.STATE_RUNNING)

if __name__ == '__main__':
    unittest.main()
