import sys
import os
import time
from utils.resource_path import get_resource_path

# Ensure src is in path and sanitize sys.path from external interference
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# [FIX] Remove external PYTHONPATH if it points to incompatible locations
# This ensures that even if user has a global PYTHONPATH set, the VENV takes precedence.
if os.environ.get('PYTHONPATH'):
    ppath = os.environ.get('PYTHONPATH')
    for p in ppath.split(os.pathsep):
        if p and p in sys.path:
            # Only remove if it's not the current script dir or venv dir
            if "venv" not in p.lower() and script_dir.lower() not in p.lower():
                while p in sys.path:
                    sys.path.remove(p)

from core.logger import setup_logger
from core.localization import LocalizationManager
import traceback
import ctypes

# Setup global logger
logger = setup_logger()


def preload_ocr_runtime():
    """Load OCR runtime before Qt to avoid DLL init conflicts on Windows."""
    try:
        from core.vision.performance import (
            apply_rapidocr_runtime_limits,
            ensure_onnxruntime_dll_search_paths,
            preload_onnxruntime_native_binaries,
        )

        ensure_onnxruntime_dll_search_paths()
        preload_onnxruntime_native_binaries()
        apply_rapidocr_runtime_limits({})
        import onnxruntime  # noqa: F401
        from rapidocr_onnxruntime import RapidOCR  # noqa: F401
        logger.info("OCR runtime preloaded before QApplication.")
        return True
    except Exception as e:
        logger.warning(f"Failed to preload OCR runtime before QApplication: {e}")
        return False

_OCR_RUNTIME_PRELOADED = preload_ocr_runtime()

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QAction, QDesktopServices
from PyQt6.QtCore import QThread, pyqtSignal, QUrl
from core.update_checker import UpdateCheckError, check_github_update, load_update_config
from core.version import __version__


_preloaded_logic_engine_cls = None
_preloaded_overlay_window_cls = None
_startup_preload_error = None
_startup_preload_done = False


class StartupPreloadWorker(QThread):
    finished_preload = pyqtSignal(bool, str)

    def run(self):
        global _preloaded_logic_engine_cls, _preloaded_overlay_window_cls, _startup_preload_error, _startup_preload_done

        start_ts = time.perf_counter()
        try:
            logger.info("Startup preload: importing LogicEngine...")
            from core.logic_engine import LogicEngine
            logic_elapsed = time.perf_counter() - start_ts
            logger.info(f"Startup preload: LogicEngine imported in {logic_elapsed:.3f}s")

            overlay_start = time.perf_counter()
            from ui.overlay import OverlayWindow
            overlay_elapsed = time.perf_counter() - overlay_start
            total_elapsed = time.perf_counter() - start_ts
            logger.info(f"Startup preload: OverlayWindow imported in {overlay_elapsed:.3f}s")
            logger.info(f"Startup preload completed in {total_elapsed:.3f}s")

            _preloaded_logic_engine_cls = LogicEngine
            _preloaded_overlay_window_cls = OverlayWindow
            _startup_preload_error = None
            _startup_preload_done = True
            self.finished_preload.emit(True, "")
        except Exception as e:
            _startup_preload_error = str(e)
            _startup_preload_done = False
            logger.warning(f"Startup preload failed: {e}")
            logger.error(traceback.format_exc())
            self.finished_preload.emit(False, str(e))


class UpdateCheckWorker(QThread):
    check_finished = pyqtSignal(object)
    check_failed = pyqtSignal(str)

    def run(self):
        try:
            config = load_update_config()
            self.check_finished.emit(check_github_update(config["github_repository"]))
        except UpdateCheckError as exc:
            self.check_failed.emit(str(exc))
        except Exception as exc:
            logger.exception("Unexpected update check failure.")
            self.check_failed.emit(str(exc))


