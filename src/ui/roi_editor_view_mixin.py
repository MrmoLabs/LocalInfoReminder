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


class RoiEditorViewMixin:
    def _apply_initial_window_size(self, pixmap):
        if self._available_geometry is not None:
            available = self._available_geometry
            side_panel_width = 560
            target_canvas_width = 360
            if pixmap is not None and not pixmap.isNull():
                target_canvas_width = min(520, max(320, int(pixmap.width() * 0.24)))
            desired_width = target_canvas_width + side_panel_width + 36
            width = max(900, min(available.width() - 180, desired_width))
            height = max(500, min(available.height() - 220, 560))
            self.resize(width, height)
        else:
            self.resize(920, 560)

    def _recapture_screen(self):
        if hasattr(self, "btn_pick_color") and self.btn_pick_color.isChecked():
            self.btn_pick_color.setChecked(False)
        current_zoom = self.canvas.zoom
        new_pixmap = self._capture_screen()
        self.canvas.pixmap = new_pixmap
        self._configure_coord_inputs()
        self.canvas.set_zoom(current_zoom)
        self._refresh_side_panel(self.combo_region.currentData())

    def _capture_screen(self):
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img = np.array(sct.grab(monitor), dtype=np.uint8)
            rgb = np.ascontiguousarray(img[:, :, :3][:, :, ::-1])
            h, w, _ = rgb.shape
            self._screen_size = (w, h)
            bytes_per_line = rgb.strides[0]
            qimage = QImage(rgb.tobytes(), w, h, bytes_per_line, QImage.Format.Format_RGB888)
            return QPixmap.fromImage(qimage.copy())
        except Exception as exc:
            QMessageBox.warning(self, "ROI Editor", f"Failed to capture the current screen: {exc}")
            fallback = QPixmap(1280, 720)
            fallback.fill(QColor("#202020"))
            self._screen_size = (1280, 720)
            return fallback

    def _initial_zoom(self):
        if self.canvas.pixmap.isNull():
            return 1.0
        target_width = 860.0
        return max(0.2, min(1.0, target_width / max(1, self.canvas.pixmap.width())))

    def _sync_zoom_combo(self):
        percent = int(round(self.canvas.zoom * 100))
        self.combo_zoom.blockSignals(True)
        for idx in range(self.combo_zoom.count()):
            if int(self.combo_zoom.itemData(idx)) == percent:
                self.combo_zoom.setCurrentIndex(idx)
                self.combo_zoom.blockSignals(False)
                return
        self.combo_zoom.setCurrentIndex(-1)
        self.combo_zoom.blockSignals(False)

    def _set_zoom(self, zoom, sync_combo=False):
        self.canvas.set_zoom(zoom)
        if sync_combo:
            self._sync_zoom_combo()
        self._refresh_side_panel(self.combo_region.currentData())

    def _set_zoom_with_anchor(self, zoom, anchor_x, anchor_y, sync_combo=False):
        old_zoom = max(0.0001, float(self.canvas.zoom))
        hbar = self.canvas_scroll.horizontalScrollBar()
        vbar = self.canvas_scroll.verticalScrollBar()
        content_x = hbar.value() + anchor_x
        content_y = vbar.value() + anchor_y
        scale = float(zoom) / old_zoom
        self.canvas.set_zoom(zoom)
        if sync_combo:
            self._sync_zoom_combo()
        hbar.setValue(int(round(content_x * scale - anchor_x)))
        vbar.setValue(int(round(content_y * scale - anchor_y)))
        self._refresh_side_panel(self.combo_region.currentData())

    def _on_ctrl_wheel_zoom(self, direction, anchor_x, anchor_y):
        self._step_zoom(direction, anchor_x=anchor_x, anchor_y=anchor_y)

    def _step_zoom(self, direction, anchor_x=None, anchor_y=None):
        current = int(round(self.canvas.zoom * 100))
        target_zoom = None
        if direction > 0:
            for value in self.ZOOM_CHOICES:
                if value > current:
                    target_zoom = value / 100.0
                    break
            if target_zoom is None:
                target_zoom = min(5.0, self.canvas.zoom + 0.25)
        else:
            for value in reversed(self.ZOOM_CHOICES):
                if value < current:
                    target_zoom = value / 100.0
                    break
            if target_zoom is None:
                target_zoom = max(0.1, self.canvas.zoom - 0.25)
        if anchor_x is not None and anchor_y is not None:
            self._set_zoom_with_anchor(target_zoom, anchor_x, anchor_y, sync_combo=True)
        else:
            self._set_zoom(target_zoom, sync_combo=True)

    def _on_zoom_combo_changed(self):
        data = self.combo_zoom.currentData()
        if data is not None:
            self._set_zoom(float(data) / 100.0)

    def _fit_canvas_width(self):
        viewport_width = max(200, self.canvas_scroll.viewport().width() - 24)
        pixmap_width = max(1, self.canvas.pixmap.width())
        self._set_zoom(viewport_width / pixmap_width, sync_combo=True)

    def _region_pixels(self, region):
        screen_w, screen_h = self._screen_size
        return {
            "left": int(round(region["left"] * screen_w)),
            "top": int(round(region["top"] * screen_h)),
            "width": int(round(region["width"] * screen_w)),
            "height": int(round(region["height"] * screen_h)),
        }

    def _configure_coord_inputs(self):
        screen_w, screen_h = self._screen_size
        if self._coord_mode == "pixel":
            config = {
                "left": (0, max(1, screen_w), 1, 0, " px"),
                "top": (0, max(1, screen_h), 1, 0, " px"),
                "width": (1, max(1, screen_w), 1, 0, " px"),
                "height": (1, max(1, screen_h), 1, 0, " px"),
            }
        else:
            config = {
                "left": (0.0, 1.0, 0.001, 4, ""),
                "top": (0.0, 1.0, 0.001, 4, ""),
                "width": (0.001, 1.0, 0.001, 4, ""),
                "height": (0.001, 1.0, 0.001, 4, ""),
            }
        for key, spin in self._coord_inputs.items():
            minimum, maximum, step, decimals, suffix = config[key]
            spin.blockSignals(True)
            spin.setDecimals(decimals)
            spin.setSingleStep(step)
            spin.setRange(minimum, maximum)
            spin.setSuffix(suffix)
            spin.blockSignals(False)

    def _region_to_input_values(self, region):
        if self._coord_mode == "pixel":
            pixels = self._region_pixels(region)
            return {key: float(value) for key, value in pixels.items()}
        return {key: float(region[key]) for key in ("left", "top", "width", "height")}

    def _input_values_to_region(self, values):
        if self._coord_mode == "pixel":
            screen_w, screen_h = self._screen_size
            return {
                "left": float(values["left"]) / max(1, screen_w),
                "top": float(values["top"]) / max(1, screen_h),
                "width": float(values["width"]) / max(1, screen_w),
                "height": float(values["height"]) / max(1, screen_h),
            }
        return {key: float(values[key]) for key in ("left", "top", "width", "height")}

