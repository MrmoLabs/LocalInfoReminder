from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ColorDebugPanel(QWidget):
    profile_changed = pyqtSignal(int)
    value_changed = pyqtSignal()
    pick_toggled = pyqtSignal(bool)
    test_clicked = pyqtSignal()

    def __init__(self, color_profiles, parent=None):
        super().__init__(parent)
        self.color_inputs = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        color_bar = QHBoxLayout()
        color_bar.addWidget(QLabel("颜色规则:"))
        self.combo_profile = QComboBox()
        for idx, profile in enumerate(color_profiles):
            self.combo_profile.addItem(profile.get("label", f"Color {idx + 1}"), idx)
        self.combo_profile.currentIndexChanged.connect(self.profile_changed.emit)
        color_bar.addWidget(self.combo_profile)
        color_bar.addStretch()
        layout.addLayout(color_bar)

        content_row = QHBoxLayout()
        content_row.setSpacing(8)
        layout.addLayout(content_row, 1)

        controls_col = QVBoxLayout()
        controls_col.setSpacing(4)
        content_row.addLayout(controls_col, 5)

        previews_col = QVBoxLayout()
        previews_col.setSpacing(4)
        content_row.addLayout(previews_col, 7)

        self.profile_id_label = QLabel()
        self.profile_id_label.setWordWrap(True)
        self.profile_id_label.setStyleSheet("color: #5f6368;")
        controls_col.addWidget(self.profile_id_label)

        self.profile_state_label = QLabel()
        self.profile_state_label.setWordWrap(True)
        self.profile_state_label.setStyleSheet("color: #2b8a3e; font-weight: 600;")
        controls_col.addWidget(self.profile_state_label)

        color_form = QFormLayout()
        color_form.setContentsMargins(0, 0, 0, 0)
        color_form.setSpacing(4)
        for key, title_text, max_value in (("r", "R", 255), ("g", "G", 255), ("b", "B", 255)):
            spin = QDoubleSpinBox()
            spin.setDecimals(0)
            spin.setRange(0, max_value)
            spin.setSingleStep(1)
            spin.setKeyboardTracking(False)
            spin.valueChanged.connect(self.value_changed.emit)
            self.color_inputs[key] = spin
            color_form.addRow(title_text, spin)
        tolerance_spin = QDoubleSpinBox()
        tolerance_spin.setDecimals(1)
        tolerance_spin.setRange(0.0, 441.0)
        tolerance_spin.setSingleStep(5.0)
        tolerance_spin.setKeyboardTracking(False)
        tolerance_spin.valueChanged.connect(self.value_changed.emit)
        self.color_inputs["tolerance"] = tolerance_spin
        color_form.addRow("容差", tolerance_spin)
        ratio_spin = QDoubleSpinBox()
        ratio_spin.setDecimals(4)
        ratio_spin.setRange(0.0, 1.0)
        ratio_spin.setSingleStep(0.001)
        ratio_spin.setKeyboardTracking(False)
        ratio_spin.valueChanged.connect(self.value_changed.emit)
        self.color_inputs["min_ratio"] = ratio_spin
        color_form.addRow("触发比例", ratio_spin)
        controls_col.addLayout(color_form)

        self.color_preview = QLabel()
        self.color_preview.setMinimumHeight(26)
        self.color_preview.setStyleSheet("border: 1px solid #999;")
        self.color_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_col.addWidget(self.color_preview)

        color_actions = QHBoxLayout()
        color_actions.setSpacing(6)
        self.btn_pick_color = QPushButton("截图取色")
        self.btn_pick_color.setCheckable(True)
        self.btn_pick_color.toggled.connect(self.pick_toggled.emit)
        color_actions.addWidget(self.btn_pick_color)
        self.btn_test_color = QPushButton("测试颜色")
        self.btn_test_color.clicked.connect(self.test_clicked.emit)
        color_actions.addWidget(self.btn_test_color)
        controls_col.addLayout(color_actions)

        self.color_pick_hint = QLabel("点击“截图取色”后，在左侧截图上单击即可取样。")
        self.color_pick_hint.setWordWrap(True)
        self.color_pick_hint.setStyleSheet("color: #5f6368;")
        controls_col.addWidget(self.color_pick_hint)

        self.color_result_label = QLabel()
        self.color_result_label.setWordWrap(True)
        controls_col.addWidget(self.color_result_label)
        controls_col.addStretch()

        self.color_range_label = QLabel("容差切片预览")
        previews_col.addWidget(self.color_range_label)

        self.color_range_preview = QLabel()
        self.color_range_preview.setMinimumSize(190, 84)
        self.color_range_preview.setMaximumHeight(92)
        self.color_range_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_range_preview.setStyleSheet("border: 1px solid #999; background-color: #f3f4f6;")
        previews_col.addWidget(self.color_range_preview)

        self.color_mask_title = QLabel("命中遮罩预览")
        previews_col.addWidget(self.color_mask_title)

        self.color_mask_stats = QLabel("命中像素: - / -")
        self.color_mask_stats.setWordWrap(True)
        self.color_mask_stats.setStyleSheet("color: #5f6368;")
        previews_col.addWidget(self.color_mask_stats)

        self.color_mask_label = QLabel()
        self.color_mask_label.setMinimumSize(260, 96)
        self.color_mask_label.setMaximumHeight(112)
        self.color_mask_label.setStyleSheet("background-color: #f3f4f6; border: 1px solid #999;")
        self.color_mask_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_mask_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        previews_col.addWidget(self.color_mask_label)

        self.compare_mask_title = QLabel("红蓝重叠预览")
        previews_col.addWidget(self.compare_mask_title)

        self.compare_mask_stats = QLabel("当前规则: - | 对照规则: - | 重叠: -")
        self.compare_mask_stats.setWordWrap(True)
        self.compare_mask_stats.setStyleSheet("color: #5f6368;")
        previews_col.addWidget(self.compare_mask_stats)

        self.compare_mask_label = QLabel()
        self.compare_mask_label.setMinimumSize(260, 96)
        self.compare_mask_label.setMaximumHeight(112)
        self.compare_mask_label.setStyleSheet("background-color: #f3f4f6; border: 1px solid #999;")
        self.compare_mask_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.compare_mask_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        previews_col.addWidget(self.compare_mask_label)
        previews_col.addStretch()


