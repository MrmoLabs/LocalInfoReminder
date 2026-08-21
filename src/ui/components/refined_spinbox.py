from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox, QAbstractSpinBox
from PyQt6.QtCore import Qt

class RefinedSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        # Optional: Set focus policy if needed
        
    def wheelEvent(self, event):
        # Ignore wheel event to prevent value change, 
        # allowing it to bubble up to parent scroll area
        event.ignore()

class RefinedDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        
    def wheelEvent(self, event):
        event.ignore()
