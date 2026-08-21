from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.config_loader import ConfigLoader


class BossTargetConfigCard(QFrame):
    delete_requested = pyqtSignal(object)

    def __init__(self, target_data, parent=None):
        super().__init__(parent)
        self.target_data = target_data or {}
        self.setObjectName("BossTargetCard")
        self.setStyleSheet(
            """
            #BossTargetCard {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 10px;
            }
            #BossTargetCard:hover {
                border: 1px solid #4dabf7;
                background-color: #f8f9fa;
            }
            QLabel {
                color: #495057;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #4dabf7;
            }
            QGroupBox {
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin-top: 10px;
                background-color: #fbfbfc;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #343a40;
            }
            QLabel[role="hint"] {
                color: #6c757d;
                font-size: 11px;
            }
            """
        )
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        header = QHBoxLayout()
        self.edit_display_name = QLineEdit(self.target_data.get("display_name", ""))
        self.edit_display_name.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.edit_display_name.setPlaceholderText("目标名称")
        self.edit_id = QLineEdit(self.target_data.get("id", ""))
        self.edit_id.setPlaceholderText("内部 ID")
        self.edit_id.setFixedWidth(180)
        btn_delete = QPushButton("删除")
        btn_delete.setFixedSize(60, 28)
        btn_delete.setStyleSheet("QPushButton { color: #666; background-color: transparent; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; } QPushButton:hover { color: white; background-color: #dc3545; border-color: #dc3545; }")
        btn_delete.clicked.connect(lambda: self.delete_requested.emit(self))

        header.addWidget(self.edit_display_name)
        header.addWidget(self.edit_id)
        header.addWidget(btn_delete)
        main_layout.addLayout(header)

        summary = QLabel("运行流程：进入时间窗口后检测播报 OCR，命中后生成预计出现倒计时；随后在结果监听窗口内检测结果文本，并根据颜色模式与关键词决定是否播报完成结果。")
        summary.setWordWrap(True)
        summary.setProperty("role", "hint")
        main_layout.addWidget(summary)

        schedule_group = QGroupBox("1. 播报检测")
        schedule_layout = QVBoxLayout(schedule_group)
        schedule_layout.setContentsMargins(12, 14, 12, 12)
        schedule_layout.setSpacing(8)

        schedule_hint = QLabel("这一段决定：什么时候开始监听、播报文本里识别哪个目标、播报命中后播放什么音频。")
        schedule_hint.setWordWrap(True)
        schedule_hint.setProperty("role", "hint")
        schedule_layout.addWidget(schedule_hint)

        schedule_form = QFormLayout()
        schedule_form.setContentsMargins(0, 0, 0, 0)
        schedule_form.setSpacing(8)

        self.edit_time_windows = QLineEdit(self._format_time_windows(self.target_data.get("time_windows", [])))
        self.edit_time_windows.setPlaceholderText("27:10-24:30,17:20-14:30")
        schedule_form.addRow("监听时间窗口", self.edit_time_windows)

        self.edit_match_names = QLineEdit(",".join(self.target_data.get("match_names", [])))
        self.edit_match_names.setPlaceholderText("界面实际名称1,界面实际名称2")
        schedule_form.addRow("目标名称匹配", self.edit_match_names)

        self.edit_ocr_keywords = QLineEdit(",".join(self.target_data.get("ocr_keywords", [])))
        self.edit_ocr_keywords.setPlaceholderText("播报 OCR 识别词1,识别词2")
        schedule_form.addRow("播报 OCR 识别词", self.edit_ocr_keywords)

        self.edit_spawn_sound = QLineEdit(self.target_data.get("spawn_sound", ""))
        self.edit_spawn_sound.setPlaceholderText("dragon_spawn.mp3")
        schedule_form.addRow("播报命中音频", self.edit_spawn_sound)

        schedule_layout.addLayout(schedule_form)
        main_layout.addWidget(schedule_group)

        kill_group = QGroupBox("2. 结果识别")
        kill_layout = QVBoxLayout(kill_group)
        kill_layout.setContentsMargins(12, 14, 12, 12)
        kill_layout.setSpacing(8)

        kill_hint = QLabel("这一段决定：播报命中后，接下来多长时间内继续监听结果文本，以及结果文本要满足哪些关键词和颜色条件。")
        kill_hint.setWordWrap(True)
        kill_hint.setProperty("role", "hint")
        kill_layout.addWidget(kill_hint)

        kill_form = QFormLayout()
        kill_form.setContentsMargins(0, 0, 0, 0)
        kill_form.setSpacing(8)

        self.edit_kill_window = QLineEdit(str(self.target_data.get("kill_window_seconds", 180)))
        self.edit_kill_window.setPlaceholderText("180")
        kill_form.addRow("结果监听窗口(秒)", self.edit_kill_window)

        self.combo_faction_match = QComboBox()
        self.combo_faction_match.addItem("区分颜色", "distinguish")
        self.combo_faction_match.addItem("不区分颜色", "ignore")
        current_mode = str(self.target_data.get("faction_match", "distinguish") or "distinguish")
        idx = self.combo_faction_match.findData(current_mode)
        self.combo_faction_match.setCurrentIndex(idx if idx >= 0 else 0)
        kill_form.addRow("颜色匹配方式", self.combo_faction_match)

        self.edit_kill_keywords = QLineEdit(",".join(self.target_data.get("kill_keywords", [])))
        self.edit_kill_keywords.setPlaceholderText("完成,获得,最后一击")
        kill_form.addRow("结果 OCR 关键词", self.edit_kill_keywords)

        self.edit_ignore_keywords = QLineEdit(",".join(self.target_data.get("ignore_keywords", [])))
        self.edit_ignore_keywords.setPlaceholderText("即将,出现,提示")
        kill_form.addRow("OCR 屏蔽关键词", self.edit_ignore_keywords)

        kill_layout.addLayout(kill_form)
        main_layout.addWidget(kill_group)

        result_group = QGroupBox("3. 完成后处理")
        result_layout = QVBoxLayout(result_group)
        result_layout.setContentsMargins(12, 14, 12, 12)
        result_layout.setSpacing(8)

        result_hint = QLabel("这一段决定：结果命中后播放什么音频，以及悬浮窗状态持续多久。")
        result_hint.setWordWrap(True)
        result_hint.setProperty("role", "hint")
        result_layout.addWidget(result_hint)

        result_form = QFormLayout()
        result_form.setContentsMargins(0, 0, 0, 0)
        result_form.setSpacing(8)

        self.edit_kill_sound = QLineEdit(self.target_data.get("kill_sound", ""))
        self.edit_kill_sound.setPlaceholderText("kill.mp3")
        result_form.addRow("完成命中音频", self.edit_kill_sound)

        self.edit_buff_duration = QLineEdit(str(self.target_data.get("buff_duration", 0)))
        self.edit_buff_duration.setPlaceholderText("120")
        result_form.addRow("结果展示时长(秒)", self.edit_buff_duration)

        result_layout.addLayout(result_form)
        main_layout.addWidget(result_group)

    def _format_time_windows(self, windows):
        normalized = ConfigLoader._normalize_time_windows(windows)
        return ",".join(
            f"{window.get('start', '00:00')}-{window.get('end', '00:00')}"
            for window in normalized
        )

    def _parse_list(self, raw_text):
        return [item.strip() for item in str(raw_text or "").split(",") if item.strip()]

    def get_data(self):
        try:
            kill_window_seconds = int(self.edit_kill_window.text().strip() or 180)
        except Exception:
            kill_window_seconds = 180

        try:
            buff_duration = int(self.edit_buff_duration.text().strip() or 0)
        except Exception:
            buff_duration = 0

        target_id = self.edit_id.text().strip()
        display_name = self.edit_display_name.text().strip() or target_id or "target"

        return {
            "id": target_id or display_name,
            "display_name": display_name,
            "match_names": self._parse_list(self.edit_match_names.text()),
            "ocr_keywords": self._parse_list(self.edit_ocr_keywords.text()) or [display_name],
            "time_windows": ConfigLoader._normalize_time_windows(self.edit_time_windows.text()),
            "kill_window_seconds": kill_window_seconds,
            "kill_keywords": self._parse_list(self.edit_kill_keywords.text()),
            "faction_match": self.combo_faction_match.currentData(),
            "ignore_keywords": self._parse_list(self.edit_ignore_keywords.text()),
            "spawn_sound": self.edit_spawn_sound.text().strip(),
            "kill_sound": self.edit_kill_sound.text().strip(),
            "buff_duration": buff_duration,
        }
