# CP2K Studio

跨平台 Python / PySide6 桌面应用，为 **CP2K 2026.1** 生成 Quickstep / GPW 的 DFT 单点能（`ENERGY`）、固定晶胞几何优化（`GEO_OPT`）、晶胞与原子联合优化（`CELL_OPT`）、振动分析（`VIBRATIONAL_ANALYSIS`）及 Born–Oppenheimer 分子动力学（`MD`）输入。应用负责配置、生成和验证；独立 Local Run 工具可经用户确认，在系统终端运行已导出的计算包。

`CELL_OPT` 在第 02 页选择，第 06 页切换为独立的晶胞优化设置。首版支持三维 `PERIODIC XYZ`、Quickstep/GPW、`POISSON_SOLVER PERIODIC` 与解析应力；不自动改变边界条件或晶胞。外部压力始终显式写入，默认 0 bar；保留已有分数坐标固定约束。配置、对称性要求、测试和运行验证范围见[晶胞优化说明](docs/cell-optimization.md)。

DFT 页面现支持[表面偶极校正](docs/surface-dipole-correction.md)：Poisson 参考表下方可开启校正并手动选择 X/Y/Z 法向；默认关闭，仅生成 DFT 根层的 SURFACE_DIPOLE_CORRECTION 与 SURF_DIP_DIR。

SCF 的 OT 参数支持可选 [ENERGY_GAP](docs/ot-energy-gap.md)，默认 Auto，不额外输出关键字。ENERGY_GAP、MINIMIZER 和 DFT 的 QS / EPS_DEFAULT 标签旁提供中英双语帮助；不自动调整用户参数。

新增 [Born–Oppenheimer AIMD](docs/aimd.md)：第 02 页选择 Molecular Dynamics (AIMD)，第 06 页设置 NVT/CSVR 或 NVE、步数、时间步长、轨迹及 Restart。继续复用现有 DFT/SCF、原子约束、综合检查及计算包导出，不在 Studio 中执行计算或生成模拟结果。

## 安装与启动

Windows x64 免安装版可通过 GitHub **Actions → Build CP2K Studio Windows Portable → Run workflow** 手动构建。成功后在 Artifacts 下载 `CP2K-Studio-v1.0-Windows-x64-Portable`，取出其中的 `CP2K_Studio_v1.0_Windows_x64_Portable.zip`，完整解压后双击 `CP2K Studio.exe`。无需 Python，实际 CP2K/MPI 仍需单独配置；详细步骤及验证范围见 [Windows 构建说明](docs/WINDOWS_BUILD.md)。

需要 **Python 3.10 或更新版本**，推荐 Python 3.12。CP2K 本体不是启动依赖。

macOS / Linux：

```bash
cd CP2K-Studio
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Windows PowerShell：

```powershell
cd CP2K-Studio
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

若 PowerShell 不允许激活脚本，可以直接执行 `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` 和 `.\.venv\Scripts\python.exe main.py`。Linux 桌面需要系统图形环境及 Qt 所需的 xcb/OpenGL 运行库。无显示环境仅用于测试，可设 `QT_QPA_PLATFORM=offscreen`。

## 应用图标

正式图标保存在 `resources/icons/cp2k_studio.png`，为用户提供的 1024×1024 透明 PNG 原样副本。入口通过 `ui/app_icon.py` 在创建 QApplication 后统一设置应用与主窗口图标，路径不依赖启动时的工作目录；加载失败时记录警告，继续启动。

Qt 图标加载成功不等于 macOS Dock 已显示该图标。直接通过 Python 启动时，Dock 可能保留解释器图标；v1.0.0 的 macOS 个人测试版现已提供 `.icns`、独立 ARM64 `.app` 及稳定的 Bundle 元数据。通过 `bash build_macos.sh` 重新构建；使用方式与测试范围见 [macOS 打包说明](docs/macos-packaging.md)。资源结构和未来格式预留见 [图标资源说明](resources/icons/README.md)。

## 界面语言 / Interface language

每次启动默认 **English**。顶部工具栏最右侧 **Language:** 可随时切换 **English / 简体中文**，无需重启，也不保存上次选择。页面、菜单、Tooltip、弹窗、3D 统计和已有校验报告即时更新；项目、编辑草稿、原子约束、相机及 CP2K 输入保持不变。

翻译维护：`python scripts/build_translations.py --update` 提取并编译 TS/QM；运行程序直接加载已附带的 QM，无网络依赖。架构、完整覆盖范围、发布资源和维护约定见[中英文界面说明](docs/internationalization.md)。

## 使用流程

