import time
from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker
from core.input.key_mapper import KeyMapper
from core.input.input_listener import InputListener
from core.input.input_state import InputState
from core.logger import setup_logger

logger = setup_logger()

class InputManager(QObject):
    """
    Responsibilities:
    1. Orchestrator Facade: Connects Listener, Mapper, and State.
    2. Exposes signals to LogicEngine.
    3. Thread-Safety: Manages mutex for state updates.
    """
    
    # Signals for logic engine
    gesture_detected = pyqtSignal(str, str, object) # group_id, gesture_type, optional_data
    skill_triggered = pyqtSignal(dict)      # skill_config
    overlay_toggled = pyqtSignal()
    debug_screenshot = pyqtSignal()
    debug_boss_screenshot = pyqtSignal()
    debug_prep_screenshot = pyqtSignal()

    def __init__(self, config, enable_debug_hotkeys=False):
        super().__init__()
        self.config = config
        self.mutex = QMutex()
        
        # Components
        self.mapper = KeyMapper(config)
        self.state = InputState(self.mapper)
        self.listener = InputListener(enable_debug_hotkeys=enable_debug_hotkeys)
        
        # Wiring
        self.listener.on_key_pressed = self._on_press
        self.listener.on_key_released = self._on_release
        self.listener.on_global_hotkey = self._on_global_hotkey

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()

    def update_keys(self):
        """
        Rebuild key maps after config hot-reload.
        Clears pending gesture state to avoid mixing old and new bindings.
        """
        with QMutexLocker(self.mutex):
            self.mapper = KeyMapper(self.config)
            self.state = InputState(self.mapper)
        
    def clear_state(self):
        with QMutexLocker(self.mutex):
             self.state.clear()

    def poll_holds(self, now):
        """
        Polls for Hold gestures and pending taps.
        """
        actions = []
        with QMutexLocker(self.mutex):
            actions = self.state.poll_holds(now)
        
        if actions:
            self._dispatch_actions(actions)

    def _on_press(self, key):
        if not key: return
        trace_key = self._should_trace_key(key)
        if trace_key:
            logger.debug(
                f"[InputManager] Press received: key={key} mapped_entries={len(self.mapper.get_entries(key))} "
                f"skip={'yes' if self.mapper.get_skip_cid(key) else 'no'} "
                f"skill={'yes' if self.mapper.get_skill_config(key) else 'no'}"
            )
        actions = []
        with QMutexLocker(self.mutex):
            actions = self.state.process_press(key, time.time())
        
        if actions:
            if trace_key:
                logger.debug(f"[InputManager] Press produced actions: key={key} actions={actions}")
            self._dispatch_actions(actions)
        elif trace_key:
            logger.debug(f"[InputManager] Press produced no actions: key={key}")

    def _on_release(self, key):
        if not key: return
        trace_key = self._should_trace_key(key)
        if trace_key:
            logger.debug(
                f"[InputManager] Release received: key={key} mapped_entries={len(self.mapper.get_entries(key))} "
                f"skip={'yes' if self.mapper.get_skip_cid(key) else 'no'}"
            )
        actions = []
        with QMutexLocker(self.mutex):
            actions = self.state.process_release(key, time.time())
            
        if actions:
            if trace_key:
                logger.debug(f"[InputManager] Release produced actions: key={key} actions={actions}")
            self._dispatch_actions(actions)
        elif trace_key:
            logger.debug(f"[InputManager] Release produced no actions: key={key}")

    def _on_global_hotkey(self, event_type):
        if event_type == 'overlay':
            self.overlay_toggled.emit()
        elif event_type == 'debug_skill':
            self.debug_screenshot.emit()
        elif event_type == 'debug_boss':
            self.debug_boss_screenshot.emit()
        elif event_type == 'debug_prep':
            self.debug_prep_screenshot.emit()

    def _dispatch_actions(self, actions: list):
        """
        Emits signals based on actions returned by InputState.
        Action format: (TYPE, DATA...)
        """
        for act in actions:
            start_t = time.time()
            act_type = act[0]
            
            if act_type == InputState.ACTION_GESTURE:
                # ('gesture', cid, gesture_name, pid)
                self.gesture_detected.emit(act[1], act[2], act[3])
                
            elif act_type == InputState.ACTION_SKILL:
                # ('skill', skill_config)
                self.skill_triggered.emit(act[1])

    @staticmethod
    def _should_trace_key(key):
        return key in {"num_1", "num_2", "num_3", "num_4", "num_5"}
