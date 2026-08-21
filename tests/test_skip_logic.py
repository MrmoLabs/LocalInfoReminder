import unittest
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.logic_engine import GroupController

class TestSkipLogic(unittest.TestCase):
    def test_skip_auto_detect(self):
        """Verify GroupController.skip(None) correctly skips RECENTLY FIRED player"""
        # Config: P1, P2. Buff=5, CD=20.
        cfg = {'id': 'TestGroup', 'name': 'Test', 'buff_duration': 5.0, 'skill_cooldown': 20.0, 'players': [1, 2]}
        grp = GroupController('TestGroup', cfg)
        grp.start()
        
        now = 1000.0
        
        # 1. Fire P1
        action = grp.scheduler.get_next_action(now)
        self.assertEqual(action['player_id'], 1)
        self.assertEqual(action['action_type'], 'FIRE')
        
        # State Check: P1 CD = 1020. Mutex = 1005.
        p1 = grp.scheduler.players[0]
        self.assertEqual(p1.cd_ready_time, 1020.0)
        self.assertEqual(grp.scheduler.current_buff_end_time, 1005.0)
        
        # 2. Simulate User Double Tap 1 sec later (Reactive Skip)
        skip_time = 1001.0
        grp.skip(skip_time, player_id=None)
        
        # Expectation: 
        # - P1 detected as "Last Fired".
        # - P1 CD reverted/clamped to Penalty (SkipTime + 10 = 1011).
        # - Mutex cleared (reset to SkipTime = 1001).
        
        self.assertEqual(p1.penalty_end_time, 1011.0)
        self.assertEqual(p1.cd_ready_time, 1011.0) # CD matched to penalty
        self.assertEqual(grp.scheduler.current_buff_end_time, 1001.0) # Mutex cleared
        
        # 3. Verify Immediate Next Action
        # Now = 1001. P1 Ready=1011. P2 Ready=0.
        # Should Fire P2 immediately.
        action = grp.scheduler.get_next_action(skip_time)
        self.assertEqual(action['player_id'], 2)
        self.assertEqual(action['action_type'], 'FIRE')

if __name__ == '__main__':
    unittest.main()