顶部工具栏为 **项目管理 / 预设管理 / XML 规范 / 环境检测 / 本地运行 / 使用说明**。「项目管理」下拉菜单提供新建项目、打开项目和保存项目，保留系统标准快捷键（macOS 为 Cmd+N/O/S，Linux/Windows 为 Ctrl+N/O/S）及未保存修改提示。结构导入入口位于第 01 页的「导入结构…」，支持 XSD、CIF、XYZ 和 EXTXYZ。左侧固定八步：结构与晶胞、GLOBAL、DFT、SCF、基组与赝势、几何优化／晶胞优化／振动分析、**运行环境**、**导出与预设**。XML 设置继续使用顶部独立对话框，校验入口统一为第 08 页「综合检查」。

**Environment Check / 环境检测** 打开独立的非模态窗口，异步检查本机 CP2K/MPI、动态链接库、当前 Python 声明依赖和 CPU/内存，支持重新检测、复制报告及中英文切换。版本差异、缺失项或未知项只在本窗口提示，不改变项目、XML、综合检查状态或导出参数。新依赖 `psutil` 和 `packaging` 已加入 requirements.txt；检测本身不会安装任何软件，也不执行计算。详见[环境检测说明与平台限制](docs/environment-check.md)。

**Local Run / 本地运行** 选择已解压的计算目录，检查并确认后打开计算和 `output.out` 监控两个独立终端。不读取项目 JSON 或修改当前项目。macOS Terminal.app 和 Linux 图形终端执行原始 `bash run.sh`；[Windows 原生模式](docs/WINDOWS_LOCAL_RUN.md)直接运行 `cp2k.ssmp.exe` / `cp2k.sopt.exe`，可设置仅对子进程生效的 DLL 目录和 OpenMP 线程数，不执行 Bash/MPI/WSL。启动成功不等于 CP2K 计算成功，详细行为及验证限制见[本地运行说明](docs/local-run.md)。

1. **结构与晶胞**：通过 ASE 导入 XSD、CIF、XYZ 或 EXTXYZ。保留真实元素、笛卡尔坐标和完整三斜晶胞。Materials Studio XSD 支持分子、显式晶胞及源对称算符展开；Slab/链的部分周期性需手动确认，不根据真空层自动推断。分子缺少晶胞时可明确选择生成非周期计算盒，导入本身不平移坐标。[XSD 支持范围和真实文件验证](docs/xsd-import.md)。可手动修改晶胞、坐标和 `NONE/X/Y/Z/XY/XZ/YZ/XYZ` 周期性；明确的 XSD Molecule 或经用户确认的孤立分子固定为 NONE，晶胞仍可编辑。结构类型随项目保存，旧项目与普通 XYZ 不自动锁定。坐标表显示元素、x/y/z 及固定状态，隐藏的逐原子 KIND 映射仍参与保存和导出。结构预览默认隐藏元素标签；右上角工具控制标签、实际晶胞 A/B/C 视角和复位。左键拖动空白旋转、单击原子选择（Ctrl/Cmd 切换多选）、右键拖动平移、滚轮缩放；复位同时恢复默认观察中心、角度和缩放。左下角 XYZ 指示笛卡尔方向；非正交晶胞的 ABC 不等于 XYZ。预览不推断化学键，视图操作不改变坐标。大结构仅绘制前 3000 个原子，模型和导出保留全部原子。
2. **DFT**：明确填写总电荷、自旋多重度、是否 UKS、泛函和 Poisson 求解器；按需要调整网格和 QS 精度。首期支持 PBE、BLYP、PADE。Poisson 下拉框下方提供六种求解器的双语言只读参考表；WAVELET 的二维参考范围限定为 XZ，参考表不改动求解器选择；非周期 WAVELET 的立方盒要求由统一校验器检查。[周期性参考与分子锁定](docs/poisson-periodicity.md)。带电/开壳层体系应自行审查所选物理模型。
3. **SCF**：选择 OT 或 DIAGONALIZATION。OT 生成 `OT`；对角化生成 `DIAGONALIZATION` 与 `MIXING`，可选择 Fermi–Dirac 展宽及额外轨道。可启用 `OUTER_SCF`。切换至 OT 时停用对角化的额外轨道和展宽。
4. **基组与赝势**：在第 05 页按真实元素从下拉列表选择 `BASIS_SET`、`POTENTIAL`；输入关键字可搜索名称和 Alias。可按质量、来源、XC 和 q 筛选。选择后自动记录真实文件、版本、SHA-256，并立即更新预览。下拉框失焦时只保留实际选项，搜索文本不会变成任意参数。
5. **GLOBAL / 第 06 页任务设置**：设置项目名和运行类型。`GEO_OPT` 时生成 `MOTION/GEO_OPT`，支持 BFGS、LBFGS、CG、最大迭代数及力/位移阈值。ENERGY 时不生成 MOTION，第 06 页显示不适用并停用编辑，保留已有参数。选择 `VIBRATIONAL_ANALYSIS` 后第 06 页切换为振动分析，始终计算频率和简正模式，IR/Raman 独立勾选且可同时计算；支持分子及 XYZ 绝缘体 Γ 点超胞的实验性周期光谱路径；生成顶层 Section，分别保留各任务参数。详见[振动与光谱说明](docs/vibrational-analysis.md)。Raman 提供与 SCF/OT 独立的[LINRES 预条件器和能隙估计](docs/raman-linres.md)。
6. **顶部 XML 设置**：点击「XML 规范」查看版本、来源、路径、加载状态，选择自定义 2026.1 XML 或恢复内置规范；确认前检查版本。切换规范会更新校验服务，不修改计算参数和预览内容。
7. **第 07 步：运行环境**：选择 Linux / Rocky Linux、macOS 或 Windows / WSL2，设置 MPI 进程数和每进程 OpenMP 线程数。默认 Linux、1 MPI、1 OpenMP。自动显示逻辑执行槽位和运行类型，不检测本机硬件，也不直接启动计算。
8. **第 08 步：导出与预设**：点击「综合检查」，后台依次执行配置完整性、当前生成 INP 的 XML 校验、最终依赖文件及计算包运行配置检查；自动切换到右侧校验报告。可单独导出 `.inp`、导出计算包，或保存当前设置为个人预设。导出前必须补齐必需信息并通过 XML 语法校验。

