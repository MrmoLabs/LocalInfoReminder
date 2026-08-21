import os
import sys
import ctypes
import importlib.util
import logging

import cv2


REFERENCE_SCREEN_WIDTH = 1920
REFERENCE_SCREEN_HEIGHT = 1080
DEFAULT_OCR_MAX_THREADS = 4

_LAST_APPLIED_THREAD_LIMIT = None
_DLL_DIRECTORY_HANDLES = []
_PRELOADED_ORT_DLLS = {}
_logger = logging.getLogger("LocalInfoReminder")


def _safe_int(value, default):
    try:
        return int(value)
    except Exception:
        return int(default)


def ocr_thread_limit_from_config(config):
    limit = _safe_int((config or {}).get("ocr_runtime_max_threads", DEFAULT_OCR_MAX_THREADS), DEFAULT_OCR_MAX_THREADS)
    return max(1, limit)


def reference_screen_size_from_config(config):
    cfg = config or {}
    width = max(640, _safe_int(cfg.get("ocr_reference_screen_width", REFERENCE_SCREEN_WIDTH), REFERENCE_SCREEN_WIDTH))
    height = max(360, _safe_int(cfg.get("ocr_reference_screen_height", REFERENCE_SCREEN_HEIGHT), REFERENCE_SCREEN_HEIGHT))
    return width, height


def downsample_region_for_processing(image, ratio_region, config=None):
    if image is None or getattr(image, "size", 0) == 0:
        return image

    cfg = config or {}
    if not cfg.get("ocr_downsample_to_reference", True):
        return image

    if not isinstance(ratio_region, dict):
        return image

    reference_width, reference_height = reference_screen_size_from_config(cfg)
    target_width = max(1, int(round(reference_width * float(ratio_region.get("width", 1.0)))))
    target_height = max(1, int(round(reference_height * float(ratio_region.get("height", 1.0)))))

    height, width = image.shape[:2]
    if width <= target_width and height <= target_height:
        return image

    return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_AREA)


