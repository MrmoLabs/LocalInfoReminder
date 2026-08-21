from pathlib import Path

# roi_editor_color.py: add overlap preview builder
p = Path('src/ui/roi_editor_color.py')
text = p.read_text(encoding='utf-8')
if 'def build_dual_color_mask_preview' not in text:
    text += '''


def build_dual_color_mask_preview(img_rgb, primary_mask, secondary_mask, target_size):
    if img_rgb is None or img_rgb.size == 0:
        return QPixmap()
    base = (img_rgb.copy().astype(np.uint8) * 0.25).astype(np.uint8)
    primary = primary_mask.astype(bool) if primary_mask is not None else np.zeros(base.shape[:2], dtype=bool)
    secondary = secondary_mask.astype(bool) if secondary_mask is not None else np.zeros(base.shape[:2], dtype=bool)
    overlap = primary & secondary
    primary_only = primary & ~secondary
    secondary_only = secondary & ~primary

    # current profile: green, compare profile: blue, overlap: yellow
    base[primary_only] = np.array([70, 200, 120], dtype=np.uint8)
    base[secondary_only] = np.array([80, 140, 255], dtype=np.uint8)
    base[overlap] = np.array([255, 210, 60], dtype=np.uint8)

    h, w, _ = base.shape
    qimage = QImage(base.tobytes(), w, h, base.strides[0], QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(qimage.copy())
    return pixmap.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
'''
p.write_text(text, encoding='utf-8')

# roi_editor_panels.py: compact heights + compare preview
p = Path('src/ui/roi_editor_panels.py')
text = p.read_text(encoding='utf-8')
text = text.replace('        layout.setSpacing(10)\n', '        layout.setSpacing(6)\n', 1)
text = text.replace('        self.color_range_preview.setMinimumSize(180, 110)\n        self.color_range_preview.setMaximumHeight(130)\n', '        self.color_range_preview.setMinimumSize(160, 84)\n        self.color_range_preview.setMaximumHeight(96)\n')
text = text.replace('        self.color_mask_label.setMinimumSize(280, 140)\n', '        self.color_mask_label.setMinimumSize(240, 110)\n')
if 'self.compare_mask_title = QLabel(' not in text:
    insert_after = '        layout.addWidget(self.color_mask_label)\n'
    insert = '''        layout.addWidget(self.color_mask_label)\n\n        self.compare_mask_title = QLabel("红蓝重叠预览")\n        layout.addWidget(self.compare_mask_title)\n\n        self.compare_mask_stats = QLabel("当前规则: - | 对照规则: - | 重叠: -")\n        self.compare_mask_stats.setWordWrap(True)\n        self.compare_mask_stats.setStyleSheet("color: #5f6368;")\n        layout.addWidget(self.compare_mask_stats)\n\n        self.compare_mask_label = QLabel()\n        self.compare_mask_label.setMinimumSize(240, 110)\n        self.compare_mask_label.setStyleSheet("background-color: #f3f4f6; border: 1px solid #999;")\n        self.compare_mask_label.setAlignment(Qt.AlignmentFlag.AlignCenter)\n        layout.addWidget(self.compare_mask_label)\n'''
    text = text.replace(insert_after, insert)
text = text.replace('        layout.setSpacing(10)\n', '        layout.setSpacing(6)\n', 1)
text = text.replace('        self.ocr_result_box.setMinimumHeight(140)\n', '        self.ocr_result_box.setMinimumHeight(110)\n')
p.write_text(text, encoding='utf-8')

