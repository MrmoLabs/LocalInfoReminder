import sys
import os
import json
from utils.resource_path import get_resource_path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QSpinBox, QComboBox, QPushButton, 
                             QScrollArea, QFrame, QMessageBox, QGroupBox, QDialog, QApplication, 
                             QGraphicsDropShadowEffect, QAbstractSpinBox, QGridLayout, QFileDialog, QMenu, QProgressBar)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon
# Adjust path to import core modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from core.config_loader import ConfigLoader
from core.runtime_config import RuntimeConfig
from ui.components.modern_card import ModernCard
from ui.config_editor import ConfigEditor # [NEW]
from core.localization import LocalizationManager
from core.logger import setup_logger
from core.app_paths import existing_state_path, preferred_state_path
from core.version import __version__
logger = setup_logger()
# --- Constants & Styles (Light Theme) ---
COLOR_BG = "#f6f8fa"        # Snow White / Very Light Gray
COLOR_FG = "#202020"        # Almost Black
COLOR_PRIMARY = "#007bff"   # Bright Blue
COLOR_SECONDARY = "#6c757d" # Gray
COLOR_ACCENT = "#17a2b8"    # Cyan/Teal
COLOR_SURFACE0 = "#ffffff"  # Pure White
COLOR_SURFACE1 = "#e9ecef"  # Light Gray for inputs/borders
COLOR_SUCCESS = "#28a745"   # Green
COLOR_ERROR = "#dc3545"     # Red
COLOR_WARN = "#ffc107"      # Yellow/Orange
STYLESHEET = f"""
    QWidget {{
        background-color: {COLOR_BG};
        color: {COLOR_FG};
        font-family: "Segoe UI", "Microsoft YaHei";
        font-size: 13px; /* Slightly smaller font for compact look */
        selection-background-color: {COLOR_PRIMARY};
        selection-color: white;
    }}
    
    QLabel {{
        color: {COLOR_FG};
        border: none;
    }}
    
    QFrame#Card {{
        background-color: {COLOR_SURFACE0};
        border-radius: 8px; /* Slightly sharper corners */
        border: 1px solid #d0d7de;
    }}
    QLineEdit, QSpinBox, QComboBox {{
        background-color: {COLOR_SURFACE0};
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 4px; /* Reduced padding */
        color: {COLOR_FG};
        selection-background-color: {COLOR_PRIMARY};
    }}
    
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 2px solid {COLOR_PRIMARY};
        background-color: {COLOR_SURFACE0};
    }}
    /* ScrollBar */
    QScrollBar:vertical {{
        border: none;
        background: {COLOR_BG};
        width: 8px;
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:vertical {{
        background: #adb5bd;
        min-height: 20px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLOR_SECONDARY};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    /* Buttons */
    QPushButton {{
        background-color: {COLOR_SURFACE0};
        color: {COLOR_FG};
        border: 1px solid #ced4da;
        border-radius: 6px;
        padding: 5px 12px; /* Reduced padding */
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {COLOR_SURFACE1};
        border-color: {COLOR_SECONDARY};
    }}
    QPushButton:pressed {{
        background-color: #dde2e6;
    }}
    /* Primary Button (Start) */
    QPushButton#PrimaryBtn {{
        background-color: {COLOR_PRIMARY};
        color: white;
        border: none;
        font-size: 14px;
        padding: 8px;
    }}
    QPushButton#PrimaryBtn:hover {{
        background-color: #0056b3;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {COLOR_SURFACE0};
        color: {COLOR_FG};
        selection-background-color: {COLOR_PRIMARY};
        selection-color: white;
        border: 1px solid #ced4da;
    }}
"""
class LauncherWindow(QWidget):
    game_start = pyqtSignal(RuntimeConfig)
    def __init__(self):
        super().__init__()
        self.loc = LocalizationManager()
        
        
        self.setWindowTitle(f"{self.loc.get('WIN_TITLE')} v{__version__}")
        
        # [REFINED] Use centralized resource path utility
        icon_path = get_resource_path("assets/LocalInfoReminder.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            logger.warning(f"Window icon file missing at: {icon_path}")
            
        self.resize(440, 330)
        self.setMinimumSize(420, 315)
        
        # Load Config Preference
        self.current_config_path = self.load_launcher_preferences()
        self.config = ConfigLoader.load_config(self.current_config_path) # Load specific file
        if not self.config: # Fallback
            self.current_config_path = "config.json"
            self.config = ConfigLoader.get_config()
            
        self.setStyleSheet(STYLESHEET)
        self.init_ui()
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(20, 18, 20, 16)

        header_layout = QHBoxLayout()
        title_container = QVBoxLayout()
        title_container.setSpacing(2)
        self.subtitle_lbl = QLabel(self.loc.get("SUBTITLE"))
        self.subtitle_lbl.setFont(QFont("Segoe UI", 19, QFont.Weight.Bold))
        self.subtitle_lbl.setStyleSheet(f"color: {COLOR_PRIMARY}; background: transparent;")
        title_container.addWidget(self.subtitle_lbl)

        self.edition_lbl = QLabel(self.loc.get("PROJECT_EDITION"))
        self.edition_lbl.setStyleSheet(f"color: {COLOR_SECONDARY}; background: transparent; font-size: 11px;")
        title_container.addWidget(self.edition_lbl)

        self.scope_lbl = QLabel(self.loc.get("PROJECT_SCOPE"))
        self.scope_lbl.setStyleSheet(f"color: {COLOR_SECONDARY}; background: transparent; font-size: 11px;")
        title_container.addWidget(self.scope_lbl)
        
        header_layout.addLayout(title_container)
        header_layout.addStretch()
        
        self.btn_lang = QPushButton(self.loc.get("UI_LANG_TOGGLE"))
        self.btn_lang.setFixedSize(70, 24)
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.setStyleSheet(f"background: transparent; color: {COLOR_SECONDARY}; border: 1px solid {COLOR_SECONDARY}; border-radius: 4px; font-size: 11px;")
        self.btn_lang.clicked.connect(self.toggle_language)
        header_layout.addWidget(self.btn_lang)
        main_layout.addLayout(header_layout)

        action_container = QFrame()
        action_container.setObjectName("Card")
        action_layout = QVBoxLayout(action_container)
        action_layout.setSpacing(8)
        action_layout.setContentsMargins(14, 14, 14, 12)

        self.btn_config_mgr = QPushButton(self.loc.get("BTN_CONFIG_EDITOR"))
        self.btn_config_mgr.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_config_mgr.setMinimumHeight(40)
        self.btn_config_mgr.clicked.connect(self.on_config_mgr_clicked)
        self.btn_config_mgr.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLOR_SURFACE0}; 
                border: 2px solid {COLOR_SECONDARY}; 
                color: {COLOR_FG}; 
                font-size: 14px; 
                border-radius: 8px;
            }}
            QPushButton:hover {{ 
                border-color: {COLOR_PRIMARY}; 
                color: {COLOR_PRIMARY}; 
                background-color: #f8f9fa;
            }}
        """)
        action_layout.addWidget(self.btn_config_mgr)
        self.lbl_config_info = QLabel(self.loc.get("LBL_CURRENT_CONFIG").format(os.path.basename(self.current_config_path)))
        self.lbl_config_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_config_info.setStyleSheet(f"color: {COLOR_SECONDARY}; font-size: 11px; margin-top: 2px;")
        action_layout.addWidget(self.lbl_config_info)
        main_layout.addWidget(action_container)

        self.boundary_lbl = QLabel(self.loc.get("PROJECT_BOUNDARY"))
        self.boundary_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.boundary_lbl.setWordWrap(True)
        self.boundary_lbl.setStyleSheet(
            f"color: {COLOR_SECONDARY}; background: #f8f9fa; border: 1px solid #e1e4e8; "
            "border-radius: 6px; padding: 7px; font-size: 10px;"
        )
        main_layout.addWidget(self.boundary_lbl)

        main_layout.addStretch(1)

        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(9)
        self.btn_start = QPushButton(self.loc.get("BTN_START"))
        self.btn_start.setObjectName("PrimaryBtn")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setMinimumHeight(44)
        
        # Button Shadow
        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(10)
        btn_shadow.setColor(QColor(0, 123, 255, 60)) 
        btn_shadow.setOffset(0, 3)
        self.btn_start.setGraphicsEffect(btn_shadow)
        
        self.btn_start.clicked.connect(self.on_start_clicked)
        footer_layout.addWidget(self.btn_start)
        
        self.copyright_lbl = QLabel(self.loc.get("COPYRIGHT"))
        self.copyright_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.copyright_lbl.setWordWrap(True)
        self.copyright_lbl.setOpenExternalLinks(True)
        self.copyright_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.copyright_lbl.setStyleSheet(f"color: {COLOR_SECONDARY}; font-size: 10px; line-height: 1.35;")
        footer_layout.addWidget(self.copyright_lbl)
        
        main_layout.addLayout(footer_layout)

        self._init_loading_overlay()
        self._update_loading_overlay()

    def _init_loading_overlay(self):
        self.loading_overlay = QFrame(self)
        self.loading_overlay.setStyleSheet("""
            QFrame {
                background-color: rgba(246, 248, 250, 235);
                border: 1px solid #d0d7de;
                border-radius: 12px;
            }
            QLabel {
                background: transparent;
                color: #202020;
            }
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 6px;
                background: white;
                text-align: center;
                min-height: 12px;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self.loading_overlay)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addStretch()

        self.loading_title = QLabel(self.loc.get("UI_LOADING_TITLE"))
        self.loading_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(self.loading_title)

        self.loading_message = QLabel(self.loc.get("UI_LOADING_ENV"))
        self.loading_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_message.setWordWrap(True)
        layout.addWidget(self.loading_message)

        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setTextVisible(False)
        layout.addWidget(self.loading_bar)

        layout.addStretch()
        self._sync_loading_overlay_geometry()
        self.loading_overlay.show()
        self.loading_overlay.raise_()

    def show_loading_message(self, message: str):
        self.loading_message.setText(message)
        self._sync_loading_overlay_geometry()
        self.loading_overlay.show()
        self.loading_overlay.raise_()

    def _sync_loading_overlay_geometry(self):
        margin = 14
        self.loading_overlay.setGeometry(margin, margin, self.width() - margin * 2, self.height() - margin * 2)

    def _set_interactive_enabled(self, enabled: bool):
        for widget_name in ('btn_start', 'btn_config_mgr', 'btn_lang'):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.setEnabled(enabled)

    def _update_loading_overlay(self):
        self._set_interactive_enabled(True)
        self.loading_overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self._sync_loading_overlay_geometry()
            self.loading_overlay.raise_()

    def toggle_language(self):
        self.loc.toggle_language()
        self.refresh_ui()
        
    def refresh_ui(self):
        self.setWindowTitle(f"{self.loc.get('WIN_TITLE')} v{__version__}")
        self.subtitle_lbl.setText(self.loc.get("SUBTITLE"))
        self.edition_lbl.setText(self.loc.get("PROJECT_EDITION"))
        self.scope_lbl.setText(self.loc.get("PROJECT_SCOPE"))
        self.boundary_lbl.setText(self.loc.get("PROJECT_BOUNDARY"))
        self.btn_config_mgr.setText(self.loc.get("BTN_CONFIG_EDITOR"))
        self.lbl_config_info.setText(self.loc.get("LBL_CURRENT_CONFIG").format(os.path.basename(self.current_config_path)))
        self.btn_start.setText(self.loc.get("BTN_START"))
        self.copyright_lbl.setText(self.loc.get("COPYRIGHT"))
    def on_config_mgr_clicked(self):
        """Handle Config Load/Edit."""
        # Optional: Ask user if they want to load a new file or edit current
        # For now, following spec: "Click button -> User chooses file"
        
        file_path, _ = QFileDialog.getOpenFileName(self, self.loc.get("UI_SELECT_CONFIG"), self.current_config_path, "JSON Files (*.json);;All Files (*)")
        
        if not file_path:
            return # Cancelled
            
        # Load the selected config
        new_config = ConfigLoader.load_config(file_path)
        if not new_config:
            QMessageBox.critical(self, self.loc.get("UI_ERROR"), self.loc.get("UI_LOAD_CONFIG_FAIL"))
            return
        # Open Editor
        editor = ConfigEditor(new_config, self, file_path)
        editor.config_updated.connect(lambda data: self.on_config_saved(data, file_path))
        editor.exec()
    def on_config_saved(self, new_data, file_path):
        """Callback when ConfigEditor saves data."""
        # 1. Save to disk
        if ConfigLoader.save_config(new_data, file_path):
            self.current_config_path = file_path
            self.config = new_data
            self.save_launcher_preferences() # Persist preference
            
            # 2. Refresh UI
            self.lbl_config_info.setText(self.loc.get("LBL_CURRENT_CONFIG").format(os.path.basename(self.current_config_path)))
            
            QMessageBox.information(self, self.loc.get("UI_SUCCESS"), self.loc.get("MSG_SAVE_SUCCESS"))
        else:
            QMessageBox.critical(self, self.loc.get("UI_ERROR"), self.loc.get("MSG_SAVE_FAIL"))
    def on_reload_clicked(self): # Keeping for backward compat if needed, but button replaced
        self.on_config_mgr_clicked()
    def on_start_clicked(self):
        # Read from config session_state
        state = self.config.get("session_state", {})
        time_str = state.get("time", "30:00")
        seconds = ConfigLoader.parse_time_str(time_str)
        
        if seconds <= 0:
            QMessageBox.warning(self, self.loc.get("UI_CONFIG_ERROR"), self.loc.get("UI_INVALID_COUNTDOWN"))
            return
            
        class_configs = {}
        state_classes = state.get("classes", {})
        
        # We also need to loop through template to ensure we only add enabled classes
        if "classes_template" in self.config:
            for cls in self.config["classes_template"]:
                cid = cls['id']
                if not cls.get('is_enabled', True): continue
                
                # Get session overrides or default
                s_data = state_classes.get(cid, {})
                count = s_data.get("count", 0)
                mode_idx = s_data.get("mode_index", 0)
                
                # Convert index to string mode
                modes = ["loop", "once", "step", "independent"]
                loop_mode = modes[mode_idx] if 0 <= mode_idx < len(modes) else "loop"
                
                if count > 0:
                     class_configs[cid] = {
                        "count": count,
                        "loop_mode": loop_mode
                    }
        
        runtime_config = RuntimeConfig(
            start_seconds=seconds,
            class_configs=class_configs,
            show_ally_panel=True, 
            show_command_monitor=True,
        )
        self.show_loading_message(self.loc.get("UI_LOADING_STARTUP"))
        self._set_interactive_enabled(False)
        QApplication.processEvents()
        logger.info("Launcher emitting game_start signal.")
        self.game_start.emit(runtime_config)

    def on_runtime_started(self):
        """Close the launcher only after the runtime reports readiness."""
        self.starting_game = True
        logger.info("Runtime startup succeeded; closing launcher.")
        self.close()

    def on_runtime_start_failed(self, error_message):
        """Restore the launcher when runtime initialization fails."""
        self.starting_game = False
        self._update_loading_overlay()
        self.show()
        self.raise_()
        self.activateWindow()
        QMessageBox.critical(
            self,
            self.loc.get("UI_SYSTEM_ERROR"),
            f"{self.loc.get('UI_LOADING_STARTUP')}\n\n{error_message}",
        )
    def closeEvent(self, event):
        if not getattr(self, 'starting_game', False):
            QApplication.instance().quit()
        super().closeEvent(event)
    def load_launcher_preferences(self):
        try:
            state_path = existing_state_path("launcher_state.json")
            if os.path.exists(state_path):
                with open(state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    path = data.get("last_config_path")
                    if path and os.path.exists(path):
                        return path
        except Exception:
            pass
        return "config.json"
    def save_launcher_preferences(self):
        try:
            state_path = preferred_state_path("launcher_state.json")
            state_dir = os.path.dirname(state_path)
            if state_dir:
                os.makedirs(state_dir, exist_ok=True)
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump({"last_config_path": self.current_config_path}, f, indent=4)
        except Exception:
            pass