第 01 页支持原子整行多选、固定分量及按笛卡尔 X/Y/Z 坐标范围选择。选择只高亮，不自动固定；固定后显示状态列及 3D 标记，GEO_OPT 自动生成 `MOTION/CONSTRAINT/FIXED_ATOMS`。固定分量遵循 CP2K 的**分数坐标**定义，与范围筛选的笛卡尔轴独立；详情和修改清单见[原子固定说明](docs/atom-constraints.md)。

晶胞与原子坐标使用 Delegate 统一显示四位小数，表格条目仍保留完整精度。双击编辑显示原始值，未修改直接回车、Esc、Tab 或失焦不会提交修改；范围筛选、3D、保存和 INP 导出继续使用真实坐标。

原子操作栏按「固定方向：分量 / 固定所选 / 解除固定 / 按坐标范围选择 / 清除全部固定」排列为一行，透明背景与卡片一致；窄窗口仅在该操作栏内水平滚动，保持按钮完整文字。点击窗口内表格、3D 视图和操作控件之外的空白区域会清除表格及 3D 选择，不解除固定约束；按钮、分量下拉框和范围对话框中的点击不会提前丢失选择。

3D 结构预览固定显示在右侧 INP 预览上方，切换 01–08 页保持可见及当前相机状态。上下使用可拖动分隔条，默认约 60% / 40%，小窗口下按最小高度保留两个区域。第 01 页仅保留结构、晶胞、坐标与固定操作。操作说明收纳在标题旁的 ⓘ 中；视窗和视角按钮无悬停提示，其他参数的信息图标仍可使用。[布局截图（步骤顺序调整前）](docs/images/right-structure-preview.png)。

### 界面与配置状态

八页使用统一暗色卡片和 8px 无箭头滚动条；短数值字段采用可退回单列的双列布局。单位是输入框内独立、不可编辑的提示，不进入配置模型，不进行隐式单位换算；科学计数法与原有浮点精度保持一致。

前七步的左侧图标仍来自实时本地配置检查。第 08 步默认为灰色空心圆，只有主动点击「综合检查」，四个必需阶段全部执行且无错误、无警告，才显示绿色勾号；警告显示黄色感叹号，错误显示红色叉号。前置错误使后续阶段明确显示「未执行」。修改配置、切换 XML、依赖文件变化、新建或重新打开项目后需重新检查；标记不写入项目。切换页面、预览标签或保存项目不使有效结果失效。配置就绪和 q 匹配均不等同于物理适用性、数值精度或收敛验证。

第 08 页以全宽青绿色「导出计算包」为主按钮，下方左侧为「导出 .inp 文件」、右侧为「打开导出目录」。当前综合检查有阻断错误时禁止导出；警告允许按原策略导出并提示。未检查或检查失效时，导出流程仍独立复核配置、XML、实际文件引用和脚本，不使用旧结果，也不自动将第 08 步标绿。详见[综合检查说明](docs/comprehensive-check.md)。