def _show_update_result(result, manual=False):
    loc = LocalizationManager()
    if result.update_available:
        message = QMessageBox()
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle(loc.get("UI_UPDATE_AVAILABLE_TITLE"))
        message.setText(loc.get("UI_UPDATE_AVAILABLE").format(
            current=result.current_version,
            latest=result.latest_version,
        ))
        if result.release_notes.strip():
            message.setDetailedText(result.release_notes.strip()[:8000])
        open_button = message.addButton(loc.get("UI_OPEN_RELEASE"), QMessageBox.ButtonRole.AcceptRole)
        message.addButton(QMessageBox.StandardButton.Close)
        message.exec()
        if message.clickedButton() is open_button:
            QDesktopServices.openUrl(QUrl(result.release_url))
    elif manual:
        QMessageBox.information(
            None,
            loc.get("UI_UPDATE_CHECK_TITLE"),
            loc.get("UI_ALREADY_LATEST").format(version=result.current_version),
        )


def _start_update_check(app, manual=False):
    global _update_check_worker
    if "_update_check_worker" in globals() and _update_check_worker.isRunning():
        if manual:
            QMessageBox.information(
                None,
                LocalizationManager().get("UI_UPDATE_CHECK_TITLE"),
                LocalizationManager().get("UI_UPDATE_CHECKING"),
            )
        return

    worker = UpdateCheckWorker(app)
    worker.check_finished.connect(lambda result: _show_update_result(result, manual))
    worker.check_failed.connect(
        lambda error: QMessageBox.warning(
            None,
            LocalizationManager().get("UI_UPDATE_CHECK_TITLE"),
            LocalizationManager().get("UI_UPDATE_CHECK_FAILED").format(error=error),
        ) if manual else logger.warning(f"Startup update check skipped or failed: {error}")
    )
    _update_check_worker = worker
    worker.start()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False



def start_overlay(runtime_config, launcher=None):
    """Starts the overlay with the given configuration."""
    logger.info("Initializing Overlay...")
    
    try:
        global _preloaded_logic_engine_cls, _preloaded_overlay_window_cls

        LogicEngine = _preloaded_logic_engine_cls
        OverlayWindow = _preloaded_overlay_window_cls

        if LogicEngine is None:
            logger.info("Importing LogicEngine...")
            from core.logic_engine import LogicEngine
            logger.info("LogicEngine import completed.")
        else:
            logger.info("LogicEngine import completed via startup preload cache.")

        if OverlayWindow is None:
            logger.info("Importing OverlayWindow...")
            from ui.overlay import OverlayWindow
            logger.info("OverlayWindow import completed.")
        else:
            logger.info("OverlayWindow import completed via startup preload cache.")

        # Create Logic Engine
        logger.info("Creating LogicEngine...")
        logic = LogicEngine(runtime_config)
        
        # Create Overlay Window
        logger.info("Creating OverlayWindow...")
        overlay = OverlayWindow(logic)

        if launcher is not None:
            logic.startup_ready.connect(launcher.on_runtime_started)

            def _restore_launcher(error_message):
                overlay.hide()
                launcher.on_runtime_start_failed(error_message)

            logic.startup_failed.connect(_restore_launcher)
        
        # Connect Signals
        logic.ui_update.connect(overlay.update_state)
        logic.toggle_overlay_mode.connect(overlay.toggle_passthrough)
        
        # Show Overlay first so the UI appears before background services finish warming up.
        logger.info("Showing OverlayWindow...")
        overlay.show()

        # Start Logic
        logger.info("Starting LogicEngine thread...")
        logic.start()
        
        # Keep references to prevent garbage collection
        global _keep_alive_logic, _keep_alive_overlay
        _keep_alive_logic = logic
        _keep_alive_overlay = overlay
        logger.info("Overlay started successfully.")
        
    except Exception as e:
        logger.error(f"Failed to start overlay: {e}")
        logger.error(traceback.format_exc())
        if launcher is not None:
            launcher.on_runtime_start_failed(str(e))

def disable_quickedit():
    """Disables Windows Console QuickEdit mode to prevent blocking execution on click."""
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-10) # STD_INPUT_HANDLE
        mode = ctypes.c_uint32()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        # 0x0040 is ENABLE_QUICK_EDIT_MODE, we clear it
        mode.value &= ~0x0040
        # 0x0080 is ENABLE_EXTENDED_FLAGS (required to set)
        mode.value |= 0x0080
        kernel32.SetConsoleMode(handle, mode)
        logger.info("QuickEdit Mode disabled.")
    except Exception as e:
        logger.warning(f"Failed to disable QuickEdit Mode: {e}")

