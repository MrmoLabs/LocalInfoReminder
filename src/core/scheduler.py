import time
import math

class Player:
    def __init__(self, player_id):
        self.id = player_id
        self.cd_ready_time = 0.0
        self.penalty_end_time = 0.0
        self.buff_end_time = 0.0 # [NEW] Per-player buff tracking for Independent Mode

    def get_actual_ready_time(self):
        """
        Calculates the actual ready time considering both Skill CD and Skip Penalty.
        Formula: Actual_Ready_Time = MAX(CD_Ready_Time, Penalty_End_Time)
        """
        return max(self.cd_ready_time, self.penalty_end_time)

from core.constants import TimeConstants

class SkillScheduler:
    SKIP_PENALTY_DURATION = TimeConstants.SKIP_PENALTY_DURATION # seconds

    def __init__(self, group_id, config):
        self.group_id = group_id
        self.buff_duration = config.get('buff_duration', TimeConstants.DEFAULT_BUFF_DURATION)
        self.skill_cooldown = config.get('skill_cooldown', TimeConstants.DEFAULT_SKILL_COOLDOWN)
        
        # Parse players
        player_ids = config.get('players', [])
        # Support legacy count-based config if needed? 
        # LogicEngine passes fully formed list, so we assume list.
        self.players = [Player(pid) for pid in player_ids]
        self.loop_mode = config.get('loop_mode', 'loop')
        
        self.current_buff_end_time = 0.0
        
        # State for Skip Logic
        self.last_fired_player_id = None
        self.last_fired_time = 0.0

    def reset(self):
        """Resets the scheduler state (clears CDs, Penalties, Mutex)."""
        self.current_buff_end_time = 0.0
        self.last_fired_player_id = None
        self.last_fired_time = 0.0
        self.cached_next_prediction = None
        for p in self.players:
            p.cd_ready_time = 0.0
            p.penalty_end_time = 0.0
            p.buff_end_time = 0.0

    def get_next_action(self, current_time, commit=True):

        # 1. Buff Mutex Check
        # Strict Rule: Must wait for current buff to end.
        # Strict Rule: Must wait for current buff to end.
        if current_time < self.current_buff_end_time:
            wait_time = self.current_buff_end_time - current_time
            # print(f"[Scheduler-DEBUG] LOCKED. Mutex={self.current_buff_end_time:.2f}, Now={current_time:.2f}, Wait={wait_time:.2f}")
            return self._build_action('WAIT', None, wait_time, "Global Buff Active")


        # 2. Global Scan Algorithm
        
        # Level 1: Find "Immediate" Candidates
        # Candidates whose actual ready time <= current_time
        ready_candidates = []
        min_future_time = float('inf')
        
        for p in self.players:
            actual_ready = p.get_actual_ready_time()
            if actual_ready <= current_time:
                ready_candidates.append(p)
            else:
                if actual_ready < min_future_time:
                    min_future_time = actual_ready

        # Logic Branch
        if ready_candidates:
            # Sort by ID (Lowest First)
            ready_candidates.sort(key=lambda p: p.id)
            selected_player = ready_candidates[0]
            
            # --- Single Cycle Intercept ---
            # If we are about to fire the FIRST player (Wrap Around)
            # AND we recently fired the LAST player (Cycle Done)
            # AND mode is 'once' -> STOP.
            if self.loop_mode == 'once' and self.players:
                first_player_id = self.players[0].id
                last_player_id = self.players[-1].id
                
                if selected_player.id == first_player_id and self.last_fired_player_id == last_player_id:
                     return self._build_action('STOP', None, 0, "Single Cycle Complete")
            
            # FIRE!
            # print(f"[Scheduler-DEBUG] DECISION: FIRE P{selected_player.id} at T={current_time:.2f}. ActualReady={selected_player.get_actual_ready_time():.2f}")
            return self._fire_player(selected_player, current_time, commit=commit)

        else:
            # Level 2: System Wait
            # No one is ready right now. Find the earliest future ready time.
            if min_future_time == float('inf'):
                wait_time = 999
            else:
                wait_time = min_future_time - current_time
                wait_time = max(0.0, wait_time)
            
            return self._build_action('WAIT', None, wait_time, "Cooling Down")

    def get_predicted_next(self, current_time):
        """
        Predicts who will be the next player to fire.
        Returns (Player, Reason).
        """
        # CACHED PREDICTION (The Latch)
        # If we have a cached prediction from the moment of firing, return it.
        # This ensures stability during the buff.
        # But we must invalidate it if state changes drastically (e.g. skip).
        # Simple Logic: If we are in the "Buff Wait" phase (which we are if calling predict during buff),
        # return the cache.
        if hasattr(self, 'cached_next_prediction') and self.cached_next_prediction:
             # Verify it's still valid logic? No, trust the latch.
             return self.cached_next_prediction, "Cached"

        if not self.players:
            return None, "No Players"
            
        # 1. Ready Candidates (Level 1)
        # Any player whose actual ready time <= current_time?
        ready_candidates = [p for p in self.players if p.get_actual_ready_time() <= current_time]
        if ready_candidates:
            ready_candidates.sort(key=lambda p: p.id)
            return ready_candidates[0], "Ready"
            
        # 2. Future Candidates (Level 2)
        # Find minimum ready time
        min_ready_time = float('inf')
        for p in self.players:
            rt = p.get_actual_ready_time()
            if rt < min_ready_time:
                min_ready_time = rt
        
        # Collect all who match that minimum time
        future_candidates = [p for p in self.players if p.get_actual_ready_time() == min_ready_time]
        if future_candidates:
            future_candidates.sort(key=lambda p: p.id)
            return future_candidates[0], "Cooling Down"
            
        return None, "Unknown"

    def skip_player(self, player_id, current_time):
        """
        Applies skip penalty. 
        If player_id is None, targets the LAST FIRED player (if within reasonable window),
        converting their Cooldown into a Penalty.
        """
        target_player = None
        
        if player_id is None:
            # Auto-detect: Prioritize the player we JUST fired (User reacting to prompt)
            # Window: If we fired P1 < BuffDuration ago, user is likely skipping P1.
            if self.last_fired_player_id is not None:
                # Check if it was recent
                if current_time - self.last_fired_time < self.buff_duration + 1.0: # +1s buffer
                     # Find P1
                     for p in self.players:
                         if p.id == self.last_fired_player_id:
                             target_player = p
                             break
            
            # Fallback: If no recent fire, use standard priority (maybe user is pre-skipping?)
            if not target_player:
                # 1. Ready Candidates
                ready_candidates = [p for p in self.players if p.get_actual_ready_time() <= current_time]
                if ready_candidates:
                    ready_candidates.sort(key=lambda p: p.id)
                    target_player = ready_candidates[0]
                else:
                    # 2. Min Time
                    min_time = float('inf')
                    cand = None
                    for p in self.players:
                        rt = p.get_actual_ready_time()
                        if rt < min_time:
                            min_time = rt
                            cand = p
                        elif rt == min_time:
                            if cand and p.id < cand.id:
                                cand = p
                    target_player = cand
        else:
             for p in self.players:
                if p.id == player_id:
                    target_player = p
                    break
        
        if target_player:
            # CORE LOGIC CHANGE: Revert Cooldown?
            # If this target was just fired, they have a huge CD.
            # We must shorten it to the Penalty Duration.
            
            # Set Penalty
            target_player.penalty_end_time = current_time + self.SKIP_PENALTY_DURATION
            
            # Fix CD if it was the reason for delay
            if target_player.id == self.last_fired_player_id:
                 # Reset CD to match penalty (effectively erasing the 100s CD)
                 target_player.cd_ready_time = target_player.penalty_end_time
                 # Also clear mutex so next person can go immediately
                 self.current_buff_end_time = current_time 
            
            # Record that this player "acted" (via skip)
            self.last_fired_player_id = target_player.id
            self.last_fired_time = current_time
            
            # Recalculate Prediction since state changed drastically
            future_check_time = current_time + self.buff_duration + 0.1
            self.cached_next_prediction = self._internal_predict(future_check_time)
            
            print(f"[Scheduler-DEBUG] SKIP_PLAYER SUCCESS. Target=P{target_player.id} (LastFired=P{self.last_fired_player_id}). Reverted CD -> Penalty ends at T={target_player.penalty_end_time:.2f}. MutexReset to T={current_time:.2f}")
            return True
        print(f"[Scheduler-DEBUG] SKIP_PLAYER FAILED. No valid target found. CurrentTime={current_time:.2f}")
        return False

    def _fire_player(self, player, current_time, commit=True):

        if commit:
            # Update Global Mutex
            self.current_buff_end_time = current_time + self.buff_duration
            
            # Update Player State
            player.cd_ready_time = current_time + self.skill_cooldown
            
            # Record History
            self.last_fired_player_id = player.id
            self.last_fired_time = current_time
            
            # LATCH PREDICTION:
            # Immediately calculate who will be next after this buff ends.
            # We simulate state at (current_time + buff_duration + 0.01).
            # Since we just updated 'player.cd_ready_time', the calc will be accurate.
            future_check_time = current_time + self.buff_duration + 0.1
            self.cached_next_prediction = self._internal_predict(future_check_time)
        
        return self._build_action('FIRE', player.id, 0, "Player Ready")

    def consume_turn(self, player_id, current_time):
        """
        Forces the player to 'use' their turn without firing.
        Effectively skips the player but applies FULL COOLDOWN.
        Used when a player effectively missed their window or cast failed to register but is on CD.
        """
        target_player = None
        
        # Logic 1: Use specific ID
        if player_id is not None:
             for p in self.players:
                if p.id == player_id:
                    target_player = p
                    break
        
        # Logic 2: Auto-Detect (Next available or currently gating)
        # Usually we want to skip the person who SHOULD have fired or IS firing.
        # If we are waiting for P1, and user hits SkipCD, we assume P1 is the culprit.
        if not target_player:
            # Check Level 1 Candidates first (Ready <= Now)
            ready_candidates = [p for p in self.players if p.get_actual_ready_time() <= current_time]
            if ready_candidates:
                ready_candidates.sort(key=lambda p: p.id)
                target_player = ready_candidates[0]
            else:
                 # Check Level 2 (Future) - The next person in line
                 # Find minimum ready time
                min_rt = float('inf')
                for p in self.players:
                    rt = p.get_actual_ready_time()
                    if rt < min_rt: min_rt = rt
                
                future_candidates = [p for p in self.players if p.get_actual_ready_time() == min_rt]
                if future_candidates:
                    future_candidates.sort(key=lambda p: p.id)
                    target_player = future_candidates[0]

        if target_player:
            # Apply Full Cooldown
            # [FIX] If we are consuming the player who JUST fired (e.g. correcting a failure),
            # we should calculate CD from their ORIGINAL fire time (T0), not now (T0+t).
            # Otherwise, we penalize them by an extra 't' seconds.
            base_time = current_time
            if target_player.id == self.last_fired_player_id:
                # Sanity check: ensure last_fired_time is reasonable (not ages ago)
                # If they fired < 30s ago, we assume this is a correction.
                if current_time - self.last_fired_time < 30.0:
                     base_time = self.last_fired_time
                     # print(f"[Scheduler] Backdating Consumed CD for P{target_player.id} to T-{current_time - base_time:.2f}s")
            
            target_player.cd_ready_time = base_time + self.skill_cooldown
            
            # Update Global Mutex
            # User clarified: "Immediately trigger the next character".
            # [FIX] Set to 0.0 (or past time) to ENSURE the very next tick picks it up immediately.
            # Do not use current_time + 0.1, as that causes a 1-frame "WAIT" state which might flicker the Gating bar.
            self.current_buff_end_time = 0.0 
            
            # Record History (Keep original time if backdated? Or update to now? 
            # If we update to 'now', next skip check might fail window. 
            # But 'last_fired_time' implies 'action time'. 
            # Let's update to 'current_time' to reflect the INTERVENTION point, 
            # but we already secured the CD.)
            self.last_fired_player_id = target_player.id
            self.last_fired_time = current_time
            
            # Update Prediction
            future_check_time = current_time + self.buff_duration + 0.1
            self.cached_next_prediction = self._internal_predict(future_check_time)
            
            print(f"[Scheduler-DEBUG] CONSUME_TURN SUCCESS. Target=P{target_player.id}. BackdatedCD? {base_time < current_time}. CD_Ready={target_player.cd_ready_time:.2f}. Mutex CLEARED (0.0). Next should be immediate.")
            return True, target_player.id
            
        print(f"[Scheduler-DEBUG] CONSUME_TURN FAILED. No valid target. CurrentTime={current_time:.2f}")
        return False, None


    def _internal_predict(self, check_time):
        """Helper to predict best candidate at a specific time."""
        if not self.players: return None
        
        # 1. Ready at check_time
        ready = [p for p in self.players if p.get_actual_ready_time() <= check_time]
        if ready:
            ready.sort(key=lambda p: p.id)
            return ready[0]
            
        # 2. Future relative to check_time
        min_rt = float('inf')
        for p in self.players:
            rt = p.get_actual_ready_time()
            if rt < min_rt: min_rt = rt
            
        future = [p for p in self.players if p.get_actual_ready_time() == min_rt]
        if future:
            future.sort(key=lambda p: p.id)
            return future[0]
        
        return None

    def _build_action(self, action_type, player_id, wait_time, reason):
        return {
            'group_id': self.group_id,
            'action_type': action_type,
            'player_id': player_id,
            'wait_time': wait_time,
            'reason': reason
        }

    # === Independent Mode Support ===========================================
    def check_independent_fire(self, player_id, current_time):
        """Checks if a specific player can fire (Independent Mode)."""
        target = next((p for p in self.players if p.id == player_id), None)
        if not target: return False, "Invalid ID"
        
        # 1. Check Buff Status (Is currently active?)
        if current_time < target.buff_end_time:
             return False, "Buff Active"
             
        # 2. Check CD Status
        if target.get_actual_ready_time() > current_time:
             return False, "Cooling Down"
             
        return True, "Ready"

    def fire_independent_player(self, player_id, current_time):
        """Fires a specific player (Independent Mode), ignoring global mutex."""
        target = next((p for p in self.players if p.id == player_id), None)
        if not target: return None
        
        # Update Individual State
        target.buff_end_time = current_time + self.buff_duration
        target.cd_ready_time = current_time + self.skill_cooldown
        
        return self._build_action('FIRE', target.id, 0, "Independent Fire")

    def reset_independent_player(self, player_id):
        """Resets a specific player to IDLE (Independent Mode)."""
        target = next((p for p in self.players if p.id == player_id), None)
        if target:
            target.cd_ready_time = 0.0
            target.penalty_end_time = 0.0
            target.buff_end_time = 0.0
            return True
        return False
