from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar)
from PyQt6.QtGui import QFont
from core.localization import LocalizationManager
from core.localization import LocalizationManager

class EnemyListWidget(QWidget):
    """
    Manages the display of enemy cooldowns.
    Optimized to update existing widgets instead of full rebuilds where possible.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.loc = LocalizationManager()
        self.setStyleSheet("background: transparent; border: none;")
        self.loc = LocalizationManager()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        
        # Cache widgets: name -> container_widget
        self.widgets = {} 
        self.flash_threshold = 3.0 # Default

    def set_flash_threshold(self, val):
        self.flash_threshold = float(val)

    def update_state(self, enemies_data):
        """
        Updates the list based on the provided data list.
        Data format: [{'name': '...', 'remaining': 10, 'total_duration': 100, 'state': '...', 'type': '...'}, ...]
        """
        current_names = set()
        
        # 1. Update or Create
        for i, enemy in enumerate(enemies_data):
            name = enemy['name']
            current_names.add(name)
            
            if name not in self.widgets:
                self._create_row(name, i)
            
            # Ensure order (re-insert if index changed? naive append for now, 
            # but usually order is stable. If unstable, layout.insertWidget is needed)
            # For simplicity, we assume stable config order.
            
            self._update_row(name, enemy)

        # 2. Key Removals (Stale entries)
        for name in list(self.widgets.keys()):
            if name not in current_names:
                w = self.widgets[name]['container']
                w.deleteLater()
                del self.widgets[name]

    def _create_row(self, name, index):
        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(2)
        
        # Header: Name + Time
        header_layout = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Segoe UI", 10)) # Increased from 9
        name_lbl.setStyleSheet("color: #E0E0E0; background: transparent;")
        
        time_lbl = QLabel("")
        time_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold)) # Increased from 9
        # Default style with background for better visibility
        time_lbl.setStyleSheet("""
            color: #FF5555; 
            background-color: rgba(0, 0, 0, 0.6); 
            border-radius: 4px;
            padding: 0px 4px;
        """)
        
        header_layout.addWidget(name_lbl)
        header_layout.addStretch()
        header_layout.addWidget(time_lbl)
        
        # Progress Bar
        bar = QProgressBar()
        bar.setFixedHeight(4)
        bar.setTextVisible(False)
        # Default style
        bar.setStyleSheet("""
            QProgressBar { border: none; background-color: rgba(0, 0, 0, 0.3); border-radius: 3px; }
            QProgressBar::chunk { background-color: #6C7086; border-radius: 3px; }
        """)
        
        v_layout.addLayout(header_layout)
        v_layout.addWidget(bar)
        
        self.layout.insertWidget(index, container)
        
        self.widgets[name] = {
            'container': container,
            'time_lbl': time_lbl,
            'name_lbl': name_lbl, # [FIX] Store name label
            'bar': bar,
            'last_state': None # Optimization
        }
        
        # Apply current scale if exists
        if hasattr(self, 'current_scale'):
             self._apply_row_scale(self.widgets[name], self.current_scale)

    def _update_row(self, name, data):
        w_map = self.widgets[name]
        time_lbl = w_map['time_lbl']
        bar = w_map['bar']
        
        state = data.get('state', 'COOLDOWN')
        remaining = data.get('remaining', 0)
        total = data.get('total_duration', 100)
        skill_type = data.get('type', 'enemy')
        
        # Text Logic
        state_text = ""
        time_text = f"{int(remaining)}s"
        
        if state == "ACTIVE":
            state_text = self.loc.get("UI_ACTIVE_SUFFIX")
        elif state == "READY":
            state_text = ""
            time_text = self.loc.get("UI_READY")
            
        time_lbl.setText(f"{time_text}{state_text}")
        
        # Bar & Color Logic
        color = "#6C7086"
        val = 0
        
        if state == 'ACTIVE':
            bar.setRange(0, int(total * 10)) 
            val = int(remaining * 10)
            if skill_type == 'ally':
                 color = "#89B4FA" 
            elif skill_type == 'miracle':
                 color = "#89DCEB" # Cyan for Miracle
            else:
                 color = "#FF5555"
        elif state == 'COOLDOWN':
            bar.setRange(0, int(total * 10)) 
            val = int(remaining * 10)
            if skill_type == 'miracle':
                 color = "#89DCEB" # Keep Cyan for visibility or use a shade
            else:
                 color = "#6C7086"
        elif state == 'READY':
            bar.setRange(0, 100)
            val = 100
            color = "#A6E3A1"
            
        bar.setValue(val)

        # Style Update (Optimization: only set stylesheet on change)
        # However, for color dynamic changes we might need to set it.
        # Ideally we only set it if color changed.
        
        # Calculate Flash State for Key (0=None, 1=Red, 2=White)
        flash_state = 0
        
        # [NEW] Determine Threshold: miracles can fall back to global; command skills use their own CD threshold
        row_threshold = float(data.get('flash_threshold', 0) or 0)
        if skill_type == 'miracle':
            final_threshold = row_threshold if row_threshold > 0 else self.flash_threshold
            should_flash = state == 'COOLDOWN' and 0 < remaining <= final_threshold
        else:
            final_threshold = row_threshold
            should_flash = (
                state == 'COOLDOWN'
                and bool(data.get('flash_enabled', False))
                and final_threshold > 0
                and 0 < remaining <= final_threshold
            )

        if should_flash:
            import time
            flash_state = 1 if int(time.time() * 3.33) % 2 == 0 else 2
        
        current_style_key = (state, skill_type, flash_state)
        if w_map.get('last_style_key') != current_style_key:
             w_map['last_style_key'] = current_style_key
             
             base_time_style = """
                background-color: rgba(0, 0, 0, 0.6); 
                border-radius: 4px;
                padding: 0px 4px;
             """
             
             # [FIX] Use transparent border to prevent layout shift (2px reserved)
             container_style = "background: transparent; border: 2px solid transparent; border-radius: 6px;"

             # Specific text color for READY
             if state == 'READY':
                 time_lbl.setStyleSheet(f"color: #A6E3A1; font-weight: bold; {base_time_style}")
             else:
                 # Active/Cooldown Color
                 txt_col = "#FF5555"

                 if skill_type == 'miracle':
                     txt_col = "#89DCEB"

                 if flash_state == 1:
                     container_style = "background: transparent; border: 2px solid #FF5555; border-radius: 6px;"
                 elif flash_state == 2:
                     container_style = "background: transparent; border: 2px solid #FFFFFF; border-radius: 6px;"
                 
                 time_lbl.setStyleSheet(f"color: {txt_col}; {base_time_style}")

             # Apply to Container
             w_map['container'].setStyleSheet(container_style)

             bar.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    background-color: rgba(0, 0, 0, 0.3);
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 3px;
                }}
            """)

    def set_scale(self, scale: float):
        self.current_scale = scale
        
        # Scale all existing rows
        for w_map in self.widgets.values():
            self._apply_row_scale(w_map, scale)

    def _apply_row_scale(self, w_map, scale):
        # Fonts
        base_name = 10
        base_time = 12
        
        s_name = max(8, int(base_name * scale))
        s_time = max(9, int(base_time * scale))
        
        # Name Label is actually part of layout, we didn't store it explicitly in map!
        # Wait, we need to store name_lbl too if we want to resize it.
        # Checking _create_row... we didn't store 'name_lbl'. 
        # We need to find it or modify _create_row to store it.
        # Let's fix _create_row first. But for now, let's look at children of container?
        # Container -> VLayout -> [HLayout, Bar]
        # HLayout -> [Name, Stretch, Time]
        
        # Access via container children is fragile. Let's update _create_row storage first.
        # But wait, I can edit _create_row below.
        
        if 'name_lbl' in w_map:
            w_map['name_lbl'].setFont(QFont("Segoe UI", s_name))
        
        if 'time_lbl' in w_map:
            w_map['time_lbl'].setFont(QFont("Segoe UI", s_time, QFont.Weight.Bold))
            
        if 'bar' in w_map:
            h_bar = max(2, int(4 * scale))
            w_map['bar'].setFixedHeight(h_bar)


