# -*- mode: python ; coding: utf-8 -*-

import os
import glob
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

PROJECT_ROOT = os.path.abspath(os.getcwd())

rapidocr_datas = collect_data_files('rapidocr_onnxruntime')
onnxruntime_binaries = collect_dynamic_libs('onnxruntime')
rapidocr_hiddenimports = collect_submodules('rapidocr_onnxruntime')

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'src', 'main.py')],
    pathex=[os.path.join(PROJECT_ROOT, 'src')],
    binaries=onnxruntime_binaries,
    datas=rapidocr_datas,
    hiddenimports=['jaraco.text', 'jaraco.context', 'jaraco.functools', 'pyclipper', 'six', 'shapely', 'yaml'] + rapidocr_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(PROJECT_ROOT, 'packaging', 'pyinstaller_hooks', 'preload_onnxruntime.py')],
    excludes=['torch', 'torchvision', 'torchaudio', 'matplotlib', 'scipy', 'tkinter', 'transformers', 'tensorboard', 'pytest', 'unittest', 'pdb', 'pandas', 'llvmlite', 'numba', 'PIL.AvifImagePlugin', 'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets', 'PyQt6.QtPdfQuick'],
    noarchive=False,
    module_collection_mode={
        'rapidocr_onnxruntime': 'py',
        'onnxruntime': 'py',
    },
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LocalInfoReminder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, 'assets', 'LocalInfoReminder.ico'),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LocalInfoReminder',
)

import shutil
import os
dist_path = os.path.join(PROJECT_ROOT, 'dist', 'LocalInfoReminder')
if not os.path.exists(dist_path):
    os.makedirs(dist_path)
shutil.copy(os.path.join(PROJECT_ROOT, 'config.json'), os.path.join(dist_path, 'config.json'))
shutil.copy(os.path.join(PROJECT_ROOT, 'update_config.json'), os.path.join(dist_path, 'update_config.json'))
manual_name = '使用手册.md'
manual_src = os.path.join(PROJECT_ROOT, 'docs', manual_name)
shutil.copy(manual_src, os.path.join(dist_path, manual_name))
shutil.copy(os.path.join(PROJECT_ROOT, 'LICENSE'), os.path.join(dist_path, 'LICENSE'))

dest_assets = os.path.join(dist_path, 'assets')
if os.path.exists(dest_assets):
    shutil.rmtree(dest_assets)
shutil.copytree(os.path.join(PROJECT_ROOT, 'assets'), dest_assets)

# The application only processes still PNG screenshots through OpenCV and uses
# ICO assets in Qt. Remove optional codecs and plugins that PyInstaller hooks
# collect conservatively but the application never imports or exposes.
optional_runtime_patterns = [
    os.path.join('_internal', 'cv2', 'opencv_videoio_ffmpeg*_64.dll'),
    os.path.join('_internal', 'PIL', '_avif*.pyd'),
    os.path.join('_internal', 'PyQt6', 'Qt6', 'bin', 'Qt6Pdf.dll'),
    os.path.join('_internal', 'PyQt6', 'Qt6', 'plugins', 'imageformats', 'qpdf.dll'),
    os.path.join('_internal', 'PyQt6', 'Qt6', 'plugins', 'imageformats', 'qwebp.dll'),
    os.path.join('_internal', 'PyQt6', 'Qt6', 'plugins', 'imageformats', 'qtiff.dll'),
    os.path.join('_internal', 'PyQt6', 'Qt6', 'plugins', 'imageformats', 'qgif.dll'),
    os.path.join('_internal', 'PyQt6', 'Qt6', 'plugins', 'imageformats', 'qicns.dll'),
    os.path.join('_internal', 'PyQt6', 'Qt6', 'plugins', 'imageformats', 'qtga.dll'),
    os.path.join('_internal', 'PyQt6', 'Qt6', 'plugins', 'imageformats', 'qwbmp.dll'),
    os.path.join('_internal', 'PyQt6', 'Qt6', 'plugins', 'imageformats', 'qsvg.dll'),
    os.path.join('_internal', 'PyQt6', 'Qt6', 'plugins', 'iconengines', 'qsvgicon.dll'),
]
for relative_pattern in optional_runtime_patterns:
    for candidate in glob.glob(os.path.join(dist_path, relative_pattern)):
        if os.path.isfile(candidate):
            os.remove(candidate)
