import unittest
from unittest.mock import MagicMock
import sys
import os
import time

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.scheduler import SkillScheduler, Player

class TestSchedulerFull(unittest.TestCase):
    def setUp(self):
        self.config = {
            "buff_duration": 5.0,
            "skill_cooldown": 20.0,
            "players": [1, 2, 3],
            "loop_mode": "loop"
        }
        self.sch = SkillScheduler("test_group", self.config)

    def test_priority_level_1_ready(self):
        """Level 1: Players who are ready NOW (<= current_time) should fire first."""
        # P1 is ready at 100, P2 ready at 90. Current is 100.
        # Both are ready. Should pick P1 (Lowest ID).
        self.sch.players[0].cd_ready_time = 100
        self.sch.players[1].cd_ready_time = 90
        
        action = self.sch.get_next_action(100)
        self.assertEqual(action['action_type'], 'FIRE')
        self.assertEqual(action['player_id'], 1)

    def test_priority_level_2_future(self):
        """Level 2: No one ready. Should find earliest future time."""
        # P1 ready at 110, P2 ready at 105. P3 ready at 999. Current is 100.
        # Should WAIT for P2 (105).
        self.sch.players[0].cd_ready_time = 110
        self.sch.players[1].cd_ready_time = 105
        self.sch.players[2].cd_ready_time = 999 # Fix: P3 must not be 0
        
        action = self.sch.get_next_action(100)
        self.assertEqual(action['action_type'], 'WAIT')
        self.assertAlmostEqual(action['wait_time'], 5.0)

    def test_mutex_locking(self):
        """Verify scheduler locks logic during buff duration."""
        # Fire P1 at 100. Buff duration 5s.
        self.sch.get_next_action(100, commit=True)
        self.assertEqual(self.sch.current_buff_end_time, 105.0)
        
        # At 102, should be LOCKED.
        action = self.sch.get_next_action(102)
        self.assertEqual(action['action_type'], 'WAIT')
        self.assertEqual(action['reason'], "Global Buff Active")
        self.assertAlmostEqual(action['wait_time'], 3.0)

    def test_loop_mode(self):
        """Verify normal wrapping behavior."""
        # Fix: Increase CD to prevent P1 from jumping queue at T=20
        # CD = 100.
        self.sch.skill_cooldown = 100.0
        
        t = 0
        # P1
        action = self.sch.get_next_action(t, commit=True)
        self.assertEqual(action['player_id'], 1) 
        
        # P2
        t += 10 
        action = self.sch.get_next_action(t, commit=True)
        self.assertEqual(action['player_id'], 2)
        
        # P3
        t += 10
        action = self.sch.get_next_action(t, commit=True)
        self.assertEqual(action['player_id'], 3)
        
        # Wrap to P1 (T=30). P1 CD=100 (ready at 100). P2=110, P3=120.
        # Wait, if CD=100, P1 is NOT ready at 30.
        # So it should be WAIT?
        # A loop mode forces order?
        # No, Loop Mode just means "Don't Stop". It still respects CD.
        # If I want P1 to fire at 30, CD must be <= 30.
        # BUT CD must be > 20 to prevent P1 firing at T=20 (instead of P3).
        # So CD must be in (20, 30]. Let's say 25.
        self.sch.skill_cooldown = 25.0
        
        # P1 (T=0) -> Ready at 25.
        # P2 (T=10) -> Ready at 35.
        # P3 (T=20) -> Ready at 45.
        
        # At T=30: P1 ready (25<=30). P2(35 no), P3(45 no).
        # Should be P1.
        
        # Re-run logic with CD=25
        self.sch.reset() # Clear state
        
        # T=0: P1
        action = self.sch.get_next_action(0, commit=True)
        self.assertEqual(action['player_id'], 1)
        
        # T=10: P1(25>10). P2(0). P3(0). -> P2.
        action = self.sch.get_next_action(10, commit=True)
        self.assertEqual(action['player_id'], 2)
        
        # T=20: P1(25>20). P2(35>20). P3(0). -> P3.
        action = self.sch.get_next_action(20, commit=True)
        self.assertEqual(action['player_id'], 3)
        
        # T=30: P1(25<=30 OK). P2(35). P3(45). -> P1.
        action = self.sch.get_next_action(30, commit=True)
        self.assertEqual(action['player_id'], 1)

    def test_once_mode_stop(self):
        """Verify 'once' mode stops after the last player."""
        self.sch.loop_mode = 'once'
        self.sch.skill_cooldown = 25.0
        t = 0
        
        # Fire P1, P2, P3
        self.sch.reset()
        for pid in [1, 2, 3]:
            self.sch.get_next_action(t, commit=True)
            self.assertEqual(self.sch.last_fired_player_id, pid)
            t += 10
            
        # At T=30. P1 is ready (25<=30).
        # But 'once' mode should detect cycle complete.
        action = self.sch.get_next_action(t)
        self.assertEqual(action['action_type'], 'STOP')

    def test_skip_penalty(self):
        """Test user manually skipping a player."""
        # Fire P1 at 100
        self.sch.get_next_action(100, commit=True)
        self.assertEqual(self.sch.players[0].cd_ready_time, 120.0) # 100 + 20
        
        # User Skips P1 at 102 (Logic: "Pass")
        # Should reduce CD to Penalty (10s) -> 102+10 = 112
        success = self.sch.skip_player(1, 102)
        self.assertTrue(success)
        
        # Check Penalty State
        p1 = self.sch.players[0]
        self.assertEqual(p1.penalty_end_time, 112.0)
        self.assertEqual(p1.cd_ready_time, 112.0) # CD should be reverted
        
        # Mutex should be cleared to allow immediate next
        self.assertEqual(self.sch.current_buff_end_time, 102.0)

    def test_consume_turn_backdating(self):
        """Test consuming a turn with auto-backdating logic."""
        # Fire P1 at 100
        self.sch.get_next_action(100, commit=True)
        
        # At 102, user realizes "Oh, P1 cast failed/missed". Consumes turn.
        # We invoke explicit consume on P1 to test backdating.
        
        success, pid = self.sch.consume_turn(1, 102) 
        self.assertTrue(success)
        self.assertEqual(pid, 1)
        
        p1 = self.sch.players[0]
        # CD = Original(100) + 20 = 120.
        # NOT 102 + 20 = 122.
        self.assertEqual(p1.cd_ready_time, 120.0)
        
        # Mutex should be cleared (0.0) for immediate next
        self.assertEqual(self.sch.current_buff_end_time, 0.0)

    def test_smart_gating_high_pressure(self):
        """Simulate interval (2s) faster than CD (20s). Should GATE."""
        # Config: 2 players. Loop time 4s. CD 20s.
        self.sch.players = [Player(1), Player(2)]
        
        # Fix: Buff Duration must be <= Interval (2s) so Mutex clears.
        self.sch.buff_duration = 1.0 
        
        t = 0
        
        # 1. Fire P1 (CD -> 20)
        self.sch.get_next_action(t, commit=True) # Mutex -> 1.0 relative
        
        t += 2 # Buff(1s) done. Interval done.
        # 2. Fire P2 (CD -> 22)
        self.sch.get_next_action(t, commit=True) # Mutex -> 2+1 = 3.0
        
        t += 2 # Now t=4. Mutex(3.0) done.
        # P1 logic ready?
        # P1 CD is 20. Current is 4.
        # Should WAIT 16s.
        
        action = self.sch.get_next_action(t)
        self.assertEqual(action['action_type'], 'WAIT')
        self.assertEqual(action['reason'], "Cooling Down")
        self.assertAlmostEqual(action['wait_time'], 16.0)

if __name__ == '__main__':
    unittest.main()
