from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, 
                             QPushButton, QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit, QFileDialog, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from .hotkey_recorder import HotkeyRecorder
from .refined_spinbox import RefinedSpinBox, RefinedDoubleSpinBox
from core.localization import LocalizationManager
import os

class ClassConfigCard(QFrame):
    """
    Card-based widget for configuring a specific Class.
    Merges template data (name, id, interval, etc.) and session data (count, mode).
    """
    delete_requested = pyqtSignal(object) # Emit self when delete clicked

    def __init__(self, template_data, session_data, parent=None):
        super().__init__(parent)
        self.loc = LocalizationManager()
        self.template_data = template_data
        self.session_data = session_data
        
        # Store original values for diff tracking
        self.orig_vals = {
            'is_enabled': self.template_data.get("is_enabled", True),
            'name': self.template_data.get("name", ""),
            'id': self.template_data.get("id", ""),
            'is_muted': self.template_data.get("is_muted", False),
            'cooldown': float(self.template_data.get("cooldown", 0)),
            'interval': float(self.template_data.get("interval", 0)),
            'loop_mode': self.session_data.get("mode_index", 0),
            'count': int(self.session_data.get("count", 0)),
            'default_hotkey': self.template_data.get("default_hotkey", ""),
            'skip_cd_hotkey': self.template_data.get("skip_cd_hotkey", "")
        }
        
        self.setObjectName("ConfigCard")
        # Hover effect handles via parent stylesheet or local
        self.setStyleSheet("""
            #ConfigCard {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
            }
            #ConfigCard:hover {
                border: 1px solid #4dabf7;
                background-color: #f8f9fa;
            }
            QLabel { color: #495057; }
            QDoubleSpinBox, QSpinBox, QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 2px;
                background-color: white;
            }
            QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #4dabf7;
            }
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
        self.chk_enabled.setFixedSize(24, 24) # Fix Layout Shift
        self.chk_enabled.setChecked(self.template_data.get("is_enabled", True))
        self.chk_enabled.setToolTip(self.loc.get("UI_ENABLE_CLASS_TOOLTIP"))
        # Base Style to prevent shift
        self.chk_enabled.setStyleSheet("QCheckBox { border: 1px solid transparent; border-radius: 4px; padding: 2px; }") 
        
        # Name
        self.edit_name = QLineEdit(self.template_data.get("name", "Unknown"))
        self.edit_name.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold)) 
        self.edit_name.setStyleSheet("color: #333; background: transparent; border: 1px solid transparent;")
        self.edit_name.setToolTip(self.loc.get("UI_EDIT_CLASS_NAME_TOOLTIP"))
        self.edit_name.setFixedWidth(150)

        # ID
        self.edit_id = QLineEdit(self.template_data.get("id", ""))
        self.edit_id.setPlaceholderText("ID")
        self.edit_id.setStyleSheet("color: #666; font-size: 11px; background: transparent; border: 1px solid transparent;")
        self.edit_id.setToolTip(self.loc.get("UI_EDIT_CLASS_ID_TOOLTIP"))
        self.edit_id.setFixedWidth(180)
        
        # Mute Button
        self.btn_mute = QPushButton(self.loc.get("HDR_MUTE"))
        self.btn_mute.setCheckable(True)
        self.btn_mute.setChecked(self.template_data.get("is_muted", False))
        self.btn_mute.setFixedSize(50, 24) # Fix Layout Shift
        self.btn_mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mute.setStyleSheet("""
            QPushButton { background-color: #f0f0f0; border: 1px solid transparent; border-radius: 4px; color: #666; font-size: 11px; padding: 2px;}
            QPushButton:checked { background-color: #ffcccc; color: #cc0000; }
        """)
        
        row_header.addWidget(self.chk_enabled)
        row_header.addWidget(self.edit_name)
        row_header.addWidget(self.edit_id)
        row_header.addStretch()
        
        # Delete Button
        self.btn_delete = QPushButton(self.loc.get("BTN_DELETE"))
        self.btn_delete.setToolTip(self.loc.get("UI_DELETE_CLASS_TOOLTIP"))
        self.btn_delete.setFixedSize(60, 24)
        self.btn_delete.setStyleSheet("QPushButton { color: #666; background-color: transparent; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; } QPushButton:hover { color: white; background-color: #dc3545; border-color: #dc3545; }")
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self))
        row_header.addWidget(self.btn_delete)
        
        row_header.addSpacing(5)
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
        self.spin_cooldown = RefinedDoubleSpinBox()
        self.spin_cooldown.setRange(0, 9999)
        self.spin_cooldown.setSingleStep(0.5)
        self.spin_cooldown.setValue(float(self.template_data.get("cooldown", 0)))
        self.spin_cooldown.setSuffix(" s")
        params_layout.addLayout(create_param_row(self.loc.get("LBL_COOLDOWN"), self.spin_cooldown))
        
        # Interval
        self.spin_interval = RefinedDoubleSpinBox()
        self.spin_interval.setRange(0, 9999)
        self.spin_interval.setSingleStep(0.1)
        self.spin_interval.setValue(float(self.template_data.get("interval", 0)))
        self.spin_interval.setSuffix(" s")
        params_layout.addLayout(create_param_row(self.loc.get("LBL_INTERVAL"), self.spin_interval))
        
        # Mode
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([self.loc.get("UI_LOOP_MODE"), self.loc.get("UI_SINGLE_MODE"), self.loc.get("UI_STEP_MODE"), self.loc.get("UI_INDEPENDENT_MODE")])
        self.combo_mode.setCurrentIndex(self.session_data.get("mode_index", 0))
        # Handle Mode Change for UI updates
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        params_layout.addLayout(create_param_row(self.loc.get("LBL_MODE"), self.combo_mode))
        
        # Count
        self.spin_count = RefinedSpinBox()
        self.spin_count.setRange(0, 99)
        self.spin_count.setValue(int(self.session_data.get("count", 0)))
        self.spin_count.valueChanged.connect(self._on_count_changed)
        params_layout.addLayout(create_param_row(self.loc.get("LBL_COUNT"), self.spin_count))
        
        content_layout.addLayout(params_layout, stretch=1)
        
        # Right: Hotkeys
        self.hotkey_frame = QFrame()
        self.hotkey_frame.setStyleSheet("background-color: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;")
        self.hotkey_layout = QVBoxLayout(self.hotkey_frame)
        self.hotkey_layout.setContentsMargins(8, 8, 8, 8)
        
        content_layout.addWidget(self.hotkey_frame, stretch=1)
        
        main_layout.addLayout(content_layout)

        # Initialize Hotkey UI based on initial mode
        self.independent_recorders = []
        self._refresh_hotkey_ui()

        # Setup Tracking
        self.setup_conn(self.chk_enabled, 'is_enabled', self.chk_enabled.isChecked)
        self.setup_conn(self.edit_name, 'name', self.edit_name.text)
        self.setup_conn(self.edit_id, 'id', self.edit_id.text)
        self.setup_conn(self.btn_mute, 'is_muted', self.btn_mute.isChecked)
        self.setup_conn(self.spin_cooldown, 'cooldown', self.spin_cooldown.value)
        self.setup_conn(self.spin_interval, 'interval', self.spin_interval.value)
        self.setup_conn(self.combo_mode, 'loop_mode', self.combo_mode.currentIndex)
        self.setup_conn(self.spin_count, 'count', self.spin_count.value)
        
        # Note: Hotkey tracking is complex due to dynamic UI. 
        # We trigger "modified" style if any independent hotkey differs from template?
        # For now, simplistic tracking for standard mode.

    def _on_mode_changed(self, idx):
        self._refresh_hotkey_ui()
        # Trigger diff check
        self.check_val(self.combo_mode, 'loop_mode', self.combo_mode.currentIndex)

    def _on_count_changed(self, val):
        if self.combo_mode.currentIndex() == 3: # Independent
             self._refresh_hotkey_ui()
        self.check_val(self.spin_count, 'count', self.spin_count.value)

    def _refresh_hotkey_ui(self):
        # Recursive Clear Helper
        def clear_layout(layout):
            if not layout: return
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    clear_layout(child.layout())
                    child.layout().deleteLater()

        clear_layout(self.hotkey_layout)
        
        mode_idx = self.combo_mode.currentIndex()
        
        if mode_idx == 3: # Independent
            self.hk_default = None
            self.hk_skip = None
            self.independent_recorders = []
            
            self.hotkey_layout.addWidget(QLabel(f"⌨️ {self.loc.get('LBL_HOTKEY')} (Independent)"))
            
            count = self.spin_count.value()
            stored_keys = self.template_data.get('independent_hotkeys', [])
            
            # Create scroll area if too many? For now just list.
            for i in range(count):
                row = QHBoxLayout()
                lbl = QLabel(f"P{i+1}:")
                lbl.setFixedWidth(30)
                
                # Retrieve key safely
                key_val = stored_keys[i] if i < len(stored_keys) else ""
                
                rec = HotkeyRecorder(key_val)
                rec.setMinimumHeight(30)
                self.independent_recorders.append(rec)
                
                row.addWidget(lbl)
                row.addWidget(rec)
                self.hotkey_layout.addLayout(row)
                
            self.hotkey_layout.addStretch()

        else: # Standard
            self.independent_recorders = []
            
            self.hotkey_layout.addWidget(QLabel(f"⌨️ {self.loc.get('LBL_HOTKEY')}"))
            self.hk_default = HotkeyRecorder(self.template_data.get("default_hotkey", ""))
            self.hk_default.setMinimumHeight(30)
            self.hotkey_layout.addWidget(self.hk_default)
            
            self.hotkey_layout.addSpacing(4)
            
            self.hotkey_layout.addWidget(QLabel(f"⏩ {self.loc.get('LBL_SKIP_HOTKEY')}"))
            self.hk_skip = HotkeyRecorder(self.template_data.get("skip_cd_hotkey", ""))
            self.hk_skip.setMinimumHeight(30)
            self.hotkey_layout.addWidget(self.hk_skip)
            
            self.hotkey_layout.addStretch()
            
            # Reattach listeners (Since we recreated widgets)
            self.setup_conn(self.hk_default, 'default_hotkey', lambda: self.hk_default.current_hotkey)
            self.setup_conn(self.hk_skip, 'skip_cd_hotkey', lambda: self.hk_skip.current_hotkey)

    def setup_conn(self, widget, key, getter):
        signal = None
        if isinstance(widget, (QCheckBox, QPushButton)) and not isinstance(widget, HotkeyRecorder):
            signal = widget.toggled
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            signal = widget.valueChanged
        elif isinstance(widget, QComboBox):
            signal = widget.currentIndexChanged
        elif isinstance(widget, HotkeyRecorder):
            signal = widget.hotkey_changed
        elif isinstance(widget, QLineEdit): 
            signal = widget.textChanged
            
        if signal:
            signal.connect(lambda: self.check_val(widget, key, getter))

    def check_val(self, widget, key, getter):
        orig = self.orig_vals[key]
        curr = getter()
        
        # Float tolerance
        is_diff = False
        if isinstance(orig, float):
            try:
                is_diff = abs(float(curr) - orig) > 0.001
            except: is_diff = True
        else:
            is_diff = (curr != orig)
            
        if is_diff:
            if isinstance(widget, (QCheckBox)):
                 # Fix Visibility: Style the widget, not indicator. Use border/bg on widget.
                 widget.setStyleSheet("QCheckBox { background-color: #fff5f5; border: 1px solid #dc3545; border-radius: 4px; padding: 2px; }")
            elif isinstance(widget, HotkeyRecorder):
                 widget.setStyleSheet("border: 1px solid #dc3545; background-color: #fff5f5; border-radius: 4px; text-align: center;")
            elif isinstance(widget, QPushButton):
                 widget.setStyleSheet("background-color: #fff5f5; border: 1px solid #dc3545; border-radius: 4px; color: #dc3545; font-size: 11px; padding: 2px;")
            else:
                 widget.setStyleSheet("border: 1px solid #dc3545; background-color: #fff5f5;")
        else:
            # Revert styles
            if isinstance(widget, (QCheckBox)):
                 widget.setStyleSheet("QCheckBox { border: 1px solid transparent; border-radius: 4px; padding: 2px; }")
            elif isinstance(widget, QPushButton) and not isinstance(widget, HotkeyRecorder):
                 if key == 'is_muted':
                    widget.setStyleSheet("""QPushButton { background-color: #f0f0f0; border: 1px solid transparent; border-radius: 4px; color: #666; font-size: 11px; padding: 2px;} QPushButton:checked { background-color: #ffcccc; color: #cc0000; }""")
            elif isinstance(widget, HotkeyRecorder):
                    widget.setStyleSheet("text-align: center; border: none; background: transparent;")
            else:
                 widget.setStyleSheet("")

    def get_data(self):
        """Scrape data to return (updates original dicts logically)"""
        # Template updates
        t_data = self.template_data.copy()
        t_data = self.template_data.copy()
        t_data['is_enabled'] = self.chk_enabled.isChecked()
        t_data['name'] = self.edit_name.text().strip()
        t_data['id'] = self.edit_id.text().strip()
        t_data['is_muted'] = self.btn_mute.isChecked()
        t_data['cooldown'] = self.spin_cooldown.value()
        t_data['interval'] = self.spin_interval.value()
        
        if self.combo_mode.currentIndex() == 3: # Independent
             # Save independent keys
             keys = [rec.current_hotkey for rec in self.independent_recorders]
             t_data['independent_hotkeys'] = keys
        else:
             t_data['default_hotkey'] = self.hk_default.current_hotkey
             t_data['skip_cd_hotkey'] = self.hk_skip.current_hotkey
        
        # Session updates
        s_data = {
            'count': self.spin_count.value(),
            'mode_index': self.combo_mode.currentIndex()
        }
        
        return t_data, s_data

