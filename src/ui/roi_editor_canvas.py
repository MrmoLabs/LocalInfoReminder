from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QScrollArea, QWidget

import numpy as np


class RoiCanvas(QWidget):
    region_changed = pyqtSignal(str, dict)
    color_previewed = pyqtSignal(int, int, int, int, int)
    color_picked = pyqtSignal(int, int, int, int, int)

    HANDLE_SIZE = 10.0
    MIN_SIZE = 12.0
    HANDLE_ORDER = (
        "top_left",
        "top",
        "top_right",
        "left",
        "right",
        "bottom_left",
        "bottom",
        "bottom_right",
    )
    HANDLE_CURSORS = {
        "top_left": Qt.CursorShape.SizeFDiagCursor,
        "bottom_right": Qt.CursorShape.SizeFDiagCursor,
        "top_right": Qt.CursorShape.SizeBDiagCursor,
        "bottom_left": Qt.CursorShape.SizeBDiagCursor,
        "left": Qt.CursorShape.SizeHorCursor,
        "right": Qt.CursorShape.SizeHorCursor,
        "top": Qt.CursorShape.SizeVerCursor,
        "bottom": Qt.CursorShape.SizeVerCursor,
    }
    REGION_COLORS = {
        "time_main": QColor("#00c853"),
        "time_prep": QColor("#aeea00"),
        "skill_bar": QColor("#2962ff"),
        "boss_notification": QColor("#d50000"),
        "boss_kill": QColor("#ff8800"),
    }
    REGION_LABELS = {
        "time_main": "Time Main",
        "time_prep": "Time Prep",
        "skill_bar": "Command Skill",
        "boss_notification": "目标事件播报",
        "boss_kill": "目标事件结果",
    }

    def __init__(self, pixmap: QPixmap, regions, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.zoom = 1.0
        self.canvas_margin = 12.0
        self.regions = {key: dict(value) for key, value in regions.items()}
        self.region_order = list(self.regions.keys())
        self.region_colors = dict(self.REGION_COLORS)
        self.region_labels = dict(self.REGION_LABELS)
        self.active_region = self.region_order[0] if self.region_order else None
        self.drag_mode = None
        self.drag_handle = None
        self.drag_start = QPointF()
        self.drag_origin = None
        self.pan_active = False
        self.pan_start = QPointF()
        self.pan_scroll_start = (0, 0)
        self.space_pressed = False
        self.color_pick_mode = False
        self.color_pick_drag_active = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self._update_canvas_size()

    def set_active_region(self, key):
        if key in self.regions:
            self.active_region = key
            self.update()

    def set_color_pick_mode(self, enabled):
        self.color_pick_mode = bool(enabled)
        self.color_pick_drag_active = False
        if self.color_pick_mode:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif not self.pan_active and not self.space_pressed:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_zoom(self, zoom):
        self.zoom = max(0.1, min(5.0, float(zoom)))
        self._update_canvas_size()
        self.update()

    def get_regions(self):
        return {key: dict(value) for key, value in self.regions.items()}

    def _update_canvas_size(self):
        if self.pixmap.isNull():
            width = 960
            height = 540
        else:
            width = int(self.pixmap.width() * self.zoom + self.canvas_margin * 2)
            height = int(self.pixmap.height() * self.zoom + self.canvas_margin * 2)
        self.resize(max(320, width), max(240, height))
        self.setMinimumSize(320, 240)

    def _draw_rect(self):
        if self.pixmap.isNull():
            return QRectF(), 1.0, 1.0
        width = self.pixmap.width() * self.zoom
        height = self.pixmap.height() * self.zoom
        return QRectF(self.canvas_margin, self.canvas_margin, width, height), width, height

    def _region_to_rect(self, key):
        draw_rect, draw_w, draw_h = self._draw_rect()
        ratio = self.regions[key]
        return QRectF(
            draw_rect.x() + ratio["left"] * draw_w,
            draw_rect.y() + ratio["top"] * draw_h,
            ratio["width"] * draw_w,
            ratio["height"] * draw_h,
        )

    def _rect_to_region(self, rect):
        draw_rect, draw_w, draw_h = self._draw_rect()
        return {
            "left": max(0.0, min(1.0, (rect.x() - draw_rect.x()) / draw_w)),
            "top": max(0.0, min(1.0, (rect.y() - draw_rect.y()) / draw_h)),
            "width": max(0.001, min(1.0, rect.width() / draw_w)),
            "height": max(0.001, min(1.0, rect.height() / draw_h)),
        }

    def _clamp_rect(self, rect):
        draw_rect, _, _ = self._draw_rect()
        width = max(self.MIN_SIZE, min(rect.width(), draw_rect.width()))
        height = max(self.MIN_SIZE, min(rect.height(), draw_rect.height()))
        x = min(max(rect.x(), draw_rect.left()), draw_rect.right() - width)
        y = min(max(rect.y(), draw_rect.top()), draw_rect.bottom() - height)
        return QRectF(x, y, width, height)

    def _handle_rects(self, rect):
        half = self.HANDLE_SIZE / 2.0
        center_x = rect.center().x()
        center_y = rect.center().y()
        return {
            "top_left": QRectF(rect.left() - half, rect.top() - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
            "top": QRectF(center_x - half, rect.top() - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
            "top_right": QRectF(rect.right() - half, rect.top() - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
            "left": QRectF(rect.left() - half, center_y - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
            "right": QRectF(rect.right() - half, center_y - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
            "bottom_left": QRectF(rect.left() - half, rect.bottom() - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
            "bottom": QRectF(center_x - half, rect.bottom() - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
            "bottom_right": QRectF(rect.right() - half, rect.bottom() - half, self.HANDLE_SIZE, self.HANDLE_SIZE),
        }

    def _hit_test(self, pos):
        if not self.active_region:
            return None, None
        rect = self._region_to_rect(self.active_region)
        handle_rects = self._handle_rects(rect)
        for handle_name in self.HANDLE_ORDER:
            if handle_rects[handle_name].contains(pos):
                return "resize", handle_name
        if rect.contains(pos):
            return "move", None
        return None, None

    def _update_region_from_rect(self, rect):
        rect = self._clamp_rect(rect)
        self.regions[self.active_region] = self._rect_to_region(rect)
        self.region_changed.emit(self.active_region, dict(self.regions[self.active_region]))
        self.update()

    def _find_scroll_area(self):
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                return parent
            parent = parent.parent()
        return None

    def _should_start_pan(self, event):
        return event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self.space_pressed
        )

    def _begin_pan(self, event):
        scroll = self._find_scroll_area()
        if scroll is None:
            return False
        self.pan_active = True
        self.pan_start = event.position()
        self.pan_scroll_start = (
            scroll.horizontalScrollBar().value(),
            scroll.verticalScrollBar().value(),
        )
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        return True

    def _update_pan(self, event):
        scroll = self._find_scroll_area()
        if scroll is None:
            return
        delta = event.position() - self.pan_start
        scroll.horizontalScrollBar().setValue(int(self.pan_scroll_start[0] - delta.x()))
        scroll.verticalScrollBar().setValue(int(self.pan_scroll_start[1] - delta.y()))

    def _end_pan(self):
        self.pan_active = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _image_point_from_canvas(self, pos):
        draw_rect, _, _ = self._draw_rect()
        if self.pixmap.isNull() or not draw_rect.contains(pos):
            return None
        x_ratio = (pos.x() - draw_rect.left()) / max(1.0, draw_rect.width())
        y_ratio = (pos.y() - draw_rect.top()) / max(1.0, draw_rect.height())
        image_x = int(np.clip(round(x_ratio * max(0, self.pixmap.width() - 1)), 0, max(0, self.pixmap.width() - 1)))
        image_y = int(np.clip(round(y_ratio * max(0, self.pixmap.height() - 1)), 0, max(0, self.pixmap.height() - 1)))
        return image_x, image_y

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111111"))
        draw_rect, _, _ = self._draw_rect()
        if not self.pixmap.isNull():
            scaled_pixmap = self.pixmap.scaled(
                int(draw_rect.width()),
                int(draw_rect.height()),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(draw_rect.toRect(), scaled_pixmap)
        for key in self.region_order:
            rect = self._region_to_rect(key)
            color = self.region_colors.get(key, QColor("#ffffff"))
            is_active = key == self.active_region
            pen = QPen(color)
            pen.setWidth(3 if is_active else 2)
            painter.setPen(pen)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 40 if is_active else 20))
            painter.drawRect(rect)
            painter.setPen(color)
            painter.drawText(QPointF(rect.left() + 4.0, rect.top() - 6.0), self.region_labels.get(key, key))
            if is_active:
                for handle_name in self.HANDLE_ORDER:
                    painter.fillRect(self._handle_rects(rect)[handle_name], color)

    def mousePressEvent(self, event):
        self.setFocus()
        if self._should_start_pan(event) and self._begin_pan(event):
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self.color_pick_mode:
            image_point = self._image_point_from_canvas(event.position())
            if image_point is not None:
                color = self.pixmap.toImage().pixelColor(*image_point)
                self.color_pick_drag_active = True
                self.color_previewed.emit(image_point[0], image_point[1], color.red(), color.green(), color.blue())
                event.accept()
                return
        if event.button() != Qt.MouseButton.LeftButton or not self.active_region:
            return
        hit, handle_name = self._hit_test(event.position())
        if not hit:
            for key in reversed(self.region_order):
                if self._region_to_rect(key).contains(event.position()):
                    self.active_region = key
                    hit = "move"
                    handle_name = None
                    break
        if hit:
            self.drag_mode = hit
            self.drag_handle = handle_name
            self.drag_start = event.position()
            self.drag_origin = self._region_to_rect(self.active_region)
            self.update()

    def mouseMoveEvent(self, event):
        if self.pan_active:
            self._update_pan(event)
            event.accept()
            return
        if self.color_pick_mode and self.color_pick_drag_active:
            image_point = self._image_point_from_canvas(event.position())
            if image_point is not None:
                color = self.pixmap.toImage().pixelColor(*image_point)
                self.color_previewed.emit(image_point[0], image_point[1], color.red(), color.green(), color.blue())
                event.accept()
                return
        if not self.active_region:
            return
        if not self.drag_mode or self.drag_origin is None:
            if self.color_pick_mode:
                self.setCursor(Qt.CursorShape.CrossCursor)
                return
            hit, handle_name = self._hit_test(event.position())
            if hit == "resize":
                self.setCursor(self.HANDLE_CURSORS.get(handle_name, Qt.CursorShape.ArrowCursor))
            elif hit == "move":
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        delta = event.position() - self.drag_start
        rect = QRectF(self.drag_origin)
        if self.drag_mode == "move":
            rect.moveTo(rect.x() + delta.x(), rect.y() + delta.y())
        elif self.drag_mode == "resize":
            if self.drag_handle in {"top_left", "left", "bottom_left"}:
                rect.setLeft(min(rect.right() - self.MIN_SIZE, rect.left() + delta.x()))
            if self.drag_handle in {"top_left", "top", "top_right"}:
                rect.setTop(min(rect.bottom() - self.MIN_SIZE, rect.top() + delta.y()))
            if self.drag_handle in {"top_right", "right", "bottom_right"}:
                rect.setRight(max(rect.left() + self.MIN_SIZE, rect.right() + delta.x()))
            if self.drag_handle in {"bottom_left", "bottom", "bottom_right"}:
                rect.setBottom(max(rect.top() + self.MIN_SIZE, rect.bottom() + delta.y()))
        self._update_region_from_rect(rect)

    def mouseReleaseEvent(self, event):
        if self.pan_active:
            self._end_pan()
            event.accept()
            return
        if self.color_pick_mode and self.color_pick_drag_active and event.button() == Qt.MouseButton.LeftButton:
            image_point = self._image_point_from_canvas(event.position())
            if image_point is not None:
                color = self.pixmap.toImage().pixelColor(*image_point)
                self.color_picked.emit(image_point[0], image_point[1], color.red(), color.green(), color.blue())
            self.color_pick_drag_active = False
            event.accept()
            return
        self.drag_mode = None
        self.drag_handle = None
        self.drag_origin = None
        self.setCursor(Qt.CursorShape.CrossCursor if self.color_pick_mode else Qt.CursorShape.ArrowCursor)
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.space_pressed = True
            if not self.pan_active:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.space_pressed = False
            if not self.pan_active and not self.color_pick_mode:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().keyReleaseEvent(event)


class ZoomScrollArea(QScrollArea):
    ctrl_wheel_zoom = pyqtSignal(int, int, int)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                pos = event.position()
                self.ctrl_wheel_zoom.emit(1 if delta > 0 else -1, int(pos.x()), int(pos.y()))
                event.accept()
                return
        super().wheelEvent(event)