def apply_rapidocr_runtime_limits(config=None):
    global _LAST_APPLIED_THREAD_LIMIT

    max_threads = ocr_thread_limit_from_config(config)
    if _LAST_APPLIED_THREAD_LIMIT == max_threads:
        return max_threads

    thread_value = str(max_threads)
    for env_key in (
        "OMP_NUM_THREADS",
        "OMP_THREAD_LIMIT",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[env_key] = thread_value

    try:
        from rapidocr_onnxruntime.utils import infer_engine

        def patched_init_sess_opts(config, _infer_engine=infer_engine, _max_threads=max_threads):
            sess_opt = _infer_engine.SessionOptions()
            sess_opt.log_severity_level = 4
            sess_opt.enable_cpu_mem_arena = False
            sess_opt.graph_optimization_level = _infer_engine.GraphOptimizationLevel.ORT_ENABLE_ALL

            cpu_nums = os.cpu_count() or _max_threads
            intra_threads = int(config.get("intra_op_num_threads", _max_threads))
            inter_threads = int(config.get("inter_op_num_threads", 1))

            if 1 <= intra_threads <= cpu_nums:
                sess_opt.intra_op_num_threads = intra_threads
            if 1 <= inter_threads <= cpu_nums:
                sess_opt.inter_op_num_threads = inter_threads

            return sess_opt

        infer_engine.OrtInferSession._init_sess_opts = staticmethod(patched_init_sess_opts)
    except Exception:
        try:
            import rapidocr_onnxruntime.utils as rapid_utils

            def patched_init(self, config, _rapid_utils=rapid_utils, _max_threads=max_threads):
                sess_opt = _rapid_utils.SessionOptions()
                sess_opt.log_severity_level = 4
                sess_opt.enable_cpu_mem_arena = False
                sess_opt.graph_optimization_level = _rapid_utils.GraphOptimizationLevel.ORT_ENABLE_ALL
                sess_opt.intra_op_num_threads = _max_threads
                sess_opt.inter_op_num_threads = 1

                cpu_ep = "CPUExecutionProvider"
                cpu_provider_options = {
                    "arena_extend_strategy": "kSameAsRequested",
                }

                cuda_ep = "CUDAExecutionProvider"
                cuda_provider_options = {
                    "device_id": 0,
                    "arena_extend_strategy": "kNextPowerOfTwo",
                    "cudnn_conv_algo_search": "EXHAUSTIVE",
                    "do_copy_in_default_stream": True,
                }

                providers = []
                if config["use_cuda"] and _rapid_utils.get_device() == "GPU" and cuda_ep in _rapid_utils.get_available_providers():
                    providers = [(cuda_ep, cuda_provider_options)]
                providers.append((cpu_ep, cpu_provider_options))

                self._verify_model(config["model_path"])
                self.session = _rapid_utils.InferenceSession(
                    config["model_path"],
                    sess_options=sess_opt,
                    providers=providers,
                )

                if config["use_cuda"] and cuda_ep not in self.session.get_providers():
                    _rapid_utils.warnings.warn(
                        f"{cuda_ep} is not avaiable for current env, the inference part is automatically shifted to be executed under {cpu_ep}.\n"
                        "Please ensure the installed onnxruntime-gpu version matches your cuda and cudnn version, "
                        "you can check their relations from the offical web site: "
                        "https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html",
                        RuntimeWarning,
                    )

            rapid_utils.OrtInferSession.__init__ = patched_init
        except Exception:
            pass

    _LAST_APPLIED_THREAD_LIMIT = max_threads
    return max_threads


def ensure_onnxruntime_dll_search_paths():
    if not hasattr(os, "add_dll_directory"):
        return

    candidate_dirs = []

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        internal_dir = os.path.join(exe_dir, "_internal")
        candidate_dirs.extend(
            [
                os.path.join(internal_dir, "PyQt6", "Qt6", "bin"),
                internal_dir,
                os.path.join(internal_dir, "onnxruntime"),
                os.path.join(internal_dir, "onnxruntime", "capi"),
            ]
        )

    try:
        import onnxruntime

        ort_dir = os.path.dirname(getattr(onnxruntime, "__file__", "") or "")
        if ort_dir:
            candidate_dirs.extend(
                [
                    os.path.join(ort_dir, "capi"),
                    ort_dir,
                ]
            )
    except Exception:
        pass

    seen = set()
    for path in candidate_dirs:
        normalized = os.path.normpath(path)
        if not normalized or normalized in seen or not os.path.isdir(normalized):
            continue
        seen.add(normalized)
        try:
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(normalized))
        except Exception:
            pass


def _onnxruntime_capi_dir():
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "_internal", "onnxruntime", "capi")

    spec = importlib.util.find_spec("onnxruntime")
    if spec and spec.submodule_search_locations:
        package_dir = next(iter(spec.submodule_search_locations), "")
        if package_dir:
            return os.path.join(package_dir, "capi")
    return ""


def preload_onnxruntime_native_binaries():
    if os.name != "nt":
        return
    if not getattr(sys, "frozen", False):
        return

    capi_dir = _onnxruntime_capi_dir()
    if not capi_dir or not os.path.isdir(capi_dir):
        return

    # On frozen Windows builds, Qt's DLL directory can be registered before OCR starts.
    # Force ORT to resolve its own adjacent DLLs with the DLL's directory as the search base.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32]
    kernel32.LoadLibraryExW.restype = ctypes.c_void_p

    load_with_altered_search_path = 0x00000008
    for name in ("onnxruntime.dll", "onnxruntime_providers_shared.dll"):
        dll_path = os.path.join(capi_dir, name)
        if not os.path.isfile(dll_path) or dll_path in _PRELOADED_ORT_DLLS:
            continue
        handle = kernel32.LoadLibraryExW(dll_path, None, load_with_altered_search_path)
        if not handle:
            raise OSError(ctypes.get_last_error(), ctypes.FormatError(ctypes.get_last_error()), dll_path)
        _PRELOADED_ORT_DLLS[dll_path] = handle
