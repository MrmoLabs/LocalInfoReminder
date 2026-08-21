import time
from typing import Dict, List, Set, Tuple, Any, Optional, Union
from core.logger import setup_logger

logger = setup_logger()

class CommandManager:
    """
    Manages command skill cooldowns and tracking.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.command_cds: Dict[str, Any] = {} 
        self.processed_names: Set[str] = set() # optimization for quick lookups
        
        # Pre-process config for faster iterating? 
        # Actually existing logic iterates config to preserve order.

    def trigger_skill(self, skill_config: Dict[str, Any]) -> str:
        name = skill_config['name']
        cooldown = skill_config['cooldown']
        duration = skill_config.get('duration', 0)
        skill_type = skill_config.get('type', 'command')
        sound = skill_config.get('sound', '')
        
        now = time.time()
        
        # [DEBUG] Log previous state
        if name in self.command_cds:
            prev = self.command_cds[name]
            elapsed = now - prev['start_time']
            rem = max(0, prev['cooldown'] - elapsed)
            logger.info(f"[CommandManager] Triggering '{name}' - WAS Active (Rem: {rem:.2f}s). Overwriting/Restarting.")
        else:
            logger.info(f"[CommandManager] Triggering '{name}' - Fresh Start.")

        self.command_cds[name] = {
            'start_time': now,
            'duration': duration,
            'cooldown': cooldown,
            'type': skill_type,
            'threshold_alerted': False,
        }
        
        return sound # LogicEngine will play this

    def update(self, now: float) -> List[Dict[str, Any]]:
        """
        Ticks internal state (cleanup) and returns active command/miracle list for UI.
        """
        active_entries: List[Dict[str, Any]] = []
        processed_names: Set[str] = set()

        # A. Iterate Configured Skills (Preserve Order)
        if 'command_skills' in self.config:
            for skill_cfg in self.config['command_skills']:
                if not skill_cfg.get('is_enabled', True):
                    continue
                
                name = skill_cfg['name']
                processed_names.add(name)
                
                # Check status
                if name in self.command_cds:
                    data = self.command_cds[name]
                    state, rem_show, total = self._calc_status(data, now)
                    
                    # Logic: If READY, we show it as ready (or don't show depending on UI pref, 
                    # but logic says we append with state)
                    # Actually existing logic: If READY, we typically might remove from CDS but we keep in list as "Ready" for UI.
                    
                    if state == 'READY':
                         # If strictly configured, we show it as Ready (0 remaining)
                         pass
                else:
                    # Not in CD tracking -> READY
                    state = 'READY'
                    rem_show = 0
                    total = skill_cfg.get('cooldown', 100)
                    if state != 'ACTIVE': total = skill_cfg.get('cooldown', 100) # Default
                
                active_entries.append({
                    "name": name,
                    "remaining": rem_show,
                    "total_duration": total,
                    "state": state,
                    "type": skill_cfg.get('type', 'command'),
                    "flash_threshold": float(skill_cfg.get('cd_threshold', 0) or 0),
                    "flash_enabled": bool(skill_cfg.get('cd_flash', False)),
                })

        # B. Miracle Skills
        if 'miracle_skills' in self.config:
            for m_cfg in self.config['miracle_skills']:
                if not m_cfg.get('is_enabled', True):
                    continue
                
                name = m_cfg['name']
                processed_names.add(name)
                
                if name in self.command_cds:
                    data = self.command_cds[name]
                    state, rem_show, total = self._calc_status(data, now)
                else:
                    state = 'READY'
                    rem_show = 0
                    total = m_cfg.get('cooldown', 100)
                
                active_entries.append({
                    "name": name,
                    "remaining": rem_show,
                    "total_duration": total,
                    "state": state,
                    "type": "miracle",
                    # [NEW] Inject Per-Skill Flash Threshold
                    "flash_threshold": m_cfg.get('flash_threshold', 0) 
                })

        # C. Check for Dynamic/Legacy Skills NOT in Config
        keys_to_remove = []
        for name, data in self.command_cds.items():
            if name in processed_names:
                continue
            
            # Legacy/Dynamic
            state, rem_show, total = self._calc_status(data, now)
            
            if state == 'READY':
                keys_to_remove.append(name)
                continue
                
            active_entries.append({
                "name": name,
                "remaining": rem_show,
                "total_duration": total,
                "state": state,
                "type": data.get('type', 'command')
            })

        # Cleanup expired dynamic entries
        for name in keys_to_remove:
            del self.command_cds[name]

        return active_entries

    def collect_due_audio_notifications(self, now: float) -> List[str]:
        """Returns cooldown-threshold audio cues that should fire on this tick."""
        due_sounds: List[str] = []

        for skill_cfg in self.config.get('command_skills', []):
            if not skill_cfg.get('is_enabled', True):
                continue

            threshold = float(skill_cfg.get('cd_threshold', 0) or 0)
            if threshold <= 0:
                continue

            name = skill_cfg.get('name')
            data = self.command_cds.get(name)
            if not data:
                continue

            state, remaining, _ = self._calc_status(data, now)
            if state != 'COOLDOWN' or remaining > threshold:
                continue

            if data.get('threshold_alerted', False):
                continue

            data['threshold_alerted'] = True
            sound = skill_cfg.get('cd_sound', '')
            if sound and not skill_cfg.get('is_muted', False):
                due_sounds.append(sound)

        return due_sounds

    def _calc_status(self, data: Any, now: float) -> Tuple[str, float, float]:
        # Support legacy tuple (expiry, total)
        if isinstance(data, tuple):
             expiry, total = data
             rem = expiry - now
             if rem <= 0: return 'READY', 0, total
             return 'COOLDOWN', rem, total
        
        # Dict
        start_time = data['start_time']
        duration = data['duration']
        cooldown = data['cooldown']
        elapsed = now - start_time
        
        if elapsed < duration:
            return 'ACTIVE', duration - elapsed, duration
        
        remaining = cooldown - elapsed
        if remaining > 0:
            # We are past duration, but still within cooldown.
            # Gap Total = Total Cooldown - Active Duration
            # This is the "b - a" the user requested.
            gap = max(0.1, cooldown - duration)
            
            return 'COOLDOWN', remaining, gap
        
        return 'READY', 0, cooldown
