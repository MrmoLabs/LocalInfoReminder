from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence

class HotkeyRecorder(QPushButton):
    hotkey_changed = pyqtSignal(str) # Custom signal
    PLACEHOLDER_TEXT = "Click to Set"

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.current_hotkey = self._normalize_hotkey(text)
        self.setText(self.current_hotkey if self.current_hotkey else self.PLACEHOLDER_TEXT)
        self.setCheckable(True)
        self.clicked.connect(self.on_click)
        self.setStyleSheet("text-align: center; border: none; background: transparent;")
        
    def on_click(self):
        if self.isChecked():
            self.setText("Recording...")
            self.setStyleSheet("background-color: #ffcccc; border: 1px solid red; border-radius: 4px;")
            self.grabKeyboard()
            self.grabMouse() # Capture mouse buttons
        else:
            self.finish_recording()

    def finish_recording(self):
        self.releaseKeyboard()
        self.releaseMouse()
        self.setChecked(False)
        self.setText(self.current_hotkey if self.current_hotkey else self.PLACEHOLDER_TEXT)
        self.setStyleSheet("text-align: center; border: none; background: transparent;")
        self.hotkey_changed.emit(self.current_hotkey) # Emit signal

    def keyPressEvent(self, event):
        if not self.isChecked():
            return super().keyPressEvent(event)
            
        key = event.key()
        modifiers = event.modifiers()
        
        # Check if the pressed key itself is a modifier
        is_modifier_key = key in [Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta]
        
        # Build String
        parts = []
        
        # Add Modifiers from State
        if modifiers & Qt.KeyboardModifier.ControlModifier: parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier: parts.append("alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier: parts.append("shift")
        
        # Determine Key Text
        key_text = ""
        is_numpad = (modifiers & Qt.KeyboardModifier.KeypadModifier)
        
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            key_text = str(key - Qt.Key.Key_0)
        elif Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            key_text = chr(key).lower()
        elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            key_text = f"f{key - Qt.Key.Key_F1 + 1}"
        else:
            # Fallback
            key_text = QKeySequence(key).toString().lower()

        # Handle Numpad
        if is_numpad and key_text.isdigit():
             key_text = f"num_{key_text}"

        # Logic to avoid "ctrl+ctrl"
        # If the key IS a modifier, we only want it if it wasn't already added by the modifiers bitmask
        # OR we just rebuild the list carefully.
        
        # Simplified approach:
        # If key is modifier, ensure it's in parts.
        # If key is NOT modifier, append it to parts.
        
        if is_modifier_key:
            modifier_names = {
                Qt.Key.Key_Control: "ctrl",
                Qt.Key.Key_Shift: "shift",
                Qt.Key.Key_Alt: "alt",
                Qt.Key.Key_Meta: "meta",
            }
            k_lower = modifier_names.get(key, key_text.lower())
            if k_lower not in parts:
                parts.append(k_lower)
        else:
            parts.append(key_text)
            
        result = "+".join(parts)
        
        self.current_hotkey = result
        self.setText(result)
        
        # Only finish if it's NOT a modifier key
        if not is_modifier_key:
            self.finish_recording()

    def keyReleaseEvent(self, event):
        if not self.isChecked():
            return super().keyReleaseEvent(event)
            
        key = event.key()
        is_modifier_key = key in [Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta]
        
        # If a modifier is released and we are STILL recording, it means the user wants to bind the modifier itself.
        if is_modifier_key:
            self.finish_recording()

    def mousePressEvent(self, event):
        if not self.isChecked():
            if event.button() == Qt.MouseButton.RightButton:
                self.current_hotkey = ""
                self.setText(self.PLACEHOLDER_TEXT)
                self.setChecked(False)
                self.hotkey_changed.emit(self.current_hotkey) # Emit
            return super().mousePressEvent(event)
        
        btn = event.button()
        btn_name = ""
        if btn == Qt.MouseButton.LeftButton: btn_name = "mouse_left"
        elif btn == Qt.MouseButton.RightButton: btn_name = "mouse_right"
        elif btn == Qt.MouseButton.MiddleButton: btn_name = "mouse_middle"
        elif btn == Qt.MouseButton.XButton1: btn_name = "mouse_x1"
        elif btn == Qt.MouseButton.XButton2: btn_name = "mouse_x2"
        
        if btn_name:
            self.current_hotkey = btn_name
            self.setText(btn_name)
            self.finish_recording()

    @classmethod
    def _normalize_hotkey(cls, value):
        text = str(value or "").strip()
        if text.lower() in {"click to set", "recording..."}:
            return ""
        return text
