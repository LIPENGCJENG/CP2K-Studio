# Windows x64 Portable — CP2K Studio v1.0

## 从 Mac 触发云端构建

先提交并推送本次文件到 GitHub 默认分支。进入仓库 → **Actions** → **Build CP2K Studio Windows Portable** → **Run workflow**，选择分支并执行。Workflow 仅有 `workflow_dispatch`，不会因 push/PR/定时任务自动执行。

成功后，在该次运行底部 **Artifacts** 下载 **CP2K-Studio-v1.0-Windows-x64-Portable**。GitHub 下载的外层 ZIP 内含：

- `CP2K_Studio_v1.0_Windows_x64_Portable.zip`
- `SHA256SUMS.txt`

构建产物保留 14 天，不创建 Release，不改变仓库可见性。工作流仅请求 `contents: read`。

## Windows 用户使用

将内层 Portable ZIP 解压到有写入权限的位置，例如 `D:\Software\CP2K Studio` 或用户目录（支持空格、中文及 OneDrive 路径）。保留完整 **CP2K Studio** 文件夹及 `_internal`，双击 **CP2K Studio.exe**。不需要 Python、安装程序或管理员权限。

可在 PowerShell 对比校验值：

```powershell
Get-FileHash .\CP2K_Studio_v1.0_Windows_x64_Portable.zip -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

默认 English，支持实时简体中文。Qt 用户预设沿用标准 GenericConfigLocation 下的 `CP2K-Studio/presets`，运行日志位于 `%LOCALAPPDATA%\CP2K Studio\logs`；不往 Portable 文件夹保存用户配置。项目和计算包由用户另选位置保存。

GUI 自带 Python/Qt/ASE 等运行库，**不包含 CP2K 引擎、MSYS2 DLL 或 MPI**。Environment Check 只识别原生 Windows PE 可执行程序，不执行 WSL、otool、ldd 或 Terminal.app；完整 Windows DLL 依赖解析仍暂标为 Unknown。缺少 CP2K 不影响生成/导出输入。新增 [Windows Native Local Run](WINDOWS_LOCAL_RUN.md) 可直接运行原生 Serial/OpenMP EXE，不把 Bash 脚本交给 CMD，也不启动 WSL。导出的 run.sh 仍面向所选计算环境，不会转换成 Windows 脚本。

## 构建配置和本机复用

- GitHub 官方 `windows-2025` x64 Runner，Python **3.12 x64**。
- PyInstaller **6.22.3**、hooks-contrib **2026.9**，one-dir/windowed；PySide6 **6.12.0**，Pillow **12.0.0** 仅用于从原 PNG 生成多尺寸 ICO。
- EXE 产品/文件版本 **1.0.0**；不请求 UAC 管理员权限。ICO、Qt 应用图标和任务栏 AppUserModelID 共用产品身份。
- Checkout **7.0.1**、Setup Python **7.1.0**、Upload Artifact **7.0.2**，均固定 release 对应 SHA，使用 Node 24。官方托管 Runner 提供所需 Node 运行环境。
- Qt 文档目前列出 Windows 10（1809+）/11 x64 支持；实际适用范围仍取决于最终依赖和真实桌面测试。本次固定 Qt 版本，避免未来 Qt 升级改变 Windows 10 支持范围。

Windows 本机 PowerShell 7：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt -c requirements-build-win.txt
.\.venv\Scripts\python -m pip install -r requirements-build-win.txt
.\.venv\Scripts\python scripts/test_windows_core.py
./build_windows.ps1 -Python .\.venv\Scripts\python.exe
```

脚本明确检查原生 Windows x64、依赖、退出码、EXE PE 架构/GUI 子系统、Python DLL、Cocoa 以外的 Windows Qt 平台插件、翻译、XML 和每个数据库 SHA-256。`.gitattributes` 防止 Windows checkout 改写带指纹资源的换行。所有必要资源均在 Git 中，无需访问开发者 Mac 或下载可变数据库。

Windows 路径转为正斜杠后允许 Unicode 字母/数字，继续拒绝换行和 CP2K 预处理元字符；不改变参数或数值。移动 Portable 文件夹后，旧项目的内置数据库路径只在原文件不存在且 SHA-256 完全相同时重绑定，不替换用户自定义文件或不匹配的数据。

