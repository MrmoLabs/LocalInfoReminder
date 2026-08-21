from PyQt6.QtCore import QSize, QTimer, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QImage, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import html

import mss
import numpy as np

from ui.roi_editor_canvas import RoiCanvas, ZoomScrollArea
from ui.roi_editor_color import build_color_mask_preview, build_color_range_preview, build_dual_color_mask_preview
from ui.roi_editor_panels import ColorDebugPanel, OcrDebugPanel


from ui.roi_editor_view_mixin import RoiEditorViewMixin
from ui.roi_editor_analysis_mixin import RoiEditorAnalysisMixin

class RoiEditorDialog(RoiEditorViewMixin, RoiEditorAnalysisMixin, QDialog):
    REGION_TEXT = {
        "time_main": "Time Main",
        "time_prep": "Time Prep",
        "skill_bar": "Command Skill",
        "boss_notification": "目标事件播报",
        "boss_kill": "目标事件结果",
    }
    ZOOM_CHOICES = [25, 33, 50, 67, 75, 100, 125, 150, 200]
    OCR_ENGINE = None

    def __init__(self, regions, parent=None, region_keys=None, title="ROI Editor", helper_text=None, ocr_fields=None, ocr_profiles=None, color_profiles=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        screen = QGuiApplication.primaryScreen()
        self._available_geometry = screen.availableGeometry() if screen is not None else None
        ordered_keys = list(region_keys or regions.keys())
        self._regions = {key: dict(regions[key]) for key in ordered_keys if key in regions}
        self._all_regions = {key: dict(value) for key, value in regions.items()}
        self._region_keys = ordered_keys or list(self._regions.keys())
        self._screen_size = (1280, 720)
        self._ocr_profiles = [dict(profile) for profile in (ocr_profiles or [])]
        self._color_profiles = [dict(profile) for profile in (color_profiles or [])]
        self._default_color_profiles = []
        self._ocr_field_specs = list(ocr_fields or [])
        if self._ocr_profiles and not self._ocr_field_specs:
            self._ocr_field_specs = [dict(field) for field in self._ocr_profiles[0].get("fields", [])]
        self._ocr_field_widgets = {}
        self._ocr_profile_index = 0
        self._color_profile_index = 0
        self._color_inputs = {}
        self._coord_inputs = {}
        self._updating_coord_inputs = False
        self._coord_mode = "ratio"
        self._color_pick_mode = False
        self._ocr_debounce_timer = QTimer(self)
        self._ocr_debounce_timer.setSingleShot(True)
        self._ocr_debounce_timer.setInterval(400)
        self._ocr_debounce_timer.timeout.connect(self._run_debounced_ocr_test)

        pixmap = self._capture_screen()
        self._apply_initial_window_size(pixmap)
        self.canvas = RoiCanvas(pixmap, self._regions, self)
        self.canvas.region_changed.connect(self._on_canvas_region_changed)
        self.canvas.color_previewed.connect(self._on_canvas_color_previewed)
        self.canvas.color_picked.connect(self._on_canvas_color_picked)

        layout = QVBoxLayout(self)
        helper = QLabel(
            helper_text
            or "Drag inside a box to move it. Drag any side or corner handle to resize it. Use Ctrl+T to run OCR on the active region."
        )
        helper.setWordWrap(True)
        layout.addWidget(helper)

        zoom_bar = QHBoxLayout()
        zoom_bar.addWidget(QLabel("Zoom:"))
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.clicked.connect(lambda: self._step_zoom(-1))
        zoom_bar.addWidget(self.btn_zoom_out)
        self.combo_zoom = QComboBox()
        for value in self.ZOOM_CHOICES:
            self.combo_zoom.addItem(f"{value}%", value)
        self.combo_zoom.currentIndexChanged.connect(self._on_zoom_combo_changed)
        zoom_bar.addWidget(self.combo_zoom)
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.clicked.connect(lambda: self._step_zoom(1))
        zoom_bar.addWidget(self.btn_zoom_in)
        self.btn_zoom_reset = QPushButton("100%")
        self.btn_zoom_reset.clicked.connect(lambda: self._set_zoom(1.0))
        zoom_bar.addWidget(self.btn_zoom_reset)
        self.btn_zoom_fit = QPushButton("适应宽度")
        self.btn_zoom_fit.clicked.connect(self._fit_canvas_width)
        zoom_bar.addWidget(self.btn_zoom_fit)
        self.btn_recapture = QPushButton("\u91cd\u65b0\u622a\u56fe")
        self.btn_recapture.clicked.connect(self._recapture_screen)
        zoom_bar.addWidget(self.btn_recapture)
        zoom_bar.addStretch()
        layout.addLayout(zoom_bar)

        content_layout = QHBoxLayout()
        self.canvas_scroll = ZoomScrollArea()
        self.canvas_scroll.setWidgetResizable(False)
        self.canvas_scroll.ctrl_wheel_zoom.connect(self._on_ctrl_wheel_zoom)
        self.canvas_scroll.setWidget(self.canvas)
        content_layout.addWidget(self.canvas_scroll, 1)

        self.side_panel_widget = QWidget()
        self.side_panel_widget.setMinimumWidth(500)
        self.side_panel_widget.setMaximumWidth(700)
        self.side_panel_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        side_panel = QVBoxLayout(self.side_panel_widget)
        side_panel.setContentsMargins(0, 0, 0, 0)
        side_panel.setSpacing(6)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("当前区域:"))
        self.combo_region = QComboBox()
        for key in self._region_keys:
            self.combo_region.addItem(self.REGION_TEXT.get(key, key), key)
        self.combo_region.currentIndexChanged.connect(self._on_region_changed)
        top_bar.addWidget(self.combo_region)
        side_panel.addLayout(top_bar)

        self.side_tabs = QTabWidget()
        self.side_tabs.setDocumentMode(True)
        self.side_tabs.setUsesScrollButtons(False)
        side_panel.addWidget(self.side_tabs, 1)

        self.overview_page = QWidget()
        overview_page_layout = QVBoxLayout(self.overview_page)
        overview_page_layout.setContentsMargins(4, 4, 4, 4)
        overview_page_layout.setSpacing(6)

        overview_group = QGroupBox("\u533a\u57df\u6982\u89c8")
        overview_layout = QVBoxLayout(overview_group)
        overview_layout.setContentsMargins(8, 8, 8, 8)
        overview_layout.setSpacing(4)

        self.preview_title = QLabel("区域预览")
        overview_layout.addWidget(self.preview_title)

        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(220, 96)
        self.preview_label.setMaximumHeight(120)
        self.preview_label.setStyleSheet("background-color: #1f1f1f; border: 1px solid #555;")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        overview_layout.addWidget(self.preview_label)

        self.pixel_label = QLabel()
        self.pixel_label.setWordWrap(True)
        overview_layout.addWidget(self.pixel_label)

        self.ratio_label = QLabel()
        self.ratio_label.setWordWrap(True)
        overview_layout.addWidget(self.ratio_label)

        coord_mode_bar = QHBoxLayout()
        coord_mode_bar.addWidget(QLabel("\u5750\u6807\u6a21\u5f0f:"))
        self.combo_coord_mode = QComboBox()
        self.combo_coord_mode.addItem("\u6bd4\u4f8b\u6a21\u5f0f", "ratio")
        self.combo_coord_mode.addItem("\u50cf\u7d20\u6a21\u5f0f", "pixel")
        self.combo_coord_mode.currentIndexChanged.connect(self._on_coord_mode_changed)
        coord_mode_bar.addWidget(self.combo_coord_mode)
        coord_mode_bar.addStretch()
        overview_layout.addLayout(coord_mode_bar)

        coords_form = QFormLayout()
        for key, title_text in (("left", "Left"), ("top", "Top"), ("width", "Width"), ("height", "Height")):
            spin = QDoubleSpinBox()
            spin.setKeyboardTracking(False)
            spin.valueChanged.connect(self._on_coord_input_changed)
            self._coord_inputs[key] = spin
            coords_form.addRow(title_text, spin)
        overview_layout.addLayout(coords_form)
        overview_page_layout.addWidget(overview_group)
        overview_page_layout.addStretch()
        self.side_tabs.addTab(self.overview_page, "\u533a\u57df\u6982\u89c8")

        self.combo_ocr_profile = None
        self.ocr_panel = None
        self.color_panel = None

        self.debug_page = QWidget()
        debug_page_layout = QVBoxLayout(self.debug_page)
        debug_page_layout.setContentsMargins(4, 4, 4, 4)
        debug_page_layout.setSpacing(6)

        self.debug_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.debug_splitter.setChildrenCollapsible(False)
        self.debug_splitter.setHandleWidth(8)

        if self._color_profiles:
            color_group = QGroupBox("\u989c\u8272\u8c03\u8bd5")
            color_group_layout = QVBoxLayout(color_group)
            color_group_layout.setContentsMargins(8, 10, 8, 8)
            self.color_panel = ColorDebugPanel(self._color_profiles, color_group)
            self.color_panel.profile_changed.connect(self._on_color_profile_changed)
            self.color_panel.value_changed.connect(self._on_color_profile_value_changed)
            self.color_panel.pick_toggled.connect(self._toggle_color_pick_mode)
            self.color_panel.test_clicked.connect(self.run_color_test)
            self._color_inputs = self.color_panel.color_inputs
            self.combo_color_profile = self.color_panel.combo_profile
            self.color_preview = self.color_panel.color_preview
            self.color_range_label = self.color_panel.color_range_label
            self.color_range_preview = self.color_panel.color_range_preview
            self.btn_pick_color = self.color_panel.btn_pick_color
            self.btn_test_color = self.color_panel.btn_test_color
            self.color_pick_hint = self.color_panel.color_pick_hint
            self.color_result_label = self.color_panel.color_result_label
            self.color_mask_title = self.color_panel.color_mask_title
            self.color_mask_stats = self.color_panel.color_mask_stats
            self.color_mask_label = self.color_panel.color_mask_label
            self.compare_mask_title = self.color_panel.compare_mask_title
            self.compare_mask_stats = self.color_panel.compare_mask_stats
            self.compare_mask_label = self.color_panel.compare_mask_label
            color_group_layout.addWidget(self.color_panel)
            self.debug_splitter.addWidget(color_group)
            self.debug_splitter.setStretchFactor(0, 3)

        ocr_group = QGroupBox("OCR\u8c03\u8bd5")
        ocr_group_layout = QVBoxLayout(ocr_group)
        ocr_group_layout.setContentsMargins(8, 10, 8, 8)
        self.ocr_panel = OcrDebugPanel(self._ocr_profiles, self._ocr_field_specs, ocr_group)
        if self.ocr_panel.combo_profile is not None:
            self.ocr_panel.profile_changed.connect(self._on_ocr_profile_changed)
        self.ocr_panel.test_clicked.connect(self.run_ocr_test)
        self.combo_ocr_profile = self.ocr_panel.combo_profile
        self._ocr_field_widgets = self.ocr_panel.field_widgets
        self._ocr_field_labels = self.ocr_panel.field_labels
        self.btn_test_ocr = self.ocr_panel.btn_test_ocr
        self.ocr_status_label = self.ocr_panel.ocr_status_label
        self.ocr_result_box = self.ocr_panel.ocr_result_box
        self.ocr_result_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        ocr_group_layout.addWidget(self.ocr_panel)
        self.debug_splitter.addWidget(ocr_group)
        self.debug_splitter.setStretchFactor(1, 2)

        if self.debug_splitter.count() > 0:
            if self.debug_splitter.count() == 2:
                self.debug_splitter.setSizes([380, 260])
            debug_page_layout.addWidget(self.debug_splitter, 1)
        self.side_tabs.addTab(self.debug_page, "\u8054\u52a8\u8c03\u8bd5")

        content_layout.addWidget(self.side_panel_widget, 0)
        content_layout.setStretch(0, 1)
        content_layout.setStretch(1, 0)
        layout.addLayout(content_layout, 1)

        btn_bar = QHBoxLayout()
        btn_reset = QPushButton("Reset Defaults")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_bar.addWidget(btn_reset)
        btn_bar.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Apply")
        btn_ok.clicked.connect(self.accept)
        btn_bar.addWidget(btn_cancel)
        btn_bar.addWidget(btn_ok)
        layout.addLayout(btn_bar)

        self.shortcut_test_ocr = QShortcut(QKeySequence("Ctrl+T"), self)
        self.shortcut_test_ocr.activated.connect(self.run_ocr_test)

        self._configure_coord_inputs()
        if self._ocr_profiles:
            self._load_ocr_profile(0)
        if self._color_profiles:
            self._default_color_profiles = [dict(profile) for profile in self._color_profiles]
            self._load_color_profile(0)
        self._set_zoom(self._initial_zoom(), sync_combo=True)
        self._fit_canvas_width()
        self._refresh_side_panel(self.combo_region.currentData())

