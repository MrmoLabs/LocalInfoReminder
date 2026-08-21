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


class ConfigEditorMixin:
    def on_class_table_changed(self, item):
        pass

    def on_time_editing_finished(self):
        text = self.edit_session_time.text().strip()
        # Auto-format MMSS -> MM:SS
        if text.isdigit():
            if len(text) == 4: # 2243 -> 22:43
                self.edit_session_time.setText(f"{text[:2]}:{text[2:]}")
            elif len(text) == 3: # 130 -> 1:30
                self.edit_session_time.setText(f"{text[:1]}:{text[1:]}")
            elif len(text) == 1 or len(text) == 2: # 30 -> 00:30
                self.edit_session_time.setText(f"00:{text.zfill(2)}")

    def setup_session_section(self):
        # [NEW] Checkbox enabled (Using enable_time_display as user requested manual toggle for time display)
        enabled = self.config_data.get("enable_time_display", True)
        box = CollapsibleBox(self.loc.get("SEC_SESSION"), enable_check=True, checked=enabled)
        self.box_session = box
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        form_layout = QFormLayout()
        session_state = self.config_data.get("session_state", {})
        
        # [NEW] Time Display Toggle linked to session? Or separate in overlay?
        # User asked for "enable_time_display". We can associate it with this box or separate.
        # But this box title is "Session Settings". Let's put Time Sync OCR here.
        
        # OCR Toggle (Time Sync)
        self.chk_ocr_time = QCheckBox(self.loc.get("LBL_OCR_TIME"))
        self.chk_ocr_time.setChecked(self.config_data.get("ocr_time_sync", True))
        self.chk_ocr_time.setToolTip(self.loc.get("UI_OCR_TIME_TOOLTIP"))
        form_layout.addRow(self.chk_ocr_time)

        self.edit_session_time = QLineEdit(session_state.get("time", "00:00"))
        
        # Tracking
        self.orig_session_time = session_state.get("time", "00:00")
        self.edit_session_time.textChanged.connect(self.check_session_time)
        self.edit_session_time.editingFinished.connect(self.on_time_editing_finished)
        
        form_layout.addRow(self.loc.get("LBL_INIT_TIME"), self.edit_session_time)
        
        # Overlay Transparency Slider
        self.lbl_transparency = QLabel(self.loc.get("LBL_TRANSPARENCY").format(self.config_data.get('overlay_bg_alpha', 220)))
        form_layout.addRow(self.lbl_transparency)
        
        self.slider_transparency = QSlider(Qt.Orientation.Horizontal)
        self.slider_transparency.setRange(5, 255)
        # Handle migration: if no new key, check old key
        default_alpha = 220
        if 'overlay_bg_alpha' in self.config_data:
            default_alpha = self.config_data['overlay_bg_alpha']
        elif self.config_data.get('hide_overlay_background', False):
            default_alpha = 5
            
        self.slider_transparency.setValue(default_alpha)
        self.slider_transparency.valueChanged.connect(self.update_transparency_label)
        
        form_layout.addRow(self.slider_transparency)

        self.btn_edit_time_roi = QPushButton("查看 / 调整时间OCR区域")
        self.btn_edit_time_roi.clicked.connect(lambda: self.open_roi_editor(
            ["time_main", "time_prep"],
            "时间OCR区域",
            "这里调整主倒计时与准备倒计时的OCR截图区域，保存的是屏幕相对比例，会随分辨率自适应。",
        ))
        form_layout.addRow("时间OCR区域", self.btn_edit_time_roi)

        layout.addLayout(form_layout)
        
        box.set_content_layout(layout)
        box.set_content_visible(True) # Expand by default
        self.content_layout.addWidget(box)

    def _exec_roi_editor(self, region_keys, title, helper_text, ocr_fields=None, ocr_profiles=None, color_profiles=None):
        dialog = RoiEditorDialog(
            self.vision_detection.get("regions", {}),
            self,
            region_keys=region_keys,
            title=title,
            helper_text=helper_text,
            ocr_fields=ocr_fields,
            ocr_profiles=ocr_profiles,
            color_profiles=color_profiles,
        )
        if dialog.exec():
            self.vision_detection["regions"] = dialog.get_regions()
            if hasattr(dialog, "get_color_profiles"):
                updated_color_profiles = dialog.get_color_profiles()
                if updated_color_profiles:
                    existing_profiles = dict(self.vision_detection.get("color_profiles", {}))
                    for profile in updated_color_profiles:
                        profile_id = profile.get("id")
                        if not profile_id:
                            continue
                        existing_profiles[profile_id] = {
                            k: v for k, v in profile.items() if k not in {"id", "label", "roi_key"}
                        }
                    self.vision_detection["color_profiles"] = existing_profiles
            return dialog
        return None

    def open_roi_editor(self, region_keys, title, helper_text):
        self._exec_roi_editor(region_keys, title, helper_text)

    def _open_command_ocr_editor(self):
        profiles = []
        for index, card in enumerate(getattr(self, "command_cards", []), start=1):
            profiles.append({
                "id": f"command_{index}",
                "label": card.edit_name.text().strip() or card.edit_id.text().strip() or f"条目{index}",
                "fields": [
                    {
                        "key": "ocr_keywords",
                        "label": "识别词",
                        "value": card.edit_keywords.text().strip(),
                        "placeholder": self.loc.get("UI_OCR_KEYWORDS_PLACEHOLDER"),
                    }
                ],
            })
        color_profiles = []
        stored_profiles = self.vision_detection.get("color_profiles", {})
        for profile_id, label in (("skill_red", "红色触发"), ("skill_blue", "蓝色触发")):
            profile_data = dict(stored_profiles.get(profile_id, {}))
            profile_data["id"] = profile_id
            profile_data["label"] = label
            profile_data["roi_key"] = "skill_bar"
            color_profiles.append(profile_data)
        dialog = self._exec_roi_editor(
            ["skill_bar"],
            "主条目标识别区域",
            "这里调整主条目识别截图区域，并可在右侧切换具体条目，直接编辑对应识别词并测试 OCR 结果。",
            ocr_profiles=profiles,
            color_profiles=color_profiles,
        )
        if dialog:
            updated_profiles = dialog.get_ocr_profiles()
            for card, profile in zip(getattr(self, "command_cards", []), updated_profiles):
                fields = {field.get("key"): field.get("value", "") for field in profile.get("fields", [])}
                card.edit_keywords.setText(fields.get("ocr_keywords", ""))
            skill_red = self.vision_detection.get("color_profiles", {}).get("skill_red", {})
            if skill_red:
                self.spin_skill_trigger_ratio.setValue(float(skill_red.get("min_ratio", self.spin_skill_trigger_ratio.value())))

    def _open_boss_ocr_editor(self):
        profiles = []
        for index, card in enumerate(getattr(self, "boss_target_cards", []), start=1):
            profiles.append({
                "id": f"boss_{index}",
                "label": card.edit_display_name.text().strip() or card.edit_id.text().strip() or f"目标{index}",
                "fields": [
                    {
                        "key": "ocr_keywords",
                        "label": "识别词",
                        "value": card.edit_ocr_keywords.text().strip(),
                        "placeholder": "目标名1,目标名2",
                    },
                    {
                        "key": "kill_keywords",
                        "label": "结果词",
                        "value": card.edit_kill_keywords.text().strip(),
                        "placeholder": "完成,获得",
                    },
                    {
                        "key": "ignore_keywords",
                        "label": "屏蔽词",
                        "value": card.edit_ignore_keywords.text().strip(),
                        "placeholder": "即将,出现,提示",
                    },
                ],
            })
        color_profiles = []
        stored_profiles = self.vision_detection.get("color_profiles", {})
        for profile_id, label in (("boss_red", "颜色规则A"), ("boss_blue", "颜色规则B")):
            profile_data = dict(stored_profiles.get(profile_id, {}))
            profile_data["id"] = profile_id
            profile_data["label"] = label
            profile_data["roi_key"] = "boss_kill"
            color_profiles.append(profile_data)
        dialog = self._exec_roi_editor(
            ["boss_notification", "boss_kill"],
            "目标事件识别区域",
            "这里调整目标事件播报区与结果区的 OCR 截图区域，并可在右侧切换具体目标，直接编辑识别词、结果词和屏蔽词。",
            ocr_profiles=profiles,
            color_profiles=color_profiles,
        )
        if dialog:
            updated_profiles = dialog.get_ocr_profiles()
            for card, profile in zip(getattr(self, "boss_target_cards", []), updated_profiles):
                fields = {field.get("key"): field.get("value", "") for field in profile.get("fields", [])}
                card.edit_ocr_keywords.setText(fields.get("ocr_keywords", ""))
                card.edit_kill_keywords.setText(fields.get("kill_keywords", ""))
                card.edit_ignore_keywords.setText(fields.get("ignore_keywords", ""))
            boss_red = self.vision_detection.get("color_profiles", {}).get("boss_red", {})
            if boss_red:
                self.spin_boss_faction_ratio.setValue(float(boss_red.get("min_ratio", self.spin_boss_faction_ratio.value())))

    def check_session_time(self):
        curr = self.edit_session_time.text().strip()
        if curr != self.orig_session_time:
             self.edit_session_time.setStyleSheet("border: 1px solid #dc3545; background-color: #fff5f5;")
        else:
             self.edit_session_time.setStyleSheet("border: 1px solid #ced4da; border-radius: 4px; padding: 4px;") # Revert to default QLineEdit style defined in STYLESHEET

    def update_transparency_label(self, value):
        self.lbl_transparency.setText(self.loc.get("LBL_TRANSPARENCY").format(value))

    def setup_classes_section(self):
        # [NEW] Checkbox enabled
        enabled = self.config_data.get("enable_classes", True)
        box = CollapsibleBox(self.loc.get("SEC_CLASSES"), enable_check=True, checked=enabled)
        self.box_classes = box # Keep ref
        
        layout = QVBoxLayout()
        header_layout = QHBoxLayout()
        btn_add = QPushButton(self.loc.get("BTN_ADD_CLASS"))
        btn_add.clicked.connect(self.add_class_card)
        header_layout.addWidget(btn_add)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Use a Vertical Layout for Cards
        self.classes_layout = QVBoxLayout()
        self.classes_layout.setSpacing(10)
        layout.addLayout(self.classes_layout)
        
        classes = self.config_data.get("classes_template", [])
        session_state = self.config_data.get("session_state", {})
        stored_classes_state = session_state.get("classes", {})
        
        self.class_cards = []
        for cls in classes:
            c_id = cls.get('id')
            c_data = stored_classes_state.get(c_id, {})
            self.add_class_card_to_layout(cls, c_data)
            
        box.set_content_layout(layout)
        box.set_content_visible(True) # Expanded mainly
        self.content_layout.addWidget(box)

    def add_class_card_to_layout(self, template, session):
        card = ClassConfigCard(template, session)
        card.delete_requested.connect(self.remove_class_card)
        self.classes_layout.addWidget(card)
        self.class_cards.append(card)

    def add_class_card(self):
        # Prompt for ID and Name
        cid, ok1 = QInputDialog.getText(self, self.loc.get("DLG_TITLE_ADD_CLASS"), self.loc.get("DLG_MSG_CLASS_ID"))
        if not ok1 or not cid: return
        name, ok2 = QInputDialog.getText(self, self.loc.get("DLG_TITLE_ADD_CLASS"), self.loc.get("DLG_MSG_CLASS_NAME"))
        if not ok2 or not name: return

        # Check for duplicates
        if any(c.template_data.get('id') == cid for c in self.class_cards):
            QMessageBox.warning(self, self.loc.get("WIN_TITLE"), self.loc.get("ERR_ID_EXISTS").format(cid))
            return

        new_template = {
            "is_enabled": True,
            "id": cid,
            "name": name,
            "default_hotkey": "Click to Set",
            "interval": 10.0,
            "cooldown": 20.0,
            "skip_cd_hotkey": "Click to Set",
            "is_muted": False
        }
        new_session = {"count": 1, "mode_index": 0}
        self.add_class_card_to_layout(new_template, new_session)

    def remove_class_card(self, card):
        reply = QMessageBox.question(self, self.loc.get("UI_DELETE_CONFIRM"), self.loc.get("UI_DELETE_CLASS_MSG").format(card.template_data.get("name")),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.class_cards.remove(card)
            card.deleteLater()
            # Note: We don't remove from config_data yet, save_and_apply will handle it.

    def adjust_table_height(self, table, min_h=100, max_h=400):
        """Helper to auto-size table height based on rows."""
        # Calculate required height
        header_h = table.horizontalHeader().height()
        rows_h = 0
        for i in range(table.rowCount()):
             rows_h += table.rowHeight(i)
        
        total_h = header_h + rows_h + 20 # Buffer
        final_h = max(min_h, min(total_h, max_h))
        table.setMinimumHeight(final_h)
        # If rows are few, we want it short.
        if total_h < max_h:
             table.setFixedHeight(total_h) 
        else:
             table.setMinimumHeight(max_h) # Force scroll if many rows

    def setup_command_skills_section(self):
        # [NEW] Checkbox enabled
        enabled = self.config_data.get("enable_command_skills", True)
        box = CollapsibleBox(self.loc.get("SEC_COMMAND"), enable_check=True, checked=enabled)
        self.box_command = box
        
        layout = QVBoxLayout()
        header_layout = QHBoxLayout()
        btn_add = QPushButton(self.loc.get("BTN_ADD_COMMAND"))
        btn_add.clicked.connect(lambda: self.add_skill_card(False))
        header_layout.addWidget(btn_add)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # [NEW] OCR Toggle for Command Skills
        self.chk_ocr_command = QCheckBox(self.loc.get("LBL_OCR_COMMAND"))
        self.chk_ocr_command.setChecked(self.config_data.get("ocr_command_skills", True))
        self.chk_ocr_command.setToolTip(self.loc.get("UI_OCR_COMMAND_TOOLTIP"))
        layout.addWidget(self.chk_ocr_command)

        command_ocr_form = QFormLayout()
        self.btn_edit_command_roi = QPushButton("查看 / 调整主条目标识别区域")
        self.btn_edit_command_roi.clicked.connect(self._open_command_ocr_editor)
        command_ocr_form.addRow("OCR区域", self.btn_edit_command_roi)

        self.spin_skill_trigger_ratio = QDoubleSpinBox()
        self.spin_skill_trigger_ratio.setDecimals(4)
        self.spin_skill_trigger_ratio.setRange(0.0001, 1.0)
        self.spin_skill_trigger_ratio.setSingleStep(0.001)
        self.spin_skill_trigger_ratio.setValue(float(self.vision_detection.get("thresholds", {}).get("skill_trigger_ratio", 0.01)))
        command_ocr_form.addRow("颜色触发阈值", self.spin_skill_trigger_ratio)
        layout.addLayout(command_ocr_form)

        self.command_layout = QVBoxLayout()
        self.command_layout.setSpacing(10)
        layout.addLayout(self.command_layout)
        
        skills = self.config_data.get("command_skills", [])
        self.command_cards = []
        
        for skill in skills:
            self.add_skill_card_to_layout(skill, False)
            
        box.set_content_layout(layout)
        box.set_content_visible(False) # Collapsed
        self.content_layout.addWidget(box)

    def setup_miracle_skills_section(self):
        # [NEW] Checkbox enabled
        enabled = self.config_data.get("enable_miracle_skills", True)
        box = CollapsibleBox(self.loc.get("SEC_MIRACLE"), enable_check=True, checked=enabled)
        self.box_miracle = box
        
        layout = QVBoxLayout()
        header_layout = QHBoxLayout()
        btn_add = QPushButton(self.loc.get("BTN_ADD_MIRACLE"))
        btn_add.clicked.connect(lambda: self.add_skill_card(True))
        header_layout.addWidget(btn_add)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.miracle_layout = QVBoxLayout()
        self.miracle_layout.setSpacing(10)
        layout.addLayout(self.miracle_layout)
        
        miracles = self.config_data.get("miracle_skills", [])
        self.miracle_cards = []
        
        for m in miracles:
            self.add_skill_card_to_layout(m, True)
            
        box.set_content_layout(layout)
        box.set_content_visible(False)
        self.content_layout.addWidget(box)

    def add_skill_card_to_layout(self, data, is_miracle):
        card = SkillConfigCard(data, is_miracle=is_miracle)
        card.delete_requested.connect(self.remove_skill_card)
        if is_miracle:
            self.miracle_layout.addWidget(card)
            self.miracle_cards.append(card)
        else:
            self.command_layout.addWidget(card)
            self.command_cards.append(card)

    def add_skill_card(self, is_miracle):
        title = self.loc.get("UI_MIRACLE_SKILL") if is_miracle else self.loc.get("UI_COMMAND_SKILL")
        name, ok = QInputDialog.getText(self, self.loc.get("UI_ADD_SKILL_TITLE").format(title), self.loc.get("UI_ADD_SKILL_PROMPT").format(title))
        if not ok or not name: return
        
        new_skill = {
            "is_enabled": True,
            "is_muted": False,
            "id": name, # Simplification: ID = Name if not specified
            "name": name,
            "cooldown": 180.0,
            "default_hotkey": "Click to Set",
            "sound": ""
        }
        if not is_miracle:
            new_skill["duration"] = 5.0
            new_skill["type"] = "enemy"
            new_skill["cd_threshold"] = 0
            new_skill["cd_flash"] = False
            new_skill["cd_sound"] = ""
        # else: Miracle skills don't need explicit type in config
            
        self.add_skill_card_to_layout(new_skill, is_miracle)

    def remove_skill_card(self, card):
        title = self.loc.get("UI_MIRACLE_SKILL") if card.is_miracle else self.loc.get("UI_COMMAND_SKILL")
        reply = QMessageBox.question(self, self.loc.get("UI_DELETE_CONFIRM"), self.loc.get("UI_DELETE_SKILL_MSG").format(title, card.skill_data.get("name")),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if card.is_miracle:
                self.miracle_cards.remove(card)
            else:
                self.command_cards.remove(card)
            card.deleteLater()

    def setup_boss_section(self):
        enabled = self.config_data.get("enable_boss_settings", True)
        box = CollapsibleBox(self.loc.get("SEC_BOSS"), enable_check=True, checked=enabled)
        self.box_boss = box

        boss_detection = ConfigLoader.normalize_boss_detection(
            self.config_data.get("boss_detection", {}),
            {},
        )
        targets = boss_detection.get("targets", ConfigLoader.default_boss_targets())

        layout = QVBoxLayout()
        layout.setSpacing(12)

        overview_group = QGroupBox("运行逻辑概览")
        overview_layout = QVBoxLayout(overview_group)
        overview_layout.setContentsMargins(12, 12, 12, 12)
        overview_layout.setSpacing(8)

        overview_text = QLabel(
            "1. 到达监听时间窗口后，系统开始监听目标事件播报。\n"
            "2. 播报 OCR 命中后，会生成预计出现倒计时，并准备进入完成检测阶段。\n"
            "3. 在结果监听窗口内，系统结合颜色与 OCR 文本判断结果是否成立，并决定播放哪种结果音频。"
        )
        overview_text.setWordWrap(True)
        overview_layout.addWidget(overview_text)
        layout.addWidget(overview_group)

        baseline_group = QGroupBox("全局识别基准")
        baseline_layout = QVBoxLayout(baseline_group)
        baseline_layout.setContentsMargins(12, 12, 12, 12)
        baseline_layout.setSpacing(8)

        baseline_hint = QLabel("这里放的是所有目标事件共用的识别基础能力：是否启用 OCR、识别区域，以及颜色规则的整体阈值。具体某个目标识别什么词、监听多久，放在下面的目标用例里配置。")
        baseline_hint.setWordWrap(True)
        baseline_layout.addWidget(baseline_hint)

        self.chk_ocr_boss = QCheckBox(self.loc.get("LBL_OCR_BOSS"))
        self.chk_ocr_boss.setChecked(self.config_data.get("ocr_boss_detection", True))
        self.chk_ocr_boss.setToolTip(self.loc.get("UI_OCR_BOSS_TOOLTIP"))
        baseline_layout.addWidget(self.chk_ocr_boss)

        boss_ocr_form = QFormLayout()
        self.btn_edit_boss_roi = QPushButton("查看 / 调整目标事件识别区域")
        self.btn_edit_boss_roi.clicked.connect(self._open_boss_ocr_editor)
        boss_ocr_form.addRow("识别区域与 OCR 调试", self.btn_edit_boss_roi)

        self.spin_boss_faction_ratio = QDoubleSpinBox()
        self.spin_boss_faction_ratio.setDecimals(4)
        self.spin_boss_faction_ratio.setRange(0.0001, 1.0)
        self.spin_boss_faction_ratio.setSingleStep(0.001)
        self.spin_boss_faction_ratio.setValue(float(self.vision_detection.get("thresholds", {}).get("boss_faction_ratio", 0.03)))
        boss_ocr_form.addRow("全局颜色阈值", self.spin_boss_faction_ratio)
        baseline_layout.addLayout(boss_ocr_form)
        layout.addWidget(baseline_group)

        cases_group = QGroupBox("目标用例")
        cases_layout = QVBoxLayout(cases_group)
        cases_layout.setContentsMargins(12, 12, 12, 12)
        cases_layout.setSpacing(10)

        cases_hint = QLabel("每一张目标卡片都对应一个完整用例。请按“播报检测 → 结果识别 → 完成后处理”的顺序填写，而不是把字段当作独立参数来理解。")
        cases_hint.setWordWrap(True)
        cases_layout.addWidget(cases_hint)

        action_layout = QHBoxLayout()
        btn_add_target = QPushButton("+ 新增目标")
        btn_add_target.clicked.connect(self.add_boss_target_card)
        action_layout.addWidget(btn_add_target)
        action_layout.addStretch()
        cases_layout.addLayout(action_layout)

        self.boss_targets_layout = QVBoxLayout()
        self.boss_targets_layout.setSpacing(10)
        self.boss_target_cards = []
        for target in targets:
            self.add_boss_target_card_to_layout(target)
        cases_layout.addLayout(self.boss_targets_layout)
        layout.addWidget(cases_group)

        box.set_content_layout(layout)
        box.set_content_visible(False)
        self.content_layout.addWidget(box)

    def add_boss_target_card_to_layout(self, target):
        card = BossTargetConfigCard(target)
        card.delete_requested.connect(self.remove_boss_target_card)
        self.boss_targets_layout.addWidget(card)
        self.boss_target_cards.append(card)

    def add_boss_target_card(self):
        index = len(getattr(self, 'boss_target_cards', [])) + 1
        self.add_boss_target_card_to_layout({
            "id": f"target_{index}",
            "display_name": f"\u76ee\u6807{index}",
            "match_names": [],
            "ocr_keywords": [f"\u76ee\u6807{index}"],
            "time_windows": ConfigLoader.default_boss_time_windows(),
            "kill_window_seconds": 180,
            "kill_keywords": ["\u5b8c\u6210"],
            "faction_match": "distinguish",
            "ignore_keywords": ["\u5373\u5c06", "\u51fa\u73b0", "\u63d0\u793a"],
            "spawn_sound": "dragon_spawn.mp3",
            "kill_sound": "",
            "buff_duration": 120,
        })

    def remove_boss_target_card(self, card):
        if card in self.boss_target_cards:
            self.boss_target_cards.remove(card)
            card.deleteLater()

    def setup_events_section(self):
        # [NEW] Checkbox enabled
        enabled = self.config_data.get("enable_global_events", True)
        box = CollapsibleBox(self.loc.get("SEC_EVENTS"), enable_check=True, checked=enabled)
        self.box_events = box

        layout = QVBoxLayout()
        
        # Helper: Select All / None (REMOVED per user request)
        action_layout = QHBoxLayout()
        btn_add = QPushButton(self.loc.get("BTN_ADD_EVENT"))
        btn_add.clicked.connect(self.add_event_row)
        
        action_layout.addWidget(btn_add)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Table
        # Columns: [Enabled] [Mute] [Time] [Name] [Sound] [Action]
        columns = [self.loc.get("HDR_ENABLED"), self.loc.get("HDR_MUTE"), self.loc.get("HDR_TIME"), self.loc.get("HDR_NAME"), self.loc.get("HDR_SOUND"), self.loc.get("HDR_ACTION")]
        self.table_events = QTableWidget()
        self.table_events.setAlternatingRowColors(True)
        self.table_events.verticalHeader().setVisible(False)
        self.table_events.setColumnCount(len(columns))
        self.table_events.setHorizontalHeaderLabels(columns)
        self.table_events.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_events.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_events.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_events.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        events = self.config_data.get("global_events", [])
        self.orig_events = copy.deepcopy(events) # Store original
        
        self.table_events.itemChanged.connect(self.on_event_item_changed)
        
        for row, evt in enumerate(events):
            self.add_event_row_to_table(evt)
            
        self.table_events.resizeRowsToContents()
        self.table_events.verticalHeader().setDefaultSectionSize(40) # Ensure min height for inputs
        self.adjust_table_height(self.table_events)
        layout.addWidget(self.table_events)
        box.set_content_layout(layout)
        box.set_content_visible(False)
        self.content_layout.addWidget(box)

    def add_event_row_to_table(self, evt):
        row = self.table_events.rowCount()
        self.table_events.insertRow(row)
        
        # 0: Enabled
        self.set_checkbox_cell(self.table_events, row, 0, evt.get("is_enabled", True))
        w0 = self.table_events.cellWidget(row, 0)
        if w0 and hasattr(w0, 'checkbox'):
            w0.checkbox.toggled.connect(lambda: self.check_event_row(row))

        # 1: Mute
        self.set_checkbox_cell(self.table_events, row, 1, evt.get("is_muted", False))
        w1 = self.table_events.cellWidget(row, 1)
        if w1 and hasattr(w1, 'checkbox'):
            w1.checkbox.toggled.connect(lambda: self.check_event_row(row))

        # 2: Time, 3: Name
        self.table_events.setItem(row, 2, QTableWidgetItem(evt.get("time", "")))
        self.table_events.setItem(row, 3, QTableWidgetItem(evt.get("name", "")))
        
        # 4: Sound with Browse
        sound_widget = QWidget()
        s_layout = QHBoxLayout(sound_widget)
        s_layout.setContentsMargins(2, 2, 2, 2)
        s_layout.setSpacing(2)
        
        edit_sound = QLineEdit(evt.get("sound", ""))
        edit_sound.setObjectName("edit_sound")
        edit_sound.setMinimumHeight(30)
        btn_browse = QPushButton(self.loc.get("BTN_BROWSE"))
        btn_browse.setMinimumWidth(56)
        btn_browse.setFixedHeight(30)
        btn_browse.setStyleSheet("padding: 2px 10px;")
        btn_browse.clicked.connect(lambda: self._browse_event_sound(edit_sound))
        
        s_layout.addWidget(edit_sound)
        s_layout.addWidget(btn_browse)
        self.table_events.setCellWidget(row, 4, sound_widget)

        # 5: Delete Button
        btn_del = QPushButton(self.loc.get("BTN_DELETE"))
        btn_del.setFixedSize(60, 24)
        btn_del.setStyleSheet("QPushButton { color: #666; background-color: transparent; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; } QPushButton:hover { color: white; background-color: #dc3545; border-color: #dc3545; }")
        btn_del.clicked.connect(lambda: self.remove_event_row(row))
        self.table_events.setCellWidget(row, 5, btn_del)

    def _browse_event_sound(self, line_edit):
        initial_dir = os.path.join(os.getcwd(), "assets", "global_events")
        if not os.path.exists(initial_dir): os.makedirs(initial_dir, exist_ok=True)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.loc.get("UI_SELECT_SOUND"), initial_dir, "Audio Files (*.mp3 *.wav)"
        )
        if file_path:
            assets_root = os.path.join(os.getcwd(), "assets")
            if file_path.startswith(assets_root):
                rel_path = os.path.relpath(file_path, assets_root).replace("\\", "/")
                line_edit.setText(rel_path)
            else:
                line_edit.setText(os.path.basename(file_path))

    def add_event_row(self):
        self.table_events.blockSignals(True)
        self.add_event_row_to_table({"is_enabled": True, "is_muted": False, "time": "00:00", "name": self.loc.get("UI_NEW_EVENT"), "sound": ""})
        self.table_events.blockSignals(False)
        self.adjust_table_height(self.table_events)

    def remove_event_row(self, row_index):
        button = self.sender()
        if button:
            idx = self.table_events.indexAt(button.pos())
            if idx.isValid():
                self.table_events.removeRow(idx.row())
                self.adjust_table_height(self.table_events)

    def on_event_item_changed(self, item):
        self.check_event_row(item.row())

    def check_event_row(self, row):
        if row >= len(self.orig_events): return
        
        orig = self.orig_events[row]
        
        self.table_events.blockSignals(True)
        try:
            # 0: Enabled
            curr_enabled = self.get_checkbox_state(self.table_events, row, 0)
            w0 = self.table_events.cellWidget(row, 0)
            if w0 and hasattr(w0, 'checkbox'):
                 if curr_enabled != orig.get("is_enabled", True):
                     w0.checkbox.setStyleSheet("background-color: #fff5f5; border-radius: 4px;")
                 else:
                     w0.checkbox.setStyleSheet("")

            # 1: Mute
            curr_mute = self.get_checkbox_state(self.table_events, row, 1)
            w1 = self.table_events.cellWidget(row, 1)
            if w1 and hasattr(w1, 'checkbox'):
                 if curr_mute != orig.get("is_muted", False):
                     w1.checkbox.setStyleSheet("background-color: #fff5f5; border-radius: 4px;")
                 else:
                     w1.checkbox.setStyleSheet("")

            # 2: Time
            item_time = self.table_events.item(row, 2)
            if item_time:
                 if item_time.text().strip() != orig.get("time", ""):
                     item_time.setBackground(QColor("#fff5f5"))
                 else:
                     item_time.setData(Qt.ItemDataRole.BackgroundRole, None)

            # 3: Name
            item_name = self.table_events.item(row, 3)
            if item_name:
                 if item_name.text().strip() != orig.get("name", ""):
                     item_name.setBackground(QColor("#fff5f5"))
                 else:
                     item_name.setData(Qt.ItemDataRole.BackgroundRole, None)

            # 4: Sound
            item_sound = self.table_events.item(row, 4)
            if item_sound:
                 if item_sound.text().strip() != orig.get("sound", ""):
                     item_sound.setBackground(QColor("#fff5f5"))
                 else:
                     item_sound.setData(Qt.ItemDataRole.BackgroundRole, None)

        finally:
            self.table_events.blockSignals(False)

    # --- Helpers ---
    def set_checkbox_cell(self, table, row, col, checked):
        # Create a widget with a centered checkbox
        widget = QWidget()
        chk = QCheckBox()
        chk.setChecked(checked)
        # Store checkbox in property for retrieval
        widget.checkbox = chk 
        
        layout = QHBoxLayout(widget)
        layout.addWidget(chk)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
        table.setCellWidget(row, col, widget)

    def get_checkbox_state(self, table, row, col):
        widget = table.cellWidget(row, col)
        if widget and hasattr(widget, 'checkbox'):
            return widget.checkbox.isChecked()
        return False

    def toggle_all_table(self, table, col, state):
        for row in range(table.rowCount()):
            widget = table.cellWidget(row, col)
            if widget and hasattr(widget, 'checkbox'):
                widget.checkbox.setChecked(state)

    def get_text(self, table, row, col):
        item = table.item(row, col)
        return item.text().strip() if item else ""

