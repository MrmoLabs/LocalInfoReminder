import sys
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QPen

class DebugOverlay(QWidget):
    def __init__(self):
        super().__init__()
        # Set window flags for transparency and click-through
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Maximize to cover the screen
        self.showFullScreen()
        
        self.regions = {}
        
    def update_regions(self, regions: dict):
        """
        updates the regions to draw.
        regions format: {'label': {'top': int, 'left': int, 'width': int, 'height': int, 'color': QColorish}}
        """
        self.regions = regions
        self.repaint()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for label, r_data in self.regions.items():
            if not r_data: continue
            
            # DPI Correction
            dpr = self.devicePixelRatio()
            x = int(r_data.get('left', 0) / dpr)
            y = int(r_data.get('top', 0) / dpr)
            w = int(r_data.get('width', 0) / dpr)
            h = int(r_data.get('height', 0) / dpr)
            
            # Default color: Green
            color_val = r_data.get('color', '#00FF00')
            color = QColor(color_val)
            
            # Draw Rectangle
            pen = QPen(color)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(x, y, w, h)
            
            # Draw Label
            painter.setPen(color)
            painter.drawText(x, y - 5, f"{label} ({w}x{h})")
            
