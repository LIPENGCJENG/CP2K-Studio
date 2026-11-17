# Environment Check / 环境检测

顶部 Help / 使用说明左侧新增环境检测按钮。窗口为非模态 QDialog，沿用现有主题，滚动显示报告，底部提供 Recheck、Copy Report、Close。可同时操作主窗口；环境报告与第 08 页的项目输入综合检查相互独立。

## 检测与状态

- `✓`：该项观察或检查成功。
- `!`：存在异常或兼容性提醒。
- `×`：该项失败，例如已确认的未解析动态链接或必需 Python 声明依赖缺失。
- `?`：无法确认，不作为检测通过。

汇总根据实际状态显示基本环境就绪、检测到问题、未检测到 CP2K、部分项目未验证。必要项目存在 Unknown 时不显示完全通过；可选或静态库的未确认状态不表示 CP2K 未安装。所有报告均说明没有执行 DFT、SCF 或 MD，也不代表所有 CP2K 功能正常。

## CP2K 与 MPI

优先依次查找 `cp2k.psmp`、`cp2k.popt`、`cp2k.ssmp`、`cp2k.sopt`、`cp2k`，包括当前进程 PATH、当前 Python/Conda/虚拟环境、用户 bin 目录、常见 Linux 安装目录，以及 macOS 的 `/opt/homebrew` 和 `/usr/local` Homebrew 目录。支持 CP2K_HOME、CP2K_ROOT、CP2K_BIN 目录，以及 CP2K_EXECUTABLE、CP2K_EXE 指定的可执行文件；不递归扫描硬盘。

对找到的程序执行 `--version`，列出路径、版本、修订号和确实报告的已识别编译特性。重复指向同一文件的别名复用一次版本探测，但仍显示路径。明确列出当前检测对象。文件名后缀推断的 MPI/OpenMP 构建类型会注明推断依据；通用 cp2k 名称只有具备实际编译特性证据时才判断能力。

接受其他年份和版本；与目标 2026.1 不同则提示输入规范差异，不切换 XML。Finder 启动时 PATH 可能与终端不同；标准安装目录回退有助于发现 Homebrew，非标准或其他 Conda 环境仍可能需要设置 PATH/明确安装位置。

查找 mpirun/mpiexec 并读取版本，识别常见 Open MPI、MPICH/HYDRA、Intel MPI、Microsoft MPI。仅调用版本命令，不通过启动器运行 MPI 作业。找到启动器或相同的 MPI 名称并不能证明其与 CP2K 的 ABI 兼容；该项保留 Unknown。串行 CP2K 配合多 MPI 进程会提示异常。当前导出脚本仍要求 PATH 中有 cp2k.psmp，不由此窗口替换。

只显示有效的 OMP_NUM_THREADS 数值或未设置/无效状态，不复制无效原始内容或其他任意环境变量。

## 运行库与 Python

Linux 使用 ldd，保留明确的 not found 错误，即使工具退出非零。macOS 使用 otool -L/-l，检查直接链接、LC_RPATH、loader/executable 路径，并考虑已报告的弱链接及系统共享缓存。能识别 MPI、DBCSR、BLAS/LAPACK、ScaLAPACK、FFTW、LibXC、Libint 等实际名称。

动态列表没有出现某个库不证明其缺失；静态库、可选功能、共享缓存、间接或延迟加载依赖可能仍为 Unknown。不会把没有编译的可选库自动判为安装失败。原生 Windows 不运行 ldd/otool，完整 DLL 解析暂未实现，明确显示 Unknown；WSL2 内的 Linux 进程按 Linux 路径检测。

Python 检查读取项目的 requirements.txt 和可用的 PEP 621 pyproject.toml，按当前解释器的 importlib.metadata 和 packaging 约束核对直接声明的版本、平台标记及可选依赖组。Required (declared) 表示依赖清单中的必需项；当前清单也包含 pytest。不会硬编码一套独立依赖表或审计整个系统的所有 Python 环境。报告不输出带凭据的依赖 URL。