顶部工具栏和左侧八步导航不显示悬停文字提示，保留 Hover 高亮和导航状态图标；参数帮助及基组/赝势徽章的 Tooltip 仍可使用。

第 05 页筛选只改变下拉候选，不隐藏 KIND 行、不清空已选参数；不满足筛选的已选项会保留并提示。表格状态使用短徽章，完整说明见 Tooltip。

[UI/UX 修改清单、九项问题说明、测试与各页截图](docs/ui-ux-upgrade.md)。

### 顶部预设管理

「预设管理」下拉菜单统一提供单点能、几何优化、我的预设和管理预设。GLOBAL 页面仅保留任务参数。应用预设前会列出将覆盖的设置；默认保留当前结构、坐标和晶胞。预设明确包含晶胞/坐标时必须确认后才应用。所有面板与实时预览同步刷新。

第 08 步点击「保存为预设」，填写名称、描述和分类，可分别选择包含晶胞/周期性、结构坐标，**两项默认都不包含**。默认保存 GLOBAL、DFT/SCF、逐 KIND 基组/赝势及来源、GEO_OPT 和数据库设置。预设不保存 XML 路径和运行环境，不替代完整项目。应用预设保留当前 MPI / OpenMP 和目标平台设置。不同体系应用时按真实 ELEMENT 匹配 KIND；没有唯一匹配的元素保持未选择并提示，不复制其他元素的参数。

个人预设采用独立的 `format_version=1`、`cp2k_version=2026.1` JSON，存放在 Qt 跨平台配置目录的 `CP2K-Studio/presets` 中。保存后立即进入「我的预设」，同名时可选择覆盖或修改名称另存。「管理预设」支持加载、编辑/重命名、用当前配置更新参数和删除。缺失、损坏或版本不兼容的文件会提示，不阻止其他有效预设使用。

未完成参数也可保存为草稿，会明确标记“不完整”。预设中的 `syntax_validated` 始终为 false，避免把可复用参数当作针对某个体系已通过 CP2K 语法校验的输入。保存预设不会修改当前项目。

### 四种保存 / 导出操作

| 操作 | 内容与用途 |
|---|---|
| 保存项目 | 整个工作项目，包括结构、参数、运行环境、XML 路径及数据库设置 |
| 保存为预设 | 可复用的计算参数，默认不含晶胞、坐标 |
| 导出 .inp | 当前生成器输出的原生输入，坐标内嵌；保留基组/赝势依赖 |
| 导出计算包 | INP、结构、完整项目、所需数据库副本、run.sh 和运行说明；支持文件夹或 ZIP |

第 08 步的「导出 .inp 文件」默认文件名为项目名；导出前从当前模型重新生成并检查，不从预览控件复制文本。其内容与右侧完整配置时的实时预览一致。基组和单来源赝势仍引用原库文件，须保持路径可用；多来源赝势所需的 `studio_potentials.dat` 会同时写入所选目录。若已有同名依赖文件且内容不同，导出会拒绝覆盖并提示选择新目录或计算包。成功提示列出依赖，第 08 步还可打开导出目录。跨机器传输建议使用计算包。

本次文件清单、运行环境与脚本验证范围见 [运行环境升级说明](docs/run-environment.md)。之前的顶部工具栏改造见 [UI 重构记录](docs/ui-layout-upgrade.md)。

`文件 → 打开水分子示例` 可打开明确填写了示例化学参数的演示项目。示例不代表针对任意体系的推荐设置，也不是生产精度或收敛性的承诺。

### 数据库管理与选择

第 05 页的「数据库管理」可查看来源、路径、CP2K 版本、文件指纹、载入状态及被排除的条目。程序依次扫描用户指定 data 目录、`CP2K_DATA_DIR` 和常见 macOS/Linux 安装路径、用户官方缓存及随附官方缓存。仅载入真实存在且版本可确认的数据；未知或不一致版本显示 Error。自定义文件必须由用户在高级模式主动添加并声明版本，界面显示 Warning，不将用户声明当作官方认证。

「数据库文件管理」标题旁的 ⓘ 动态显示已加载文件名、版本和记录数量。搜索、质量/来源/XC/q 筛选及 KIND 表格统一放在「基组与赝势配置」卡片中，筛选区域随可用宽度在四列、两列和一列间调整。

