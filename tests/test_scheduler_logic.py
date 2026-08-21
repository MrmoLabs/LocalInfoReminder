import unittest
import time
import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.scheduler import SkillScheduler, Player

class TestSkillScheduler(unittest.TestCase):
    def setUp(self):
        # Default config for testing
        self.config = {
            'buff_duration': 5.0,
            'skill_cooldown': 20.0,
            'players': [1, 2, 3]
        }
        self.scheduler = SkillScheduler('test_group', self.config)
        self.current_time = 1000.0 # Arbitrary start time

    def test_global_scan_level_1_priority(self):
        """Test Case 1: All Ready -> Lowest ID wins"""
        # All players fresh (ready time 0)
        
        # Action 1: Should fire P1
        action = self.scheduler.get_next_action(self.current_time)
        self.assertEqual(action['action_type'], 'FIRE')
        self.assertEqual(action['player_id'], 1)
        
        # P1 fired. Buff active until 1000 + 5 = 1005. P1 CD until 1000 + 20 = 1020.
        
        # Advance time to 1006 (Buff ended)
        self.current_time = 1006.0
        
        # Action 2: Should fire P2 (P1 is on CD, P2 & P3 ready)
        action = self.scheduler.get_next_action(self.current_time)
        self.assertEqual(action['action_type'], 'FIRE')
        self.assertEqual(action['player_id'], 2)

    def test_skip_mechanism(self):
        """Test Case 2: Skip 10s Penalty"""
        # P1 is ready. Skip P1.
        self.scheduler.skip_player(1, self.current_time)
        
        # P1 Penalty until 1000 + 10 = 1010.
        # P2, P3 are ready (time 0).
        
        # Action: Should fire P2 (P1 skipped/penalized)
        action = self.scheduler.get_next_action(self.current_time)
        self.assertEqual(action['action_type'], 'FIRE')
        self.assertEqual(action['player_id'], 2)
        
        # Verify P1 is indeed delayed
        # Advance to 1006 (Buff Ended for P2) (P2 fired at 1000, buff end 1005)
        # Wait, if I fired P2 at 1000, buff ends 1005.
        self.current_time = 1006.0
        
        # Now P1 penalty (1010) > current (1006). P3 ready (0).
        # Should fire P3.
        action = self.scheduler.get_next_action(self.current_time)
        self.assertEqual(action['action_type'], 'FIRE')
        self.assertEqual(action['player_id'], 3)

    def test_single_player_loop_avoidance(self):
        """Test Case: Single Player Dead Loop Avoidance"""
        scheduler = SkillScheduler('solo', {'players': [1], 'buff_duration': 5, 'skill_cooldown': 20})
        
        # P1 ready. Skip P1.
        scheduler.skip_player(1, self.current_time)
        # P1 Penalty -> 1010.
        
        # Action: Should WAIT until 1010.
        action = scheduler.get_next_action(self.current_time)
        self.assertEqual(action['action_type'], 'WAIT')
        self.assertAlmostEqual(action['wait_time'], 10.0, places=1) # 1010 - 1000 = 10s

    def test_priority_return(self):
        """Test Case: Pause Regression / Priority Return
        P1, P2, P3. P1 fired. P2 fired. 
        Then we wait long enough for everyone to be ready.
        Should start with P1 again.
        """
        # Fire P1
        self.scheduler.get_next_action(self.current_time) 
        # Fire P2 (Manual advance logic for test simulation)
        self.scheduler.current_buff_end_time = 0 # Hack to clear buff
        self.scheduler.get_next_action(self.current_time) # Fires P2
        
        # Wait huge time (everyone CD ready)
        self.current_time += 9999
        
        # Should fire P1 (ID 1) not P3
        action = self.scheduler.get_next_action(self.current_time)
        self.assertEqual(action['player_id'], 1)

if __name__ == '__main__':
    unittest.main()
