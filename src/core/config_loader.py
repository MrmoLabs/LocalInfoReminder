import json
import os
import sys
import tempfile

from core.vision.color_profile import default_color_profiles, normalize_color_profile
from core.vision.vision_constants import default_detection_regions, default_detection_thresholds


class ConfigLoader:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance

    @classmethod
    def load_config(cls, config_path="config.json"):
        if not os.path.isabs(config_path):
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
                if not os.path.exists(os.path.join(base_dir, "config.json")) and os.path.exists(
                    os.path.join(base_dir, "_internal", "config.json")
                ):
                    base_dir = os.path.join(base_dir, "_internal")
            else:
                base_dir = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )

            config_path = os.path.join(base_dir, config_path)
            print("=" * 60)
            print(f"[ConfigLoader] Target Config Path: {config_path}")
            print(f"[ConfigLoader] Path Exists: {os.path.exists(config_path)}")
            try:
                print(f"[ConfigLoader] Abs Path: {os.path.abspath(config_path)}")
            except Exception:
                pass
            print("=" * 60)

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cls._config = cls._migrate_target_event_aliases(json.load(f))

            if "command_skills" not in cls._config and "enemy_skills" in cls._config:
                cls._config["command_skills"] = cls._config.pop("enemy_skills")
            if "enable_command_skills" not in cls._config and "enable_enemy_skills" in cls._config:
                cls._config["enable_command_skills"] = cls._config.pop("enable_enemy_skills")
            if "ocr_command_skills" not in cls._config and "ocr_enemy_skills" in cls._config:
                cls._config["ocr_command_skills"] = cls._config.pop("ocr_enemy_skills")

            if "session_state" not in cls._config:
                cls._config["session_state"] = {}
            if "miracle_skills" not in cls._config:
                cls._config["miracle_skills"] = []
            if "command_skills" not in cls._config:
                cls._config["command_skills"] = []

            for event in cls._config.get("global_events", []):
                if "is_enabled" not in event:
                    event["is_enabled"] = True
                if "is_muted" not in event:
                    event["is_muted"] = False
                sound = event.get("sound", "")
                if sound and "/" not in sound and "\\" not in sound:
                    event["sound"] = f"global_events/{sound}"

            for cls_tmpl in cls._config.get("classes_template", []):
                if "is_enabled" not in cls_tmpl:
                    cls_tmpl["is_enabled"] = True

            for skill in cls._config.get("command_skills", []):
                if "is_enabled" not in skill:
                    skill["is_enabled"] = True
                if "is_muted" not in skill:
                    skill["is_muted"] = False
                if "cd_threshold" not in skill:
                    skill["cd_threshold"] = 0
                if "cd_flash" not in skill:
                    skill["cd_flash"] = False
                if "cd_sound" not in skill:
                    skill["cd_sound"] = ""
                sound = skill.get("sound", "")
                if sound.startswith("enemy_skills/"):
                    skill["sound"] = sound.replace("enemy_skills/", "command_skills/", 1)
                elif sound and "/" not in sound and "\\" not in sound:
                    skill["sound"] = f"command_skills/{sound}"
                cd_sound = skill.get("cd_sound", "")
                if cd_sound and "/" not in cd_sound and "\\" not in cd_sound:
                    skill["cd_sound"] = f"command_skills/{cd_sound}"

            for m_skill in cls._config.get("miracle_skills", []):
                if "is_enabled" not in m_skill:
                    m_skill["is_enabled"] = True
                if "is_muted" not in m_skill:
                    m_skill["is_muted"] = False
                sound = m_skill.get("sound", "")
                if sound and "/" not in sound and "\\" not in sound:
                    m_skill["sound"] = f"miracle_skills/{sound}"

            if "boss_detection" not in cls._config:
                cls._config["boss_detection"] = {}
            legacy_boss_durations = cls._config.pop("boss_buff_durations", {})

            cls._config["boss_detection"] = cls.normalize_boss_detection(
                cls._config["boss_detection"],
                legacy_boss_durations,
            )
            cls._config["vision_detection"] = cls.normalize_vision_detection(
                cls._config.get("vision_detection", {})
            )

            if "ocr_enabled" not in cls._config:
                cls._config["ocr_enabled"] = True

            feature_defaults = {
                "enable_time_display": True,
                "enable_classes": True,
                "enable_command_skills": True,
                "enable_miracle_skills": True,
                "enable_global_events": True,
                "enable_boss_settings": True,
                "ocr_time_sync": True,
                "ocr_command_skills": True,
                "ocr_boss_detection": True,
                "miracle_flash_threshold": 3.0,
                "ocr_time_sync_interval_seconds": 60.0,
                "screen_monitor_interval_seconds": 0.7,
                "ocr_downsample_to_reference": True,
                "ocr_reference_screen_width": 1920,
                "ocr_reference_screen_height": 1080,
                "ocr_runtime_max_threads": 4,
            }
            for key, value in feature_defaults.items():
                if key not in cls._config:
                    cls._config[key] = value

            cls._config["ocr_time_sync_interval_seconds"] = cls._safe_float(
                cls._config.get("ocr_time_sync_interval_seconds", 60.0),
                60.0,
            )
            cls._config["screen_monitor_interval_seconds"] = cls._safe_float(
                cls._config.get("screen_monitor_interval_seconds", 0.7),
                0.7,
            )
            if cls._config["ocr_time_sync_interval_seconds"] < 5.0:
                cls._config["ocr_time_sync_interval_seconds"] = 5.0
            if cls._config["screen_monitor_interval_seconds"] < 0.1:
                cls._config["screen_monitor_interval_seconds"] = 0.1
            cls._config["ocr_reference_screen_width"] = max(
                640,
                cls._safe_int(cls._config.get("ocr_reference_screen_width", 1920), 1920),
            )
            cls._config["ocr_reference_screen_height"] = max(
                360,
                cls._safe_int(cls._config.get("ocr_reference_screen_height", 1080), 1080),
            )
            cls._config["ocr_runtime_max_threads"] = max(
                1,
                cls._safe_int(cls._config.get("ocr_runtime_max_threads", 4), 4),
            )

            return cls._config
        except FileNotFoundError:
            print(f"Error: Config file not found at {config_path}")
            return None
        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON from {config_path}")
            return None

    @classmethod
    def save_config(cls, config_data, config_path="config.json"):
        target_path = config_path
        if not os.path.isabs(config_path) and config_path == "config.json":
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
                if not os.path.exists(os.path.join(base_dir, "config.json")) and os.path.exists(
                    os.path.join(base_dir, "_internal", "config.json")
                ):
                    base_dir = os.path.join(base_dir, "_internal")
            else:
                base_dir = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            target_path = os.path.join(base_dir, "config.json")

        temp_path = None
        try:
            data_to_save = dict(config_data or {})
            data_to_save.pop("boss_buff_durations", None)
            data_to_save = cls._export_target_event_aliases(data_to_save)

            target_dir = os.path.dirname(os.path.abspath(target_path))
            os.makedirs(target_dir, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(
                prefix=f".{os.path.basename(target_path)}.",
                suffix=".tmp",
                dir=target_dir,
            )
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, target_path)
            temp_path = None

            # Keep the singleton cache in the normalized runtime schema rather
            # than the public/exported JSON schema written to disk.
            cls.load_config(target_path)
            return True
        except Exception as e:
            print(f"Error saving config to {target_path}: {e}")
            return False
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    @classmethod
    def _migrate_target_event_aliases(cls, config_data):
        data = dict(config_data or {})

        if "enable_target_event_settings" in data and "enable_boss_settings" not in data:
            data["enable_boss_settings"] = data.get("enable_target_event_settings")
        if "ocr_target_event_detection" in data and "ocr_boss_detection" not in data:
            data["ocr_boss_detection"] = data.get("ocr_target_event_detection")
        if "target_event_detection" in data and "boss_detection" not in data:
            data["boss_detection"] = data.get("target_event_detection")

        if "primary_entries" in data and "command_skills" not in data:
            data["command_skills"] = data.get("primary_entries")
        if "extended_entries" in data and "miracle_skills" not in data:
            data["miracle_skills"] = data.get("extended_entries")
        if "enable_primary_entries" in data and "enable_command_skills" not in data:
            data["enable_command_skills"] = data.get("enable_primary_entries")
        if "enable_extended_entries" in data and "enable_miracle_skills" not in data:
            data["enable_miracle_skills"] = data.get("enable_extended_entries")
        if "ocr_primary_entries" in data and "ocr_command_skills" not in data:
            data["ocr_command_skills"] = data.get("ocr_primary_entries")

        vision_detection = dict(data.get("vision_detection", {}))
        regions = dict(vision_detection.get("regions", {}))
        if "target_event_notification" in regions and "boss_notification" not in regions:
            regions["boss_notification"] = regions.get("target_event_notification")
        if "target_event_result" in regions and "boss_kill" not in regions:
            regions["boss_kill"] = regions.get("target_event_result")
        if regions:
            vision_detection["regions"] = regions

        thresholds = dict(vision_detection.get("thresholds", {}))
        if "target_event_color_ratio" in thresholds and "boss_faction_ratio" not in thresholds:
            thresholds["boss_faction_ratio"] = thresholds.get("target_event_color_ratio")
        if thresholds:
            vision_detection["thresholds"] = thresholds

        color_profiles = dict(vision_detection.get("color_profiles", {}))
        if "target_event_color_a" in color_profiles and "boss_red" not in color_profiles:
            color_profiles["boss_red"] = color_profiles.get("target_event_color_a")
        if "target_event_color_b" in color_profiles and "boss_blue" not in color_profiles:
            color_profiles["boss_blue"] = color_profiles.get("target_event_color_b")
        if color_profiles:
            vision_detection["color_profiles"] = color_profiles

        if vision_detection:
            data["vision_detection"] = vision_detection

        if "boss_detection" in data:
            data["boss_detection"] = cls._migrate_target_event_targets(data.get("boss_detection", {}))

        return data

    @classmethod
    def _migrate_target_event_targets(cls, detection_data):
        detection = dict(detection_data or {})
        targets = []
        for target in detection.get("targets", []) or []:
            item = dict(target or {})
            if "result_window_seconds" in item and "kill_window_seconds" not in item:
                item["kill_window_seconds"] = item.get("result_window_seconds")
            if "result_keywords" in item and "kill_keywords" not in item:
                item["kill_keywords"] = item.get("result_keywords")
            if "result_sound" in item and "kill_sound" not in item:
                item["kill_sound"] = item.get("result_sound")
            targets.append(item)
        if targets:
            detection["targets"] = targets
        return detection

    @classmethod
    def _export_target_event_aliases(cls, config_data):
        data = dict(config_data or {})

        if "enable_boss_settings" in data:
            data["enable_target_event_settings"] = data.pop("enable_boss_settings")
        if "ocr_boss_detection" in data:
            data["ocr_target_event_detection"] = data.pop("ocr_boss_detection")
        if "boss_detection" in data:
            data["target_event_detection"] = cls._export_target_event_targets(data.pop("boss_detection"))

        if "enable_command_skills" in data:
            data["enable_primary_entries"] = data.pop("enable_command_skills")
        if "enable_miracle_skills" in data:
            data["enable_extended_entries"] = data.pop("enable_miracle_skills")
        if "ocr_command_skills" in data:
            data["ocr_primary_entries"] = data.pop("ocr_command_skills")
        if "command_skills" in data:
            data["primary_entries"] = data.pop("command_skills")
        if "miracle_skills" in data:
            data["extended_entries"] = data.pop("miracle_skills")

        vision_detection = dict(data.get("vision_detection", {}))
        regions = dict(vision_detection.get("regions", {}))
        if "boss_notification" in regions:
            regions["target_event_notification"] = regions.pop("boss_notification")
        if "boss_kill" in regions:
            regions["target_event_result"] = regions.pop("boss_kill")
        if regions:
            vision_detection["regions"] = regions

        thresholds = dict(vision_detection.get("thresholds", {}))
        if "boss_faction_ratio" in thresholds:
            thresholds["target_event_color_ratio"] = thresholds.pop("boss_faction_ratio")
        if thresholds:
            vision_detection["thresholds"] = thresholds

        color_profiles = dict(vision_detection.get("color_profiles", {}))
        if "boss_red" in color_profiles:
            color_profiles["target_event_color_a"] = color_profiles.pop("boss_red")
        if "boss_blue" in color_profiles:
            color_profiles["target_event_color_b"] = color_profiles.pop("boss_blue")
        if color_profiles:
            vision_detection["color_profiles"] = color_profiles

        if vision_detection:
            data["vision_detection"] = vision_detection

        return data

    @classmethod
    def _export_target_event_targets(cls, detection_data):
        detection = dict(detection_data or {})
        targets = []
        for target in detection.get("targets", []) or []:
            item = dict(target or {})
            if "kill_window_seconds" in item:
                item["result_window_seconds"] = item.pop("kill_window_seconds")
            if "kill_keywords" in item:
                item["result_keywords"] = item.pop("kill_keywords")
            if "kill_sound" in item:
                item["result_sound"] = item.pop("kill_sound")
            targets.append(item)
        detection["targets"] = targets
        return detection

    @classmethod
    def get_config(cls):
        if cls._config is None:
            return cls.load_config()
        return cls._config

    @staticmethod
    def default_boss_time_windows():
        return [
            {"start": "27:10", "end": "24:30"},
            {"start": "17:20", "end": "14:30"},
        ]

    @classmethod
    def default_boss_targets(cls):
        shared_windows = cls.default_boss_time_windows()
        return [
            {
                "id": "zhang_bao",
                "display_name": "\u76ee\u6807A",
                "match_names": ["Zhang Bao", "\u5f20\u8c79"],
                "ocr_keywords": ["\u76ee\u6807A"],
                "time_windows": [dict(window) for window in shared_windows],
                "kill_window_seconds": 180,
                "kill_keywords": ["\u5b8c\u6210", "\u83b7\u5f97"],
                "faction_match": "distinguish",
                "ignore_keywords": ["\u5373\u5c06", "\u51fa\u73b0", "\u63d0\u793a", "\u6570\u636e"],
                "spawn_sound": "dragon_spawn.mp3",
                "kill_sound": "",
                "buff_duration": 120,
            },
            {
                "id": "zhuye_gule",
                "display_name": "\u76ee\u6807B",
                "match_names": ["Zhuye Gule", "\u6731\u90aa\u9aa8\u52d2", "\u6731\u90aa"],
                "ocr_keywords": ["\u76ee\u6807B"],
                "time_windows": [dict(window) for window in shared_windows],
                "kill_window_seconds": 180,
                "kill_keywords": ["\u5b8c\u6210", "\u83b7\u5f97"],
                "faction_match": "distinguish",
                "ignore_keywords": ["\u5373\u5c06", "\u51fa\u73b0", "\u63d0\u793a", "\u6570\u636e"],
                "spawn_sound": "dragon_spawn.mp3",
                "kill_sound": "",
                "buff_duration": 300,
            },
        ]

    @classmethod
    def normalize_boss_detection(cls, boss_detection=None, boss_buff_durations=None):
        raw_detection = dict(boss_detection or {})
        durations = boss_buff_durations or {}

        legacy_time_windows = raw_detection.get("notification_windows", [])
        shared_windows = cls._normalize_time_windows(legacy_time_windows)
        if not shared_windows:
            shared_windows = cls.default_boss_time_windows()

        legacy_enemy = cls._normalize_string_list(
            raw_detection.get("kill_keywords", {}).get("enemy", ["完成"])
        )
        legacy_ally = cls._normalize_string_list(
            raw_detection.get("kill_keywords", {}).get("ally", ["获得", "完成"])
        )
        shared_kill_keywords = []
        for keyword in legacy_enemy + legacy_ally:
            if keyword not in shared_kill_keywords:
                shared_kill_keywords.append(keyword)

        raw_targets = raw_detection.get("targets")
        normalized_targets = []
        if isinstance(raw_targets, list) and raw_targets:
            for index, target in enumerate(raw_targets):
                normalized_targets.append(
                    cls._normalize_single_boss_target(
                        target,
                        index=index,
                        shared_windows=shared_windows,
                        shared_kill_keywords=shared_kill_keywords,
                        shared_ignore_keywords=raw_detection.get("ignore_keywords", []),
                        shared_kill_window=raw_detection.get("kill_check_timeout_seconds", 180),
                    )
                )
        else:
            spawn_keywords = raw_detection.get("spawn_keywords", {})
            for index, default_target in enumerate(cls.default_boss_targets()):
                target = dict(default_target)
                target_id = target["id"]
                target["ocr_keywords"] = cls._normalize_string_list(
                    spawn_keywords.get(target_id, target.get("ocr_keywords", []))
                )
                target["time_windows"] = [dict(window) for window in shared_windows]
                target["kill_window_seconds"] = cls._safe_int(
                    raw_detection.get("kill_check_timeout_seconds", target.get("kill_window_seconds", 180)),
                    target.get("kill_window_seconds", 180),
                )
                target["kill_keywords"] = list(shared_kill_keywords or target.get("kill_keywords", []))
                target["ignore_keywords"] = cls._normalize_string_list(
                    raw_detection.get("ignore_keywords", target.get("ignore_keywords", []))
                )
                target["faction_match"] = "distinguish"
                target["buff_duration"] = cls._safe_int(
                    durations.get(target_id, target.get("buff_duration", 0)),
                    target.get("buff_duration", 0),
                )
                normalized_targets.append(
                    cls._normalize_single_boss_target(
                        target,
                        index=index,
                        shared_windows=shared_windows,
                        shared_kill_keywords=shared_kill_keywords,
                        shared_ignore_keywords=raw_detection.get("ignore_keywords", []),
                        shared_kill_window=raw_detection.get("kill_check_timeout_seconds", 180),
                    )
                )

        return {"targets": normalized_targets}

    @classmethod
    def _normalize_single_boss_target(
        cls,
        target,
        index=0,
        shared_windows=None,
        shared_kill_keywords=None,
        shared_ignore_keywords=None,
        shared_kill_window=180,
    ):
        defaults = cls.default_boss_targets()
        default_target = defaults[index] if index < len(defaults) else {}
        target_data = dict(target or {})

        target_id = str(
            target_data.get("id") or default_target.get("id") or f"target_{index + 1}"
        ).strip()
        display_name = str(
            target_data.get("display_name")
            or target_data.get("name")
            or default_target.get("display_name")
            or target_id
        ).strip()

        ocr_keywords = cls._normalize_string_list(
            target_data.get("ocr_keywords") or target_data.get("spawn_keywords") or default_target.get("ocr_keywords", [])
        )

        kill_keywords = target_data.get("kill_keywords")
        if isinstance(kill_keywords, dict):
            merged_keywords = []
            for key in ("enemy", "ally"):
                for value in cls._normalize_string_list(kill_keywords.get(key, [])):
                    if value not in merged_keywords:
                        merged_keywords.append(value)
            kill_keywords = merged_keywords
        kill_keywords = cls._normalize_string_list(
            kill_keywords or target_data.get("completion_keywords") or shared_kill_keywords or default_target.get("kill_keywords", [])
        )

        faction_match = str(target_data.get("faction_match") or "distinguish").strip().lower()
        if faction_match not in {"distinguish", "ignore"}:
            faction_match = "distinguish"

        return {
            "id": target_id,
            "display_name": display_name or target_id,
            "match_names": cls._normalize_string_list(
                target_data.get("match_names") or default_target.get("match_names", [])
            ),
            "ocr_keywords": ocr_keywords,
            "time_windows": cls._normalize_time_windows(
                target_data.get("time_windows") or target_data.get("time_window") or shared_windows or default_target.get("time_windows", [])
            ),
            "kill_window_seconds": cls._safe_int(
                target_data.get("kill_window_seconds"),
                shared_kill_window if shared_kill_window is not None else default_target.get("kill_window_seconds", 180),
            ),
            "kill_keywords": kill_keywords,
            "faction_match": faction_match,
            "ignore_keywords": cls._normalize_string_list(
                target_data.get("ignore_keywords") or shared_ignore_keywords or default_target.get("ignore_keywords", [])
            ),
            "spawn_sound": str(target_data.get("spawn_sound") or default_target.get("spawn_sound", "")).strip(),
            "kill_sound": str(target_data.get("kill_sound") or default_target.get("kill_sound", "")).strip(),
            "buff_duration": cls._safe_int(
                target_data.get("buff_duration"),
                default_target.get("buff_duration", 0),
            ),
        }

    @staticmethod
    def _normalize_time_windows(values):
        if isinstance(values, dict):
            values = [values]
        elif isinstance(values, str):
            values = [value for value in values.split(",") if value.strip()]

        normalized = []
        for value in values or []:
            if isinstance(value, dict):
                start_text = str(value.get("start", "")).strip() or "00:00"
                end_text = str(value.get("end", "")).strip() or "00:00"
            else:
                text = str(value or "").strip()
                if not text:
                    continue
                if "-" in text:
                    start_text, end_text = text.split("-", 1)
                else:
                    start_text, end_text = "00:00", "00:00"
                start_text = start_text.strip() or "00:00"
                end_text = end_text.strip() or "00:00"
            item = {"start": start_text, "end": end_text}
            if item not in normalized:
                normalized.append(item)
        return normalized

    @staticmethod
    def _normalize_string_list(values):
        if isinstance(values, str):
            values = [values]
        normalized = []
        for value in values or []:
            text = str(value).strip()
            if text and text not in normalized:
                normalized.append(text)
        return normalized

    @staticmethod
    def _safe_int(value, default):
        try:
            return int(value)
        except Exception:
            return int(default)

    @staticmethod
    def targets_to_boss_durations(targets):
        durations = {}
        for target in targets or []:
            target_id = str(target.get("id", "")).strip()
            if not target_id:
                continue
            try:
                durations[target_id] = int(target.get("buff_duration", 0))
            except Exception:
                durations[target_id] = 0
        return durations

    @classmethod
    def normalize_vision_detection(cls, vision_detection=None):
        raw_detection = dict(vision_detection or {})
        default_regions = default_detection_regions()
        raw_regions = raw_detection.get("regions", {})
        normalized_regions = {}
        for key, default_region in default_regions.items():
            normalized_regions[key] = cls._normalize_region_ratio(
                raw_regions.get(key, default_region),
                default_region,
            )

        default_thresholds = default_detection_thresholds()
        raw_thresholds = raw_detection.get("thresholds", {})
        normalized_thresholds = {}
        for key, default_value in default_thresholds.items():
            normalized_thresholds[key] = cls._safe_float(
                raw_thresholds.get(key, default_value),
                default_value,
            )

        default_profiles = default_color_profiles()
        raw_profiles = raw_detection.get("color_profiles", {})
        normalized_profiles = {}
        for key, default_profile in default_profiles.items():
            profile_value = raw_profiles.get(key, default_profile)
            normalized_profiles[key] = normalize_color_profile(profile_value, default_profile)

        raw_detection["regions"] = normalized_regions
        raw_detection["thresholds"] = normalized_thresholds
        raw_detection["color_profiles"] = normalized_profiles
        return raw_detection

    @staticmethod
    def _normalize_region_ratio(value, default_region):
        region = dict(default_region)
        if isinstance(value, dict):
            for key in ("left", "top", "width", "height"):
                region[key] = ConfigLoader._safe_float(value.get(key, region[key]), region[key])
        return region

    @staticmethod
    def _safe_float(value, default):
        try:
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def parse_time_str(mm_ss_str):
        try:
            time_str = str(mm_ss_str).strip()
            if ":" in time_str:
                parts = time_str.split(":")
                if len(parts) != 2:
                    raise ValueError("Invalid time format. Expected 'MM:SS' or 'MMSS'")
                minutes = int(parts[0])
                seconds = int(parts[1])
            elif time_str.isdigit():
                if len(time_str) <= 2:
                    minutes = 0
                    seconds = int(time_str)
                else:
                    minutes = int(time_str[:-2])
                    seconds = int(time_str[-2:])
            else:
                if not time_str:
                    return 0
                raise ValueError("Invalid characters. Expected digits or 'MM:SS' format.")
            return minutes * 60 + seconds
        except (ValueError, IndexError) as e:
            print(f"Error parsing time string '{mm_ss_str}': {e}")
            return 0

    @staticmethod
    def format_time_str(seconds):
        if seconds < 0:
            seconds = 0
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"
