from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QProgressBar)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from core.localization import LocalizationManager

class GroupRowWidget(QWidget):
    """
    Represents a single group/class row in the ally panel.
    Handles creation and strict property updaters to minimize flickering.
    """
    def __init__(self, class_id, logic_engine, parent=None):
        super().__init__(parent)
        self.class_id = class_id
        self.logic = logic_engine
        self.loc = LocalizationManager()
        self.last_state = None
        self.mode = "standard" # standard vs independent
        
        self.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        
        self._init_standard_ui()

    def _init_standard_ui(self):
        # Clear existing
        self._clear_layout_recursive(self.layout)

        # --- UI Construction ---
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)
        
        # 1. Big Number (Next/Current High Level Step)
        self.lbl_big = QLabel("1")
        self.lbl_big.setFont(QFont("Segoe UI", 20, QFont.Weight.Normal)) # Init with 20 to avoid jump
        self.lbl_big.setFixedWidth(24)
        self.lbl_big.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_big.setStyleSheet("color: #A6E3A1; background: transparent;")
        
        # 2. Info Column
        info_col = QWidget()
        info_col_layout = QVBoxLayout(info_col)
        info_col_layout.setContentsMargins(0, 0, 0, 0)
        info_col_layout.setSpacing(0)
        
        # Row 1: Name + Misc
        row1_widget = QWidget()
        row1_layout = QHBoxLayout(row1_widget)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(8)
        
        self.lbl_name = QLabel("Unknown") # To be set by update
        self.lbl_name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: #CDD6F4; background: transparent;")
        
        self.lbl_misc = QLabel(self.loc.get("UI_TOTAL").format(0))
        self.lbl_misc.setFont(QFont("Segoe UI", 9))
        self.lbl_misc.setStyleSheet("color: #6C7086; background: transparent;")
        
        row1_layout.addWidget(self.lbl_name)
        row1_layout.addWidget(self.lbl_misc)
        row1_layout.addStretch()
        
        # Row 2: Next
        self.lbl_next = QLabel(self.loc.get("UI_NEXT").format("-"))
        self.lbl_next.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_next.setStyleSheet("color: #F9E2AF; background: transparent;")
        
        info_col_layout.addWidget(row1_widget)
        info_col_layout.addWidget(self.lbl_next)
        
        # Controls
        self.btn_toggle = QPushButton("▶")
        self.btn_toggle.setFixedSize(20, 20)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self._on_toggle)
        
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setFixedSize(20, 20)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.clicked.connect(self._on_stop)
        
        btn_style = """
            QPushButton { background-color: rgba(255, 255, 255, 0.1); border-radius: 4px; color: white; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.2); }
        """
        self.btn_toggle.setStyleSheet(btn_style)
        self.btn_stop.setStyleSheet(btn_style)
        
        top_row.addWidget(self.lbl_big)
        top_row.addWidget(info_col)
        top_row.addStretch()
        top_row.addWidget(self.btn_toggle)
        top_row.addWidget(self.btn_stop)
        
        # Progress Bar
        self.bar = QProgressBar()
        self.bar.setFixedHeight(4)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet("QProgressBar { border: none; background-color: rgba(0,0,0,0.3); border-radius: 2px; } QProgressBar::chunk { background-color: #A6E3A1; border-radius: 2px; }")
        
        self.layout.addLayout(top_row)
        self.layout.addWidget(self.bar)

        self.mode = "standard"

    def _clear_layout_recursive(self, layout):
        if not layout: return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout_recursive(item.layout())
                item.layout().deleteLater()

    def _init_independent_ui(self, count):
        # Clear existing
        self._clear_layout_recursive(self.layout)
                
        # Header (Name Only)
        header = QHBoxLayout()
        self.lbl_name_indep = QLabel("Name")
        self.lbl_name_indep.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_name_indep.setStyleSheet("color: #CDD6F4; background: transparent;")
        header.addWidget(self.lbl_name_indep)
        header.addStretch()
        self.layout.addLayout(header)
        
        # Grid of Bars
        self.indep_bars = []
        for i in range(count):
             row = QHBoxLayout()
             row.setSpacing(4)
             
             # Index
             lbl = QLabel(f"{i+1}")
             lbl.setFixedWidth(16)
             lbl.setStyleSheet("color: #A6E3A1; font-weight: bold;")
             
             # Bar
             bar = QProgressBar()
             bar.setFixedHeight(8) # Slightly thicker
             bar.setTextVisible(False)
             bar.setStyleSheet("QProgressBar { border: none; background-color: rgba(0,0,0,0.3); border-radius: 2px; } QProgressBar::chunk { background-color: #A6E3A1; border-radius: 2px; }")
             
             # Status Text
             status_lbl = QLabel(self.loc.get("UI_READY"))
             status_lbl.setFixedWidth(40) # Ensure space for "XX.Xs"
             status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
             status_lbl.setStyleSheet("color: #CDD6F4; font-size: 10px;")
             
             row.addWidget(lbl)
             row.addWidget(bar)
             row.addWidget(status_lbl)
             
             self.layout.addLayout(row)
             self.indep_bars.append((lbl, bar, status_lbl))
             
        self.mode = "independent"

    def _on_toggle(self):
        self.logic.toggle_class_state(self.class_id)
        
    def _on_stop(self):
        self.logic.stop_class(self.class_id)

    def update_state(self, cls_data):
        # Check Mode Switch
        mode = cls_data.get('mode', 'standard')
        
        if mode == 'independent':
             if self.mode != 'independent' or len(self.indep_bars) != cls_data['count']:
                  self._init_independent_ui(cls_data['count'])
             
             self.lbl_name_indep.setText(cls_data['name'])
             
             players = cls_data.get('players', [])
             for i, p_meta in enumerate(players):
                 if i >= len(self.indep_bars): break
                 
                 lbl, bar, status_lbl = self.indep_bars[i]
                 
                 state = p_meta['state']
                 rem = p_meta['remaining']
                 total = p_meta['total']
                 
                 if state == 'BUFFING':
                      bar.setStyleSheet("QProgressBar::chunk { background-color: #A6E3A1; }") # Green
                      val = 100
                      if total > 0: val = int((rem / total) * 100) # Count down
                      bar.setValue(val)
                      status_lbl.setText(f"{rem:.1f}s")
                      status_lbl.setStyleSheet("color: #A6E3A1; font-size: 10px;")
                      
                 elif state == 'CD':
                      bar.setStyleSheet("QProgressBar::chunk { background-color: #89B4FA; }") # Blue
                      val = 0
                      if total > 0: val = int((rem / total) * 100) # Count down
                      bar.setValue(val)
                      status_lbl.setText(f"{rem:.1f}s")
                      status_lbl.setStyleSheet("color: #89B4FA; font-size: 10px;")

                 else:
                      bar.setValue(0)
                      status_lbl.setText(self.loc.get("UI_READY"))
                      status_lbl.setStyleSheet("color: #CDD6F4; font-size: 10px;")
                      
             return

        # Standard Mode Update
        if self.mode == 'independent':
             self._init_standard_ui()

        self.lbl_name.setText(cls_data['name'])
        
        # Logic for Numbers
        idx = cls_data['index']
        count = cls_data['count']
        state = cls_data['state']
        
        if state == 'IDLE':
            display_main = 1
            next_val = 2 if count > 1 else 1 
        else:
            display_main = max(1, idx)
            next_val = cls_data.get('next_index', 1)
            
        # Text Update Logic
        if state == 'GATING':
            self.lbl_big.setText("CD")
        else:
            self.lbl_big.setText(str(display_main))

        self.lbl_next.setText(self.loc.get("UI_NEXT").format(next_val))

        # Misc Label
        if cls_data['remaining_cd'] != "0.0" and state == 'GATING':
            self.lbl_misc.setText(f"CD: {cls_data['remaining_cd']}s")
            self.lbl_misc.setStyleSheet("color: #89B4FA; background: transparent;")
        else:
            self.lbl_misc.setText(self.loc.get("UI_TOTAL").format(count))
            self.lbl_misc.setStyleSheet("color: #6C7086; background: transparent;")
             
        # Update Bar
        total = cls_data.get('total_interval', 10)
        remaining = cls_data.get('remaining_interval', 0)
        if total > 0:
            self.bar.setRange(0, int(total * 10))
            self.bar.setValue(int(remaining * 10))
        else:
            self.bar.setValue(0)
            
        # Style Updates
        self._update_style(state)

    def _update_style(self, current_state):
        if current_state == self.last_state:
            return
            
        self.last_state = current_state
        
        COLOR_RUNNING = "#A6E3A1" # Green
        COLOR_PAUSED = "#F9E2AF" # Yellow
        COLOR_CD = "#89B4FA" # Blue
        COLOR_IDLE = "#6C7086" # Grey
        
        # Scale Fonts
        scale = getattr(self, 'current_scale', 1.0)
        size_big = max(12, int(20 * scale))
        size_big_gating = max(10, int(16 * scale))
        
        font_running = QFont("Segoe UI", size_big, QFont.Weight.Bold)
        font_idle = QFont("Segoe UI", size_big, QFont.Weight.Normal)
        font_gating = QFont("Segoe UI", size_big_gating, QFont.Weight.Bold)
        
        # Check standard widgets existence before styling
        if self.mode != 'standard':
            return
            
        try:
            if current_state == 'RUNNING':
                self.lbl_big.setFont(font_running)
                self.lbl_big.setStyleSheet(f"color: {COLOR_RUNNING}; background: transparent;")
                self.bar.setStyleSheet(f"QProgressBar {{ border: none; background-color: rgba(0,0,0,0.3); border-radius: 2px; }} QProgressBar::chunk {{ background-color: {COLOR_RUNNING}; border-radius: 2px; }}")
                self.btn_toggle.setText("⏸")
                self.btn_toggle.setToolTip(self.loc.get("UI_PAUSE"))
                
            elif current_state == 'PAUSED':
                self.lbl_big.setFont(font_running)
                self.lbl_big.setStyleSheet(f"color: {COLOR_PAUSED}; background: transparent;")
                self.bar.setStyleSheet(f"QProgressBar {{ border: none; background-color: rgba(0,0,0,0.3); border-radius: 2px; }} QProgressBar::chunk {{ background-color: {COLOR_PAUSED}; border-radius: 2px; }}")
                self.btn_toggle.setText("▶")
                self.btn_toggle.setToolTip(self.loc.get("UI_RESUME"))

            elif current_state == 'GATING':
                self.lbl_big.setFont(font_gating)
                self.lbl_big.setStyleSheet(f"color: {COLOR_CD}; background: transparent;")
                self.bar.setStyleSheet(f"QProgressBar {{ border: none; background-color: rgba(0,0,0,0.3); border-radius: 2px; }} QProgressBar::chunk {{ background-color: {COLOR_CD}; border-radius: 2px; }}")
                self.btn_toggle.setText("⏸") 

            else: # IDLE
                self.lbl_big.setFont(font_idle)
                self.lbl_big.setStyleSheet(f"color: {COLOR_IDLE}; background: transparent;")
                self.bar.setStyleSheet(f"QProgressBar {{ border: none; background-color: rgba(0,0,0,0.3); border-radius: 2px; }} QProgressBar::chunk {{ background-color: {COLOR_IDLE}; border-radius: 2px; }}")
                self.btn_toggle.setText("▶")
                self.btn_toggle.setToolTip(self.loc.get("UI_START_ACTION"))
        except RuntimeError:
            pass

    def set_scale(self, scale: float):
        self.current_scale = scale
        
        # Info Fonts
        base_name = 10
        base_misc = 9
        base_next = 10
        
        s_name = max(8, int(base_name * scale))
        s_misc = max(7, int(base_misc * scale))
        s_next = max(8, int(base_next * scale))
        
        # Standard Mode Widgets
        if self.mode == 'standard':
            if hasattr(self, 'lbl_name') and self.lbl_name:
                try:
                    self.lbl_name.setFont(QFont("Segoe UI", s_name, QFont.Weight.Bold))
                    self.lbl_misc.setFont(QFont("Segoe UI", s_misc))
                    self.lbl_next.setFont(QFont("Segoe UI", s_next, QFont.Weight.Bold))
                    
                    # Big Number Width (Scale 24)
                    w_big = max(16, int(24 * scale))
                    self.lbl_big.setFixedWidth(w_big)
                    
                    # Bar Height
                    h_bar = max(2, int(4 * scale))
                    self.bar.setFixedHeight(h_bar)
                    
                    # Buttons
                    s_btn = max(14, int(20 * scale))
                    self.btn_toggle.setFixedSize(s_btn, s_btn)
                    self.btn_stop.setFixedSize(s_btn, s_btn)
                    
                except RuntimeError:
                    # Widget might be deleted but mode update pending?
                    pass
        
        # Independent Mode Widgets
        elif self.mode == 'independent':
             if hasattr(self, 'lbl_name_indep') and self.lbl_name_indep:
                 try:
                     s_indep_name = max(8, int(10 * scale))
                     self.lbl_name_indep.setFont(QFont("Segoe UI", s_indep_name, QFont.Weight.Bold))
                     
                     for (lbl, bar, status) in self.indep_bars:
                         # Index
                         lbl.setFont(QFont("Segoe UI", max(7, int(9 * scale)), QFont.Weight.Bold))
                         lbl.setFixedWidth(max(10, int(16 * scale)))
                         
                         # Bar
                         bar.setFixedHeight(max(4, int(8 * scale)))
                         
                         # Status
                         status.setFont(QFont("Segoe UI", max(7, int(10 * scale))))
                         status.setFixedWidth(max(25, int(40 * scale)))
                 except RuntimeError:
                     pass
                 
        # Force re-style to update big font (Only if standard logic applies or we update universally?)
        if self.mode == 'standard':
            try:
                ls = self.last_state
                self.last_state = None
                self._update_style(ls if ls else 'IDLE')
            except RuntimeError:
                pass
