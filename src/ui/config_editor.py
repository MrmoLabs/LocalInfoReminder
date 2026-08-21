from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget, 
                              QTableWidget, QTableWidgetItem,  QPushButton, QHeaderView, 
                              QCheckBox, QFileDialog, QMessageBox, QAbstractItemView,
                              QScrollArea, QGroupBox, QLineEdit, QFormLayout, QFrame, QToolButton, QSlider, QLabel, QInputDialog, QDoubleSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QParallelAnimationGroup
from PyQt6.QtGui import QFont, QColor, QIcon
from utils.resource_path import get_resource_path
import time
import copy
import os

from ui.components.collapsible_box import CollapsibleBox
from ui.components.config_cards import ClassConfigCard, SkillConfigCard
from ui.components.boss_target_card import BossTargetConfigCard
from ui.roi_editor import RoiEditorDialog
from core.localization import LocalizationManager
from core.config_loader import ConfigLoader

from ui.config_editor_mixin import ConfigEditorMixin

class ConfigEditor(ConfigEditorMixin, QDialog):
    STYLESHEET = """
    QDialog {
        background-color: #f8f9fa;
        font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        font-size: 10pt;
    }
    QScrollArea {
        border: none;
        background-color: transparent;
    }
    QScrollBar:vertical {
        border: none;
        background: #e9ecef;
        width: 10px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: #adb5bd;
        min-height: 20px;
        border-radius: 5px;
    }
    QTableWidget {
        background-color: white;
        border: 1px solid #dee2e6;
        border-radius: 4px;
        gridline-color: #f1f3f5;
        selection-background-color: #e7f5ff;
        selection-color: black;
    }
    QHeaderView::section {
        background-color: #e9ecef;
        padding: 4px;
        border: none;
        font-weight: bold;
        color: #495057;
    }
    CollapsibleBox {
        margin-top: 10px;
    }
    QLineEdit {
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 4px;
    }
    QPushButton {
        border-radius: 4px;
        padding: 6px 12px;
    }
    QToolButton {
        font-size: 10pt;
    }
    QCheckBox::indicator {
        width: 16px; 
        height: 16px;
    }
    """
    config_updated = pyqtSignal(dict) # Signal emitted when config is saved/applied

    def __init__(self, config_data, parent=None, config_path="config.json"):
        super().__init__(parent)
        self.loc = LocalizationManager()
        self.setWindowTitle(self.loc.get("EDITOR_TITLE"))
        self.setWindowIcon(QIcon(get_resource_path("assets/LocalInfoReminder.ico")))
        self.resize(1000, 800)
        self.setFont(QFont("Microsoft YaHei", 10))
        self.setStyleSheet(self.STYLESHEET)
        
        # Deep copy config data
        self.config_data = copy.deepcopy(config_data)
        self.config_path = config_path
        self.vision_detection = copy.deepcopy(
            ConfigLoader.normalize_vision_detection(
                self.config_data.get("vision_detection", {})
            )
        )

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(5)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        
        # 1. Session State Section
        self.setup_session_section()
        
        # 2. Class Templates Section
        self.setup_classes_section()
        
        # 3. Command Skills Section
        self.setup_command_skills_section()

        # 4. Global Events Section
        self.setup_events_section()

        # 5. Miracle Skills Section
        self.setup_miracle_skills_section()
        
        # 6. Target event settings section
        self.setup_boss_section()

        self.content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_save = QPushButton(self.loc.get("BTN_SAVE"))
        self.btn_save.clicked.connect(self.save_and_apply)
        self.btn_save.setStyleSheet("background-color: #007bff; color: white; padding: 10px; font-weight: bold; font-size: 14px; border-radius: 4px;")
        
        btn_cancel = QPushButton(self.loc.get("BTN_CANCEL"))
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_save)
        
        main_layout.addLayout(btn_layout)

    def save_and_apply(self):
        # A. Scrape Session State (Time only)
        session_state = self.config_data.get("session_state", {})
        session_state["time"] = self.edit_session_time.text().strip()
        
        self.config_data["session_state"] = session_state
        
        # Save Transparency
        self.config_data["overlay_bg_alpha"] = self.slider_transparency.value()
        # Deprecate or sync old key
        self.config_data["hide_overlay_background"] = (self.slider_transparency.value() < 50)
        
        # [NEW] Save Granular Configs
        
        # 1. Feature Enable Flags
        if hasattr(self, 'box_classes'): self.config_data['enable_classes'] = self.box_classes.is_checked()
        if hasattr(self, 'box_command'): self.config_data['enable_command_skills'] = self.box_command.is_checked()
        if hasattr(self, 'box_miracle'): self.config_data['enable_miracle_skills'] = self.box_miracle.is_checked()
        if hasattr(self, 'box_events'): self.config_data['enable_global_events'] = self.box_events.is_checked()
        if hasattr(self, 'box_boss'): self.config_data['enable_boss_settings'] = self.box_boss.is_checked()
        if hasattr(self, 'box_session'): self.config_data['enable_time_display'] = self.box_session.is_checked() # Assuming session box controls time display
        
        # 2. Granular OCR
        if hasattr(self, 'chk_ocr_time'): self.config_data['ocr_time_sync'] = self.chk_ocr_time.isChecked()
        if hasattr(self, 'chk_ocr_command'): self.config_data['ocr_command_skills'] = self.chk_ocr_command.isChecked()
        if hasattr(self, 'chk_ocr_boss'): self.config_data['ocr_boss_detection'] = self.chk_ocr_boss.isChecked()

        # B. Scrape Classes (Card Logic)
        new_classes = []
        # Rebuild classes_state entirely to avoid stale keys on rename
        classes_state = {} 
        
        # Ensure we have class_cards
        if hasattr(self, 'class_cards'):
            for card in self.class_cards:
                t_data, s_data = card.get_data()
                
                # Get ID (New or Old)
                # We do NOT rename folders. Logic engine/Audio manager will just fail to find sound if user doesn't move it.
                # User specifically requested: "If not found, output log. Never rename folders."
                
                cid = t_data.get("id")

                # Update Template List
                new_classes.append(t_data)
                
                # Update Session Dict
                if cid:
                    classes_state[cid] = s_data
        
        # Assign rebuilding dict back to session
        session_state["classes"] = classes_state
        
        self.config_data["classes_template"] = new_classes
        session_state["classes"] = classes_state

        # C. Scrape Skills (Card Logic)
        new_skills = []
        if hasattr(self, 'command_cards'):
            for card in self.command_cards:
                new_skills.append(card.get_data())
        self.config_data["command_skills"] = new_skills

        # [NEW] Scrape Miracle Skills
        new_miracles = []
        if hasattr(self, 'miracle_cards'):
            for card in self.miracle_cards:
                new_miracles.append(card.get_data())
        self.config_data["miracle_skills"] = new_miracles

        # D. Scrape Events
        new_events = []
        for row in range(self.table_events.rowCount()):
            evt = {}
            evt["is_enabled"] = self.get_checkbox_state(self.table_events, row, 0)
            evt["is_muted"] = self.get_checkbox_state(self.table_events, row, 1)
            evt["time"] = self.get_text(self.table_events, row, 2)
            evt["name"] = self.get_text(self.table_events, row, 3)
            
            # Get sound from cell widget
            w4 = self.table_events.cellWidget(row, 4)
            if w4:
                edit = w4.findChild(QLineEdit, "edit_sound")
                evt["sound"] = edit.text() if edit else ""
            else:
                evt["sound"] = ""
                
            new_events.append(evt)
        self.config_data["global_events"] = new_events

        # E. Scrape target event settings
        new_targets = []
        if hasattr(self, 'boss_target_cards'):
            for card in self.boss_target_cards:
                new_targets.append(card.get_data())

        boss_detection = ConfigLoader.normalize_boss_detection({"targets": new_targets}, {})
        self.config_data["boss_detection"] = boss_detection
        self.config_data.pop("boss_buff_durations", None)

        # F. Scrape vision detection settings
        self.vision_detection.setdefault("thresholds", {})
        self.vision_detection["thresholds"]["skill_trigger_ratio"] = self.spin_skill_trigger_ratio.value()
        self.vision_detection["thresholds"]["boss_faction_ratio"] = self.spin_boss_faction_ratio.value()
        self.config_data["vision_detection"] = ConfigLoader.normalize_vision_detection(self.vision_detection)

        # Emit signal with new data
        self.config_updated.emit(self.config_data)
        self.accept()
