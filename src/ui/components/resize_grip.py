from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

class VersionResizeGrip(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.3);
                background: transparent;
                font-family: 'Consolas';
                font-size: 12px;
                padding: 5px;
            }
            QLabel:hover {
                color: rgba(255, 255, 255, 0.8);
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("Drag to Resize")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            if window.windowHandle():
                # Start system resize from bottom-right corner
                window.windowHandle().startSystemResize(Qt.Edge.RightEdge | Qt.Edge.BottomEdge)
