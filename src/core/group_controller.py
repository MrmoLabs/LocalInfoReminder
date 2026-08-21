import time
from typing import Dict, List, Any, Optional, Union
from core.scheduler import SkillScheduler

class GroupController:
    """
    Manages the lifecycle and state of a single SkillScheduler group.
    Acts as the bridge between LogicEngine (Input/Output) and Scheduler (Logic).
    Replaces the old ClassInstance.
    """
    STATE_IDLE: str = "IDLE"
    STATE_RUNNING: str = "RUNNING"
    STATE_PAUSED: str = "PAUSED"
    
    MODE_INDEPENDENT: str = "independent" # [NEW]

    def __init__(self, group_id: str, config: Dict[str, Any]):
        self.group_id: str = group_id
        self.config = config # Store config for access by LogicEngine
        self.name: str = config.get('name', group_id)
        
        # Instantiate the pure logic scheduler
        self.scheduler = SkillScheduler(group_id, config)
        
        self.state: str = self.STATE_IDLE
        self.pause_time: float = 0
        
        # For UI Visualization
        self.last_action_meta: Optional[Dict[str, Any]] = None 
        self.current_player_id: int = 1 # Default to 1 (Legacy 'index')

        self.loop_mode: str = config.get('loop_mode', 'loop')
        self.step_ready: bool = False # Flag for manual trigger in Step Mode

        # Internal wait context for UI stability
        self._wait_ctx: Dict[str, Any] = {'reason': None, 'total': 10.0}

    def start(self) -> None:
        self.state = self.STATE_RUNNING
        self.current_player_id = 1 # Reset on start
        self.step_ready = True # Allow first execution
        self.scheduler.reset() # User requested full reset on Start
        # We don't need to reset scheduler state usually, as it's time-based.
        # But if we want a fresh start, maybe?
        # For now, we assume "Start" just enables the polling.

    def stop(self) -> None:
        self.state = self.STATE_IDLE
        self.last_action_meta = None

    def toggle_pause(self) -> None:
        if self.state == self.STATE_RUNNING:
            self.state = self.STATE_PAUSED
            self.pause_time = time.time()
        elif self.state == self.STATE_PAUSED:
            self.state = self.STATE_RUNNING
            if self.loop_mode == 'step':
                self.step_ready = True # Enable next Step execution on resume
            # We might need to adjust scheduler times if pause should "freeze" the world.
            # But usually in PVP, time flows even if you pause the tool.
            # The prompt says: "Wait for Buff_End_Time".
            # If I pause, the buff still ticks down in game. So we do NOT shift time.
            # We just resume polling.
        elif self.state == self.STATE_IDLE:
            self.start()

    def update(self, current_time: float) -> Optional[List[str]]:
        """
        Ticks the scheduler. Returns list of sound files to play.
        """
        if self.state != self.STATE_RUNNING:
            return None

        # POLL Scheduler (PEEK FIRST - Do not commit state yet!)
        action = self.scheduler.get_next_action(current_time, commit=False)
        self.last_action_meta = action # Store for UI
        
        if action['action_type'] == 'FIRE':
            if self.loop_mode == 'step':
                if not self.step_ready:
                    # We are ready to fire, but we need manual confirm.
                    # Pause self.
                    if self.state == self.STATE_RUNNING:
                        # Auto Pause
                        print(f"[{self.name}] Step Mode: Buff ended. Auto-pausing for manual step.")
                        self.toggle_pause()
                    return None
            
            # If we are here, we are GO for launch.
            # COMMIT the action to update state (CDs, etc.)
            self.step_ready = False # Consume Token
            
            # Re-call with commit=True to actually update scheduler state
            final_action = self.scheduler.get_next_action(current_time, commit=True)
            
            # [Fix Phantom Fire] Verify commit matched peek
            if final_action['action_type'] != 'FIRE':
                print(f"[{self.name}] Scheduler Glitch: Peek=FIRE, Commit={final_action['action_type']}. Ignoring.")
                return None

            player_id = final_action['player_id']
            self.current_player_id = player_id
            
            sound_name = f"classes_template/{self.group_id}/{player_id}.mp3"
            
            # Reset wait context on FIRE
            self._wait_ctx['reason'] = None
            
            return [sound_name]
            
        elif action['action_type'] == 'STOP':
            # Scheduler requested stop (End of Once mode or other termination)
            print(f"[{self.name}] Scheduler requested STOP.")
            self.stop()
            return []
            
        return None

    def skip(self, current_time: float, player_id: Optional[int] = None) -> None:
        """
        Manually skips the CURRENT or specific player.
        """
        if self.state != self.STATE_RUNNING:
            return None
            
        # If no specific player, skip the one that is currently "waiting"?
        # But skip usually implies "Skip the specific person I clicked on".
        # We will expose skip_player(id) in UI.
        # But for hotkey "Double Tap", it implies "Skip Current Turn".
        # We need to ask Scheduler: "Who is the next intended candidate?" (Level 1)
        # OR just strictly require ID.
        # For Double Tap legacy support, let's assume we skip the 'current active' (if feasible) or just ignore?
        # User defined: "Skip Player Px... Px.Penalty = 10s".
        
        if self.scheduler.skip_player(player_id, current_time):
            # Trigger "Next" sound immediately?
            # The requirement says: "Immediately re-trigger priority scheduling".
            # The next update() loop will catch the new state.
            pass
                
        return None # User requested no sound for skip/next
        
    def skip_with_cooldown(self, current_time: float) -> None:
        """
        Skips current turn BUT applies full cooldown.
        Used for 'missed/failed' cast recovery.
        """
        if self.state != self.STATE_RUNNING:
            return None

        # Fix: Pass self.current_player_id explicitly.
        # If we pass None, scheduler might pick the NEXT ready player (#2) if #1 is already on CD (due to just firing).
        # We want to force #1 to be 'consumed' (or re-consumed/cleared) to allow #2 to go.
        success, pid = self.scheduler.consume_turn(self.current_player_id, current_time)
        if success:
             self.current_player_id = pid
             # Just like skip, we might want a sound, or maybe a 'fail' sound?
             # User said: "Current person released but no effect, need next".
             # So maybe play "cancel" or just silent?
             # Let's return nothing for now, or maybe a distinct click.
             return []
        return None

    def trigger_independent(self, player_id: int, current_time: float) -> Optional[List[str]]:
        """Handles manual trigger for Independent Mode."""
        if self.loop_mode != self.MODE_INDEPENDENT: return None
        
        # Check eligibility
        can_fire, reason = self.scheduler.check_independent_fire(player_id, current_time)
        if can_fire:
             action = self.scheduler.fire_independent_player(player_id, current_time)
             sound_name = f"classes_template/{self.group_id}/{player_id}.mp3"
             return [sound_name]
        
        print(f"[{self.name}] Independent Trigger Blocked P{player_id}: {reason}")
        return None

    def reset_independent(self, player_id: int) -> None:
        """Handles manual reset for Independent Mode."""
        if self.loop_mode != self.MODE_INDEPENDENT: return
        self.scheduler.reset_independent_player(player_id)
        print(f"[{self.name}] Independent Reset P{player_id}")

    def get_ui_state(self, now: float) -> Dict[str, Any]:
        """
        Generates the UI state dictionary for this group.
        Encapsulates the UI logic that was previously in LogicEngine.
        """
        if self.loop_mode == self.MODE_INDEPENDENT:
             # SPECIAL UI STATE FOR INDEPENDENT MODE
             # Fix Time Base Mismatch: Scheduler stores System Time (time.time()), 
             # but LogicEngine passes Countdown Time. We must use System Time here.
             now = time.time()
             
             players_meta = []
             for p in self.scheduler.players:
                 # Calc status
                 state = "IDLE"
                 rem = 0.0
                 total = self.scheduler.buff_duration
                 
                 if now < p.buff_end_time:
                     state = "BUFFING"
                     rem = p.buff_end_time - now
                     total = self.scheduler.buff_duration
                 elif now < p.get_actual_ready_time():
                     state = "CD"
                     rem = p.get_actual_ready_time() - now
                     total = self.scheduler.skill_cooldown
                 
                 players_meta.append({
                     'id': p.id,
                     'state': state,
                     'remaining': round(max(0, rem), 1),
                     'total': total
                 })
                 
             return {
                "id": self.group_id,
                "name": self.name,
                "mode": "independent",
                "players": players_meta,
                # Legacy fields to prevent crashes if UI reads them
                "state": "RUNNING", 
                "index": 0, "next_index": 0, "count": len(players_meta),
                "remaining_interval": 0, "remaining_cd": 0
             }

        if self.state == self.STATE_IDLE:
             return {
                "id": self.group_id,
                "name": self.name,
                "state": self.state,
                "index": 0, # Legacy shim
                "count": 0, # Legacy shim
                "remaining_cd": 0,
                "remaining_interval": 0,
                "total_interval": 100,
                "meta": None
             }
        
        # State Construction Logic (Moved from LogicEngine)
        meta = self.last_action_meta
        
        # Default values
        ui_state = self.state
        rem_cd_disp = 0.0
        rem_int = 0.0
        total_int = self.scheduler.buff_duration 
        next_idx = 1
        
        if meta:
            if meta['action_type'] == 'STOP':
                # Self-Stop logic found in LogicEngine update loop
                pass

            elif meta['action_type'] == 'WAIT':
                rem_int = meta['wait_time']
                
                # Logic: Stabilize Total Interval
                if meta.get('reason') == "Global Buff Active":
                    total_int = self.scheduler.buff_duration
                else:
                    current_reason = meta.get('reason')
                    
                    if self._wait_ctx['reason'] != current_reason:
                            self._wait_ctx['reason'] = current_reason
                            # Use the actual remaining wait time as the full bar duration
                            # This ensures the bar starts at 100% and drops to 0% for the gap duration.
                            self._wait_ctx['total'] = max(0.1, rem_int)
                    
                    total_int = self._wait_ctx['total']

                # Logic: State Overrides
                if self.state == self.STATE_RUNNING:
                     if meta['reason'] == "Cooling Down":
                         ui_state = 'GATING'
                         rem_cd_disp = round(rem_int, 1)

        # Predict Next
        pred_player, pred_reason = self.scheduler.get_predicted_next(now)
        if pred_player:
            next_idx = pred_player.id

        return {
            "id": self.group_id,
            "name": self.name,
            "state": ui_state, 
            "meta": meta, 
            "index": self.current_player_id, 
            "next_index": next_idx, 
            "count": len(self.scheduler.players), 
            "remaining_interval": round(rem_int, 1),
            "remaining_cd": str(rem_cd_disp),
            "total_interval": total_int
        }
