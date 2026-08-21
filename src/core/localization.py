import os

from core.app_paths import existing_state_path, preferred_state_path


class LocalizationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalizationManager, cls).__new__(cls)
            cls._instance._init_data()
        return cls._instance

    def _init_data(self):
        self.current_lang = "zh_CN"
        self._load_state()
        self.strings = {
    "zh_CN": {
        "BTN_ADD_CLASS": "+ 新增分组",
        "BTN_ADD_COMMAND": "+ 新增主条目",
        "BTN_ADD_EVENT": "+ 新增事件",
        "BTN_ADD_MIRACLE": "+ 新增扩展条目",
        "BTN_BROWSE": "浏览",
        "BTN_CANCEL": "取消",
        "BTN_CONFIG_EDITOR": "打开配置编辑器",
        "BTN_DELETE": "删除",
        "BTN_SAVE": "保存并应用",
        "BTN_START": "启动",
        "COPYRIGHT": "当前版本由 <a href=\"https://space.bilibili.com/43072148\" style=\"color: #6c757d; text-decoration: underline; font-weight: bold;\">B站 [灰化肥发黑_] (UID: 43072148)</a> 维护。",
        "PROJECT_SCOPE": "通用本地屏幕识别与提醒工具",
        "PROJECT_BOUNDARY": "仅分析可见屏幕信息，不读取或控制第三方进程，不发送自动操作。使用前请遵守相关平台规则。",
        "DLG_CONFIRM_DELETE": "确认删除",
        "DLG_MSG_CLASS_ID": "请输入分组ID (如: Group A):",
        "DLG_MSG_CLASS_NAME": "请输入显示名称 (如: 轮换组A):",
        "DLG_MSG_COMMAND_NAME": "请输入主条目名称:",
        "DLG_MSG_DELETE": "确定要删除 '{}' 吗？",
        "DLG_MSG_MIRACLE_NAME": "请输入扩展条目名称:",
        "DLG_TITLE_ADD_CLASS": "新增分组",
        "DLG_TITLE_ADD_COMMAND": "新增主条目",
        "DLG_TITLE_ADD_MIRACLE": "新增扩展条目",
        "EDITOR_TITLE": "配置管理",
        "ERR_ID_EXISTS": "ID '{}' 已存在。",
        "HDR_ACTION": "操作",
        "HDR_ENABLED": "启用",
        "HDR_MUTE": "静音",
        "HDR_NAME": "名称",
        "HDR_SOUND": "音效文件",
        "HDR_TIME": "时间 (MM:SS)",
        "LBL_COOLDOWN": "冷却时间:",
        "LBL_COUNT": "执行次数:",
        "LBL_CURRENT_CONFIG": "当前配置: {}",
        "LBL_DURATION": "持续时间:",
        "LBL_HOTKEY": "触发热键:",
        "LBL_INIT_TIME": "初始时间:",
        "LBL_INTERVAL": "运行间隔:",
        "LBL_MODE": "运行模式:",
        "LBL_OCR_BOSS": "启用目标事件识别",
        "LBL_OCR_COMMAND": "启用主条目标识别",
        "LBL_OCR_TIME": "启用时间识别",
        "LBL_SKIP_HOTKEY": "跳过冷却:",
        "LBL_TRANSPARENCY": "背景透明度: {}",
        "MSG_SAVE_FAIL": "配置保存失败。",
        "MSG_SAVE_SUCCESS": "配置已保存并应用。",
        "PROJECT_EDITION": "本地运行 · 用户可配置",
        "SEC_BOSS": "目标事件设置",
        "SEC_CLASSES": "分组配置",
        "SEC_COMMAND": "主条目",
        "SEC_EVENTS": "全局事件",
        "SEC_MIRACLE": "扩展条目",
        "SEC_SESSION": "会话设置",
        "SUBTITLE": "本地信息提醒工具",
        "UI_ACTIVE_SUFFIX": " (持续)",
        "UI_ADD_SKILL_PROMPT": "请输入{}名称:",
        "UI_ADD_SKILL_TITLE": "新增{}",
        "UI_ANY_COLOR": "任意 (Any)",
        "UI_BLUE_COLOR": "蓝色 (Blue)",
        "UI_BOSS_IGNORE_KEYWORDS": "OCR屏蔽关键字:",
        "UI_BOSS_KILL_ALLY": "颜色规则A结果OCR关键字:",
        "UI_BOSS_KILL_ENEMY": "颜色规则B结果OCR关键字:",
        "UI_BOSS_KILL_TIMEOUT": "结果监听窗口(秒):",
        "UI_BOSS_WINDOW_1": "事件检测窗口1:",
        "UI_BOSS_WINDOW_2": "事件检测窗口2:",
        "UI_CD_EFFECT": "截止特效",
        "UI_CD_FLASH": "截止闪烁",
        "UI_CD_FLASH_TOOLTIP": "开启后，条目冷却进入截止阈值时，该条目行会闪烁提示。",
        "UI_CD_SOUND": "截止音频",
        "UI_CD_SOUND_TOOLTIP": "冷却截止阈值触发时播放的音频文件路径",
        "UI_CD_THRESHOLD": "CD截止阈值",
        "UI_CD_THRESHOLD_TOOLTIP": "当冷却剩余时间小于等于该值时，触发截止提醒与可选闪烁。",
        "UI_COMMAND_SKILL": "主条目",
        "UI_CONFIG_ERROR": "配置错误",
        "UI_DEFAULT_GLOBAL": "默认 (Global)",
        "UI_DELETE_CLASS_MSG": "确定要删除分组 '{}' 吗？",
        "UI_DELETE_CLASS_TOOLTIP": "删除此分组",
        "UI_DELETE_CONFIRM": "确认删除",
        "UI_DELETE_SKILL_MSG": "确定要删除{} '{}' 吗？",
        "UI_EDIT_CLASS_ID_TOOLTIP": "点击修改唯一ID (需谨慎)",
        "UI_EDIT_CLASS_NAME_TOOLTIP": "点击修改分组名称",
        "UI_EDIT_TIME_LABEL": "输入时间 (MM:SS):",
        "UI_EDIT_TIME_TITLE": "修正时间",
        "UI_ENABLE_CLASS_TOOLTIP": "启用此分组",
        "UI_ERROR": "错误",
        "UI_ALREADY_LATEST": "当前已是最新版本（v{version}）。",
        "UI_CHECK_UPDATE_ACTION": "检查更新",
        "UI_OPEN_RELEASE": "打开 GitHub Releases",
        "UI_UPDATE_AVAILABLE": "发现新版本 v{latest}\n当前版本：v{current}\n\n本程序不会自动下载或安装更新。",
        "UI_UPDATE_AVAILABLE_TITLE": "发现新版本",
        "UI_UPDATE_CHECK_FAILED": "检查更新失败：\n{error}",
        "UI_UPDATE_CHECK_TITLE": "检查更新",
        "UI_UPDATE_CHECKING": "正在检查更新，请稍候。",
        "UI_VERSION_ACTION": "当前版本：v{version}",
        "UI_EXIT_ACTION": "退出 (Exit)",
        "UI_FLASH_THRESHOLD": "闪烁阈值",
        "UI_FLASH_THRESHOLD_TOOLTIP": "设置此条目的独立闪烁阈值。设为 0 则使用全局设置。",
        "UI_INDEPENDENT_MODE": "独立 (Independent)",
        "UI_INVALID_COUNTDOWN": "配置文件中的倒计时时间无效，请在配置编辑器中修正。",
        "UI_LANG_TOGGLE": "🌐 中/En",
        "UI_LOADING_ENV": "正在初始化运行环境，请稍候...",
        "UI_LOADING_STARTUP": "正在预加载启动组件，请稍候...",
        "UI_LOADING_TITLE": "正在加载",
        "UI_LOAD_CONFIG_FAIL": "加载配置文件失败。",
        "UI_LOOP_MODE": "循环 (Loop)",
        "UI_MENU_EXIT": "退出程序 (Exit)",
        "UI_MENU_TOGGLE_LOCK": "锁定/解锁 (Toggle Lock)",
        "UI_MIRACLE_SKILL": "扩展条目",
        "UI_NEW_EVENT": "新事件",
        "UI_NEXT": "下个: {}",
        "UI_OCR_BOSS_TOOLTIP": "启用后自动检测目标事件出现与完成信息",
        "UI_OCR_COLOR": "OCR颜色",
        "UI_OCR_COMMAND_TOOLTIP": "开启后自动识别屏幕上的主条目提示",
        "UI_OCR_KEYWORDS": "OCR关键字",
        "UI_OCR_KEYWORDS_PLACEHOLDER": "关键字1,关键字2...",
        "UI_OCR_KEYWORDS_TOOLTIP": "OCR识别关键字，用逗号分隔",
        "UI_OCR_TIME_TOOLTIP": "开启后自动识别并同步界面时间",
        "UI_PAUSE": "暂停",
        "UI_PLEASE_WAIT": "请稍候",
        "UI_READY": "已就绪",
        "UI_RED_COLOR": "红色 (Red)",
        "UI_REMAINING_USES": "剩余次数已更新",
        "UI_RESUME": "继续",
        "UI_SELECT_CONFIG": "选择配置文件",
        "UI_SELECT_SOUND": "选择音效文件",
        "UI_SINGLE_MODE": "单次 (Single)",
        "UI_SOUND_PATH_TOOLTIP": "提示音效文件路径",
        "UI_START_ACTION": "开始",
        "UI_STEP_MODE": "步进 (Step)",
        "UI_SUCCESS": "成功",
        "UI_SYNC_TIME": "同步屏幕时间",
        "UI_SYSTEM_ERROR": "系统错误",
        "UI_TOTAL": "总计: {}",
        "UI_TRAY_TOOLTIP": "本地信息提醒工具 (Local Info Reminder)",
        "UI_TRIGGER_HOTKEY": "触发热键",
        "WIN_CONFIGURATION": "配置",
        "WIN_TITLE": "本地信息提醒工具"
    },
    "en_US": {
        "BTN_ADD_CLASS": "+ Add Group",
        "BTN_ADD_COMMAND": "+ Add Primary Entry",
        "BTN_ADD_EVENT": "+ Add Event",
        "BTN_ADD_MIRACLE": "+ Add Extended Entry",
        "BTN_BROWSE": "Browse",
        "BTN_CANCEL": "Cancel",
        "BTN_CONFIG_EDITOR": "Open Config Editor",
        "BTN_DELETE": "Delete",
        "BTN_SAVE": "Save & Apply",
        "BTN_START": "Start",
        "COPYRIGHT": "Maintained by <a href=\"https://space.bilibili.com/43072148\" style=\"color: #6c757d; text-decoration: underline; font-weight: bold;\">Bilibili [灰化肥发黑_] (UID: 43072148)</a>.",
        "PROJECT_SCOPE": "General local screen recognition and reminder tool",
        "PROJECT_BOUNDARY": "Analyzes visible screen content only. It does not access or control third-party processes or send automated input. Follow applicable platform rules.",
        "DLG_CONFIRM_DELETE": "Confirm Delete",
        "DLG_MSG_CLASS_ID": "Enter Group ID (e.g., Group A):",
        "DLG_MSG_CLASS_NAME": "Enter Display Name:",
        "DLG_MSG_COMMAND_NAME": "Enter Primary Entry Name:",
        "DLG_MSG_DELETE": "Are you sure you want to delete '{}'?",
        "DLG_MSG_MIRACLE_NAME": "Enter Extended Entry Name:",
        "DLG_TITLE_ADD_CLASS": "Add Group",
        "DLG_TITLE_ADD_COMMAND": "Add Primary Entry",
        "DLG_TITLE_ADD_MIRACLE": "Add Extended Entry",
        "EDITOR_TITLE": "Configuration Editor",
        "ERR_ID_EXISTS": "ID '{}' already exists.",
        "HDR_ACTION": "Action",
        "HDR_ENABLED": "Enabled",
        "HDR_MUTE": "Mute",
        "HDR_NAME": "Name",
        "HDR_SOUND": "Sound File",
        "HDR_TIME": "Time (MM:SS)",
        "LBL_COOLDOWN": "Cooldown:",
        "LBL_COUNT": "Count:",
        "LBL_CURRENT_CONFIG": "Config: {}",
        "LBL_DURATION": "Duration:",
        "LBL_HOTKEY": "Hotkey:",
        "LBL_INIT_TIME": "Initial Time:",
        "LBL_INTERVAL": "Interval:",
        "LBL_MODE": "Mode:",
        "LBL_OCR_BOSS": "Enable Target Event Detection",
        "LBL_OCR_COMMAND": "Enable Primary Entry OCR",
        "LBL_OCR_TIME": "Enable Time Sync OCR",
        "LBL_SKIP_HOTKEY": "Skip CD Key:",
        "LBL_TRANSPARENCY": "Background Transparency: {}",
        "MSG_SAVE_FAIL": "Failed to save configuration.",
        "MSG_SAVE_SUCCESS": "Configuration saved and applied.",
        "PROJECT_EDITION": "Local · Configurable",
        "SEC_BOSS": "Target Event Settings",
        "SEC_CLASSES": "Group Settings",
        "SEC_COMMAND": "Primary Entry",
        "SEC_EVENTS": "Global Events",
        "SEC_MIRACLE": "Extended Entry",
        "SEC_SESSION": "Session Settings",
        "SUBTITLE": "Local Info Reminder",
        "UI_ACTIVE_SUFFIX": " (Active)",
        "UI_ADD_SKILL_PROMPT": "Enter {} name:",
        "UI_ADD_SKILL_TITLE": "Add {}",
        "UI_ANY_COLOR": "Any",
        "UI_BLUE_COLOR": "Blue",
        "UI_BOSS_IGNORE_KEYWORDS": "OCR ignore keywords:",
        "UI_BOSS_KILL_ALLY": "Friendly target event completion OCR keywords:",
        "UI_BOSS_KILL_ENEMY": "Opponent target event completion OCR keywords:",
        "UI_BOSS_KILL_TIMEOUT": "Completion detection timeout (s):",
        "UI_BOSS_WINDOW_1": "Target event window 1:",
        "UI_BOSS_WINDOW_2": "Target event window 2:",
        "UI_CD_EFFECT": "End Effect",
        "UI_CD_FLASH": "End Flash",
        "UI_CD_FLASH_TOOLTIP": "Flash this entry row when it enters the cooldown-end threshold.",
        "UI_CD_SOUND": "End Sound",
        "UI_CD_SOUND_TOOLTIP": "Audio file played when the cooldown-end threshold is reached.",
        "UI_CD_THRESHOLD": "CD Threshold",
        "UI_CD_THRESHOLD_TOOLTIP": "Trigger the cooldown-end reminder and optional flash when remaining cooldown reaches this value.",
        "UI_COMMAND_SKILL": "Primary Entry",
        "UI_CONFIG_ERROR": "Configuration Error",
        "UI_DEFAULT_GLOBAL": "Default (Global)",
        "UI_DELETE_CLASS_MSG": "Are you sure you want to delete group '{}' ?",
        "UI_DELETE_CLASS_TOOLTIP": "Delete this group",
        "UI_DELETE_CONFIRM": "Confirm Delete",
        "UI_DELETE_SKILL_MSG": "Are you sure you want to delete {} '{}' ?",
        "UI_EDIT_CLASS_ID_TOOLTIP": "Click to edit the unique ID (use with care)",
        "UI_EDIT_CLASS_NAME_TOOLTIP": "Click to edit the group name",
        "UI_EDIT_TIME_LABEL": "Enter time (MM:SS):",
        "UI_EDIT_TIME_TITLE": "Edit Time",
        "UI_ENABLE_CLASS_TOOLTIP": "Enable this group",
        "UI_ERROR": "Error",
        "UI_ALREADY_LATEST": "You are using the latest version (v{version}).",
        "UI_CHECK_UPDATE_ACTION": "Check for Updates",
        "UI_OPEN_RELEASE": "Open GitHub Releases",
        "UI_UPDATE_AVAILABLE": "Version v{latest} is available.\nCurrent version: v{current}\n\nThe application will not download or install it automatically.",
        "UI_UPDATE_AVAILABLE_TITLE": "Update Available",
        "UI_UPDATE_CHECK_FAILED": "Unable to check for updates:\n{error}",
        "UI_UPDATE_CHECK_TITLE": "Check for Updates",
        "UI_UPDATE_CHECKING": "Checking for updates. Please wait.",
        "UI_VERSION_ACTION": "Current version: v{version}",
        "UI_EXIT_ACTION": "Exit",
        "UI_FLASH_THRESHOLD": "Flash Threshold",
        "UI_FLASH_THRESHOLD_TOOLTIP": "Set a per-entry flash threshold. Use 0 to fall back to the global setting.",
        "UI_INDEPENDENT_MODE": "Independent",
        "UI_INVALID_COUNTDOWN": "The countdown time in the configuration file is invalid. Please correct it in the configuration editor.",
        "UI_LANG_TOGGLE": "ZH/En",
        "UI_LOADING_ENV": "Initializing runtime environment, please wait...",
        "UI_LOADING_STARTUP": "Preloading startup components, please wait...",
        "UI_LOADING_TITLE": "Loading",
        "UI_LOAD_CONFIG_FAIL": "Failed to load config file.",
        "UI_LOOP_MODE": "Loop",
        "UI_MENU_EXIT": "Exit Program (Exit)",
        "UI_MENU_TOGGLE_LOCK": "Lock/Unlock (Toggle Lock)",
        "UI_MIRACLE_SKILL": "Extended Entry",
        "UI_NEW_EVENT": "New Event",
        "UI_NEXT": "Next: {}",
        "UI_OCR_BOSS_TOOLTIP": "Automatically detect target event appearance and completion information when enabled.",
        "UI_OCR_COLOR": "OCR Color",
        "UI_OCR_COMMAND_TOOLTIP": "Automatically recognize primary skill prompts on screen when enabled.",
        "UI_OCR_KEYWORDS": "OCR Keywords",
        "UI_OCR_KEYWORDS_PLACEHOLDER": "keyword1,keyword2...",
        "UI_OCR_KEYWORDS_TOOLTIP": "OCR recognition keywords, separated by commas",
        "UI_OCR_TIME_TOOLTIP": "Automatically recognize and sync the in-game time when enabled.",
        "UI_PAUSE": "Pause",
        "UI_PLEASE_WAIT": "Please wait",
        "UI_READY": "Ready",
        "UI_RED_COLOR": "Red",
        "UI_REMAINING_USES": "Remaining uses updated",
        "UI_RESUME": "Resume",
        "UI_SELECT_CONFIG": "Select Config File",
        "UI_SELECT_SOUND": "Select Sound File",
        "UI_SINGLE_MODE": "Single",
        "UI_SOUND_PATH_TOOLTIP": "Reminder audio file path",
        "UI_START_ACTION": "Start",
        "UI_STEP_MODE": "Step",
        "UI_SUCCESS": "Success",
        "UI_SYNC_TIME": "Sync Screen Time",
        "UI_SYSTEM_ERROR": "System Error",
        "UI_TOTAL": "Total: {}",
        "UI_TRAY_TOOLTIP": "Local Info Reminder",
        "UI_TRIGGER_HOTKEY": "Trigger Hotkey",
        "WIN_CONFIGURATION": "Configuration",
        "WIN_TITLE": "Local Info Reminder"
    }
}

    def _load_state(self):
        try:
            state_path = existing_state_path("launcher_state.json")
            if os.path.exists(state_path):
                import json
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.current_lang = data.get("language", "zh_CN")
        except Exception:
            self.current_lang = "zh_CN"

    def _save_state(self):
        try:
            import json
            data = {}
            state_path = preferred_state_path("launcher_state.json")
            state_dir = os.path.dirname(state_path)
            if state_dir:
                os.makedirs(state_dir, exist_ok=True)
            current_path = existing_state_path("launcher_state.json")
            if os.path.exists(current_path):
                with open(current_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["language"] = self.current_lang
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def get(self, key):
        lang_dict = self.strings.get(self.current_lang, self.strings["zh_CN"])
        return lang_dict.get(key, key)

    def set_language(self, lang_code):
        if lang_code in self.strings:
            self.current_lang = lang_code
            self._save_state()

    def toggle_language(self):
        new_lang = "en_US" if self.current_lang == "zh_CN" else "zh_CN"
        self.set_language(new_lang)
        return new_lang
