import time
try:
    import keyboard
    import mouse
    HAS_MOUSE = True
except:
    HAS_MOUSE = False

class InputState:
    """
    Responsibilities:
    1. Track the state of active keys (is_down, start_time, pending_tap).
    2. Implement 'Hold', 'Double Tap', and 'Short Press' heuristics.
    3. Return high-level actions (GESTURE, SKILL) based on state transitions.
    """
    
    ACTION_GESTURE = 'gesture'
    ACTION_SKILL = 'skill'
    
    def __init__(self, key_mapper):
        self.mapper = key_mapper
        self.key_states = {} # key -> dict state
        
        # Config
        self.LONG_PRESS_THRESHOLD = 0.30
        self.DOUBLE_TAP_THRESHOLD = 0.35

    def process_press(self, key: str, now: float) -> list:
        actions = []
        
        if key not in self.key_states:
             self._init_key_state(key)
        state = self.key_states[key]
        
        # Auto-repeat check
        if state['is_down']: 
            return actions
            
        # 1. Class Bindings
        entries = self.mapper.get_entries(key)
        if entries:
            for entry in entries:
                # Resolve details
                cid, mode, pid = self._resolve_entry(entry)
                
                if mode == 'strict_trigger':
                    # Independent Mode: Trigger Directly
                    print(f"[InputState] Independent Trigger: {cid} P{pid} ({key})")
                    actions.append((self.ACTION_GESTURE, cid, "strict_trigger", pid))
                    state['handled_long'] = False 
                else:
                    # Standard Mode
                    if state.get('pending_tap', 0) > 0:
                        print(f"[InputState] Double Tap: {cid} ({key})")
                        actions.append((self.ACTION_GESTURE, cid, "double_tap", pid))
                        state['handled_long'] = False
                    else:
                        print(f"[InputState] Fresh Press: {key} for {cid}")

            state['is_down'] = True
            state['handled_long'] = False
            state['start'] = now
            
            # If standard logic exists, handle double-tap state
            has_standard = any(self._resolve_entry(e)[1] != 'strict_trigger' for e in entries)
            if has_standard:
                if state.get('pending_tap', 0) > 0:
                    state['pending_tap'] = 0
                    state['ignore_release'] = True
                else:
                    state['ignore_release'] = False

        # 2. Skip CD
        skip_cid = self.mapper.get_skip_cid(key)
        if skip_cid:
            if not state['is_down']:
                print(f"[InputState] Skip With CD: {key} for {skip_cid}")
                actions.append((self.ACTION_GESTURE, skip_cid, "skip_turn_consumed", None))
                state['is_down'] = True
                state['start'] = now

        # 3. Skills
        skill_cfg = self.mapper.get_skill_config(key)
        if skill_cfg:
             last = state.get('last_trigger', 0)
             if now - last > 0.2:
                 print(f"[InputState] Skill Trigger: {skill_cfg['name']}")
                 actions.append((self.ACTION_SKILL, skill_cfg))
                 state['is_down'] = True
                 state['last_trigger'] = now

        return actions

    def process_release(self, key: str, now: float) -> list:
        actions = []
        # Only care if mapped
        if not (self.mapper.get_entries(key) or self.mapper.get_skip_cid(key)):
            # Cleanup skill logic if needed or ignore
            if key in self.key_states and self.mapper.get_skill_config(key):
                 self.key_states[key]['is_down'] = False
            return actions

        if key not in self.key_states: return actions
        state = self.key_states[key]
        
        if not state['is_down']: return actions
        
        state['is_down'] = False
        duration = now - state['start']
        
        entries = self.mapper.get_entries(key)
        skip_cid = self.mapper.get_skip_cid(key)
        
        # Priority: Class Entries > Skip ID
        
        if duration > self.LONG_PRESS_THRESHOLD:
            # Long Press
            if not state.get('handled_long', False):
                 # For Class Entries
                 for entry in entries:
                     cid, mode, pid = self._resolve_entry(entry)
                     if mode != 'strict_trigger':
                          actions.append((self.ACTION_GESTURE, cid, "long_press", pid))
                 
                 # Note: Independent (strict) keys don't have Long Press release logic usually
                 state['handled_long'] = True
        else:
            # Short Press
            # Logic: If item is Strict or Skip, we are done. 
            # If item is Standard via class entries, we handle Pending Tap
            
            has_standard = False
            # Check entries
            for entry in entries:
                if self._resolve_entry(entry)[1] != 'strict_trigger':
                    has_standard = True
                    break
            
            # If ONLY strict entries, we skip release logic.
            # If we have at least one standard entry, we must process pending tap.
            
            if has_standard and not state.get('handled_long', False) and not state.get('ignore_release', False):
                state['pending_tap'] = now

        return actions

    def poll_holds(self, now: float) -> list:
        actions = []
        
        # 1. Holds (Long Press while holding)
        # 1. Holds (Long Press while holding)
        for key, state in self.key_states.items():
            if state['is_down']:
                # Verify physical press
                if not self._is_physically_pressed(key):
                     # Detected Release via Polling (Missed Event or Race Condition)
                     duration = now - state['start']
                     state['is_down'] = False
                     
                     if duration <= self.LONG_PRESS_THRESHOLD:
                         # Short Press Recovery
                         entries = self.mapper.get_entries(key)
                         skip_cid = self.mapper.get_skip_cid(key)
                         
                         has_standard = False
                         for entry in entries:
                             if self._resolve_entry(entry)[1] != 'strict_trigger':
                                 has_standard = True
                                 break
                         
                         if has_standard and not state.get('handled_long', False) and not state.get('ignore_release', False):
                             print(f"[InputState] Polling Release Recovery: {key}")
                             state['pending_tap'] = now
                     
                     continue

                duration = now - state['start']
                if duration > self.LONG_PRESS_THRESHOLD and not state.get('handled_long', False):
                     entries = self.mapper.get_entries(key)
                     for entry in entries:
                         cid, mode, pid = self._resolve_entry(entry)
                         
                         if mode == 'strict_trigger':
                             print(f"[InputState] Independent ResetLong: {cid} P{pid}")
                             actions.append((self.ACTION_GESTURE, cid, "reset_independent", pid))
                         else:
                             print(f"[InputState] Hold Long: {cid}")
                             actions.append((self.ACTION_GESTURE, cid, "long_press", pid))
                     
                     state['handled_long'] = True
        
        # 2. Pending Taps (Double Tap timeout)
        for key, state in self.key_states.items():
             if state.get('pending_tap', 0) > 0:
                 if (now - state['pending_tap']) > self.DOUBLE_TAP_THRESHOLD:
                      # Commit Single Tap
                      entries = self.mapper.get_entries(key)
                      for entry in entries:
                          cid, mode, pid = self._resolve_entry(entry)
                          if mode != 'strict_trigger':
                               print(f"[InputState] Single Tap Commit: {cid}")
                               actions.append((self.ACTION_GESTURE, cid, "single_tap", pid))
                      
                      state['pending_tap'] = 0

        return actions

    def clear(self):
        self.key_states.clear()

    def _init_key_state(self, key):
        self.key_states[key] = {
            'start': 0, 'last_tap': 0, 'is_down': False, 
            'handled_long': False, 'pending_tap': 0, 'ignore_release': False,
            'last_trigger': 0
        }

    def _resolve_entry(self, entry):
        # Returns (cid, mode, pid)
        if isinstance(entry, dict):
            return entry['cid'], entry.get('type', 'standard'), entry.get('pid', 1)
        return entry, 'standard', 1

    def _is_physically_pressed(self, key: str) -> bool:
        # Re-implement robust check
        try:
            if keyboard.is_pressed(key): return True
        except: pass
        if "num_" in key:
            try:
                 if keyboard.is_pressed(key.replace("num_", "num ")): return True
            except: pass
        if "mouse_" in key:
             if HAS_MOUSE:
                 # Minimal fallback for now, assume ctypes in Listener if needed
                 # or basic mouse lib
                 btn = None
                 if key == "mouse_left": btn = mouse.LEFT
                 elif key == "mouse_right": btn = mouse.RIGHT
                 elif key == "mouse_middle": btn = mouse.MIDDLE
                 elif key == "mouse_x1": btn = mouse.X
                 elif key == "mouse_x2": btn = mouse.X2
                 if btn and mouse.is_pressed(btn): return True
        return False