当前新增依赖为 psutil 与 packaging。打包时应包含依赖声明及发行包元数据；冻结环境缺少元数据时标为 Unknown，不把缺少 dist-info 等同于缺少已经打包的模块。当前不执行应用打包。

## 硬件与资源限制

读取操作系统、架构、CPU 型号、物理/逻辑核心、当前可用核心、总内存、可用内存和使用率。psutil 无法获取物理核心时显示 Unknown，不使用逻辑核心数冒充。

内存统一以 GiB 显示。Linux 尝试读取进程亲和性，以及标准 cgroup v1/v2 成员路径及祖先的 CPU 配额、内存限制和使用量。存在限制时同时标明宿主机/VM 内存及容器上限、保守余量，避免把宿主机资源当作容器额度。自定义挂载、权限限制、作业调度器的额外政策等不一定可探测；内存余量不包含所有可回收缓存的精确估计。

第 07 页的 MPI/OpenMP 配置在 GUI 线程只读快照，Recheck 重新读取。所需逻辑槽位超过本机已知 CPU 容量时提醒；配置可能用于其他计算机，窗口不调整它。CPU/内存信息不用于承诺某个 DFT 计算一定能完成。

## 异步、安全与报告

工作线程执行全部探测。外部命令使用参数列表和 shell=False、空标准输入、独立临时工作目录、默认 4 秒超时及有界输出读取。CP2K 多版本探测另有 15 秒预算和独立文件数量上限；未探测到的候选明确标为未知。关闭窗口发出取消信号，POSIX 会终止当前探测进程组，Windows 终止直接子进程；不等待线程而阻塞 GUI。

某项失败不阻断其他检测。重新检测保持窗口和主项目；语言切换只重新渲染保存的结构化结果，不重跑检查。复制报告包含 UTC 时间戳、系统信息、程序路径、版本、依赖状态与简要原因，不复制任意环境变量、原始命令输出或异常中的秘密文本。没有自动安装、sudo、远程访问或真实计算。

## 验证与平台限制

在本机 macOS arm64 上执行真实版本、otool 和系统信息探测，发现 Homebrew CP2K 2026.2、Open MPI 5.0.11、Apple M4 及实际内存信息。版本差异和本机 CPU 需求提醒正确显示；项目 JSON、INP、修改标记及配置修订号保持不变。界面和中英文窗口截图采用 Qt offscreen，不作为其他操作系统原生桌面实测的证明。

Linux x86_64、cgroup v1/v2、缺失/静态库和 MPI 类型使用可控模拟数据测试；原生 Windows 的版本/硬件代码路径和 DLL 未确认状态有覆盖，但 Linux、Windows 未进行原生机器上的实际验证。原生 Windows 与 WSL 内的安装环境不同，不自动进入其他 WSL 发行版、远程服务器或非当前虚拟环境。

已有工具栏测试同步加入新按钮。INP 基准固定使用随附官方数据，避免本机新增安装目录使测试路径漂移；没有改动生产生成器、数据库选择或输入科学参数。

相关回归 **219 项通过**；最终环境检测专项 **45 项通过**，覆盖相对 PATH、超时/权限、未安装、多个版本、MPI/串行识别、动态库缺失与静态未知、Python 依赖、资源配额、GUI 异步/取消/复制/重检和双语状态保留。检测异常不会使原先通过的第 08 页综合检查失效。两组测试存在重叠，不相加为独立用例数。

## 文件

- 新增 `core/environment_check.py`、`ui/environment_dialog.py`。
- 修改 `ui/main_window.py`、`requirements.txt`。
- 更新 `i18n/catalog_sources.py`、中英 TS/QM。
- 新增 `tests/test_environment_check.py`、`tests/test_environment_dialog.py`；更新 `tests/test_ui_ux.py`、`tests/test_generation.py`。
- 更新 README 及本文档。

API 参考：[psutil](https://psutil.io/)、[packaging requirements](https://packaging.pypa.io/en/stable/requirements.html)、[ldd](https://man7.org/linux/man-pages/man1/ldd.1.html)。