项目随附固定到官方 **v2026.1 release commit** 的 `BASIS_MOLOPT`、`BASIS_MOLOPT_UCL`、`BASIS_MOLOPT_UZH`、`POTENTIAL`、`GTH_POTENTIALS`、`POTENTIAL_UZH`，以及供原有回归输入使用的 `BASIS_SET`、`GTH_BASIS_SETS`。下载地址、提交 SHA 与每个原始文件的 SHA-256 见 `data/cp2k-2026.1/manifest.json`。启动不联网；点击「从官方获取固定的 2026.1 数据」才联网，下载后校验全部指纹及格式，失败保留原缓存。

默认已加载官方库，用户无需输入文件名。高级模式仍可手动配置文件引用和添加自己的基组/赝势库。「推荐基组与赝势」只列出当前元素、当前 XC 在真实数据中存在的常规候选；用户选中一行并点击应用后才修改该 KIND。推荐会记录实际结果，不代替收敛性验证。UZH 可手动选择，但尚无独立验证的协议对应表，因此不会自动推荐或允许与常规库混作已验证协议。

推荐窗口支持按实际元素筛选，并通过 Apply 连续应用不同 KIND 的组合，直到点击 Close 或关闭窗口。Apply 一次提交完整的基组和赝势组合，即时更新项目、主表格、INP 预览和导航状态；筛选与候选表格滚动位置保持不变。顶部「已配置 X/Y 种元素」根据当前项目、数据库引用及源文件指纹计算；同元素的全部 KIND 都有效才计入完成。手动选择、项目/预设加载、结构变更和清空配置也会更新统计。未选择或应用失败时显示非阻断说明，不关闭窗口或递增计数；无结构显示 0/0。

推荐窗口右侧「当前已选配置」圆角卡片按实际 KIND 同时显示基组和赝势，未配置的字段分别显示「未选择」。文字自然换行并可悬停查看完整名称，KIND 之间以细线分隔，内容可独立滚动。该区域和配置进度共用提交后的项目同步信号；Apply、更换选择、重新加载项目及预设后即时恢复对应内容。左右外框顶部和高度对齐，保留 16px 可拖动间距及约 3:1 的默认比例，窗口仍为 1000×500；推荐表格最后一列自动填满剩余宽度。

结构坐标表隐藏 `KIND` 列，但保留逐原子标签。项目中 O1、O2 等同元素的多个 KIND 分别显示并配置，各自的 `ELEMENT O` 用于元素筛选；坐标编辑、保存和导出的 XYZ 保留这些映射。新增标签保持未选择状态。

真实官方文件中也存在 `NA` 占位、无效元素标签、缺少数值和不满足严格维数检查的记录。程序按完整头部语法、计数和数值维数解析条目；不把任意参数行当作名称，不猜测修正无效元素。可解析条目保留，被排除条目在数据库管理中逐项报告。Alias 属于同一条目，不重复作为独立基组显示。

## 不推测缺失的化学信息

新项目的 CHARGE 初始值为 0、MULTIPLICITY 初始值为 1，均可修改；这只是起始配置，不代表所有体系都适用，仍执行价电子数、自旋多重度和 UKS 一致性检查。结构、泛函、静电求解器及元素基组/赝势选择仍为空。数据库可预先载入，但不会代替用户为元素自动选取参数。旧项目缺少电荷/多重度字段时使用 0/1，已保存的数值或显式空值不覆盖；用户主动清空字段仍会报告必填错误。

普通 XYZ 没有晶胞，导入后保持零晶胞；即使是非周期分子，也需要用户明确设置计算盒。CIF 中的部分/混合占位会被拒绝，需先构建有序结构。多帧 XYZ 会被拒绝，避免静默挑选某帧。结构导入本身不居中、包裹或平移坐标；用户主动生成计算盒时才会按所选模式居中。

模型提供的网格、阈值及优化器值是清楚可见、可修改的起始设置，不代表完成了收敛测试。两份 YAML 预设仅切换任务及优化设置，不补齐化学信息。

输入格式错误（例如在数字字段输入字母、NaN、无穷值）会阻止当前预览、保存与导出，不会让程序崩溃或导出旧配置。缺少必需化学信息的草稿仍可保存为 JSON。

## 项目与导出格式

`.cp2kstudio.json` 使用带 `format_version=1` 和 `cp2k_version=2026.1` 的 Pydantic 模型。包含全部当前配置、嵌入的原子/坐标/晶胞、元素设置和库/XML 路径，因此重新打开项目不需要原始 CIF/XYZ。**保存项目本身不嵌入基组/赝势/XML 内容**；这些外部文件应继续可访问，或使用计算包导出进行归档。

