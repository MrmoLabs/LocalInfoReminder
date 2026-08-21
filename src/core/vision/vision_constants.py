import numpy as np


class RegionRatios:
    # Relative to 1920x1080
    SKILL_BAR = {"left": 0.3646, "top": 0.2083, "width": 0.2969, "height": 0.0417}
    BOSS_NOTIFICATION = {"left": 0.368, "top": 0.207, "width": 0.253, "height": 0.035}
    BOSS_KILL = {"left": 0.368, "top": 0.207, "width": 0.253, "height": 0.035}
    MAP_LOWER = {"left": 0.1042, "top": 0.2685, "width": 0.0078, "height": 0.0213}
    MAP_UPPER = {"left": 0.0677, "top": 0.0509, "width": 0.0104, "height": 0.0185}
    TIME_MAIN = {"left": 0.46875, "top": 0.02315, "width": 0.05729, "height": 0.04630}
    TIME_PREP = {"left": 0.47656, "top": 0.14352, "width": 0.04896, "height": 0.04630}


class ColorThresholds:
    # HSV Ranges as numpy arrays
    RED_1_LOWER = np.array([0, 70, 50])
    RED_1_UPPER = np.array([10, 255, 255])

    RED_2_LOWER = np.array([170, 70, 50])
    RED_2_UPPER = np.array([180, 255, 255])

    BLUE_LOWER = np.array([100, 70, 50])
    BLUE_UPPER = np.array([130, 255, 255])


class DetectionConfig:
    SKILL_TRIGGER_RATIO = 0.01
    SKILL_COLOR_ADVANTAGE_RATIO = 0.02
    BOSS_FACTION_RATIO = 0.03
    MAP_DOT_PIXEL_THRESHOLD = 60


def default_detection_regions():
    return {
        "skill_bar": dict(RegionRatios.SKILL_BAR),
        "boss_notification": dict(RegionRatios.BOSS_NOTIFICATION),
        "boss_kill": dict(RegionRatios.BOSS_KILL),
        "time_main": dict(RegionRatios.TIME_MAIN),
        "time_prep": dict(RegionRatios.TIME_PREP),
    }


def default_detection_thresholds():
    return {
        "skill_trigger_ratio": DetectionConfig.SKILL_TRIGGER_RATIO,
        "skill_color_advantage_ratio": DetectionConfig.SKILL_COLOR_ADVANTAGE_RATIO,
        "boss_faction_ratio": DetectionConfig.BOSS_FACTION_RATIO,
    }


def build_region_from_ratio(monitor, ratio_region):
    # Ratios are authored against a 1920x1080 layout. On ultrawide displays,
    # keep X-axis scaling anchored to a centered 16:9 reference canvas so the
    # OCR region does not stretch with the extra side space.
    reference_width = int(round(monitor["height"] * 1920 / 1080))
    horizontal_padding = max(0, int(round((monitor["width"] - reference_width) / 2)))

    return {
        "left": int(reference_width * ratio_region["left"]) + monitor["left"] + horizontal_padding,
        "top": int(monitor["height"] * ratio_region["top"]) + monitor["top"],
        "width": int(reference_width * ratio_region["width"]),
        "height": int(monitor["height"] * ratio_region["height"]),
    }


def crop_bgra_region(frame_bgra, frame_region, target_region):
    if frame_bgra is None or frame_region is None or target_region is None:
        return np.zeros((0, 0, 4), dtype=np.uint8)

    x1 = max(0, int(target_region["left"]) - int(frame_region["left"]))
    y1 = max(0, int(target_region["top"]) - int(frame_region["top"]))
    x2 = min(int(frame_region["width"]), x1 + int(target_region["width"]))
    y2 = min(int(frame_region["height"]), y1 + int(target_region["height"]))

    if x2 <= x1 or y2 <= y1:
        return np.zeros((0, 0, 4), dtype=np.uint8)

    return np.ascontiguousarray(frame_bgra[y1:y2, x1:x2])
