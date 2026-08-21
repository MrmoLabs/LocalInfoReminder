# 配置文件指南 (Config Guide)

`config.json` 用于控制 LocalInfoReminder 的主要行为。修改后重新加载配置或重启程序即可生效。

## 1. 全局事件 (`global_events`)

用于在指定倒计时时间点播放提醒。

```json
{
  "global_events": [
    {
      "is_enabled": true,
      "is_muted": false,
      "time": "18:30",
      "name": "事件出现",
      "sound": ""
    }
  ]
}
```

- `time`: 触发时间，格式为 `MM:SS`
- `name`: 事件名称
- `sound`: 触发时播放的音频
- `is_enabled`: 是否启用
- `is_muted`: 是否静音

## 2. 分组模板 (`classes_template`)

用于配置分组循环、独立模式和快捷键。

```json
{
  "id": "class_1",
  "name": "轮换组A",
  "default_hotkey": "F2",
  "skip_cd_hotkey": "F3",
  "interval": 10,
  "cooldown": 30,
  "is_enabled": true,
  "is_muted": false
}
```

- `id`: 唯一标识
- `name`: 显示名称
- `default_hotkey`: 主触发快捷键
- `skip_cd_hotkey`: 跳过冷却快捷键
- `interval`: 轮转间隔
- `cooldown`: 条目倒计时
- `is_enabled`: 是否启用
- `is_muted`: 是否静音

## 3. 主条目 (`primary_entries`)

用于配置主条目的触发、持续时间、冷却、OCR 识别和音频提醒。

```json
{
  "id": "primary_a",
  "name": "喝水提醒",
  "duration": 3,
  "cooldown": 60,
  "default_hotkey": "Alt+1",
  "sound": "",
  "cd_threshold": 3,
  "cd_flash": true,
  "cd_sound": "",
  "ocr_color": "",
  "ocr_keywords": ["喝水"],
  "is_enabled": true,
  "is_muted": false
}
```

- `duration`: 条目持续时间
- `cooldown`: 条目总冷却时间
- `sound`: 条目触发当下播放的音频
- `cd_threshold`: 截止提示阈值，单位秒
- `cd_flash`: 剩余冷却时间进入阈值后是否闪烁
- `cd_sound`: 剩余冷却时间进入阈值后播放的音频
- `ocr_color`: OCR 使用的颜色预设，通常为 `red` 或 `blue`
- `ocr_keywords`: OCR 关键字列表

## 4. 扩展条目 (`extended_entries`)

扩展条目主要用于提醒倒计时和结束前闪烁。

```json
{
  "id": "miracle_1",
  "name": "扩展条目",
  "cooldown": 40,
  "default_hotkey": "Alt+4",
  "sound": "miracle_skills/miracle.mp3",
  "flash_threshold": 3,
  "is_enabled": true,
  "is_muted": false
}
```

- `flash_threshold`: 闪烁提示阈值
- `sound`: 条目触发时播放的音频

## 5. 功能开关

配置中常用的总开关包括：

- `enable_time_display`
- `enable_classes`
- `enable_primary_entries`
- `enable_extended_entries`
- `enable_global_events`
- `enable_boss_settings`
- `ocr_time_sync`
- `ocr_primary_entries`
- `ocr_boss_detection`

## 6. 音频路径约定

- 主条目音频建议放在 `assets/command_skills/`
- 扩展条目音频建议放在 `assets/miracle_skills/`
- 全局事件音频建议放在 `assets/global_events/`

## 7. 视觉检测配置 (`vision_detection`)

`vision_detection` 用于统一管理 OCR 区域、颜色检测配置和相关阈值。所有 ROI 使用相对比例保存，不同分辨率会在运行时自动换算。

```json
{
  "vision_detection": {
    "regions": {
      "time_main": {"left": 0.46875, "top": 0.02315, "width": 0.05729, "height": 0.0463},
      "time_prep": {"left": 0.47656, "top": 0.14352, "width": 0.04896, "height": 0.0463},
      "skill_bar": {"left": 0.3646, "top": 0.2083, "width": 0.2969, "height": 0.0417},
      "target_event_notification": {"left": 0.368, "top": 0.207, "width": 0.253, "height": 0.035},
      "target_event_result": {"left": 0.368, "top": 0.207, "width": 0.253, "height": 0.035}
    },
    "thresholds": {
      "skill_trigger_ratio": 0.01,
      "target_event_color_ratio": 0.03
    },
    "color_profiles": {
      "skill_red": {"sample_color": [255, 60, 60], "tolerance": 110.0, "min_ratio": 0.01},
      "skill_blue": {"sample_color": [70, 130, 255], "tolerance": 110.0, "min_ratio": 0.01},
      "target_event_color_a": {"sample_color": [255, 60, 60], "tolerance": 110.0, "min_ratio": 0.03},
      "target_event_color_b": {"sample_color": [70, 130, 255], "tolerance": 110.0, "min_ratio": 0.03}
    }
  }
}
```

### `regions`

- `time_main`: 主计时 OCR 区域
- `time_prep`: 预备阶段 OCR 区域
- `skill_bar`: 主条目标识别与颜色检测区域
- `target_event_notification`: 目标事件播报 OCR 区域
- `target_event_result`: 目标事件结果 OCR 区域

### `thresholds`

- `skill_trigger_ratio`: 主条目颜色触发比例阈值
- `target_event_color_ratio`: 目标事件颜色判定比例阈值

### `color_profiles`

颜色检测现在使用“采样颜色 + 容差 + 命中比例”的方式：

- `sample_color`: RGB 采样颜色
- `tolerance`: 允许颜色偏离的范围
- `min_ratio`: ROI 内命中像素比例达到多少才算触发

## 8. ROI 编辑器

在配置页面的旧入口按钮中，可以直接打开 ROI 编辑器。目前支持：

- `区域概览` 分页：查看当前 ROI、坐标和缩略预览
- `联动调试` 分页：同屏查看颜色调试和 OCR 调试
- 重新截图、`Ctrl + 滚轮` 围绕鼠标位置缩放、中键或空格拖动画布
- 直接编辑比例坐标或像素坐标
- 截图取色、容差切片预览、命中遮罩预览和命中像素统计
- `Ctrl + T` 手动 OCR 测试，以及颜色参数变更后的自动 OCR 刷新

## 9. 目标事件配置 (`target_event_detection`)

`target_event_detection` 现在完全按用例维护，只保留 `targets` 列表。不再使用公用的结果词、屏蔽词、通知窗口或持续时间根字段。

```json
{
  "target_event_detection": {
    "targets": [
      {
        "id": "target_a",
        "display_name": "目标A",
        "match_names": ["Target A", "目标A"],
        "ocr_keywords": ["目标A"],
        "time_windows": [
          {"start": "27:10", "end": "24:30"},
          {"start": "17:20", "end": "14:30"}
        ],
        "result_window_seconds": 180,
        "result_keywords": ["完成", "结束"],
        "ignore_keywords": ["示例", "忽略"],
        "faction_match": "distinguish",
        "spawn_sound": "",
        "result_sound": "",
        "buff_duration": 120
      }
    ]
  }
}
```

每个 target 独立维护自己的：

- 播报关键字 `ocr_keywords`
- 结果关键字 `result_keywords`
- 屏蔽关键字 `ignore_keywords`
- 有效时间窗口 `time_windows`
- 结果监听时间 `result_window_seconds`
- 活动持续时间 `buff_duration`
