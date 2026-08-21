import numpy as np


DEFAULT_COLOR_PROFILES = {
    "skill_red": {
        "sample_color": [255, 60, 60],
        "tolerance": 110.0,
        "min_ratio": 0.01,
    },
    "skill_blue": {
        "sample_color": [70, 130, 255],
        "tolerance": 110.0,
        "min_ratio": 0.01,
    },
    "boss_red": {
        "sample_color": [255, 60, 60],
        "tolerance": 110.0,
        "min_ratio": 0.03,
    },
    "boss_blue": {
        "sample_color": [70, 130, 255],
        "tolerance": 110.0,
        "min_ratio": 0.03,
    },
}


def default_color_profiles():
    return {key: dict(value) for key, value in DEFAULT_COLOR_PROFILES.items()}


def normalize_color_profile(profile, default_profile):
    raw = dict(default_profile)
    value = dict(profile or {})
    sample = value.get("sample_color", raw.get("sample_color", [255, 255, 255]))
    if isinstance(sample, (list, tuple)) and len(sample) >= 3:
        normalized_sample = []
        for idx, fallback in enumerate(raw.get("sample_color", [255, 255, 255])):
            try:
                channel = int(round(float(sample[idx])))
            except Exception:
                channel = int(fallback)
            normalized_sample.append(max(0, min(255, channel)))
        raw["sample_color"] = normalized_sample
    try:
        raw["tolerance"] = float(value.get("tolerance", raw.get("tolerance", 110.0)))
    except Exception:
        raw["tolerance"] = float(raw.get("tolerance", 110.0))
    raw["tolerance"] = max(0.0, min(441.0, raw["tolerance"]))
    try:
        raw["min_ratio"] = float(value.get("min_ratio", raw.get("min_ratio", 0.01)))
    except Exception:
        raw["min_ratio"] = float(raw.get("min_ratio", 0.01))
    raw["min_ratio"] = max(0.0, min(1.0, raw["min_ratio"]))
    return raw


def match_ratio(img_rgb, profile):
    if img_rgb is None or img_rgb.size == 0:
        return 0.0, None
    sample = np.array(profile.get("sample_color", [255, 255, 255]), dtype=np.float32)
    tolerance = float(profile.get("tolerance", 110.0))
    pixels = img_rgb.astype(np.float32)
    distance = np.linalg.norm(pixels - sample.reshape((1, 1, 3)), axis=2)
    mask = distance <= tolerance
    ratio = float(mask.mean()) if mask.size else 0.0
    return ratio, mask