项目打开时，相对资源路径以项目目录为基准解析；旧项目的纯库文件名可匹配已载入的真实官方文件。每个 KIND 保存 ELEMENT、选择、文件来源/版本/指纹、打包标记及推荐记录。缺失文件、未知条目或改变的指纹会保留原记录并阻止导出，不会静默换用其他参数。当前支持的坐标、基组、赝势文件引用使用独立 CP2K 序列化，不附加单/双引号。完整包会将依赖复制为安全文件名并同步引用，原源文件保持不变；不能安全直接表示的路径会阻止单独 INP 生成，并提示改用计算包。Bash 文件名转义与 INP 文件引用互相独立，详见 [文件引用修复说明](docs/file-reference-fix.md)。

「导出计算包」先选择文件夹或 ZIP 格式，再选择上级目录和一个**尚不存在**的名称。ZIP 文件名自动补上 `.zip`。文件夹内容如下，ZIP 解压后内容相同：

```text
water_demo/
├── input.inp
├── structure.xyz
├── project.cp2kstudio.json
├── run.sh                    # 使用第 07 页的 MPI / OpenMP 配置
├── EXPORT_NOTES.txt           # 文件清单、资源需求、启动方法、常见错误
├── data/                     # 本机存在的基组/赝势文件，自动复制并避免同名冲突
├── studio_potentials.dat     # 仅使用多个赝势来源时生成的选定条目合并文件
└── cp2k_input.xml             # 仅使用了自定义 XML 时复制
```

导出的 INP 用 `SUBSYS/TOPOLOGY` 引用 `structure.xyz`，晶胞仍在 `CELL` 中明确给出；XYZ 坐标采用 Å。数据文件复制到包内并使用安全的相对路径，空格或特殊字符转换为下划线，以独立序号避免同名冲突；重复引用去重。源文件名、原项目配置不受修改。多个基组文件依次输出 `BASIS_SET_FILE_NAME`。**2026.1 的 `POTENTIAL_FILE_NAME` 不可重复**，因此多个赝势源会提取实际选中记录，保留数值原文并写入一个合并文件；只保留选中的标识符以避免通用 Alias 冲突，同时在项目 JSON 保存全部源库和指纹。包内项目可再次打开、导出。

导出先在临时目录准备文件并完整解析输入，再读取最终 input.inp 中的字面文件引用，按实际运行目录逐一打开坐标、基组和赝势文件，核对实际所选条目内容，并比对 run.sh 与 EXPORT_NOTES.txt 的 MPI/OpenMP、输入及输出文件；不会把 XML 校验通过当作文件可访问的证明。检查成功后才提交目录；失败会清理临时目录，不覆盖已有计算目录。项目保存使用临时文件加原子替换。

在具有兼容 CP2K 和 MPI 的目标环境中，完整解压或移动计算包后，进入目录运行：

```bash
bash run.sh
```

脚本为 UTF-8 / LF 的 Bash 脚本，自动切换到自身目录，检查 `input.inp`、PATH 中的 `cp2k.psmp` 和 `mpirun`。默认命令与第 07 页及运行说明一致：

```bash
export OMP_NUM_THREADS=1
mpirun -np 16 cp2k.psmp -i input.inp -o output.out
```

MPI 和 OpenMP 的值取自当前项目，不受本机平台限制。线程数为 1 时为纯 MPI，大于 1 时为 MPI + OpenMP；逻辑执行槽位为两者乘积，**不等同于物理核心数**。命令固定使用 PATH 中的 `mpirun`、`cp2k.psmp`，要求 MPI 启动器与 CP2K 的编译环境兼容，并在目标机器申请足够资源。程序不替代调度器，也不自动申请资源。

Linux / Rocky Linux 和 macOS 在 Bash 终端执行；Windows 目标指 **WSL2 的 Linux 终端**，原生 PowerShell 不能直接按 Bash 方式运行。启动脚本返回 MPI / CP2K 的失败退出码，错误显示在终端。CP2K 输出固定为 `output.out`；生成脚本或通过 XML 检查不保证计算收敛。单独导出 INP 不附带脚本。

项目增加 `run_environment` 字段（`operating_system`、`mpi_processes`、`omp_threads`），数值必须为正整数，界面和模型统一支持到 2,147,483,647。旧项目没有该字段时使用默认值；旧版 `total_cpu_cores` 和 `omp_threads` 仅在正整数且整除时换算，其他情况恢复默认并在校验报告中给出非阻断提示。现代格式的无效值会报告错误，保留当前打开项目。

