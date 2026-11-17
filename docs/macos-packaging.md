# CP2K Studio v1.0.0 — macOS ARM64 个人测试版

本版面向 Apple Silicon，实际构建和测试平台为 Apple M4、macOS 15.5。它是独立的 PyInstaller onedir/windowed App，不要求使用者安装或手动运行 Python，不内置 CP2K 引擎或 MPI。Intel Mac 不在此次原生构建范围内。

## 构建与运行

在项目现有虚拟环境安装构建工具，然后构建：

```bash
.venv/bin/python -m pip install -r requirements-build.txt
bash build_macos.sh
# 需要重新分析依赖时：
bash build_macos.sh --clean
```

首次准备开发环境时先安装 `requirements.txt`。脚本默认使用项目 `.venv/bin/python`；也可以显式设置 `CP2K_BUILD_PYTHON` 指向其他 ARM64 虚拟环境。脚本不修改系统 Python、PATH 或全局依赖，不执行 sudo。`--clean` 仅清理指定的 `build/CP2K_Studio` 可重建目录。

最终产物为 `dist/CP2K Studio.app`。在 Finder 双击即可运行，也可将**整个 App** 拖到自己的 Applications 文件夹；不要只移动 Contents/MacOS 中的可执行文件。`dist/CP2K Studio/` 是 PyInstaller 生成的 onedir 中间产物，独立 `.app` 不依赖该文件夹。

本机个人测试采用 PyInstaller 自动的 ad-hoc 签名；这不是 Apple Developer ID 签名，也没有公证、DMG、PKG 或正式发布流程，不承诺其他 Mac 的 Gatekeeper 行为。App 的名称为 CP2K Studio，版本 1.0.0，构建号 1，Bundle ID 为 `org.cp2kstudio.desktop`。

如果 Finder/Dock 仍显示旧图标，先退出 CP2K Studio，再打开新位置的 App；必要时移除旧 Dock 快捷方式，再将新 App 拖回。不要修改系统图标缓存文件。原始 PNG 保持原样，`.icns` 使用系统 sips/iconutil 生成。

## 文件和用户数据

只读的 XML、数据库、图标、Qt 样式、翻译、内置预设、示例和说明从 App 内部加载，与启动时的工作目录无关。

移动 App 后，打开旧项目或应用旧预设时，对原 App 内部已不存在的内置数据库引用，仅在当前资源的 SHA-256 与保存记录完全相同时恢复到新位置。存在的文件、自定义数据库、校验和不匹配的文件及科学参数不会被替换，原 JSON 文件不会被重写。

- 已有个人预设继续使用 `~/Library/Preferences/CP2K-Studio/presets/`，保留此前的路径，不迁移或清空。
- 新增启动日志为 `~/Library/Application Support/CP2K Studio/logs/studio.log`，最多保留两份滚动备份。
- Local Run 的独立记录继续位于 `~/Library/Caches/CP2K-Studio/local-run/`。
- 项目和计算包保存到用户在原生文件窗口中选择的外部路径。不要在 App 包内部保存自己的数据。

## Environment Check

点击 Environment Check／环境检测。除 GUI PATH 外，还会检查 Apple Silicon Homebrew 的常见位置，能显示“已安装但不在 GUI PATH 中”的区别；不会把 App 内部目录当作 CP2K 安装位置，也不会修改系统 PATH。

本机识别到 CP2K 2026.2、Open MPI 5.0.11 和 Apple M4。Studio 的输入目标仍为 CP2K 2026.1，因此版本差异提醒是预期结果。Finder 启动时通常没有终端的 Homebrew PATH，检测报告会指出这一点；Local Run 的实际终端环境仍须能找到脚本要求的程序。Python 依赖检查读取 App 自带的运行依赖声明和分发元数据，不将未打包的 pytest 当作运行依赖缺失。

## Local Run

1. 选择已解压的计算包文件夹，内有 `run.sh` 和 `input.inp`。
2. 阅读目录和脚本信任提示，点击 Run。
3. 系统 Terminal.app 分别显示 Calculation 和 Output Monitor 两个窗口。

首次运行可能由 macOS 请求控制 Terminal 的 Automation 权限；允许后才可执行。拒绝或超时会有明确提示。重建 App 后可能需要重新授权，程序不会修改 TCC 数据库或绕过系统授权。

原始 `run.sh`、MPI/OpenMP 参数和 CP2K 程序名保持不变。独立的 `cp2k-studio-runner` 自带 Python 运行时，专门在终端运行脚本或跟踪日志，不启动第二个 GUI，也不依赖开发虚拟环境。关闭监控或 GUI 不发送计算停止信号。终端启动和脚本退出码不等于 CP2K 数值计算成功。

CP2K 和兼容的 MPI 仍须在本机单独安装、配置。自动测试仅使用无害脚本，不运行真实 DFT。

## 可重复验证

静态验证：

```bash
.venv/bin/python scripts/verify_macos_bundle.py "dist/CP2K Studio.app"
```

运行真实打包程序的自动冒烟检查，所有测试文件只写入新建临时目录：

```bash
test_parent=$(mktemp -d)
QT_QPA_PLATFORM=offscreen "dist/CP2K Studio.app/Contents/MacOS/CP2K Studio" \
  --packaging-smoke-test "$test_parent/result"
cat "$test_parent/result/report.json"
```

该模式覆盖四种结构格式（含三个真实 Materials Studio XSD 测试样例）、五种任务表单及目标 XML、IR+Raman、3D 渲染、中英状态保持、项目与预设、综合检查、独立 INP 与计算包导出、环境检查，以及独立控制台助手的无害脚本。终端模拟器在自动冒烟模式中被替代；真正 Terminal.app 的双窗口和原生文件面板另做桌面测试。

构建元数据在 App 内的 `build-info.json`，包含实际 Python、PyInstaller 和运行依赖版本。最终桌面测试和回归结果另见 `docs/macos-test-report.md`。
