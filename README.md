# LocalInfoReminder

LocalInfoReminder 是一款在 Windows 本地运行的通用桌面信息识别与提醒工具。它通过屏幕图像分析、OCR 与可配置规则提供计时、事件检测、音频播报和悬浮窗提示，可用于需要观察屏幕区域并按规则提醒的多种场景。

项目只处理用户可见的屏幕像素和用户主动配置的信息。屏幕识别和状态处理均在本机完成。

## 项目定位与安全边界

本项目是独立开发的通用工具，不隶属于、不代表、也未获得任何第三方软件、平台或内容权利方的授权、认可或合作背书。

项目有意保持以下技术边界：

- 不注入、附加或控制第三方进程
- 不读取或修改第三方进程内存、客户端文件或网络通信
- 不绕过访问控制、技术保护措施或反作弊系统
- 不向第三方软件发送自动键盘、鼠标或其他操作
- 不提供一键宏、自动操作、无人值守执行或规避检测能力
- 不以获取不公平优势、破坏正常服务或违反第三方规则为用途

全局键鼠监听仅用于接收用户主动输入的本地快捷键和手势，不会代替用户向第三方软件发送输入。

## 功能

- 启动器、配置编辑器与悬浮窗
- 分组循环和主条目计时
- OCR 时间同步、目标事件和可配置区域识别
- 本地音频播报
- JSON 配置和资源模板
- PyInstaller Windows 打包

## 环境

- Windows
- Python 3.12（源码运行、测试和 PyInstaller 打包统一使用）

已使用的主要依赖列在 [requirements.txt](requirements.txt)，测试依赖列在 [requirements-dev.txt](requirements-dev.txt)。

## 安装

当前项目版本为 **v1.0.0**。程序启动后可在系统托盘菜单查看版本并检查 GitHub Releases 是否有新版本；检查操作只提示并打开发布页面，不会自动下载或安装。

本地运行时，可在 `update_config.json` 中将 `github_repository` 设置为 GitHub 的 `owner/repo`。GitHub Actions 正式发布时会自动写入当前仓库地址，无需手工修改发布包。正式版本使用 `v1.0.0` 形式的 Release 标签，并与 `pyproject.toml` 和 `src/core/version.py` 中的版本保持一致。

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

如果系统设置了全局 `PYTHONPATH`，可以先运行：

```powershell
.\use_venv.ps1
```

## 运行

```powershell
$env:PYTHONPATH = ""
.\venv\Scripts\python.exe src\main.py
```

程序会请求管理员权限，以支持全局键鼠监听等 Windows 功能。

## 测试

```powershell
.\run_tests.bat
```

## 打包

安装 PyInstaller 后运行普通打包配置：

```powershell
.\venv\Scripts\python.exe -m PyInstaller packaging\specs\LocalInfoReminder.spec --noconfirm --clean
```

输出目录为 `dist/LocalInfoReminder/`。打包产物不提交到 Git。

### GitHub Releases 发布

将版本号同步写入 `pyproject.toml` 和 `src/core/version.py`，提交后推送对应标签：

```powershell
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions 会运行测试、PyInstaller 打包和 Inno Setup 编译，然后发布：

- `LocalInfoReminder-1.0.0-Windows-x64-Setup.exe`
- `LocalInfoReminder-1.0.0-Windows-x64.zip`
- `SHA256SUMS.txt`

安装器默认安装到当前用户的 `%LOCALAPPDATA%\Programs\LocalInfoReminder`，升级时保留已有 `config.json`。

## 项目结构

- `src/`：应用源码
- `assets/`：图标和音频资源
- `docs/`：使用及开发文档
- `tests/`：自动化测试
- `templates/`：通用配置和资源模板
- `packaging/`：PyInstaller 配置与运行钩子
- `scripts/`、`tools/`：开发辅助工具

运行日志默认写入 `logs/`，本地运行状态默认写入 `state/`；这些目录不会提交到 Git。

依赖本地截图与 OCR 模型结果的集成测试默认跳过。如需运行，请先设置
`RUN_OCR_INTEGRATION=1`，再执行测试命令。

## 文档

- [中文使用手册](docs/使用手册.md)
- [配置指南](docs/CONFIG_GUIDE.md)
- [技术文档](docs/技术文档.md)
- [目标事件配置说明](docs/目标事件配置说明.md)
- [环境隔离与打包说明](docs/环境隔离与打包说明.md)

## 使用边界

使用者应在启用任何配置或模板前，自行确认其用途符合相关平台规则、服务协议及适用法律。第三方平台可能对屏幕叠加、实时提醒或其他辅助工具采用比法律更严格的限制；本项目不保证特定使用方式会得到第三方允许，也不对账号限制或其他第三方处置作出保证。

配置、模板和识别规则仅用于展示通用能力，不代表对任何特定第三方产品的适配承诺。发现可能涉及自动操作、技术措施规避、未授权数据访问或公平性破坏的用法时，请不要使用或传播相关配置，并通过项目问题追踪渠道报告。

根目录的 `config.json` 保留了维护者实际使用和验证过的识别规则，用于保证现有检测流程可直接运行；其中的名称、关键词、时间窗口和阈值仅代表一份可修改的用户配置，不属于框架本身的固定适配，也不构成官方支持或持续兼容承诺。`templates/daily_generic/` 则提供不指向特定产品的中性示例，适合用作新配置的起点。

## 支持项目

本项目免费并以 Apache-2.0 协议开源。如果项目对你有所帮助，可以通过[维护者主页](https://space.bilibili.com/43072148)自愿支持后续开发和维护。

支持完全自愿，不解锁任何功能，不构成购买技术支持，也不会用于提供自动化操作、竞争优势或规避检测服务。商业定制和技术支持应与自愿支持分开协商，并继续遵守本项目的安全边界。

## 参与贡献

提交代码、配置或文档前，请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。项目不接受自动操作、进程注入、内存或网络干预、技术措施规避以及其他可能破坏第三方服务公平性或安全性的贡献。

## 许可证

本项目依据 [Apache License 2.0](LICENSE) 开源。
