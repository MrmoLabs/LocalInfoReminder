import time
import keyboard
try:
    import mouse
    HAS_MOUSE = True
except ImportError:
    HAS_MOUSE = False
    print("[InputListener] 'mouse' library not found. Mouse bindings will not work.")

from PyQt6.QtCore import QObject, pyqtSignal
from core.logger import setup_logger

logger = setup_logger()

class InputListener(QObject):
    """
    Responsibilities:
    1. Hook into low-level Keyboard and Mouse events.
    2. Normalize raw events into a canonical string format (e.g., 'ctrl+alt+num_1').
    3. Emit signals for 'Press' and 'Release' with the canonical key.
    4. Provide Global Hotkey registration (Ctrl+M, etc).
    """
    
    key_pressed = pyqtSignal(str) # canonical_key
    key_released = pyqtSignal(str) # canonical_key
    
    # Global Signals
    global_hotkey_triggered = pyqtSignal(str) # 'overlay', 'debug_skill', 'debug_boss', 'debug_prep'

    def __init__(self, enable_debug_hotkeys=False):
        super().__init__()
        self._active = False
        self.enable_debug_hotkeys = enable_debug_hotkeys
        self.on_key_pressed = None
        self.on_key_released = None
        self.on_global_hotkey = None

    def start(self):
        if self._active: return
        self._active = True
        
        keyboard.on_press(self._on_key_press)
        keyboard.on_release(self._on_key_release)
        
        if HAS_MOUSE:
            try:
                mouse.hook(self._on_mouse_event)
            except Exception as e:
                print(f"[InputListener] Failed to hook mouse: {e}")
                
        # Register Globals
        self._register_globals()

    def stop(self):
        self._active = False
        try:
            keyboard.unhook_all()
            if HAS_MOUSE:
                mouse.unhook_all()
        except Exception as e:
            print(f"[InputListener] Error during cleanup: {e}")

    def _register_globals(self):
        try:
            keyboard.add_hotkey('ctrl+m', lambda: self._emit_global_hotkey('overlay'))
            if self.enable_debug_hotkeys:
                keyboard.add_hotkey('ctrl+i', lambda: self._emit_global_hotkey('debug_skill'))
                keyboard.add_hotkey('ctrl+o', lambda: self._emit_global_hotkey('debug_boss'))
                keyboard.add_hotkey('ctrl+u', lambda: self._emit_global_hotkey('debug_prep'))
        except Exception as e:
            print(f"[InputListener] Failed to register Global hotkeys: {e}")

    def _on_key_press(self, event):
        if not self._active: return
        key = self._get_canonical_key(event.name, event.is_keypad, is_mouse=False)
        if self._should_trace_key(key):
            logger.debug(
                f"[InputListener] Hook press received: raw={event.name} keypad={event.is_keypad} canonical={key}"
            )
        if callable(self.on_key_pressed):
            self.on_key_pressed(key)
        self.key_pressed.emit(key)

    def _on_key_release(self, event):
        if not self._active: return
        key = self._get_canonical_key(event.name, event.is_keypad, is_mouse=False)
        if self._should_trace_key(key):
            logger.debug(
                f"[InputListener] Hook release received: raw={event.name} keypad={event.is_keypad} canonical={key}"
            )
        if callable(self.on_key_released):
            self.on_key_released(key)
        self.key_released.emit(key)

    def _on_mouse_event(self, event):
        if not self._active: return
        if not isinstance(event, mouse.ButtonEvent): return
        
        key_name = self._map_mouse_button(event.button)
        if event.event_type == mouse.DOWN:
             if callable(self.on_key_pressed):
                 self.on_key_pressed(key_name)
             self.key_pressed.emit(key_name)
        elif event.event_type == mouse.UP:
             if callable(self.on_key_released):
                 self.on_key_released(key_name)
             self.key_released.emit(key_name)

    def _emit_global_hotkey(self, event_type: str):
        if callable(self.on_global_hotkey):
            self.on_global_hotkey(event_type)
        self.global_hotkey_triggered.emit(event_type)

    def _map_mouse_button(self, button) -> str:
        if button == mouse.LEFT: return "mouse_left"
        elif button == mouse.RIGHT: return "mouse_right"
        elif button == mouse.MIDDLE: return "mouse_middle"
        elif button == mouse.X: return "mouse_x1"
        elif button == mouse.X2: return "mouse_x2"
        return f"mouse_{button}"

    def _get_canonical_key(self, event_or_name: str, is_keypad=False, is_mouse=False) -> str:
        """Constructs 'ctrl+alt+num_1' style string."""
        if is_mouse: return event_or_name
        
        key = event_or_name.lower()
        parts = []
        
        # Check Modifiers
        # Note: keyboard.is_pressed is fast enough here
        if key not in ['ctrl', 'right ctrl', 'left ctrl'] and keyboard.is_pressed('ctrl'): parts.append('ctrl')
        if key not in ['alt', 'right alt', 'left alt', 'alt gr'] and keyboard.is_pressed('alt'): parts.append('alt')
        if key not in ['shift', 'right shift', 'left shift'] and keyboard.is_pressed('shift'): parts.append('shift')
        
        final_key = key
        
        # 1. Handle "num 1" -> "num_1"
        if final_key.startswith("num "):
            final_key = final_key.replace(" ", "_")
        # 2. Keypad Heuristics
        elif is_keypad:
            if final_key.isdigit() or final_key in ['enter', '+', '-', '*', '/', '.']:
                final_key = f"num_{final_key}"
        
        parts.append(final_key)
        return "+".join(parts)

    @staticmethod
    def _should_trace_key(key: str) -> bool:
        return key in {"num_1", "num_2", "num_3", "num_4", "num_5"}
