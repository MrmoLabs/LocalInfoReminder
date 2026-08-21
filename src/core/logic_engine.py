import os
import json
import time
from typing import Dict, Optional, Any, List
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker, QRecursiveMutex
from core.config_loader import ConfigLoader

from core.group_controller import GroupController
from core.constants import FilePaths, TimeConstants, allow_dev_config_overrides
from core.logger import setup_logger

logger = setup_logger()

class LogicEngine(QThread):
    ui_update = pyqtSignal(dict) 
    toggle_overlay_mode = pyqtSignal()
    startup_progress = pyqtSignal(str, int)
    startup_ready = pyqtSignal()
    startup_failed = pyqtSignal(str)
    
    def __init__(self, runtime_config: Dict[str, Any]):
        super().__init__()
        
        # Config Loading
        self.config_path = FilePaths.CONFIG_JSON
        try:
            if os.path.exists(FilePaths.LAUNCHER_STATE):
                with open(FilePaths.LAUNCHER_STATE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    path = data.get("last_config_path")
                    if path and os.path.exists(path):
                        self.config_path = path
        except Exception as e:
            logger.error(f"[LogicEngine] Error reading launcher state: {e}")

        logger.info(f"[LogicEngine] Loading Config from: {self.config_path}")
        self.config = ConfigLoader.load_config(self.config_path) 
        
        self.runtime_config = runtime_config
        self.dev_flags = self._load_dev_flags()
        self.enable_debug_hotkeys = self.dev_flags.get('enable_debug_hotkeys', False)

        self.audio = None
        self.boss_manager = None
        self.input_manager = None
        self.command_manager = None
        self.time_manager = None
        self.ui_state_builder = None
        self.match_summary = None
        self.class_control_service = None
        self.tick_coordinator = None
        self.screen_monitor = None
        self.debug_overlay = None
        self.startup_complete = False
        
        self.running = True
        self.mutex = QRecursiveMutex()
        
        # Init Time
        try:
             initial_s = runtime_config.get('initial_delay', 0)
        except:
             initial_s = getattr(runtime_config, 'start_seconds', 0)
        self.initial_seconds = initial_s

        self.last_time_check = time.time()
        
        # Auto-Sync
        self.last_auto_sync_time = time.time()
        self.auto_sync_interval = max(5.0, float(self.config.get("ocr_time_sync_interval_seconds", TimeConstants.AUTO_SYNC_INTERVAL)))
        
        self.groups = {} 
        self._init_groups()

    def _report_startup_progress(self, message: str, value: int) -> None:
        logger.info(f"[LogicEngine] Startup {value}% - {message}")
        self.startup_progress.emit(message, value)

    def _initialize_runtime_components(self) -> None:
        from core.audio_manager import AudioManager
        from core.boss_manager import BossManager
        from core.class_control_service import ClassControlService
        from core.command_manager import CommandManager
        from core.input_manager import InputManager
        from core.match_summary import MatchSummaryWriter
        from core.runtime_tick_coordinator import RuntimeTickCoordinator
        from core.screen_monitor import ScreenMonitor
        from core.time_manager import TimeManager
        from core.ui_state_builder import UiStateBuilder

        self._report_startup_progress("正在初始化计时与状态...", 10)
        self.time_manager = TimeManager(self.config)
        self.time_manager.current_seconds = self.initial_seconds
        self.ui_state_builder = UiStateBuilder()
        self.match_summary = MatchSummaryWriter(
            boss_targets=self.config.get("boss_detection", {}).get("targets", [])
        )
        self.match_summary.update_countdown(self.time_manager.current_seconds)
        self.boss_manager = BossManager(self.config)
        self.command_manager = CommandManager(self.config)

        self._report_startup_progress("正在初始化音频...", 30)
        self.audio = AudioManager()
        self.class_control_service = ClassControlService(self.groups, self.audio)

        self._report_startup_progress("正在初始化输入监听...", 50)
        self.input_manager = InputManager(self.config, enable_debug_hotkeys=self.enable_debug_hotkeys)
        self.input_manager.gesture_detected.connect(self._handle_class_gesture)
        self.input_manager.skill_triggered.connect(self._handle_manual_command_hotkey)
        self.input_manager.overlay_toggled.connect(self.toggle_overlay_mode)
        self.input_manager.debug_screenshot.connect(self.trigger_debug_screenshot)
        self.input_manager.debug_boss_screenshot.connect(self.trigger_boss_debug)
        self.input_manager.debug_prep_screenshot.connect(self.trigger_prep_debug)

        self._report_startup_progress("正在初始化屏幕监控...", 70)
        self.screen_monitor = ScreenMonitor(interval=float(self.config.get("screen_monitor_interval_seconds", TimeConstants.SCREEN_MONITOR_INTERVAL)))
        self.screen_monitor.set_config(self.config)
        self.screen_monitor.trigger_skill_id.connect(self.trigger_skill_by_id)
        self.screen_monitor.time_sync_result.connect(self._on_time_sync)
        self.screen_monitor.boss_spawn_detected.connect(self._on_boss_spawn_detected)
        self.screen_monitor.boss_kill_detected.connect(self._on_boss_kill_detected)

        self._report_startup_progress("正在连接运行协调器...", 85)
        self.tick_coordinator = RuntimeTickCoordinator(
            input_manager=self.input_manager,
            time_manager=self.time_manager,
            boss_manager=self.boss_manager,
            class_control_service=self.class_control_service,
            command_manager=self.command_manager,
            audio=self.audio,
            screen_monitor=self.screen_monitor,
            config=self.config,
            auto_sync_interval=self.auto_sync_interval,
            last_time_check=self.last_time_check,
            last_auto_sync_time=self.last_auto_sync_time,
            trigger_time_sync=self.trigger_time_sync,
            emit_time_update=lambda value: self.ui_update.emit({"time_str": value}),
            emit_state=self._emit_state,
        )

        self._report_startup_progress("正在初始化调试覆盖层...", 95)
        self._check_debug_overlay()

        self.startup_complete = True
        self._report_startup_progress("启动完成", 100)
        self.startup_ready.emit()
        self._emit_state(False)

    def _load_dev_flags(self) -> Dict[str, Any]:
        if not allow_dev_config_overrides():
            logger.info("[LogicEngine] Dev config disabled in frozen build.")
            return {}
        try:
            if os.path.exists(FilePaths.DEV_CONFIG):
                with open(FilePaths.DEV_CONFIG, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"[LogicEngine] Failed to read dev config: {e}")
        return {}

    def _check_debug_overlay(self):
        try:
            if self.dev_flags.get("debug_ocr", False) and self.screen_monitor is not None:
                logger.info("[LogicEngine] Debug Overlay ENABLED via dev_config")
                from ui.debug_overlay import DebugOverlay
                self.debug_overlay = DebugOverlay()
                self.screen_monitor.debug_regions_changed.connect(self.debug_overlay.update_regions)
                self.debug_overlay.show()
        except Exception as e:
            logger.error(f"[LogicEngine] Failed to init Debug Overlay: {e}")

    def _init_groups(self) -> None:
        if not self.config.get('enable_classes', True):
            logger.info("[LogicEngine] Classes Disabled (enable_classes=False)")
            return

        if 'classes_template' in self.config:
            logger.info("[LogicEngine] Initializing Groups from classes_template...")
            for t_cfg in self.config['classes_template']:
                if not t_cfg.get('is_enabled', True):
                    continue
                    
                cid = t_cfg['id']
                class_cfgs = {}
                if hasattr(self.runtime_config, 'get'):
                    class_cfgs = self.runtime_config.get('classes', {})
                elif hasattr(self.runtime_config, 'class_configs'):
                     class_cfgs = self.runtime_config.class_configs
                
                if cid in class_cfgs:
                    rt_cfg = class_cfgs[cid]
                    count = rt_cfg['count']
                    loop_mode = rt_cfg.get('loop_mode', 'loop') 
                    
                    new_cfg = {
                        'id': cid,
                        'name': t_cfg['name'],
                        'buff_duration': t_cfg['interval'],
                        'skill_cooldown': t_cfg['cooldown'],
                        'skip_cd_hotkey': t_cfg.get('skip_cd_hotkey', ''),
                        'is_muted': t_cfg.get('is_muted', False),
                        'players': list(range(1, count + 1)),
                        'loop_mode': loop_mode
                    }
                    self.groups[cid] = GroupController(cid, new_cfg)

    def trigger_time_sync(self, is_auto: bool = False) -> None:
        if self.screen_monitor is not None and self.time_manager is not None:
            self.time_manager.pending_auto_sync = is_auto
            self.screen_monitor.trigger_sync()

    def _on_time_sync(self, time_text: str) -> None:
        if self.time_manager is None or self.match_summary is None or self.boss_manager is None:
            return
        success, time_str, is_active_fight = self.time_manager.process_ocr_result(time_text)
        
        if success:
             self.match_summary.update_countdown(self.time_manager.current_seconds)
             self.ui_update.emit({"time_str": time_str})
             
             if is_active_fight and not self.boss_manager.info.get('kill_status'):
                 kill_target = self.boss_manager.get_kill_target_for_time(self.time_manager.current_seconds)
                 if kill_target:
                     logger.info("[LogicEngine] Mid-Game Sync detected. Enabling Boss Kill Check for current window target.")
                     if self.screen_monitor is not None:
                         self.screen_monitor.set_boss_kill_check_enabled(True, kill_target)
                 else:
                     logger.info("[LogicEngine] Mid-Game Sync detected, but no boss target matches the current window. Skipping kill check enable.")

    def _on_boss_spawn_detected(self, boss_name: str) -> None:
        if self.boss_manager is None or self.match_summary is None or self.time_manager is None:
            return
        from core.audio_manager import AudioManager
        from core.constants import AudioFiles
        # Delegate to BossManager
        self.boss_manager.handle_spawn_detected(boss_name, self.time_manager.current_seconds)
        self.match_summary.record_boss_spawn(
            boss_name=boss_name,
            countdown_seconds=self.time_manager.current_seconds,
            predicted_seconds=self.boss_manager.info.get('spawn_time_abs'),
        )
        
        # Disable Spawn Check
        if self.screen_monitor is not None:
             self.screen_monitor.set_boss_check_enabled(False, [])

        spawn_sound = self.boss_manager.get_spawn_sound(boss_name) or AudioFiles.DRAGON_SPAWN
        if self.audio is not None:
            self.audio.play(spawn_sound, AudioManager.CHANNEL_HIGH)

    def _on_boss_kill_detected(self, faction: str, boss_name: str) -> None:
        if self.boss_manager is None or self.match_summary is None or self.time_manager is None:
            return
        from core.audio_manager import AudioManager
        # Delegate to BossManager
        self.boss_manager.handle_kill_detected(faction, boss_name)
        self.match_summary.record_boss_kill(
            boss_name=boss_name,
            faction=faction,
            countdown_seconds=self.time_manager.current_seconds,
        )
        
        # Disable Kill Check
        if self.screen_monitor is not None:
             self.screen_monitor.set_boss_kill_check_enabled(False, None)

        kill_sound = self.boss_manager.get_kill_sound(boss_name)
        if kill_sound and self.audio is not None:
            self.audio.play(kill_sound, AudioManager.CHANNEL_HIGH)

    def run(self) -> None:
        try:
            self._initialize_runtime_components()
        except Exception as e:
            logger.error(f"[LogicEngine] Startup initialization failed: {e}")
            self.startup_failed.emit(str(e))
            self.startup_complete = False
            return

        if self.screen_monitor is not None and not self.screen_monitor.isRunning():
            self.screen_monitor.start()
        if self.input_manager is not None:
            self.input_manager.start()
        while self.running:
            with QMutexLocker(self.mutex):
                self._process_tick()
                
            self.msleep(30) 
        if self.input_manager is not None:
            self.input_manager.stop()

    def stop(self, timeout_ms: int = 2000) -> None:
        self.running = False
        if self.screen_monitor is not None:
            self.screen_monitor.stop(timeout_ms=max(500, timeout_ms // 2))
        if self.isRunning():
            if not self.wait(timeout_ms):
                logger.warning(f"[LogicEngine] Stop timeout after {timeout_ms}ms; continuing shutdown.")

    # --- Handlers ---
    def _handle_class_gesture(self, group_id: str, gesture: str, player_id: Optional[object] = None) -> None:
        if self.class_control_service is None: return
        logger.debug(f"[LogicEngine] Handling Gesture: {gesture} for {group_id}")

        with QMutexLocker(self.mutex):
            self.class_control_service.handle_gesture(group_id, gesture, player_id)

    def trigger_skill_by_id(self, skill_id: str) -> None:
        if self.command_manager is None: return
        
        # [OPTIMIZATION] Check global flag
        if not self.config.get('enable_command_skills', True):
            return

        try:
            if 'command_skills' in self.config:
                for skill in self.config['command_skills']:
                    if not skill.get('is_enabled', True): continue
                    if str(skill.get('id', '')).lower() == str(skill_id).lower():
                        faction = self._skill_faction_from_config(skill)
                        self._handle_command_hotkey(skill, source='OCR', faction=faction)
                        return
        except Exception as e:
            logger.error(f"[LogicEngine] Error in trigger_skill_by_id: {e}")

    def _handle_manual_command_hotkey(self, skill_config: Dict[str, Any]) -> None:
        faction = self._skill_faction_from_config(skill_config)
        self._handle_command_hotkey(skill_config, source='热键', faction=faction)

    def _skill_faction_from_config(self, skill_config: Dict[str, Any]) -> str:
        color = str(skill_config.get('ocr_color', '') or '').strip().lower()
        if color == 'red':
            return '敌方'
        if color == 'blue':
            return '友方'
        return '-'

    def _handle_command_hotkey(self, skill_config: Dict[str, Any], source: str = '热键', faction: str = '-') -> None:
        if self.command_manager is None or self.match_summary is None or self.time_manager is None: return
        logger.debug(f"[LogicEngine] Handling Command Hotkey: {skill_config.get('name')}")
        from core.audio_manager import AudioManager
        with QMutexLocker(self.mutex):
            sound = self.command_manager.trigger_skill(skill_config)
            self.match_summary.record_command_skill(
                skill_name=skill_config.get('name', 'Unknown'),
                countdown_seconds=self.time_manager.current_seconds,
                source=source,
                faction=faction,
            )
            if sound and not skill_config.get('is_muted', False) and self.audio is not None:
                 self.audio.play(sound, AudioManager.CHANNEL_SFX)

    def toggle_class_state(self, group_id: str) -> None:
        with QMutexLocker(self.mutex):
            if group_id in self.groups: 
                grp = self.groups[group_id]
                if grp.state == GroupController.STATE_IDLE: grp.start()
                else: grp.toggle_pause()

    def stop_class(self, group_id: str) -> None:
        with QMutexLocker(self.mutex):
            if group_id in self.groups: self.groups[group_id].stop()

    def update_time(self, time_str: str) -> None:
        """Manual update from UI"""
        if self.time_manager is None or self.match_summary is None:
            return
        self.time_manager.set_time(time_str)
        self.match_summary.update_countdown(self.time_manager.current_seconds)
        with QMutexLocker(self.mutex):
             self.ui_update.emit({"time_str": time_str})

    def start_countdown(self, seconds: int = 1200) -> None:
        if self.time_manager is None or self.match_summary is None:
            return
        self.time_manager.current_seconds = seconds
        self.time_manager.time_accumulator = 0.0
        self.match_summary.update_countdown(self.time_manager.current_seconds)
        with QMutexLocker(self.mutex):
            self.ui_update.emit({"time_str": ConfigLoader.format_time_str(seconds)})

    def toggle_ocr(self) -> None:
        with QMutexLocker(self.mutex):
             if self.screen_monitor is not None:
                 self.screen_monitor.paused = not self.screen_monitor.paused
                 pass # sound = "cancel.mp3" if self.screen_monitor.paused else "prepare.mp3"
                 # self.audio.play(sound, AudioManager.CHANNEL_SFX)

    def trigger_debug_screenshot(self) -> None:
        if not self.enable_debug_hotkeys: return
        with QMutexLocker(self.mutex):
            if self.screen_monitor is not None:
                self.screen_monitor.trigger_debug_capture()
                 # self.audio.play("prepare.mp3", AudioManager.CHANNEL_SFX)

    def trigger_boss_debug(self) -> None:
        if not self.enable_debug_hotkeys: return
        with QMutexLocker(self.mutex):
             if self.screen_monitor is not None:
                 self.screen_monitor.trigger_debug_boss_capture()
                 # self.audio.play("prepare.mp3", AudioManager.CHANNEL_SFX)

    def trigger_prep_debug(self) -> None:
        if not self.enable_debug_hotkeys: return
        with QMutexLocker(self.mutex):
             if self.screen_monitor is not None:
                 self.screen_monitor.trigger_debug_prep_capture()
                 # self.audio.play("prepare.mp3", AudioManager.CHANNEL_SFX)

    def reload_config(self, new_config: Dict[str, Any]) -> None:
        """Called by Commander when config is updated dynamically."""
        with QMutexLocker(self.mutex):
             logger.info("[LogicEngine] Hot-Reloading Config...")
             self.config = new_config
             
             # Propagate to managers
             if self.command_manager is not None:
                 self.command_manager.config = self.config
             
             if self.input_manager is not None:
                 self.input_manager.config = self.config
                 self.input_manager.update_keys() # Rebind logic
                 
             if self.boss_manager is not None:
                 self.boss_manager.config = self.config

             if self.match_summary is not None:
                 self.match_summary.boss_targets = self.config.get("boss_detection", {}).get("targets", [])
                 
             if self.screen_monitor is not None:
                 self.screen_monitor.set_config(self.config)

             if self.tick_coordinator is not None:
                 self.tick_coordinator.update_config(self.config)
                 
             # Re-init groups if needed (complex, but for flags it's fine)
             # self._init_groups() # Full re-init might be overkill or unsafe during run
             # Just update flags for now
             
             logger.info("[LogicEngine] Config Reloaded.")

    def _process_tick(self) -> None:
        if self.tick_coordinator is None or self.match_summary is None or self.time_manager is None:
            return
        self.tick_coordinator.process_tick()
        self.match_summary.update_countdown(self.time_manager.current_seconds)
        self.last_time_check = self.tick_coordinator.last_time_check
        self.last_auto_sync_time = self.tick_coordinator.last_auto_sync_time

    def _emit_state(self, _unused=False):
        if not self.startup_complete or self.ui_state_builder is None or self.time_manager is None or self.command_manager is None or self.boss_manager is None:
            return
        screen_monitor = self.screen_monitor
        state_update = self.ui_state_builder.build(
            time_manager=self.time_manager,
            groups=self.groups,
            command_manager=self.command_manager,
            boss_manager=self.boss_manager,
            screen_monitor=screen_monitor,
        )
        self.ui_update.emit(state_update)
