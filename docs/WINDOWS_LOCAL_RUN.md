# Windows Native Local Run

支持 Windows 原生 `cp2k.ssmp.exe`（单进程 OpenMP）和 `cp2k.sopt.exe`（单进程串行）。不包含 CP2K/MSYS2 DLL，不执行 MPI、Bash 或 WSL，不修改科学参数和输入生成逻辑。

## 使用方法

1. 点击顶部 **Local Run / 本地运行**，选择已解压的计算目录。
2. 必须有 `input.inp`，其引用的结构、基组、赝势和重启文件必须可读。无需 `run.sh` 或项目 JSON。含预处理指令的输入目前要求先转为自包含文件，程序不会猜测或改写。
3. **CP2K Executable** 优先采用 Environment Check 已检测的路径或上次成功配置，也可通过原生文件窗口选择真实 `.exe`。PowerShell Function 不会被当作实际 EXE。
4. **Runtime DLL Directory** 可填写 `C:\msys64\ucrt64\bin`；程序会尝试检测该标准目录或 EXE 旁的 `libgfortran-5.dll`，也可手动浏览。可留空以使用 EXE 所在目录及现有子进程 PATH。
5. **OpenMP Threads** 默认 1，之后恢复上次成功设置。必须为正整数；串行版本只允许 1。
6. 核对本次为单个 CP2K 进程。第 07 页的 MPI/运行脚本资源设置不会被用于本次原生执行。已有 `output.out` 时会提示可能覆盖；不接受覆盖风险可点击 Cancel，自行备份后再运行。
7. 点击 **Start Calculation / 开始计算**。异步执行绝对路径 `EXE --version`，确认可启动、版本和 Serial/OpenMP 类型。缺 DLL、无效 EXE、错误线程数均保留窗口并显示错误。
8. 成功后打开 **CP2K Studio · Calculation** 和 **CP2K Studio · Output Monitor** 两个窗口。优先 `wt.exe -w new new-tab`，不可用时回退为带 `CREATE_NEW_CONSOLE` 的 PowerShell。窗口保留至用户关闭。

相当于在所选目录执行：

```powershell
$env:PATH = "C:\msys64\ucrt64\bin;" + $env:PATH
$env:OMP_NUM_THREADS = "8"
& "C:\CP2K\cp2k.ssmp.exe" -i "input.inp" -o "output.out"
```

实际实现由独立 `cp2k-studio-runner.exe` 使用 `subprocess.Popen([absolute_exe, '-i', 'input.inp', '-o', 'output.out'], shell=False, cwd=selected_folder, env=child_environment)` 启动。用户路径通过 JSON/参数传递，PowerShell 的固定代码采用 UTF-16LE EncodedCommand，路径只以 Base64 字节进入脚本，再由 LiteralPath/调用运算符读取；不使用 CMD 或 Invoke-Expression 拼接用户命令。

## 独立性及日志

- PATH/OMP 仅对子进程生效，系统 PATH、注册表、System32 均不变。冻结 App 临时清除创建外部进程时继承的 PyInstaller DLL 搜索目录，然后立即恢复自身状态。
- `--version` 成功表明该启动路径所需的 DLL 能加载，不代表所有延迟加载库、输入版本兼容性或数值功能都已验证。CP2K 2026.2 可以被识别，Studio 仍以 2026.1 XML 为输入目标。
- 计算终端继承真实控制台标准输出/错误，显示 CP2K 实际退出码。退出码 0、窗口打开或日志出现均不代表数值收敛。
- 监控使用现有 LogFollower，默认显示末尾 30 行；未生成时等待，截断/替换后尽可能重新连接。已有日志可能属于上次计算，不能据此判断新计算成功。
- 关闭监控只结束监控；退出 GUI 不发送终止信号。关闭计算终端或在其中 Ctrl+C 则遵循正常 Windows 控制台行为，可能停止计算。
- 不删除旧输出、不修改 input.inp/run.sh/项目数据；实际 CP2K 会按该输入写入日志、重启或轨迹，启动前请自行保留需要的结果。
- 同一目录使用跨进程文件锁和短期启动保留，防止重复点击；不是队列，不自动重试或重启。无法完全检测外部手动启动、终端崩溃或主动脱离助手的计算。

## 本地设置及环境检测

上次成功启动的 EXE、DLL 目录和线程数保存在 `%LOCALAPPDATA%\CP2K Studio\local-run\windows.json`。只保存这三个本地字段，不加入 Project/Presets JSON。取消、EXE 验证失败、终端未启动不会覆盖此前设置。若终端启动较慢，由独立助手在确实创建 CP2K 子进程后保存设置。

Environment Check 读取同一配置，并可检测 MSYS2 UCRT64 标准目录；版本探测使用相同的 DLL/PATH 环境。其报告和 Local Run 均不修改当前项目、Dirty、INP 预览、综合检查状态或 3D 视角。

## 自动验证与限制

新增测试覆盖配置恢复、EXE/PE/版本/DLL 失败、Serial/OpenMP/MPI 区分、引用文件缺失、注入字符路径、PowerShell 传参及新窗口回退、旧日志确认、项目隔离、中英切换和取消期间的异步回调。原 macOS/Linux Bash、终端、文件锁和日志测试继续运行。

GitHub Actions 在 `build/windows-test-engine` 编译无害的模拟 `cp2k.ssmp.exe`，不将其打入 Portable 包。模拟程序只报告 mock 版本、记录 argv/cwd/PATH/OMP、写入 MOCK 日志并返回 7，不计算 DFT。在 Windows 上执行源码助手和冻结助手测试，包括监控独立关闭、启动器退出后完成、真实进程退出码及不改写输入文件。Qt 契约以 offscreen 测试；真实 Windows Terminal/PowerShell 视觉窗口、Windows 11 高 DPI、真实 MSYS2 CP2K 2026.2 和实际 DLL 缺失情景仍需用户实机验证。

PowerShell 首次不可用、应用控制策略阻止 EXE、文件/配置目录权限不足时将显示错误或在终端/启动日志记录，不要求管理员权限，也不修改安全策略。Windows 构建和下载步骤见 [WINDOWS_BUILD.md](WINDOWS_BUILD.md)。

依据：[Windows Terminal 新窗口参数](https://learn.microsoft.com/en-us/windows/terminal/command-line-arguments)、[PowerShell EncodedCommand](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_powershell_exe?view=powershell-5.1)、[PyInstaller 外部进程运行环境](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html)、[SetDllDirectoryW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setdlldirectoryw)。
