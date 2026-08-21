# Changelog

## 2026-08-21

### Changed

- 增加统一应用版本号、GitHub Releases 新版检查和托盘检查入口。
- 增加 Inno Setup 安装器与 GitHub Actions 发布流程，产出安装器、便携 ZIP 和 SHA-256 校验文件。
- 安装器使用 Inno Setup 内置英文界面，避免 GitHub Windows runner 缺少外部简体中文语言包时构建失败；应用内的中英文界面不受影响。
- 项目运行、测试和 PyInstaller 打包环境统一为 Python 3.12。
- 移除许可证激活、试用限制、完整性校验、许可证签发器及 PyArmor 安全打包流程。
- 普通构建配置统一为 `packaging/specs/LocalInfoReminder.spec`。
- 增加 Apache License 2.0、贡献指南、通用使用边界和本地构建说明。
- 保留根目录中经过实际验证的识别配置，并将 `templates/daily_generic/` 修正为中性示例。

### Verified

- 自动化测试：88 passed，5 skipped。
- PyInstaller 构建成功；OCR runtime、启动器、LogicEngine、OverlayWindow 和系统托盘均已完成启动验证。

## 2026-03-23（历史版本）

### Fixed

- 修复 EXE 打包后 OCR 初始化失败的问题，不再出现 `onnxruntime_pybind11_state` 的 DLL 初始化报错。
- 修复 `rapidocr_onnxruntime` 在冻结环境下遗漏 `config.yaml` 导致 OCR 无法创建的问题。
- 修复 `rapidocr_onnxruntime` 动态子模块未被收集，导致 `TextDetector` 等类加载失败的问题。

### Changed

- 明确区分源码运行环境与打包环境：
  - 源码运行继续使用 Python 3.13.3
  - EXE 打包改为使用 Python 3.12.10
- 新增 PyInstaller 自定义 runtime hook，确保 ORT 在 Qt runtime hook 之前预加载。
- 更新普通版与安全版 spec，使其完整收集 RapidOCR 数据文件与动态子模块。
- 补充当时版本的 README 和打包文档，记录当时使用的构建组合与排障要点。

### Verified

- 普通 PyInstaller 包已验证 OCR 可正常运行。
- 当时的 Secure 包已验证 OCR 可正常运行；该打包方式现已移除。
- `boss_detector` 对“即将 / 出现 / 出没 / 刷新 / 一分钟 / 可大有”等预告文本的过滤修复已保留。