class OcrDebugPanel(QWidget):
    profile_changed = pyqtSignal(int)
    test_clicked = pyqtSignal()

    def __init__(self, ocr_profiles, ocr_field_specs, parent=None):
        super().__init__(parent)
        self.field_widgets = {}
        self.field_labels = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if ocr_profiles:
            profile_bar = QHBoxLayout()
            profile_bar.addWidget(QLabel("OCR配置:"))
            self.combo_profile = QComboBox()
            for idx, profile in enumerate(ocr_profiles):
                self.combo_profile.addItem(profile.get("label", f"Profile {idx + 1}"), idx)
            self.combo_profile.currentIndexChanged.connect(self.profile_changed.emit)
            profile_bar.addWidget(self.combo_profile)
            profile_bar.addStretch()
            layout.addLayout(profile_bar)
        else:
            self.combo_profile = None

        if ocr_field_specs:
            ocr_form = QFormLayout()
            ocr_form.setContentsMargins(0, 0, 0, 0)
            ocr_form.setSpacing(4)
            for spec in ocr_field_specs:
                edit = QLineEdit(spec.get("value", ""))
                edit.setPlaceholderText(spec.get("placeholder", ""))
                self.field_widgets[spec["key"]] = edit
                label_text = spec.get("label", spec["key"])
                self.field_labels[spec["key"]] = label_text
                ocr_form.addRow(label_text, edit)
            layout.addLayout(ocr_form)

        action_bar = QHBoxLayout()
        action_bar.setSpacing(6)
        self.btn_test_ocr = QPushButton("测试识别 (Ctrl+T)")
        self.btn_test_ocr.clicked.connect(self.test_clicked.emit)
        action_bar.addWidget(self.btn_test_ocr)
        action_bar.addStretch()
        layout.addLayout(action_bar)

        self.ocr_status_label = QLabel("OCR状态：待命")
        self.ocr_status_label.setWordWrap(True)
        self.ocr_status_label.setStyleSheet("color: #5f6368;")
        layout.addWidget(self.ocr_status_label)

        self.ocr_result_box = QTextEdit()
        self.ocr_result_box.setReadOnly(True)
        self.ocr_result_box.setMinimumHeight(96)
        self.ocr_result_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.ocr_result_box, 1)