def setup_tray_icon(app):
    """Sets up the system tray icon."""
    icon_path = get_resource_path("assets/LocalInfoReminder.ico")
    if not os.path.exists(icon_path):
        logger.warning(f"Tray icon file missing: {icon_path}")
        return None
        
    loc = LocalizationManager()
    tray = QSystemTrayIcon(QIcon(icon_path), app)
    tray.setToolTip(loc.get("UI_TRAY_TOOLTIP"))
    
    menu = QMenu()

    version_action = QAction(loc.get("UI_VERSION_ACTION").format(version=__version__), app)
    version_action.setEnabled(False)
    check_update_action = QAction(loc.get("UI_CHECK_UPDATE_ACTION"), app)
    check_update_action.triggered.connect(lambda: _start_update_check(app, manual=True))
    exit_action = QAction(loc.get("UI_EXIT_ACTION"), app)
    exit_action.triggered.connect(app.quit)

    menu.addAction(version_action)
    menu.addAction(check_update_action)
    menu.addSeparator()
    menu.addAction(exit_action)
    tray.setContextMenu(menu)
    tray.show()
    
    logger.info("System Tray Icon initialized.")
    return tray


def setup_tray_icon_deferred(app):
    global _tray_icon
    try:
        _tray_icon = setup_tray_icon(app)
    except Exception as e:
        logger.warning(f"Deferred tray icon setup failed: {e}")


def cleanup():
    """Explicitly stops all threads and ensures process termination."""
    logger.info("Performing application cleanup...")
    
    # Stop Logic Engine if running
    global _keep_alive_logic
    if '_keep_alive_logic' in globals() and _keep_alive_logic:
        logger.info("Stopping LogicEngine...")
        try:
            _keep_alive_logic.stop()
        except Exception as e:
            logger.error(f"Error stopping LogicEngine: {e}")
            
    # Force kill process to ensure no zombie threads remain (e.g. keyboard hooks)
    logger.info("Forcing process exit...")
    import os
    os._exit(0)

def main():
    # [NEW] Set AppUserModelID for robust taskbar icon grouping on Windows
    try:
        my_app_id = u'LocalInfoReminder.v1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)
    except:
        pass

    # Check for admin privileges
    if not is_admin():
        logger.info("Requesting admin privileges...")
        try:
            cwd = os.getcwd()
            if getattr(sys, 'frozen', False):
                # If we are running as a compiled exe
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), cwd, 1)
            else:
                # If we are running as a script
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{__file__}"', cwd, 1)
            sys.exit(0)
        except Exception as e:
            logger.error(f"Failed to elevate privileges: {e}")
            return

    logger.info("Application starting (Admin)...")
    logger.info("LocalInfoReminder open-source edition starting.")
    
    
    # [MODIFIED] Initialize QApplication BEFORE config loading to enable UI dialogs
    try:
        from PyQt6.QtCore import Qt
        from ui.launcher import LauncherWindow

        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        # [NEW] Connect cleanup to quit signal
        app.aboutToQuit.connect(cleanup)
        
        # [NEW] Set Global Application Icon
        icon_path = get_resource_path("assets/LocalInfoReminder.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            logger.info(f"Global icon set from: {icon_path}")
        else:
            logger.warning(f"Global icon not found at: {icon_path}")
        
        launcher = LauncherWindow()
        launcher.game_start.connect(lambda runtime_config: start_overlay(runtime_config, launcher))
        launcher.show()
        app.processEvents()
        logger.info("Launcher shown.")
        QThread.msleep(1)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: setup_tray_icon_deferred(app))
        try:
            update_config = load_update_config()
            if bool(update_config.get("check_on_startup", True)):
                QTimer.singleShot(2500, lambda: _start_update_check(app, manual=False))
        except UpdateCheckError as exc:
            logger.info(f"Startup update check is not configured: {exc}")

        startup_preload_worker = StartupPreloadWorker()
        startup_preload_worker.finished_preload.connect(
            lambda ok, error: logger.info("Startup preload worker finished successfully.")
            if ok else logger.warning(f"Startup preload worker finished with fallback mode: {error}")
        )
        global _startup_preload_worker
        _startup_preload_worker = startup_preload_worker
        startup_preload_worker.start()

        ret = app.exec()
        cleanup() # Call cleanup if exec returns normally
        sys.exit(ret)
    except Exception as e:
        logger.error(f"Application crashed: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
