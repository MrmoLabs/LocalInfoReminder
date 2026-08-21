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


class RoiEditorAnalysisMixin:
    def _save_current_ocr_profile(self):
        if not self._ocr_profiles:
            return
        profile = self._ocr_profiles[self._ocr_profile_index]
        fields = []
        for spec in self._ocr_field_specs:
            key = spec["key"]
            fields.append({
                "key": key,
                "label": spec.get("label", key),
                "placeholder": spec.get("placeholder", ""),
                "value": self._ocr_field_widgets[key].text().strip(),
            })
        profile["fields"] = fields

    def _load_ocr_profile(self, index):
        if not self._ocr_profiles:
            return
        index = max(0, min(index, len(self._ocr_profiles) - 1))
        self._ocr_profile_index = index
        profile = self._ocr_profiles[index]
        field_map = {field["key"]: field for field in profile.get("fields", [])}
        for spec in self._ocr_field_specs:
            key = spec["key"]
            field = field_map.get(key, spec)
            widget = self._ocr_field_widgets.get(key)
            if widget is None:
                continue
            widget.blockSignals(True)
            widget.setPlaceholderText(field.get("placeholder", spec.get("placeholder", "")))
            widget.setText(field.get("value", ""))
            widget.blockSignals(False)

    def _on_ocr_profile_changed(self):
        if not self._ocr_profiles:
            return
        self._save_current_ocr_profile()
        self._load_ocr_profile(self.combo_ocr_profile.currentIndex())

    def _update_color_profile_meta(self):
        if not self._color_profiles or not hasattr(self, "color_panel") or self.color_panel is None:
            return
        profile = self._color_profiles[self._color_profile_index]
        profile_id = str(profile.get("id", "")).strip() or "(unknown)"
        roi_key = str(profile.get("roi_key", "")).strip()
        roi_text = self.REGION_TEXT.get(roi_key, roi_key) if roi_key else "未绑定区域"
        self.color_panel.profile_id_label.setText(f"Profile ID: {profile_id} | 区域: {roi_text}")

    def _set_color_profile_dirty(self, dirty):
        if not self._color_profiles or not hasattr(self, "color_panel") or self.color_panel is None:
            return
        if dirty:
            self.color_panel.profile_state_label.setText("状态: 未保存")
            self.color_panel.profile_state_label.setStyleSheet("color: #d9480f; font-weight: 600;")
        else:
            self.color_panel.profile_state_label.setText("状态: 已写回")
            self.color_panel.profile_state_label.setStyleSheet("color: #2b8a3e; font-weight: 600;")

    def _save_current_color_profile(self):
        if not self._color_profiles:
            return
        profile = self._color_profiles[self._color_profile_index]
        profile["sample_color"] = [
            int(round(self._color_inputs["r"].value())),
            int(round(self._color_inputs["g"].value())),
            int(round(self._color_inputs["b"].value())),
        ]
        profile["tolerance"] = float(self._color_inputs["tolerance"].value())
        profile["min_ratio"] = float(self._color_inputs["min_ratio"].value())

    def _apply_color_preview(self, sample_color):
        rgb = tuple(int(v) for v in sample_color)
        text_color = "#000000" if sum(rgb) > 382 else "#ffffff"
        self.color_preview.setText(f"RGB({rgb[0]}, {rgb[1]}, {rgb[2]})")
        self.color_preview.setStyleSheet(
            f"background-color: rgb({rgb[0]}, {rgb[1]}, {rgb[2]}); color: {text_color}; border: 1px solid #999; padding: 4px;"
        )
        if hasattr(self, "color_range_preview"):
            self.color_range_preview.setPixmap(self._build_color_range_preview(sample_color))

    def _build_color_range_preview(self, sample_color, width=None, height=None):
        if width is None:
            width = self.color_range_preview.width() - 4 if hasattr(self, "color_range_preview") else 220
        if height is None:
            height = self.color_range_preview.height() - 4 if hasattr(self, "color_range_preview") else 160
        tolerance = float(self._color_inputs.get("tolerance").value()) if self._color_inputs.get("tolerance") else 0.0
        return build_color_range_preview(sample_color, tolerance, width, height)

    def _paired_color_profile(self, profile):
        profile_id = str((profile or {}).get("id", ""))
        if profile_id == "skill_red":
            return next((item for item in self._color_profiles if item.get("id") == "skill_blue"), None)
        if profile_id == "skill_blue":
            return next((item for item in self._color_profiles if item.get("id") == "skill_red"), None)
        if profile_id == "boss_red":
            return next((item for item in self._color_profiles if item.get("id") == "boss_blue"), None)
        if profile_id == "boss_blue":
            return next((item for item in self._color_profiles if item.get("id") == "boss_red"), None)
        return None

    def _build_dual_color_mask_preview(self, img_rgb, primary_mask, secondary_mask):
        if hasattr(self, "compare_mask_label"):
            return build_dual_color_mask_preview(img_rgb, primary_mask, secondary_mask, self.compare_mask_label.size())
        return build_dual_color_mask_preview(img_rgb, primary_mask, secondary_mask, QSize(220, 90))

    def _build_color_mask_preview(self, img_rgb, mask):
        if hasattr(self, "color_mask_label"):
            return build_color_mask_preview(img_rgb, mask, self.color_mask_label.size())
        return build_color_mask_preview(img_rgb, mask, QSize(220, 90))

    def _load_color_profile(self, index):
        if not self._color_profiles:
            return
        index = max(0, min(index, len(self._color_profiles) - 1))
        self._color_profile_index = index
        profile = self._color_profiles[index]
        self._update_color_profile_meta()
        sample = profile.get("sample_color", [255, 255, 255])
        for key, value in (("r", sample[0]), ("g", sample[1]), ("b", sample[2])):
            self._color_inputs[key].blockSignals(True)
            self._color_inputs[key].setValue(float(value))
            self._color_inputs[key].blockSignals(False)
        for key in ("tolerance", "min_ratio"):
            self._color_inputs[key].blockSignals(True)
            self._color_inputs[key].setValue(float(profile.get(key, 0.0)))
            self._color_inputs[key].blockSignals(False)
        self._apply_color_preview(sample)
        if hasattr(self, "color_mask_label"):
            self.color_mask_label.setText("点击“测试颜色”查看命中遮罩")
            self.color_mask_label.setPixmap(QPixmap())
        roi_key = profile.get("roi_key")
        if roi_key in getattr(self, "_region_keys", []):
            combo_index = self.combo_region.findData(roi_key)
            if combo_index >= 0:
                self.combo_region.setCurrentIndex(combo_index)
        self.color_result_label.setText("")
        self._set_color_profile_dirty(False)

    def _on_color_profile_changed(self):
        if not self._color_profiles:
            return
        self._save_current_color_profile()
        self._load_color_profile(self.combo_color_profile.currentIndex())

    def _toggle_color_pick_mode(self, enabled):
        self._color_pick_mode = bool(enabled)
        self.canvas.set_color_pick_mode(enabled)
        if hasattr(self, "color_pick_hint"):
            if enabled:
                self.color_pick_hint.setText("取色中：请在左侧截图上点击目标颜色。")
            else:
                self.color_pick_hint.setText("点击“截图取色”后，在左侧截图上单击即可取样。")

    def _on_canvas_color_previewed(self, image_x, image_y, r, g, b):
        if not self._color_profiles:
            return
        preview_profile = dict(self._color_profiles[self._color_profile_index])
        preview_profile["sample_color"] = [r, g, b]
        self._apply_color_preview([r, g, b])
        if hasattr(self, "color_pick_hint"):
            self.color_pick_hint.setText(f"预览中：({image_x}, {image_y}) -> RGB({r}, {g}, {b})，松开鼠标确认")
        self.run_color_test(preview_profile)
        self._schedule_ocr_refresh()

    def _on_canvas_color_picked(self, image_x, image_y, r, g, b):
        if not self._color_profiles:
            return
        values = {"r": r, "g": g, "b": b}
        for key, value in values.items():
            self._color_inputs[key].blockSignals(True)
            self._color_inputs[key].setValue(float(value))
            self._color_inputs[key].blockSignals(False)
        self._save_current_color_profile()
        self._set_color_profile_dirty(True)
        self._apply_color_preview([r, g, b])
        if hasattr(self, "color_pick_hint"):
            self.color_pick_hint.setText(f"已取样：({image_x}, {image_y}) -> RGB({r}, {g}, {b})")
        if hasattr(self, "btn_pick_color") and self.btn_pick_color.isChecked():
            self.btn_pick_color.blockSignals(True)
            self.btn_pick_color.setChecked(False)
            self.btn_pick_color.blockSignals(False)
        self._color_pick_mode = False
        self.canvas.set_color_pick_mode(False)
        self.run_color_test()
        self._schedule_ocr_refresh()

    def _on_color_profile_value_changed(self):
        if not self._color_profiles:
            return
        self._save_current_color_profile()
        self._set_color_profile_dirty(True)
        self._apply_color_preview(self._color_profiles[self._color_profile_index].get("sample_color", [255, 255, 255]))
        self.run_color_test()
        self._schedule_ocr_refresh()

    def _schedule_ocr_refresh(self):
        if self.ocr_panel is None:
            return
        if hasattr(self, "ocr_status_label"):
            self.ocr_status_label.setText("OCR状态：等待自动刷新...")
        self._ocr_debounce_timer.start()

    def _run_debounced_ocr_test(self):
        if self.ocr_panel is None:
            return
        self.run_ocr_test(auto_triggered=True)

    def run_color_test(self, profile_override=None):
        if not self._color_profiles:
            return
        try:
            from core.vision.color_profile import match_ratio

            profile = dict(profile_override or self._color_profiles[self._color_profile_index])
            roi_key = profile.get("roi_key") or self.combo_region.currentData()
            if roi_key and roi_key in getattr(self, "_region_keys", []):
                combo_index = self.combo_region.findData(roi_key)
                if combo_index >= 0 and combo_index != self.combo_region.currentIndex():
                    self.combo_region.setCurrentIndex(combo_index)
            img_rgb, region_key = self._crop_active_region_rgb()
            if img_rgb is None:
                self.color_result_label.setText("未选中有效 ROI")
                if hasattr(self, "color_mask_stats"):
                    self.color_mask_stats.setText("命中像素: - / -")
                if hasattr(self, "color_mask_label"):
                    self.color_mask_label.setPixmap(QPixmap())
                    self.color_mask_label.setText("当前 ROI 无法生成遮罩预览")
                if hasattr(self, "compare_mask_label"):
                    self.compare_mask_title.setText("红蓝重叠预览")
                    self.compare_mask_stats.setText("当前规则: - | 对照规则: - | 重叠: -")
                    self.compare_mask_label.setPixmap(QPixmap())
                    self.compare_mask_label.setText("请先选择有效 ROI")
                return
            ratio, mask = match_ratio(img_rgb, profile)
            min_ratio = float(profile.get("min_ratio", 0.0))
            hit_pixels = int(mask.sum()) if mask is not None else 0
            total_pixels = int(mask.size) if mask is not None else 0
            state = "已触发" if ratio >= min_ratio else "未触发"
            self.color_result_label.setText(
                f"当前区域: {self.REGION_TEXT.get(region_key, region_key)} | 命中比例: {ratio:.4f} | 阈值: {min_ratio:.4f} | 命中像素: {hit_pixels}/{total_pixels} | 结果: {state}"
            )
            if hasattr(self, "color_mask_stats"):
                self.color_mask_stats.setText(
                    f"命中像素: {hit_pixels} / {total_pixels} | 未命中像素: {max(0, total_pixels - hit_pixels)}"
                )
            if hasattr(self, "color_mask_label"):
                if mask is not None and getattr(mask, "size", 0):
                    self.color_mask_label.setText("")
                    self.color_mask_label.setPixmap(self._build_color_mask_preview(img_rgb, mask))
                else:
                    self.color_mask_label.setPixmap(QPixmap())
                    self.color_mask_label.setText("当前参数没有生成可用遮罩")

            compare_profile = self._paired_color_profile(profile)
            if hasattr(self, "compare_mask_label"):
                if compare_profile is not None:
                    compare_ratio, compare_mask = match_ratio(img_rgb, compare_profile)
                    compare_pixels = int(compare_mask.sum()) if compare_mask is not None else 0
                    overlap_pixels = int(np.logical_and(mask, compare_mask).sum()) if mask is not None and compare_mask is not None else 0
                    self.compare_mask_stats.setText(
                        f"当前规则: {hit_pixels} | 对照规则: {compare_pixels} | 重叠: {overlap_pixels}"
                    )
                    self.compare_mask_label.setText("")
                    self.compare_mask_label.setPixmap(self._build_dual_color_mask_preview(img_rgb, mask, compare_mask))
                    compare_label = str(compare_profile.get("label", compare_profile.get("id", "对照规则")))
                    self.compare_mask_title.setText(f"红蓝重叠预览（对照: {compare_label} / 比例: {compare_ratio:.4f}）")
                else:
                    self.compare_mask_title.setText("红蓝重叠预览")
                    self.compare_mask_stats.setText("当前规则: - | 对照规则: - | 重叠: -")
                    self.compare_mask_label.setPixmap(QPixmap())
                    self.compare_mask_label.setText("当前规则没有可对比的红蓝规则")
        except Exception as exc:
            self.color_result_label.setText(f"颜色测试失败: {exc}")
            if hasattr(self, "color_mask_stats"):
                self.color_mask_stats.setText("命中像素: - / -")
            if hasattr(self, "color_mask_label"):
                self.color_mask_label.setPixmap(QPixmap())
                self.color_mask_label.setText("当前参数没有生成可用遮罩")
            if hasattr(self, "compare_mask_label"):
                self.compare_mask_title.setText("红蓝重叠预览")
                self.compare_mask_stats.setText("当前规则: - | 对照规则: - | 重叠: -")
                self.compare_mask_label.setPixmap(QPixmap())
                self.compare_mask_label.setText("当前参数没有生成可用对比图")

    def _on_coord_mode_changed(self):
        self._coord_mode = str(self.combo_coord_mode.currentData() or "ratio")
        self._configure_coord_inputs()
        self._refresh_side_panel(self.combo_region.currentData())

    def _normalize_region_input(self, region):
        left = max(0.0, min(0.999, float(region.get("left", 0.0))))
        top = max(0.0, min(0.999, float(region.get("top", 0.0))))
        width = max(0.001, min(1.0 - left, float(region.get("width", 0.001))))
        height = max(0.001, min(1.0 - top, float(region.get("height", 0.001))))
        return {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }

    def _set_region_values(self, region_key, region):
        normalized = self._normalize_region_input(region)
        self.canvas.regions[region_key] = normalized
        self.canvas.region_changed.emit(region_key, dict(normalized))
        self.canvas.update()

    def _on_coord_input_changed(self):
        if self._updating_coord_inputs:
            return
        region_key = self.combo_region.currentData()
        if not region_key or region_key not in self.canvas.regions:
            return
        input_values = {
            key: self._coord_inputs[key].value()
            for key in ("left", "top", "width", "height")
        }
        self._set_region_values(region_key, self._input_values_to_region(input_values))

    def _format_keyword_row(self, label, values, hits, color):
        safe_label = html.escape(label)
        safe_values = " | ".join(html.escape(item) for item in values) if values else "(empty)"
        if hits:
            safe_hits = " | ".join(html.escape(item) for item in hits)
            status = f'<span style="color:{color};font-weight:600;">\u547d\u4e2d: {safe_hits}</span>'
        else:
            status = '<span style="color:#6c757d;">\u672a\u547d\u4e2d</span>'
        return f'<div style="margin:4px 0;"><span style="font-weight:600;">{safe_label}:</span> {safe_values}<br>{status}</div>'

    def _build_preview(self, region_key):
        if self.canvas.pixmap.isNull() or region_key not in self.canvas.regions:
            return QPixmap()
        pixels = self._region_pixels(self.canvas.regions[region_key])
        crop = self.canvas.pixmap.copy(pixels["left"], pixels["top"], max(1, pixels["width"]), max(1, pixels["height"]))
        return crop.scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def _refresh_side_panel(self, region_key):
        if not region_key or region_key not in self.canvas.regions:
            return
        region = self.canvas.regions[region_key]
        pixels = self._region_pixels(region)
        self.preview_title.setText(f"区域预览: {self.REGION_TEXT.get(region_key, region_key)}")
        self.preview_label.setPixmap(self._build_preview(region_key))
        self.pixel_label.setText(f"Pixels: left={pixels['left']}, top={pixels['top']}, width={pixels['width']}, height={pixels['height']}")
        self.ratio_label.setText(
            "Ratios: "
            f"left={region['left']:.4f}, top={region['top']:.4f}, width={region['width']:.4f}, height={region['height']:.4f}, zoom={self.canvas.zoom:.2f}x"
        )
        self._updating_coord_inputs = True
        try:
            for key, value in self._region_to_input_values(region).items():
                self._coord_inputs[key].setValue(value)
        finally:
            self._updating_coord_inputs = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_side_panel(self.combo_region.currentData())
        if self._color_profiles:
            self._apply_color_preview(self._color_profiles[self._color_profile_index].get("sample_color", [255, 255, 255]))

    def _on_region_changed(self):
        key = self.combo_region.currentData()
        self.canvas.set_active_region(key)
        self._refresh_side_panel(key)

    def _on_canvas_region_changed(self, region_key, region):
        self._all_regions[region_key] = dict(region)
        if region_key == self.combo_region.currentData():
            self._refresh_side_panel(region_key)

    def _reset_defaults(self):
        if hasattr(self, "btn_pick_color") and self.btn_pick_color.isChecked():
            self.btn_pick_color.setChecked(False)
        from core.vision.vision_constants import default_detection_regions
        from core.vision.color_profile import default_color_profiles
        defaults = default_detection_regions()
        self.canvas.regions = {key: dict(defaults[key]) for key in self._region_keys if key in defaults}
        for key, value in self.canvas.regions.items():
            self._all_regions[key] = dict(value)
        if self._color_profiles:
            profile_defaults = default_color_profiles()
            restored_profiles = []
            for profile in self._default_color_profiles or self._color_profiles:
                restored = dict(profile)
                profile_id = str(profile.get("id", ""))
                if profile_id in profile_defaults:
                    restored.update(profile_defaults[profile_id])
                restored_profiles.append(restored)
            self._color_profiles = restored_profiles
        self.canvas.set_active_region(self.combo_region.currentData())
        self._refresh_side_panel(self.combo_region.currentData())
        if self._color_profiles:
            self._load_color_profile(min(self._color_profile_index, len(self._color_profiles) - 1))
            self._set_color_profile_dirty(False)
            self.run_color_test()
        self.canvas.update()

    def _ensure_ocr_engine(self):
        if self.OCR_ENGINE is not None:
            return self.OCR_ENGINE
        from rapidocr_onnxruntime import RapidOCR
        self.__class__.OCR_ENGINE = RapidOCR()
        return self.OCR_ENGINE

    def _crop_active_region_rgb(self):
        region_key = self.combo_region.currentData()
        if not region_key or region_key not in self.canvas.regions or self.canvas.pixmap.isNull():
            return None, region_key
        pixels = self._region_pixels(self.canvas.regions[region_key])
        crop = self.canvas.pixmap.copy(pixels["left"], pixels["top"], max(1, pixels["width"]), max(1, pixels["height"]))
        image = crop.toImage().convertToFormat(QImage.Format.Format_RGB888)
        width = image.width()
        height = image.height()
        ptr = image.bits()
        arr = np.frombuffer(ptr.asstring(image.sizeInBytes()), dtype=np.uint8)
        arr = arr.reshape((height, image.bytesPerLine()))[:, : width * 3]
        arr = np.ascontiguousarray(arr.reshape((height, width, 3)))
        return arr, region_key

    def _collect_ocr_field_lists(self):
        result = {}
        for spec in self._ocr_field_specs:
            key = spec["key"]
            raw = self._ocr_field_widgets[key].text().strip()
            result[key] = [item.strip() for item in raw.split(",") if item.strip()]
        return result

    def run_ocr_test(self, auto_triggered=False):
        try:
            if hasattr(self, "ocr_status_label"):
                self.ocr_status_label.setText("OCR状态：正在识别...")
            img_rgb, region_key = self._crop_active_region_rgb()
            if img_rgb is None:
                if hasattr(self, "ocr_status_label"):
                    self.ocr_status_label.setText("OCR状态：未选中有效区域")
                self.ocr_result_box.setHtml('<div style="color:#dc3545;">No active region selected.</div>')
                return
            ocr = self._ensure_ocr_engine()
            result, _ = ocr(img_rgb)
            raw_parts = []
            line_html = []
            for line in result or []:
                text = str(line[1])
                raw_parts.append(text)
                safe_text = html.escape(text)
                score = line[2] if len(line) > 2 else None
                if isinstance(score, (int, float)):
                    line_html.append(f'<li>{safe_text} <span style="color:#6c757d;">({score:.2f})</span></li>')
                else:
                    line_html.append(f'<li>{safe_text}</li>')
            full_text = "".join(raw_parts)
            safe_full_text = html.escape(full_text or '(empty)')
            html_parts = [
                f'<div><span style="font-weight:600;">Region:</span> {html.escape(self.REGION_TEXT.get(region_key, region_key))}</div>',
                f'<div style="margin:4px 0 10px 0;"><span style="font-weight:600;">Raw Text:</span> {safe_full_text}</div>',
            ]
            if line_html:
                html_parts.append('<div style="font-weight:600;">Lines:</div><ul style="margin-top:4px;">' + ''.join(line_html) + '</ul>')

            field_lists = self._collect_ocr_field_lists()
            if field_lists:
                color_map = {
                    "ocr_keywords": "#1f7a1f",
                    "ignore_keywords": "#c92a2a",
                    "kill_keywords": "#e67700",
                }
                html_parts.append('<div style="margin-top:10px;font-weight:600;">Keyword Check:</div>')
                for spec in self._ocr_field_specs:
                    key = spec["key"]
                    values = field_lists.get(key, [])
                    hits = [item for item in values if item and item in full_text]
                    html_parts.append(
                        self._format_keyword_row(
                            spec.get('label', key),
                            values,
                            hits,
                            color_map.get(key, '#1971c2'),
                        )
                    )
            self.ocr_result_box.setHtml(''.join(html_parts))
            if hasattr(self, "ocr_status_label"):
                self.ocr_status_label.setText("OCR状态：已自动刷新" if auto_triggered else "OCR状态：已手动刷新")

        except Exception as exc:
            if hasattr(self, "ocr_status_label"):
                self.ocr_status_label.setText("OCR状态：识别失败")
            self.ocr_result_box.setHtml(
                f'<div style="color:#dc3545;">OCR test failed: {html.escape(str(exc))}</div>'
            )

    def get_ocr_field_values(self):
        values = {}
        for spec in self._ocr_field_specs:
            key = spec["key"]
            values[key] = self._ocr_field_widgets[key].text().strip()
        return values

    def get_ocr_profiles(self):
        if self._ocr_profiles:
            self._save_current_ocr_profile()
        return [dict(profile) for profile in self._ocr_profiles]

    def get_color_profiles(self):
        if self._color_profiles:
            self._save_current_color_profile()
            self._set_color_profile_dirty(False)
        return [dict(profile) for profile in self._color_profiles]

    def get_regions(self):
        merged = {key: dict(value) for key, value in self._all_regions.items()}
        merged.update(self.canvas.get_regions())
        return merged
