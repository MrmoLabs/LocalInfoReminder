
import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.logic_engine import GroupController

class MockScheduler:
    def __init__(self, actions):
        self.actions = actions # List of (time, action_dict)
        self.buff_duration = 5.0
        self.players = [1, 2]

    def reset(self):
        pass

    def get_next_action(self, current_time):
        # Allow checking if we should fire
        for t, action in self.actions:
            if current_time >= t:
                # Basic mock: if time matches, return action
                # ideally we pop it or something
                return action
        return {'action_type': 'WAIT', 'wait_time': 1.0}

    def get_predicted_next(self, t):
        return None, "Mock"

# We'll just test the GroupController's update logic specifically
# since we can't easily mock the real Scheduler's time dependency without complex mocking.
# Instead, let's substitute the scheduler in the controller with a Mock or just test the Flag logic.

def test_step_logic():
    print("Testing Step Logic...")
    
    config = {
        'id': 'test_group',
        'name': 'Test Group',
        'players': [1, 2],
        'loop_mode': 'step',
        'buff_duration': 0.1 # fast
    }
    
    ctrl = GroupController('test_group', config)
    
    # Override scheduler to force feed actions
    class ForcedScheduler:
        def __init__(self):
            self.players = [1,2]
            self.buff_duration=1
            
        def reset(self): pass
        def get_predicted_next(self, t): return None, None
        
        def get_next_action(self, t):
            # Always say FIRE to test the gate
            return {'action_type': 'FIRE', 'player_id': 1}

    ctrl.scheduler = ForcedScheduler()

    # 1. Start
    print("[1] Starting...")
    ctrl.start()
    assert ctrl.state == GroupController.STATE_RUNNING
    assert ctrl.step_ready == True
    print(" -> Started. State: RUNNING, Ready: True")

    # 2. First Update (Should Fire P1)
    print("[2] Update 1 (Expect Fire)...")
    sounds = ctrl.update(time.time())
    
    if sounds:
        print(f" -> Fired! Sounds: {sounds}")
        assert ctrl.step_ready == False
    else:
        print(" -> FAILED: Did not fire!")
        return

    # 3. Second Update (Should Pause immediately because action is still FIRE but ready is False)
    # Note: real scheduler would return WAIT for buff duration.
    # But here our mock returns FIRE immediately.
    # This simulates "Buff Ended, Next Person Ready".
    
    print("[3] Update 2 (Expect Pause)...")
    res = ctrl.update(time.time())
    
    assert res is None # Should not fire
    assert ctrl.state == GroupController.STATE_PAUSED
    print(" -> Auto-Paused! State: PAUSED")
    
    # 4. Resume (Manual Trigger)
    print("[4] Manual Resume...")
    ctrl.toggle_pause() # Resume
    
    assert ctrl.state == GroupController.STATE_RUNNING
    assert ctrl.step_ready == True
    print(" -> Resumed. State: RUNNING, Ready: True")
    
    # 5. Third Update (Should Fire P2 - effectively, P1 again in our mock but logic is same)
    print("[5] Update 3 (Expect Fire)...")
    sounds = ctrl.update(time.time())
    
    if sounds:
         print(f" -> Fired! Sounds: {sounds}")
         assert ctrl.step_ready == False
    else:
         print(" -> FAILED: Did not fire!")
         return

    print("TEST PASSED: Step Mode Logic Verified.")

if __name__ == "__main__":
    test_step_logic()
