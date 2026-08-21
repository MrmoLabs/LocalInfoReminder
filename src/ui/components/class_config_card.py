from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, 
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox)
from PyQt6.QtCore import Qt

# Assume HotkeyRecorder is available in the same scope or imported. 
# Since we are pasting this INTO config_editor.py, we don't import it.

class ClassConfigCard(QFrame):
    """
    Card-based widget for configuring a specific Class.
    Merges template data (name, id, interval, etc.) and session data (count, mode).
    """
    def __init__(self, template_data, session_data, parent=None):
        super().__init__(parent)
        self.template_data = template_data
        self.session_data = session_data
        
        # Merge session data into a working dict for initialization (optional, but helpful)
        # We will read from widgets directly on save.
        
        self.setObjectName("ConfigCard")
        self.setStyleSheet("""
            #ConfigCard {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            #ConfigCard:hover {
                border: 1px solid #b0b0b0;
                background-color: #fdfdfd;
            }
            QLabel { color: #555; }
        """)
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # === 1. Header (Checkbox, Name, ID, Mute) ===
        row_header = QHBoxLayout()
        
        # Enabled Checkbox
        self.chk_enabled = QCheckBox()
        self.chk_enabled.setChecked(self.template_data.get("is_enabled", True))
        self.chk_enabled.setToolTip("启用此职业")
        
        # Name
        lbl_name = QLabel(self.template_data.get("name", "Unknown"))
        lbl_name.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold)) # Explicit Font
        lbl_name.setStyleSheet("color: #333;")
        
        # ID
        lbl_id = QLabel(f"ID: {self.template_data.get('id', '')}")
        lbl_id.setStyleSheet("color: #999; font-size: 11px;")
        
        # Mute Button
        self.btn_mute = QPushButton("静音")
        self.btn_mute.setCheckable(True)
        self.btn_mute.setChecked(self.template_data.get("is_muted", False))
        self.btn_mute.setFixedWidth(50)
        self.btn_mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mute.setStyleSheet("""
            QPushButton { background-color: #f0f0f0; border: none; border-radius: 4px; color: #666; font-size: 11px; padding: 2px;}
            QPushButton:checked { background-color: #ffcccc; color: #cc0000; }
        """)
        
        row_header.addWidget(self.chk_enabled)
        row_header.addWidget(lbl_name)
        row_header.addWidget(lbl_id)
        row_header.addStretch()
        row_header.addWidget(self.btn_mute)
        
        main_layout.addLayout(row_header)
        
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #f0f0f0; max-height: 1px;")
        main_layout.addWidget(line)
        
        # === 2. Configuration Area (Grid-like) ===
        content_layout = QHBoxLayout()
        
        # Left: Params
        params_layout = QVBoxLayout()
        params_layout.setSpacing(6)
        
        def create_param_row(label, widget):
            r = QHBoxLayout()
            l = QLabel(label)
            l.setFixedWidth(70)
            l.setStyleSheet("font-size: 11px;") 
            r.addWidget(l)
            r.addWidget(widget)
            return r
            
        # Cooldown
        self.spin_cooldown = QDoubleSpinBox()
        self.spin_cooldown.setRange(0, 9999)
        self.spin_cooldown.setSingleStep(0.5)
        self.spin_cooldown.setValue(float(self.template_data.get("cooldown", 0)))
        self.spin_cooldown.setSuffix(" s")
        params_layout.addLayout(create_param_row("冷却时间:", self.spin_cooldown))
        
        # Interval
        self.spin_interval = QDoubleSpinBox()
        self.spin_interval.setRange(0, 9999)
        self.spin_interval.setSingleStep(0.1)
        self.spin_interval.setValue(float(self.template_data.get("interval", 0)))
        self.spin_interval.setSuffix(" s")
        params_layout.addLayout(create_param_row("触发间隔:", self.spin_interval))
        
        # Mode
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["循环 (Loop)", "单次 (Single)", "步进 (Step)"])
        self.combo_mode.setCurrentIndex(self.session_data.get("mode_index", 0))
        params_layout.addLayout(create_param_row("运行模式:", self.combo_mode))
        
        # Count
        self.spin_count = QSpinBox()
        self.spin_count.setRange(0, 99)
        self.spin_count.setValue(int(self.session_data.get("count", 0)))
        params_layout.addLayout(create_param_row("人数配置:", self.spin_count))
        
        content_layout.addLayout(params_layout, stretch=1)
        
        # Right: Hotkeys
        hotkey_frame = QFrame()
        hotkey_frame.setStyleSheet("background-color: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;")
        hotkey_layout = QVBoxLayout(hotkey_frame)
        hotkey_layout.setContentsMargins(8, 8, 8, 8)
        
        hotkey_layout.addWidget(QLabel("⌨️ 默认热键"))
        self.hk_default = HotkeyRecorder(self.template_data.get("default_hotkey", ""))
        self.hk_default.setFixedHeight(24)
        hotkey_layout.addWidget(self.hk_default)
        
        hotkey_layout.addSpacing(4)
        
        hotkey_layout.addWidget(QLabel("⏩ 跳过热键"))
        self.hk_skip = HotkeyRecorder(self.template_data.get("skip_cd_hotkey", ""))
        self.hk_skip.setFixedHeight(24)
        hotkey_layout.addWidget(self.hk_skip)
        
        hotkey_layout.addStretch()
        content_layout.addWidget(hotkey_frame, stretch=1)
        
        main_layout.addLayout(content_layout)

    def get_data(self):
        """Scrape data to return (updates original dicts logically)"""
        # Template updates
        t_data = self.template_data.copy()
        t_data['is_enabled'] = self.chk_enabled.isChecked()
        t_data['is_muted'] = self.btn_mute.isChecked()
        t_data['cooldown'] = self.spin_cooldown.value()
        t_data['interval'] = self.spin_interval.value()
        t_data['default_hotkey'] = self.hk_default.current_hotkey
        t_data['skip_cd_hotkey'] = self.hk_skip.current_hotkey
        
        # Session updates
        s_data = {
            'count': self.spin_count.value(),
            'mode_index': self.combo_mode.currentIndex()
        }
        
        return t_data, s_data