`EXPORT_NOTES.txt` 列出实际打包的文件、目标系统、MPI / OpenMP、逻辑执行槽位、启动命令和常见故障。核心 API 使用 `copy_resources=False` 时会明确列出未打包依赖，不声称自包含。

## 验证范围与 XML 接口

配置校验包含必填信息、有限数字、正数范围、右手非退化晶胞、元素配置、自旋/价电子奇偶性（仅当赝势名明确含 `-qN`）、OT 与展宽兼容性，以及周期性和 Poisson 求解器的基本兼容性。`CELL/PERIODIC` 与 `POISSON/PERIODIC` 使用同一设置。MT 的盒大小要求会提示用户；WAVELET 自动设置其要求的 FFTSG，首期限制为正向轴对齐正交晶胞；非周期 NONE 还要求立方盒。第 01 页可选择真空边距、立方体、手动尺寸三种[计算盒生成模式](docs/simulation-box.md)，不会自动更换求解器。

`cp2k-input-tools==0.9.3` 是完整语法校验的首选和必需后端。始终明确传入 XML，**不使用其自带的未知版本规范作为静默替代**。未安装解析器、XML 损坏、版本错误均作为错误报告。

`schemas/cp2k_input_2026.1.xml` 来自 [CP2K 官方 2026.1 规范](https://manual.cp2k.org/cp2k-2026_1-branch/cp2k_input.xml)，来源与 SHA-256 记录在 `schemas/provenance.json`。也可在顶部「XML 规范」对话框选择由 CP2K 2026.1 `--xml` 生成的本地文件。

可编程接口：

```python
from core.schema import CP2KSchema
from core.models import Project
from core.generator import generate_input
from core.validator import InputValidator
from core.project_io import load_project, export_bundle

schema = CP2KSchema()  # 或 CP2KSchema("/path/to/cp2k_input.xml")
print(schema.version)
print(schema.keywords("FORCE_EVAL/DFT/SCF"))
print(schema.keyword("FORCE_EVAL/DFT/SCF", "EPS_SCF"))

project = load_project("examples/water.cp2kstudio.json")
text = generate_input(project)
result = InputValidator(project.xml_spec).parse(text)
print(result.ok, result.errors)
export_bundle(project, "water_export")  # 新目录；已有目录不会覆盖
export_bundle(project, "water_export.zip", archive=True)  # ZIP 也包含 run.sh
```

XML 解析验证关键词、枚举、Section 结构及语法。新增的数据库校验另外检查条目存在性、元素、文件/条目指纹、q、自旋价电子计数、文件搜索覆盖及方法类型。明确 q 不一致、元素错误、源文件缺失、同名不同内容无法合并、全电子用于当前 GPW/GTH 流程等显示 Error 并阻止导出；XC 标签不同、缺少 q/XC 信息、未经独立验证的协议等显示 Warning；一般说明显示 Info；正常 q 匹配和基组质量标签不再生成成功性 Info。名称相符**不保证物理适用性、数值收敛或 CP2K 运行成功**。

## 测试

```bash
python -m pytest -q
```

顶部项目菜单改造的相关回归为 **110 passed，181 warnings，54.37 秒**；新增 15 项覆盖菜单点击、保存/打开/新建、未保存修改处理、标准快捷键及第 01 页 CIF/XYZ 导入。另外在 macOS 原生 Cocoa 平台检查了菜单布局，三个标准快捷键测试均通过；Linux 原生桌面未实测。

最近一次完整测试结果为 **404 passed**（本次坐标显示与精度新增 15 项，耗时 222.20 秒）；GUI 测试自动使用 Qt offscreen 平台。本次全量验证使用临时 `XDG_CACHE_HOME`，避免本机数据库缓存路径影响原有的路径及快照断言；已有 3 项路径/快照测试依赖未配置用户缓存的环境，本次未修改这些既有断言。新增覆盖四位小数绘制、完整精度编辑、未修改退出不写回、取消编辑、三轴范围筛选、项目保存恢复以及单文件和计算包与原精度基准一致；现有 3D 平移/选择、固定约束、数据库、预设、XML 和综合检查测试继续通过。554 条警告主要来自上游 XML 解析器的重复弃用提示，另有 ASE/NumPy 提示及故意构造非法 MPI 字段的 Pydantic 序列化提示。

在 macOS / Python 3.12 环境测试，并验证 `python main.py` 进入 GUI 事件循环及窗口截图渲染。新增测试覆盖真实官方数据库、Alias、Ba/Ti/O 过滤、q/XC、无候选情况、版本/指纹变化、损坏记录隔离、多个源文件、KIND 标签、UI 选择同步、保存恢复和可重复导出。新增 Bash 模拟集成测试覆盖移动计算包、Shell 特殊字符、MPI / OpenMP 传参、缺失程序/输入、失败退出码及 ZIP；GUI 测试覆盖第 07/08 页、实时复制、运行概要、项目恢复和迁移提示。Windows/WSL2/Linux 未在本次环境进行实机验证。解析器 0.9.3 在 Python 3.12 下会报告上游 ElementTree 弃用警告。本环境未安装 CP2K，不执行数值计算。

回归基准是固定到 **CP2K v2026.1** 的官方 `He2_none.inp`（ENERGY）和 `H2O-geo-ot-evals.inp`（GEO_OPT）。原文、上游预期能量记录和来源说明位于 `tests/fixtures/`。测试检查完整官方输入能被解析，并比较生成器支持字段的语义；这些上游测试有故意缩短的迭代和不收敛开关，**不是生产参数预设**。本测试没有执行 CP2K，也没有声称重现了官方能量。详见 [回归说明](tests/fixtures/README.md)。

## 源码结构

```text
main.py                    # 应用入口
ui/                        # Qt 窗口、参数面板、结构视图、只读 INP 预览
core/models.py             # Pydantic 统一配置与版本化序列化
core/structure.py          # ASE 文件边界
core/atom_constraints.py   # 稳定原子 ID、坐标范围选择、固定约束与导出编号
core/schema.py             # 官方 XML 查询和版本检查
core/generator.py          # 结构化 Section 树与确定性渲染
core/validator.py          # 完整性/兼容性与 cp2k-input-tools 适配
core/project_io.py         # 项目持久化、旧版运行配置迁移接入、文件夹/ZIP 导出
core/run_config.py         # 执行环境模型、资源计算、旧格式换算
core/run_script_generator.py # 统一命令、安全 Shell 转义、run.sh
core/export_notes_generator.py # 实际文件清单及运行说明
ui/run_environment_panel.py # 第 07 页：运行平台、并行资源和运行说明
ui/coordinate_range_dialog.py # 第 01 页：笛卡尔坐标范围选择
core/presets.py            # 独立预设模型、应用规划、个人预设存储
core/input_export.py       # 使用原生成器的单独 INP 导出及依赖检查
core/database_format.py    # 原生数据格式、条目与文件指纹
core/basis_database.py     # 基组、别名、壳层与收缩系数解析
core/potential_database.py # GTH、三角矩阵、全电子记录与 NLCC 解析
core/database_manager.py   # 离线扫描、版本和来源、显式官方下载
core/database_resources.py # 真实资源路径与多来源赝势合并
core/kind_recommender.py   # 仅来自实际数据的保守推荐
core/kind_validator.py     # 逐 KIND 元素/q/XC/方法/指纹检查
core/input_import.py       # 已有 INP 中当前支持参数的保守导入
core/runner.py             # 保留的执行边界，首期明确不执行计算
presets/                   # 不含化学推测的工作流预设
schemas/                   # 固定版本的官方规范、来源和上游许可证
examples/                  # 明确设置的水分子演示项目
tests/                     # pytest 与官方回归夹具
```

GUI 不参与核心输入生成。生成器使用 `Section` 数据树与独立关键词/子 Section，禁止依赖对复杂输入模板做字符串替换。预览只读，防止文本与统一模型不同步。通过 `文件 → 导入已有 INP` 可导入一个 Quickstep/GPW FORCE_EVAL、受支持的 DFT/SCF/MOTION 参数、CELL、COORD 或单帧 XYZ，并依据 KIND/ELEMENT 匹配实际数据库。原输入中没有明确的电荷/多重度继续保持未设置；未恢复的参数会提示。**不支持任意 INP 的完整无损往返，务必保留原输入并核对导入结果。**

当前不包含 SSH、远程提交、CP2K 执行、结果分析、复杂扫描、晶胞优化、混合泛函、k 点或一般性 INP 编辑。采用标准 Python/Qt/ASE/Pydantic API，面向 Windows、macOS、Linux；跨平台安装仍取决于目标系统的 Python 与 Qt 运行环境。升级文件清单及验证范围见 [基组模块升级说明](docs/basis-upgrade.md)。

参考：[CP2K 2026.1 SCF](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/DFT/SCF.html)、[Poisson](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/DFT/POISSON.html)、[cp2k-input-tools 官方源码](https://github.com/cp2k/cp2k-input-tools)。随附 CP2K XML 与回归夹具适用其上游许可证，见 `schemas/CP2K-LICENSE`。