# roi_editor.py: import new helper, compact layout, add compare logic
p = Path('src/ui/roi_editor.py')
text = p.read_text(encoding='utf-8')
text = text.replace('from ui.roi_editor_color import build_color_mask_preview, build_color_range_preview\n', 'from ui.roi_editor_color import build_color_mask_preview, build_color_range_preview, build_dual_color_mask_preview\n')
text = text.replace('        self.side_panel_widget.setMinimumWidth(560)\n        self.side_panel_widget.setMaximumWidth(760)\n', '        self.side_panel_widget.setMinimumWidth(500)\n        self.side_panel_widget.setMaximumWidth(700)\n')
text = text.replace('        overview_layout.setSpacing(8)\n', '        overview_layout.setSpacing(6)\n')
text = text.replace('        self.preview_label.setMinimumSize(300, 160)\n        self.preview_label.setMaximumHeight(220)\n', '        self.preview_label.setMinimumSize(260, 120)\n        self.preview_label.setMaximumHeight(160)\n')
text = text.replace('            self.color_mask_label = self.color_panel.color_mask_label\n', '            self.color_mask_label = self.color_panel.color_mask_label\n            self.compare_mask_title = self.color_panel.compare_mask_title\n            self.compare_mask_stats = self.color_panel.compare_mask_stats\n            self.compare_mask_label = self.color_panel.compare_mask_label\n')
text = text.replace('                self.debug_splitter.setSizes([330, 330])\n', '                self.debug_splitter.setSizes([300, 300])\n')
text = text.replace('            side_panel_width = 620\n            target_canvas_width = 500\n', '            side_panel_width = 560\n            target_canvas_width = 440\n')
text = text.replace('            desired_width = target_canvas_width + side_panel_width + 72\n            width = max(1080, min(available.width() - 80, desired_width))\n            height = max(680, min(available.height() - 80, 860))\n', '            desired_width = target_canvas_width + side_panel_width + 56\n            width = max(980, min(available.width() - 120, desired_width))\n            height = max(600, min(available.height() - 120, 720))\n')
text = text.replace('            self.resize(1140, 760)\n', '            self.resize(1000, 680)\n')
if 'def _paired_color_profile' not in text:
    marker = '    def _build_color_mask_preview(self, img_rgb, mask):\n'
    insert = '''    def _paired_color_profile(self, profile):\n        profile_id = str((profile or {}).get("id", ""))\n        if profile_id == "skill_red":\n            return next((item for item in self._color_profiles if item.get("id") == "skill_blue"), None)\n        if profile_id == "skill_blue":\n            return next((item for item in self._color_profiles if item.get("id") == "skill_red"), None)\n        if profile_id == "boss_red":\n            return next((item for item in self._color_profiles if item.get("id") == "boss_blue"), None)\n        if profile_id == "boss_blue":\n            return next((item for item in self._color_profiles if item.get("id") == "boss_red"), None)\n        return None\n\n    def _build_dual_color_mask_preview(self, img_rgb, primary_mask, secondary_mask):\n        if hasattr(self, "compare_mask_label"):\n            return build_dual_color_mask_preview(img_rgb, primary_mask, secondary_mask, self.compare_mask_label.size())\n        return build_dual_color_mask_preview(img_rgb, primary_mask, secondary_mask, QSize(240, 110))\n\n'''
    text = text.replace(marker, insert + marker)
old = '''            ratio, mask = match_ratio(img_rgb, profile)
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
'''
new = '''            ratio, mask = match_ratio(img_rgb, profile)
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
'''
if old not in text:
    raise SystemExit('run_color_test block not found')
text = text.replace(old, new)
# invalid ROI branch clear compare widgets
text = text.replace('                if hasattr(self, "color_mask_label"):\n                    self.color_mask_label.setPixmap(QPixmap())\n                    self.color_mask_label.setText("当前 ROI 无法生成遮罩预览")\n                return\n', '                if hasattr(self, "color_mask_label"):\n                    self.color_mask_label.setPixmap(QPixmap())\n                    self.color_mask_label.setText("当前 ROI 无法生成遮罩预览")\n                if hasattr(self, "compare_mask_label"):\n                    self.compare_mask_title.setText("红蓝重叠预览")\n                    self.compare_mask_stats.setText("当前规则: - | 对照规则: - | 重叠: -")\n                    self.compare_mask_label.setPixmap(QPixmap())\n                    self.compare_mask_label.setText("请先选择有效 ROI")\n                return\n')
# exception branch clear compare
text = text.replace('            if hasattr(self, "color_mask_label"):\n                self.color_mask_label.setPixmap(QPixmap())\n                self.color_mask_label.setText("当前参数没有生成可用遮罩")\n', '            if hasattr(self, "color_mask_label"):\n                self.color_mask_label.setPixmap(QPixmap())\n                self.color_mask_label.setText("当前参数没有生成可用遮罩")\n            if hasattr(self, "compare_mask_label"):\n                self.compare_mask_title.setText("红蓝重叠预览")\n                self.compare_mask_stats.setText("当前规则: - | 对照规则: - | 重叠: -")\n                self.compare_mask_label.setPixmap(QPixmap())\n                self.compare_mask_label.setText("当前参数没有生成可用对比图")\n')
p.write_text(text, encoding='utf-8')

print('patched overlap preview and compact height')
