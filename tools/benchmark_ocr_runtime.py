import json
import sys
import time
from pathlib import Path

import cv2
import onnxruntime as ort
from rapidocr_onnxruntime import RapidOCR


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.config_loader import ConfigLoader
from core.vision.performance import apply_rapidocr_runtime_limits, downsample_region_for_processing
from core.vision.vision_constants import build_region_from_ratio


SAMPLE_PATHS = [
    PROJECT_ROOT / "debug_imgs" / "boss_kill_ally" / "PixPin_2026-01-15_17-36-06.png",
    PROJECT_ROOT / "debug_imgs" / "boss_reappears" / "PixPin_2026-01-15_17-34-26.png",
    PROJECT_ROOT / "debug_imgs" / "skill_enemy" / "PixPin_2026-01-15_17-36-44.png",
]

ROI_KEYS = ("boss_kill", "boss_notification", "skill_bar", "time_main", "time_prep")
THREAD_COUNTS = (1, 2, 4)


def load_config():
    config_path = PROJECT_ROOT / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    config["vision_detection"] = ConfigLoader.normalize_vision_detection(config.get("vision_detection", {}))
    return config


def format_text(result):
    if not result:
        return ""
    return "".join(str(item[1]) for item in result)[:120]


def benchmark_full_image(ocr, image_path):
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Failed to load image: {image_path}")
    height, width = image.shape[:2]
    start = time.perf_counter()
    result, _ = ocr(image)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    print(f"full_image | shape={width}x{height} | elapsed_ms={elapsed_ms:.1f} | text={format_text(result)}")


def benchmark_rois(ocr, image_path, config):
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Failed to load image: {image_path}")
    height, width = image.shape[:2]
    monitor = {"left": 0, "top": 0, "width": width, "height": height}
    regions = config["vision_detection"]["regions"]

    for key in ROI_KEYS:
        ratio = regions[key]
        region = build_region_from_ratio(monitor, ratio)
        x1, y1 = region["left"], region["top"]
        x2, y2 = x1 + region["width"], y1 + region["height"]
        crop = image[y1:y2, x1:x2]
        crop = downsample_region_for_processing(crop, ratio, config)
        if crop.size == 0:
            print(f"{key} | crop=0x0 | elapsed_ms=0.0 | text=")
            continue
        if crop.ndim == 3 and crop.shape[2] == 4:
            crop = cv2.cvtColor(crop, cv2.COLOR_BGRA2BGR)
        start = time.perf_counter()
        result, _ = ocr(crop)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        print(
            f"{key} | crop={crop.shape[1]}x{crop.shape[0]} | elapsed_ms={elapsed_ms:.1f} | text={format_text(result)}"
        )


def main():
    config = load_config()

    print(f"python={sys.version.split()[0]}")
    print(f"onnxruntime={ort.__version__}")
    print(f"providers={ort.get_available_providers()}")
    print(f"project_root={PROJECT_ROOT}")
    print()

    for image_path in SAMPLE_PATHS:
        if not image_path.exists():
            print(f"missing_sample={image_path}")
            continue

        print(f"sample={image_path}")
        for threads in THREAD_COUNTS:
            apply_rapidocr_runtime_limits({"ocr_runtime_max_threads": threads})
            ocr = RapidOCR()
            print(f"threads={threads}")
            benchmark_full_image(ocr, image_path)
            benchmark_rois(ocr, image_path, config)
            print()
        print("-" * 80)


if __name__ == "__main__":
    main()
