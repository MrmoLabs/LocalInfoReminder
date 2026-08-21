from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt

import numpy as np


def build_color_range_preview(sample_color, tolerance, width, height):
    width = max(150, int(width))
    height = max(68, int(height))
    tolerance = float(tolerance)
    sample = np.array(sample_color, dtype=np.float32)
    image = np.full((height, width, 3), 243, dtype=np.uint8)
    yy, xx = np.mgrid[0:height, 0:width]
    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0
    radius = max(1.0, min(width, height) / 2.0 - 6.0)
    norm_x = (xx - cx) / radius
    norm_y = (yy - cy) / radius
    dist = np.sqrt(norm_x ** 2 + norm_y ** 2)
    inside = dist <= 1.0

    if np.any(inside):
        red_blue_axis = np.array([1.0, -0.35, -0.65], dtype=np.float32)
        green_luma_axis = np.array([-0.45, 1.0, -0.2], dtype=np.float32)
        red_blue_axis /= np.linalg.norm(red_blue_axis)
        green_luma_axis /= np.linalg.norm(green_luma_axis)
        offsets = (
            norm_x[..., None] * tolerance * red_blue_axis[None, None, :]
            + norm_y[..., None] * tolerance * green_luma_axis[None, None, :]
        )
        colors = np.clip(sample[None, None, :] + offsets, 0, 255).astype(np.uint8)
        image[inside] = colors[inside]
        ring = np.abs(dist - 1.0) <= (1.6 / radius)
        image[ring] = np.array([90, 90, 90], dtype=np.uint8)
        center_radius = max(2.0, radius * 0.045)
        center_mask = dist <= (center_radius / radius)
        image[center_mask] = np.clip(sample, 0, 255).astype(np.uint8)

    qimage = QImage(image.tobytes(), width, height, image.strides[0], QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())


def build_color_mask_preview(img_rgb, mask, target_size):
    if img_rgb is None or mask is None or img_rgb.size == 0:
        return QPixmap()
    preview = img_rgb.copy().astype(np.uint8)
    preview = (preview * 0.35).astype(np.uint8)
    highlight = np.zeros_like(preview)
    highlight[:, :, 1] = 255
    preview[mask] = np.clip(preview[mask] * 0.4 + highlight[mask] * 0.6, 0, 255).astype(np.uint8)
    h, w, _ = preview.shape
    qimage = QImage(preview.tobytes(), w, h, preview.strides[0], QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(qimage.copy())
    return pixmap.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)



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
