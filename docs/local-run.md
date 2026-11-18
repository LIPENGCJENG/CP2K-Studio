# Local Run / 本地运行

Windows Native 新增独立适配器，使用 `cp2k.ssmp.exe` / `cp2k.sopt.exe` 直接计算，不要求或执行 `run.sh`，详细配置、命令及测试范围见 [Windows 本地运行](WINDOWS_LOCAL_RUN.md)。下方 Bash 行为针对 macOS/Linux，保持原有流程。

顶部 Local Run 位于 Environment Check 与 Help 之间。流程为：选择已解压的计算目录 → 检查 → 确认 Run → 打开两个独立系统终端。确认前不执行脚本；只运行自己创建或信任的 `run.sh`。

本工具不读取项目 JSON、不导入结构、不调用综合检查，不改变当前项目、Dirty、预览或视角。只要求目录内有可读的 `run.sh` 和 `input.inp`，本机有 Bash；不要求已有 output.out、data/ 或项目文件。ZIP 须先解压。

## 两个独立终端

- **CP2K Studio · Calculation**：在所选目录原样执行 `bash run.sh`，继承真实终端的输入、标准输出及错误输出。显示脚本退出码后等待 Enter。不修改 MPI、OMP、CP2K 路径、脚本或 PATH。终端环境可能与 GUI 不同，CP2K/MPI 须能在终端中使用。
- **CP2K Studio · Output Monitor**：独立跟踪 output.out，行为相当于 `tail -n 30 -F`。文件不存在时等待，新建文件先显示末尾 30 行，支持追加、截断及替换。跳过启动前已有文件中未变化的内容，明确提示旧日志。由独立标准库 Python 助手执行，不解析 CP2K 成功标记。初始化最多读取末尾 1 MiB，极长单行可能从中间开始。

Ctrl+C 或关闭监控不会向计算发送停止信号。关闭 Studio 不终止计算。计算终端内 Ctrl+C 遵循正常的前台进程组信号规则；关闭计算终端可能中止计算。终端打开或脚本返回 0 均不保证 CP2K 成功，须检查日志和收敛情况。run.sh 自身仍可能覆盖结果；Studio 不删除或改写计算包文件。

## 平台与生命周期

- macOS 使用 Terminal.app，固定 AppleScript 接收安全引用的命令参数，每次请求新窗口。可能需要 Automation 权限。拒绝或超时有明确提示，超时后应检查已有终端再重试；不会自动授予权限或使用 sudo。
- Linux / Rocky Linux 按桌面优先选择 GNOME Terminal、Konsole 或 Xfce Terminal，再尝试其他支持项和 xterm；各有独立 argv 适配。没有图形桌面或可用终端时拒绝启动，不降级为后台计算。
- Windows Native 使用 Windows Terminal 新窗口或独立 PowerShell 控制台及专用 console helper；不调用 CMD/Bash/MPI。WSL 启动仍未提供。
- Python 源码和 v1.0.0 macOS App 均受支持。打包版本使用 App 自带的独立 cp2k-studio-runner，不再把 GUI 可执行文件当作 Python 解释器。

启动助手副本、参数与收据保存在应用缓存，不进入项目 JSON。macOS 为 `~/Library/Caches/CP2K-Studio/local-run/`；Linux 为 `$XDG_CACHE_HOME/CP2K-Studio/local-run/`，默认 `~/.cache/CP2K-Studio/local-run/`。

同一规范化目录使用跨进程文件锁，Bash 继承锁描述符；待启动请求暂时保留目录，防止重复点击。过期请求或退出状态未知时再次运行前显示提醒。无法可靠识别手动启动或主动脱离脚本并关闭继承描述符的计算。这不是任务队列，不提供自动停止或重试。

Linux 参数参考：[GNOME Terminal](https://help.gnome.org/gnome-terminal/pref-tab-window.html)、[Konsole](https://docs.kde.org/trunk_kf6/en/konsole/konsole/command-line-options.html)、[Xfce Terminal](https://docs.xfce.org/apps/xfce4-terminal/command-line)、[xterm](https://www.invisible-island.net/xterm/manpage/xterm.html)。macOS 依据系统 Terminal.sdef 字典。

## 验证范围

新增测试使用临时无害 Bash 脚本，验证工作目录、标准输出/错误、退出码、日志跟踪、重复启动、进程独立性、确认取消、语言与项目隔离。终端适配器单元测试使用模拟调用，不等于桌面实测。

自动化结果：原有 1204 项回归测试及新增 49 项测试均通过，共覆盖当前 1253 项测试（分批执行，补充用例单独复测）。保留上游 ASE／CP2K 解析器的弃用警告，未修改其实现。新增的 42 条翻译已编译入 TS/QM；两种语言各 1015 条已完成翻译。中英文确认窗口已通过 Qt 离屏渲染检查。

早期源码阶段的 macOS 自动化尝试曾超时。v1.0.0 打包阶段已通过实际 App 的 Local Run 打开两个独立 Terminal 会话，确认不同 TTY、正确工作目录及脚本退出码 7；停止监控后无害脚本仍继续，GUI 关闭后完成标记保留。独立助手验证不依赖开发 Python。Linux、Windows 未做本次桌面实测，未执行真实 CP2K DFT；详细结果见 macOS 打包测试报告。

## 修改文件

- 新增执行模块：`core/local_run.py`、`core/local_run_runtime.py`。
- 界面：新增 `ui/local_run_dialog.py`，修改 `ui/main_window.py` 工具栏。
- 翻译：`i18n/catalog_sources.py` 及 `cp2kstudio_en_US.ts/.qm`、`cp2kstudio_zh_CN.ts/.qm`。
- 新增测试：`tests/test_local_run.py`、`test_local_run_monitor.py`、`test_local_run_terminals.py`、`test_local_run_ui.py`。
- 工具栏回归测试：`tests/test_environment_dialog.py`、`test_layout_workflow.py`、`test_ui_ux.py`。
- 文档：`README.md`、`docs/local-run.md`。
