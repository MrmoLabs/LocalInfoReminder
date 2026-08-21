import sys
import os
import ctypes
import time
from ctypes import wintypes
from utils.resource_path import get_resource_path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QFrame, QInputDialog, QPushButton, QSizeGrip, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QColor, QPalette, QFont, QCursor

from core.logger import setup_logger
from core.localization import LocalizationManager
from core.localization import LocalizationManager
from ui.components.group_row_widget import GroupRowWidget
from ui.components.enemy_list_widget import EnemyListWidget
from ui.components.boss_widget import BossWidget
from ui.components.boss_widget import BossWidget
from ui.components.resize_grip import VersionResizeGrip
from core.constants import UIConstants, FilePaths

logger = setup_logger()

class OverlayWindow(QWidget):
    def __init__(self, logic_engine):
        super().__init__()
        logger.info("OverlayWindow.__init__ started")
        self.logic = logic_engine
        self.loc = LocalizationManager()
        self.loc = LocalizationManager()
        self.passthrough_enabled = False
        self.class_widgets = {} # Map class_id -> widget dict
        
        self.version_text = "Open Source"
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        
        # [REFINED] Use centralized resource path utility
        icon_path = get_resource_path(os.path.join(FilePaths.ASSETS_DIR, FilePaths.ICON_FILE))
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        else:
            logger.warning(f"Overlay icon file missing at: {icon_path}")
            
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Fix: Set low alpha background to capture mouse events. 1 might be too low, 5 is safer.
        self.setStyleSheet("background-color: rgba(0, 0, 0, 5);")
        
        self.init_ui()
        self.resize(UIConstants.DEFAULT_WIDTH, UIConstants.DEFAULT_HEIGHT) # Slightly wider to accommodate side bar
        self.setMinimumSize(UIConstants.MIN_WIDTH, UIConstants.MIN_HEIGHT)
        self.move(100, 100)
        self._bind_logic_startup_signals()
        
        logger.info("OverlayWindow initialized")

    def init_ui(self):
        # [CHANGE] Main Layout is Horizontal
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(2, 8, 8, 8) # [FIX] Reduced left margin to 2
        main_layout.setSpacing(0) # [FIX] Closer to main overlay
        
        # [NEW] Boss Notification Widget (Left Side)
        self.boss_widget = BossWidget()
        main_layout.addWidget(self.boss_widget)

        # [NEW] Right Side Container (Holds Time, Ally, Enemy)
        right_container = QWidget()
        right_container.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        
        # Check Transparency Config
        # 1. Try integer key first
        alpha_val = self.logic.config.get('overlay_bg_alpha', UIConstants.BG_ALPHA_DEFAULT)
        
        # 2. Fallback to boolean (migration)
        if 'overlay_bg_alpha' not in self.logic.config:
            hide_bg = self.logic.config.get('hide_overlay_background', False)
            alpha_val = UIConstants.BG_ALPHA_TRANSPARENT if hide_bg else UIConstants.BG_ALPHA_DEFAULT
        
        bg_alpha = str(alpha_val)
        ally_alpha = str(alpha_val)
        command_alpha = str(alpha_val)

        # 1. Global Time
        self.time_container = QWidget()
        self.time_container.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(30, 30, 46, {bg_alpha});
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        time_layout = QHBoxLayout(self.time_container)
        time_layout.setContentsMargins(6, 4, 6, 4)
        
        self.time_label = QLabel("20:00")
        self.time_label.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_edit_time = QPushButton("✎")
        self.btn_edit_time.setFixedSize(20, 20)
        self.btn_edit_time.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit_time.clicked.connect(self.on_time_clicked)
        self.btn_edit_time.setStyleSheet("""
            QPushButton { color: #AAA; background: transparent; border: none; font-size: 16px; }
            QPushButton:hover { color: #FFF; }
        """)
        
        # Sync Button (New)
        self.btn_sync = QPushButton("⟳")
        self.btn_sync.setFixedSize(20, 20)
        self.btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync.setToolTip(self.loc.get("UI_SYNC_TIME"))
        self.btn_sync.clicked.connect(self.logic.trigger_time_sync)
        self.btn_sync.setFont(QFont("Segoe UI", 12)) 
        self.btn_sync.setStyleSheet("""
            QPushButton { color: #A6E3A1; background: transparent; border: none; font-weight: bold; }
            QPushButton:hover { color: #94E2D5; }
        """)
        
        self.btn_exit = QPushButton("✕")
        self.btn_exit.setFixedSize(20, 20)
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.clicked.connect(self.on_exit_clicked)
        self.btn_exit.setStyleSheet("""
            QPushButton { color: #FF5555; background: transparent; border: none; font-size: 16px; font-weight: bold; }
            QPushButton:hover { color: #FF8888; }
        """)

        time_layout.addWidget(self.btn_edit_time)
        time_layout.addWidget(self.btn_sync)
        time_layout.addStretch()
        time_layout.addWidget(self.time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.btn_exit)
        
        right_layout.addWidget(self.time_container)

        self.startup_container = QWidget()
        self.startup_container.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 15, 25, 220);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        startup_layout = QVBoxLayout(self.startup_container)
        startup_layout.setContentsMargins(8, 8, 8, 8)
        startup_layout.setSpacing(6)
        self.startup_label = QLabel("正在后台初始化...")
        self.startup_label.setStyleSheet("color: #CDD6F4; background: transparent; border: none;")
        self.startup_progress = QProgressBar()
        self.startup_progress.setRange(0, 100)
        self.startup_progress.setValue(0)
        self.startup_progress.setTextVisible(True)
        self.startup_progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255,255,255,0.08);
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 5px;
                text-align: center;
                min-height: 16px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)
        startup_layout.addWidget(self.startup_label)
        startup_layout.addWidget(self.startup_progress)
        right_layout.addWidget(self.startup_container)

        # 2. Ally Panel (Classes)
        self.ally_container = QWidget()
        self.ally_layout = QVBoxLayout(self.ally_container)
        self.ally_layout.setContentsMargins(6, 6, 6, 6)
        self.ally_layout.setSpacing(4)
        self.ally_container.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(30, 30, 46, {ally_alpha});
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        
        # [MODULAR] Use class_widgets dict to manage rows
        self.class_widgets = {} 
        
        right_layout.addWidget(self.ally_container)
        
        # 3. Enemy Monitor
        self.command_container = QWidget()
        self.command_layout_widget = QVBoxLayout(self.command_container)
        self.command_layout_widget.setContentsMargins(6, 6, 6, 6)
        self.command_layout_widget.setSpacing(4)
        self.command_container.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(45, 20, 20, {command_alpha});
                border-radius: 10px;
                border: 1px solid rgba(255, 100, 100, 0.1);
            }}
        """)
        
        
        # [MODULAR] Enemy List Widget
        # We need a proper layout that includes header + list
        # Current command_layout_widget has header added below, let's fix that.
        
        # [CHANGE] Removed Header + Button (Moved to Config)
        
        # The list widget (Enemy)
        self.command_list_widget = EnemyListWidget()
        self.command_layout_widget.addWidget(self.command_list_widget)
        
        right_layout.addWidget(self.command_container)
        
        # 4. Miracle Monitor (New Separate Container)
        # Using same alpha style for consistency, or maybe slightly different?
        # User requested separate split.
        self.miracle_container = QWidget()
        self.miracle_layout = QVBoxLayout(self.miracle_container)
        self.miracle_layout.setContentsMargins(6, 6, 6, 6)
        self.miracle_layout.setSpacing(4)
        self.miracle_container.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(20, 45, 45, {command_alpha});
                border-radius: 10px;
                border: 1px solid rgba(100, 255, 255, 0.1);
            }}
        """)
        
        self.miracle_list_widget = EnemyListWidget()
        # [NEW] Set Flash Threshold from Config
        flash_thresh = self.logic.config.get('miracle_flash_threshold', 3.0)
        self.miracle_list_widget.set_flash_threshold(flash_thresh)
        
        self.miracle_layout.addWidget(self.miracle_list_widget)
        
        right_layout.addWidget(self.miracle_container)
        
        # [NEW] Version Resize Handle (Footer)
        # Separate from container to avoid embedding, but close to it.
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 12, 0) # Align with container padding
        bottom_row.setSpacing(10)
        
        bottom_row.addStretch()
        
        self.version_grip = VersionResizeGrip(self.version_text, self)
        # Restore slightly larger style for usability
        self.version_grip.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.3); 
                background: transparent;
                font-family: 'Consolas';
                font-size: 12px;
                padding: 2px;
            }
            QLabel:hover {
                color: rgba(255, 255, 255, 0.8);
            }
        """)
        bottom_row.addWidget(self.version_grip)
        
        right_layout.addLayout(bottom_row)
        right_layout.addStretch() # Push everything up
        
        # Add Right Container to Main
        main_layout.addWidget(right_container)
        
        self.setLayout(main_layout)

        # Mode Label
        self.mode_label = QLabel("DRAG MODE (Ctrl+M to Lock)", self)
        self.mode_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.mode_label.setStyleSheet("color: #FF5555; background-color: rgba(0,0,0,0.8); padding: 4px 8px; border-radius: 4px;")
        self.mode_label.move(10, 5)
        self.mode_label.hide()
        self.mode_label_timer = QTimer(self)
        self.mode_label_timer.setSingleShot(True)
        self.mode_label_timer.timeout.connect(self.mode_label.hide)

        # Custom Resizing variables
        self.edge_margin = 15 # Increased to 15px to be very easy to grab
        self.resize_direction = None
        self.setMouseTracking(True)
        
        # [NEW] Right-click menu for Exit path redundancy
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def _bind_logic_startup_signals(self):
        if hasattr(self.logic, 'startup_progress'):
            self.logic.startup_progress.connect(self.on_startup_progress)
        if hasattr(self.logic, 'startup_ready'):
            self.logic.startup_ready.connect(self.on_startup_ready)
        if hasattr(self.logic, 'startup_failed'):
            self.logic.startup_failed.connect(self.on_startup_failed)
        self.btn_sync.setEnabled(False)

    def on_startup_progress(self, message, progress):
        self.startup_label.setText(message or "正在后台初始化...")
        self.startup_progress.setValue(max(0, min(100, int(progress))))
        self.startup_container.show()

    def on_startup_ready(self):
        self.startup_container.hide()
        self.btn_sync.setEnabled(True)

    def on_startup_failed(self, error_message):
        self.startup_label.setText(f"初始化失败: {error_message}")
        self.startup_progress.setValue(100)
        self.startup_container.show()
        self.btn_sync.setEnabled(False)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        # [NEW] Vertical Zoom Logic
        # Base height is 420. Scale = h / 420
        h = self.height()
        scale = h / float(UIConstants.DEFAULT_HEIGHT)
        
        # Clamping scale to reasonable limits (0.5x to 2.5x)
        scale = max(0.5, min(2.5, scale))
        
        self.apply_scale(scale)

    def apply_scale(self, scale):
        # 1. Main Time Label (Base 26)
        s_time = max(14, int(26 * scale))
        self.time_label.setFont(QFont("Segoe UI", s_time, QFont.Weight.Bold))
        
        # 2. Boss Widget
        if hasattr(self, 'boss_widget'):
            self.boss_widget.set_scale(scale)
            
        # 3. Ally Rows
        for w in self.class_widgets.values():
            w.set_scale(scale)
            
        # 4. Enemy List
        if hasattr(self, 'command_list_widget'):
            self.command_list_widget.set_scale(scale)
            
        # 5. Miracle List
        if hasattr(self, 'miracle_list_widget'):
            self.miracle_list_widget.set_scale(scale)
            
        # 6. Version Grip / Footer
        if hasattr(self, 'version_grip'):
            self.version_grip.setStyleSheet(f"""
                QLabel {{
                    color: rgba(255, 255, 255, 0.3); 
                    background: transparent;
                    font-family: 'Consolas';
                    font-size: {max(9, int(12 * scale))}px;
                    padding: 2px;
                }}
                QLabel:hover {{
                    color: rgba(255, 255, 255, 0.8);
                }}
            """)

    def on_time_clicked(self):
        if self.passthrough_enabled:
            return
        dialog = QInputDialog(self)
        dialog.setWindowTitle(self.loc.get("UI_EDIT_TIME_TITLE"))
        dialog.setLabelText(self.loc.get("UI_EDIT_TIME_LABEL"))
        dialog.setTextValue(self.time_label.text())
        
        # Force a readable style for the dialog
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2E2E3A; 
                color: #CDD6F4;
                font-family: 'Segoe UI';
                font-size: 14px;
            }
            QLabel {
                color: #CDD6F4;
            }
            QLineEdit {
                color: #CDD6F4;
                background-color: #181825;
                border: 1px solid #45475A;
                padding: 4px;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #45475A;
                color: #CDD6F4;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #585B70;
            }
        """)
        
        if dialog.exec():
            text = dialog.textValue()
            if text:
                self.logic.update_time(text)


    def show_context_menu(self, pos):
        if self.passthrough_enabled:
            return
            
        from PyQt6.QtWidgets import QMenu
        # [FIX] Keep reference to prevent GC when using popup
        self.context_menu = QMenu(self)
        self.context_menu.setStyleSheet("""
            QMenu {
                background-color: #2E2E3A;
                color: #CDD6F4;
                border: 1px solid #45475A;
            }
            QMenu::item:selected {
                background-color: #45475A;
            }
        """)
        
        exit_action = self.context_menu.addAction(self.loc.get("UI_MENU_EXIT"))
        exit_action.triggered.connect(self.on_exit_clicked)
        
        toggle_lock_action = self.context_menu.addAction(self.loc.get("UI_MENU_TOGGLE_LOCK"))
        # [FIX] Use local toggle method instead of missing logic method
        toggle_lock_action.triggered.connect(self.toggle_passthrough)
        
        # [FIX] Use popup instead of exec to prevent blocking main thread/system freeze on TopMost window
        self.context_menu.popup(self.mapToGlobal(pos))

    def on_exit_clicked(self):
        logger.info("EXIT BUTTON CLICKED - STARTING SHUTDOWN")
        self.setEnabled(False)
        self.hide()
        QApplication.processEvents()

        app = QApplication.instance()
        if app is not None:
            QTimer.singleShot(0, app.quit)

        # Fallback in case background hooks/threads still block a clean exit.
        QTimer.singleShot(2500, lambda: os._exit(0))

    
    def update_state(self, state):
        # Update Time
        if 'time_str' in state:
            self.time_label.setText(state['time_str'])
        
        # [NEW] Top-Level Boss Widget Update
        if self.logic.config.get('enable_boss_settings', True):
            if hasattr(self, 'boss_widget') and 'boss_info' in state:
                self.boss_widget.update_info(state['boss_info'])
        else:
            if hasattr(self, 'boss_widget'):
                self.boss_widget.hide()
        
        # Update Ally Roster (Modular)
        if 'classes' in state:
            current_ids = [c['id'] for c in state['classes']]
            
            # Remove stale
            for cid in list(self.class_widgets.keys()):
                if cid not in current_ids:
                    self.class_widgets[cid].deleteLater()
                    del self.class_widgets[cid]
            
            # Add/Update
            for i, cls in enumerate(state['classes']):
                cid = cls['id']
                if cid not in self.class_widgets:
                    # Create
                    row = GroupRowWidget(cid, self.logic)
                    self.ally_layout.insertWidget(i, row)
                    self.class_widgets[cid] = row
                
                # Update
                self.class_widgets[cid].update_state(cls)

        # Update Enemy Monitor (Modular)
        if 'commands' in state:
            # Split Data
            raw_commands = state.get('commands', [])
            curr_commands = []
            curr_miracles = []
            
            for e in raw_commands:
                if e.get('type') == 'miracle':
                    curr_miracles.append(e)
                else:
                    curr_commands.append(e)

            # Delegate list update & Visibility Check
            
            # 1. Command Skills
            if not self.logic.config.get('enable_command_skills', True):
                self.command_container.setVisible(False)
            else:
                self.command_list_widget.update_state(curr_commands)
                self.command_container.setVisible(len(curr_commands) > 0)
            
            # 2. Miracle Skills
            if not self.logic.config.get('enable_miracle_skills', True):
                self.miracle_container.setVisible(False)
            else:
                self.miracle_list_widget.update_state(curr_miracles)
                self.miracle_container.setVisible(len(curr_miracles) > 0)
            
        # 3. Class (Ally) container visibility
        if not self.logic.config.get('enable_classes', True):
            self.ally_container.setVisible(False)
        else:
            self.ally_container.setVisible(True)
            
        # 4. Time Display visibility
        if not self.logic.config.get('enable_time_display', True):
            self.time_container.setVisible(False)
        else:
            self.time_container.setVisible(True)

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def toggle_passthrough(self):
        self.passthrough_enabled = not self.passthrough_enabled
        self.set_passthrough(self.passthrough_enabled)
        
        if self.passthrough_enabled:
            self.mode_label_timer.stop()
            self.mode_label.hide()
            self.setStyleSheet("QWidget { background-color: rgba(0, 0, 0, 0.1); }")
        else:
            self.mode_label.show()
            self.mode_label_timer.start(3000)
            # Restore original style
            alpha_val = self.logic.config.get('overlay_bg_alpha', 220)
            if 'overlay_bg_alpha' not in self.logic.config:
                 hide_bg = self.logic.config.get('hide_overlay_background', False)
                 alpha_val = UIConstants.BG_ALPHA_TRANSPARENT if hide_bg else UIConstants.BG_ALPHA_DEFAULT
            
            self.setStyleSheet(f"background-color: rgba(0, 0, 0, {alpha_val});")

    def set_passthrough(self, enabled):
        hwnd = self.winId().__int__()
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enabled:
            style = style | WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            style = style & ~WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def mousePressEvent(self, event):
        if self.passthrough_enabled:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            edges = self._get_edges(event.position().toPoint())
            if edges:
                if self.windowHandle():
                    self.windowHandle().startSystemResize(edges)
            else:
                if self.windowHandle():
                    self.windowHandle().startSystemMove()

    def mouseMoveEvent(self, event):
        if self.passthrough_enabled:
            super().mouseMoveEvent(event)
            return

        # Just update cursor shape
        self._update_cursor_shape(event.position().toPoint())

    def mouseReleaseEvent(self, event):
        if self.passthrough_enabled:
            super().mouseReleaseEvent(event)
            return

    def _get_edges(self, pos):
        # Return Qt.Edge flags or None
        margin = self.edge_margin
        w, h = self.width(), self.height()
        
        active_edges = []
        
        on_left = pos.x() < margin
        on_right = pos.x() > w - margin
        on_top = pos.y() < margin
        on_bottom = pos.y() > h - margin

        if on_top: active_edges.append(Qt.Edge.TopEdge)
        if on_bottom: active_edges.append(Qt.Edge.BottomEdge)
        if on_left: active_edges.append(Qt.Edge.LeftEdge)
        if on_right: active_edges.append(Qt.Edge.RightEdge)
        
        if not active_edges:
            return None
            
        # Combine flags
        edges = active_edges[0]
        for e in active_edges[1:]:
            edges |= e
            
        return edges

    def _update_cursor_shape(self, pos):
        margin = self.edge_margin
        w, h = self.width(), self.height()
        
        on_left = pos.x() < margin
        on_right = pos.x() > w - margin
        on_top = pos.y() < margin
        on_bottom = pos.y() > h - margin
        
        if on_top and on_left:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif on_top and on_right:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif on_bottom and on_left:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif on_bottom and on_right:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif on_top:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif on_bottom:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif on_left:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif on_right:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