随后在原目录及含中文/空格的新解压目录执行有超时限制的离屏 Smoke Test；覆盖四种结构格式、五种任务/XML、中英切换状态、项目/预设和输入/计算包导出。ZIP CRC、解压后的逐文件 SHA-256、最终 ZIP SHA-256 均验证后才生成正式 ZIP 和校验文件。任何必需步骤失败都会使 Job 失败，不上传残缺包。

## 验证范围

2026-11-17 在 macOS Apple Silicon 完成本地验证：

- 与 Workflow 相同的核心测试选择：**625 passed**；41 个依赖 Qt 桌面 fixture 的用例明确 deselect，保留对应模块中的核心用例。Windows 不具备的 POSIX Bash 执行用例由原有平台条件单独 skip，非整体跳过测试。
- 路径/资源/Windows 契约及现有文件引用、macOS 打包、图标、原生文件面板回归：**115 passed**。
- macOS Local Run 与双语回归：**55 passed**。以上测试组存在重叠，不相加宣称独立测试总数。
- actionlint **1.7.12** 校验通过；PowerShell **7.7.0** 解析构建脚本和 Workflow 内所有 PowerShell 代码块通过；在 macOS 执行构建脚本按预期拒绝平台并返回非零。
- Windows Spec/Python 脚本及 EXE 版本资源语法检查通过。当前 Mac 缺少 Windows 专用 pefile，因此未执行 Windows PE 版本资源的实际写入/读取；该步骤由 Windows PyInstaller 构建负责。
- 使用 `win_amd64` / CPython 3.12 的二进制 wheel 依赖预解析通过，未修改本地运行依赖。跨平台 pip 预解析不等同于 Windows 实际安装，平台条件依赖仍以 Runner 安装结果为准。
- 新 Smoke Test 以源码运行模式通过（报告明确 `frozen: false`），覆盖结构、五种任务/XML、语言状态和项目/导出；冻结 Windows EXE 模式仍待云端执行。
- 原 macOS Spec、构建脚本和 PNG 的内容未修改，没有重建或覆盖现有 App/DMG。

Workflow 不会自动提交代码或触发额外的远程运行。工作流文件须先推送到默认分支，GitHub Actions 才会显示手动运行入口。当前开发环境是 macOS；Windows 云端构建是否成功须以用户触发后的 Actions 日志为准，不能仅凭本地配置检查声称已生成 Windows EXE。

Hosted Runner 的离屏测试不代表真实 Windows 桌面验收。仍需 Windows 10/11 实机检查 3D、原生文件面板、旋转/平移/选择、任务栏图标、高 DPI、窗口缩放、OneDrive，以及实际 CP2K/MPI 环境。没有执行真实 CP2K 计算，也没有生成 MSI/MSIX/Setup.exe 或修改 macOS 构建流程。

## 文件变更

新增：`.github/workflows/build-windows-portable.yml`、`CP2K_Studio_Windows.spec`、`build_windows.ps1`、`requirements-build-win.txt`、`.gitattributes`、`resources/icons/cp2k_studio.ico`、`core/windows_executable.py`、`scripts/windows_build_assets.py`、`scripts/windows_portable.py`、`scripts/windows_smoke.py`、`scripts/test_windows_core.py`、`scripts/windows_core_plugin.py`、`tests/test_windows_packaging.py`、本文档。

修改：`.gitignore`、`README.md`、`main.py`（显式冒烟入口）、`core/environment_check.py`（仅原生 Windows PE 检测）、`core/file_references.py`（Windows Unicode 路径）、`core/resources.py`（Portable 移动后验证指纹恢复路径）、`ui/app_icon.py`（Windows 任务栏身份）。没有更改科学参数或模型字段。

官方依据：[Checkout release](https://github.com/actions/checkout/releases/tag/v7.0.1)、[Setup Python release](https://github.com/actions/setup-python/releases/tag/v7.1.0)、[Upload Artifact release](https://github.com/actions/upload-artifact/releases/tag/v7.0.2)、[Windows 2025 image](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md)、[Qt 支持平台](https://doc.qt.io/qtforpython-6/overviews/qtdoc-supported-platforms.html)。
