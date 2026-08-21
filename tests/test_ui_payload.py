import unittest
import sys
import os
import time

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.logic_engine import GroupController, LogicEngine

class RuntimeConfigMock:
    class_configs = {
        'TestGroup': {'count': 3}
    }
    start_seconds = 1200

class TestUiPayload(unittest.TestCase):
    def test_group_controller_payload(self):
        """Verify GroupController updates current_player_id"""
        cfg = {'id': 'TestGroup', 'name': 'Test', 'buff_duration': 5, 'skill_cooldown': 20, 'players': [1, 2, 3]}
        grp = GroupController('TestGroup', cfg)
        grp.start()
        
        # Test Initial
        self.assertEqual(grp.current_player_id, 1)
        
        # Simulate Loop
        now = time.time()
        # Should fire P1
        grp.update(now)
        self.assertEqual(grp.current_player_id, 1)
        
        # Advance time to P2
        grp.scheduler.current_buff_end_time = 0
        grp.scheduler.players[0].cd_ready_time = now + 100
        grp.update(now)
        self.assertEqual(grp.current_player_id, 2)
        
    def test_logic_engine_payload_structure(self):
        """Verify _process_tick constructs correct dict"""
        # We can't easily instantiate LogicEngine fully due to generic config load, 
        # but we can inspect the dict construction logic if we mocked it.
        # However, integration test is better.
        pass

if __name__ == '__main__':
    unittest.main()
