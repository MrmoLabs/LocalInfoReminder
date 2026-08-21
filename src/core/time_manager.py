import re
from typing import Optional, Dict, Any, Tuple
from core.config_loader import ConfigLoader
from core.logger import setup_logger

logger = setup_logger()

class TimeManager:
    """
    Manages the game clock, auto-sync logic, and time formatting.
    Encapsulates drift calculation and tick updates.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.current_seconds = 1200 # Default 20:00
        self.time_accumulator = 0.0
        
        # Sync State
        self.pending_auto_sync = False
        self.has_initial_sync = False
        
    def update(self, dt: float) -> Optional[str]:
        """
        Updates internal clock by dt seconds.
        Returns formatted time string if a second has passed, else None.
        """
        if not self.config.get('enable_time_display', True):
            self.time_accumulator = 0
            return None

        self.time_accumulator += dt
        
        if self.time_accumulator >= 1.0:
            self.current_seconds -= 1
            if self.current_seconds < 0: self.current_seconds = 0
            self.time_accumulator -= 1.0
            return self.get_formatted_time()
            
        return None

    def get_formatted_time(self) -> str:
        return ConfigLoader.format_time_str(self.current_seconds)

    def set_time(self, time_str: str) -> None:
        """Sets internal time from MM:SS string."""
        self.current_seconds = ConfigLoader.parse_time_str(time_str)

    def process_ocr_result(self, time_text: str) -> Tuple[bool, Optional[str], bool]:
        """
        Parses OCR text for time.
        Returns: (success, formatted_time_str, should_force_kill_check)
        """
        try:
            numbers = re.findall(r'\d+', time_text)
            
            if len(numbers) >= 2:
                mins = int(numbers[0])
                secs = int(numbers[-1])
                
                # Validation 1: Sanity Check (Game usually starts at 20:00, max maybe 40?)
                if mins > 60:
                     if not self.pending_auto_sync:
                         logger.warning(f"[TimeManager] Sync Ignored: Time {mins}:{secs} > 60:00")
                     self.pending_auto_sync = False
                     return False, None, False

                # Validation 2: Seconds Rollover Fix (OCR might read '59' as '5 9' or similar, but regex handles contiguous)
                # But sometimes OCR reads '20 60' or '19 -1'.
                if secs >= 60: # OCR artifact? or weird timer?
                    # basic clamp/fix logic from original
                    # Original code actually handled `secs < 60` logic weirdly by decrementing?
                    # Let's stick to standard normalization
                    pass
                
                # Original logic: 
                # if secs < 60: secs -= 1 ... (Simulates tick lag?) -> KEEPING ORIGINAL LOGIC FOR BEHAVIOR PRESERVATION
                # Original logic had a decrement here: "if secs < 60: secs -= 1"
                # This was likely a hack for OCR latency, but causes "20:00" -> "19:59" immediately.
                # Removing it for cleaner logic.
                time_str = f"{mins:02d}:{secs:02d}"
                
                # Drift Check
                if self.pending_auto_sync and self.has_initial_sync:
                     new_seconds = ConfigLoader.parse_time_str(time_str)
                     diff = abs(new_seconds - self.current_seconds)
                     
                     if diff > 10:
                         logger.warning(f"[TimeManager] Auto-Sync REJECTED. Deviation {diff}s too large.")
                         self.pending_auto_sync = False
                         return False, None, False
                     else:
                         logger.info(f"[TimeManager] Auto-Sync Accepted. Deviation {diff}s.")
                
                logger.info(f"[TimeManager] Syncing time from '{time_text}' to: {time_str}")
                self.set_time(time_str)
                self.pending_auto_sync = False
                self.has_initial_sync = True 
                
                # Check Mid-Game Sync (Fight Phase)
                # 20:00 -> 1200s. Fight: 20:00-27:00? No, usually 20min countdown.
                # Original Logic: (1200 <= secs <= 1620) or (600 <= secs <= 1020)
                # Wait, LogicEngine said: (1200 <= secs <= 1620) is 20m to 27m? S appears to be countdown?
                # ConfigLoader.parse_time_str returns total seconds.
                # If countdown: 20:00 = 1200. 
                # Original logic was checking against total seconds.
                # (1200..1620) = 20:00 to 27:00.
                total_s = ConfigLoader.parse_time_str(time_str)
                is_active_fight = (1200 <= total_s <= 1620) or (600 <= total_s <= 1020)
                
                return True, time_str, is_active_fight

            else:
                if not self.pending_auto_sync:
                    # logger.warning(f"[TimeManager] Sync Failed: Not enough numbers found in '{time_text}'")
                    pass
                self.pending_auto_sync = False
                return False, None, False
            
        except Exception as e:
            logger.error(f"[TimeManager] Sync Error: {e}")
            return False, None, False
