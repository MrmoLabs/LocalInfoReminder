from typing import Dict, Any, List, Union

class KeyMapper:
    """
    Responsibilities:
    1. Parse raw configuration dictionaries.
    2. Build optimized lookup maps for Key -> Class/Skill.
    3. Normalize hotkey strings to lowercase.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.keypad_map: Dict[str, Any] = {} # 'num_1' -> class_id or List[dict]
        self.skip_map: Dict[str, str] = {}   # '4' -> class_id
        self.skill_map: Dict[str, Dict] = {} # 'ctrl+c' -> skill_config
        
        self._build_maps()

    def _build_maps(self):
        """
        Parses `classes_template` and `command_skills` from config.
        Populates self.keypad_map, self.skip_map, self.skill_map.
        """
        print(f"[KeyMapper] Building maps...")
        
        # 1. Class Bindings
        if 'classes_template' in self.config and self.config.get('enable_classes', True):
            for c in self.config['classes_template']:
                if not c.get('is_enabled', True): continue
                    
                cid = c['id']
                
                # Standard Hotkey
                hotkey = self._normalize_hotkey(c.get('default_hotkey', ''))
                if hotkey:
                    hotkey = hotkey.lower()
                    self.keypad_map[hotkey] = cid 
                    print(f"[KeyMapper] Mapped '{hotkey}' -> {cid}")
                    
                # Skip With CD Hotkey
                skip_hk = self._normalize_hotkey(c.get('skip_cd_hotkey', ''))
                if skip_hk:
                    skip_hk = skip_hk.lower()
                    self.skip_map[skip_hk] = cid
                    print(f"[KeyMapper] Mapped SkipCD '{skip_hk}' -> {cid}")

                # Independent Mode Hotkeys
                indep_keys = c.get('independent_hotkeys', [])
                if indep_keys:
                    for idx, key in enumerate(indep_keys):
                        k = self._normalize_hotkey(key)
                        if k:
                            k = k.lower()
                            # Support Multiple Bindings: Store as List of Dicts
                            if k not in self.keypad_map:
                                self.keypad_map[k] = []
                            elif isinstance(self.keypad_map[k], str) or isinstance(self.keypad_map[k], dict):
                                # Convert existing single entry to list
                                self.keypad_map[k] = [self.keypad_map[k]]
                            
                            entry = {
                                'cid': cid,
                                'type': 'strict_trigger',
                                'pid': idx + 1
                            }
                            self.keypad_map[k].append(entry)
                            print(f"[KeyMapper] Mapped Independent P{idx+1} '{k}' -> {cid}")

        # 2. Command Skills
        if 'command_skills' in self.config and self.config.get('enable_command_skills', True):
            for skill in self.config['command_skills']:
                if not skill.get('is_enabled', True): continue
                
                hotkey = self._normalize_hotkey(skill.get('default_hotkey', ''))
                if hotkey:
                    hotkey = hotkey.lower()
                    self.skill_map[hotkey] = skill
                    print(f"[KeyMapper] Mapped Skill '{hotkey}' -> {skill['name']}")

        # 3. Miracle Skills
        if 'miracle_skills' in self.config and self.config.get('enable_miracle_skills', True):
            for m_skill in self.config['miracle_skills']:
                if not m_skill.get('is_enabled', True): continue
                
                hotkey = self._normalize_hotkey(m_skill.get('default_hotkey', ''))
                if hotkey:
                    hotkey = hotkey.lower()
                    # Miracle skills are handled like command skills for trigger/cooldown tracking
                    self.skill_map[hotkey] = m_skill
                    print(f"[KeyMapper] Mapped Miracle '{hotkey}' -> {m_skill['name']}")

    @staticmethod
    def _normalize_hotkey(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if text.lower() in {"click to set", "recording..."}:
            return ""
        return text

    def get_entries(self, key: str) -> List[Any]:
        """
        Returns a list of binding entries for a given key.
        Normalizes single entries to a list for uniform processing.
        """
        raw = self.keypad_map.get(key)
        if not raw:
            return []
        return raw if isinstance(raw, list) else [raw]

    def get_skip_cid(self, key: str) -> Union[str, None]:
        return self.skip_map.get(key)
        
    def get_skill_config(self, key: str) -> Union[Dict, None]:
        return self.skill_map.get(key)
