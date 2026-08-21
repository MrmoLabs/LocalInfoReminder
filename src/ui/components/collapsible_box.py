from PyQt6.QtWidgets import QWidget, QToolButton, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class CollapsibleBox(QWidget):
    # Toggle signal for the checkbox (checked state)
    toggled = pyqtSignal(bool)

    def __init__(self, title="", parent=None, enable_check=False, checked=True):
        super(CollapsibleBox, self).__init__(parent)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # === Header Area ===
        self.header_frame = QWidget()
        self.header_frame.setStyleSheet("background-color: #f1f3f5; border-radius: 4px;")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(4, 4, 4, 4)
        header_layout.setSpacing(8)

        # 1. Expand/Collapse Button
        self.toggle_button = QToolButton(text="", checkable=True, checked=False)
        # Avoid Qt hover repaint warnings when the inherited button font has pointSize == -1.
        self.toggle_button.setFont(QFont("Segoe UI", 10))
        self.toggle_button.setStyleSheet("border: none; background: transparent; color: #333;")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.clicked.connect(self.on_pressed)
        header_layout.addWidget(self.toggle_button)

        # 2. Checkbox (Optional)
        self.checkbox = None
        if enable_check:
            self.checkbox = QCheckBox()
            self.checkbox.setChecked(checked)
            self.checkbox.clicked.connect(self.on_checkbox_toggled)
            header_layout.addWidget(self.checkbox)

        # 3. Title Label
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("color: #333;")
        header_layout.addWidget(self.lbl_title)
        
        # Make the title clickable to toggle expansion too?
        # For now, keep simple.

        header_layout.addStretch()
        self.main_layout.addWidget(self.header_frame)

        # === Content Area ===
        self.content_area = QWidget()
        self.content_area.setVisible(False)
        self.main_layout.addWidget(self.content_area)

    def set_content_layout(self, layout):
        self.content_area.setLayout(layout)

    def on_pressed(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self.content_area.setVisible(checked)

    def set_content_visible(self, visible):
        self.toggle_button.setChecked(visible)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if visible else Qt.ArrowType.RightArrow)
        self.content_area.setVisible(visible)
        
    def on_checkbox_toggled(self):
        if self.checkbox:
            self.toggled.emit(self.checkbox.isChecked())
            
    def is_checked(self):
        return self.checkbox.isChecked() if self.checkbox else True
