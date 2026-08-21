import ctypes
import os
import sys


def _add_dir(path):
    if hasattr(os, "add_dll_directory") and os.path.isdir(path):
        os.add_dll_directory(path)


def _preload_onnxruntime():
    if os.name != "nt":
        return

    meipass = getattr(sys, "_MEIPASS", "")
    if not meipass:
        return

    capi_dir = os.path.join(meipass, "onnxruntime", "capi")
    if not os.path.isdir(capi_dir):
        return

    _add_dir(meipass)
    _add_dir(os.path.join(meipass, "onnxruntime"))
    _add_dir(capi_dir)

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32]
    kernel32.LoadLibraryExW.restype = ctypes.c_void_p

    load_with_altered_search_path = 0x00000008
    for name in ("onnxruntime.dll", "onnxruntime_providers_shared.dll"):
        dll_path = os.path.join(capi_dir, name)
        if not os.path.isfile(dll_path):
            continue
        handle = kernel32.LoadLibraryExW(dll_path, None, load_with_altered_search_path)
        if not handle:
            raise OSError(ctypes.get_last_error(), ctypes.FormatError(ctypes.get_last_error()), dll_path)


_preload_onnxruntime()
