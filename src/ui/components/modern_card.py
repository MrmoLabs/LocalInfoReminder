from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor, QFont

class ModernCard(QFrame):
    """
    A styled container widget with a drop shadow and optional title.
    Used for grouping settings in the Launcher.
    """
    def __init__(self, title=None, parent=None, accent_color="#007bff"):
        super().__init__(parent)
        self.setObjectName("Card")
        
        # Add Drop Shadow for "Fresh" look
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10) # Reduced blur
        shadow.setColor(QColor(0, 0, 0, 10)) 
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        self.layout = QVBoxLayout(self)
        # Compact Margins
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(8)
        
        if title:
            title_lbl = QLabel(title)
            title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            title_lbl.setStyleSheet(f"color: {accent_color}; margin-bottom: 2px; background: transparent;")
            self.layout.addWidget(title_lbl)

    def add_widget(self, widget):
        self.layout.addWidget(widget)
    
    def add_layout(self, layout):
        self.layout.addLayout(layout)
