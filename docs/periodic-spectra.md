# XYZ 周期体系的 IR / Raman 输入支持

第 06 页始终计算频率和简正模式，IR、Raman 使用两个独立开关，可同时启用。根据当前结构的 CELL/PERIODIC 派生物性路径，不改变周期性或科学计算默认值。旧 mode 数据的兼容规则见[独立强度开关说明](independent-spectra.md)。

| 周期性 | IR | Raman |
|---|---|---|
| NONE | 原分子 MOMENTS：PERIODIC F、MAX_MOMENT 1、REFERENCE COM | 原分子 LINRES/POLAR：DO_RAMAN T、PERIODIC_DIPOLE_OPERATOR F |
| XYZ | MOMENTS ON、PERIODIC T、MAX_MOMENT 1 | POLAR T、DO_RAMAN T、PERIODIC_DIPOLE_OPERATOR T |
| 部分周期 | 阻止强度输入生成及导出，保持边界条件 | 同左 |

IR 的 MOMENTS 位于 FORCE_EVAL/DFT/PRINT；Raman 的 POLAR 位于 FORCE_EVAL/PROPERTIES/LINRES。为每个勾选的强度选项生成一份相应物性设置；同时启用时共用一个顶层 VIBRATIONAL_ANALYSIS。LINRES EPS/MAX_ITER、位移及副本参数继续取用户值。FULLY_PERIODIC 只控制 Hessian 转动模式处理，不设置边界条件或选择偶极算符，仍由用户独立控制；周期晶体关闭该选项时给出 Info，不计入警告。

当前生成器固定使用 Quickstep/GPW、隐式 Γ 点超胞。周期光谱面向有电子能隙的绝缘体，不通过 OT 的 ENERGY_GAP 参数推断实际带隙。周期强度配置启用展宽或 ADDED_MOS 时阻止生成；整数完全占据的 DIAGONALIZATION 可以生成周期 IR。Raman 继续使用既有闭壳层 OT 子集。无法由静态配置确定的能隙、CP2K 编译能力、极化分支连续性及尚未数值验证状态作为 Info，不计入黄色警告。数值阈值和固定原子等其他警告保持各自含义；周期晶胞使用 FULLY_PERIODIC F 的说明为 Info。

项目和预设保存两个强度开关及其参数，结构周期性决定下一次生成的算符。强度开关或周期性切换不残留仅由已取消选项需要的 PRINT/PROPERTIES，也不改 Poisson 求解器或晶胞。导入 Studio 可表达的 INP 时核对算符与边界条件，拒绝悄悄把非周期算符转换为周期算符。显式 KPOINTS 输入不在本版周期光谱导入/导出范围，包含显式 Γ 点；本版仅承诺隐式 Γ 点路径。

综合检查、单独 INP 和完整计算包除了 XML 检查，还对最终解析树进行语义核对：INTENSITIES、FULLY_PERIODIC、Quickstep/GPW、CELL/POISSON 周期性、所需物性算符及显式 KPOINTS。错误算符即使通过 XML 也不能导出。通用 XML 解析器保持原有职责，未对任意 CP2K 输入全局施加 Studio 的计算路径限制。

英文/中文模式提示、FULLY_PERIODIC 帮助、周期 Raman 信息图标、校验报告和 EXPORT_NOTES.txt 已同步。运行脚本、MPI/OpenMP 参数、坐标精度、原子固定及结果文件生成逻辑不变。支持 IR+Raman 联合输入；没有添加声子色散、Phonopy 或金属光谱。

## 规范依据

- [CP2K 2026.1 MOMENTS](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/DFT/PRINT/MOMENTS.html)：周期偶极矩、最高阶数和极化多值性的定义。
- [CP2K 2026.1 VIBRATIONAL_ANALYSIS](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/VIBRATIONAL_ANALYSIS.html)：INTENSITIES 与 FULLY_PERIODIC 的职责。
- [2026.1 周期/局域偶极算符源代码](https://github.com/cp2k/cp2k/blob/v2026.1/src/qs_linres_op.F)：polar_operators 按 do_periodic 选择 Berry-phase 或 Local 路径。
- [2026.1 极化率实现](https://github.com/cp2k/cp2k/blob/v2026.1/src/qs_linres_polar_utils.F)：读取 PERIODIC_DIPOLE_OPERATOR，计算及打印极化率。
- [2026.1 MOMENTS 实现](https://github.com/cp2k/cp2k/blob/v2026.1/src/qs_moments.F)：非均匀轨道占据的实现限制。
- 项目内 `schemas/cp2k_input_2026.1.xml` 的 POLAR 定义确认 PERIODIC_DIPOLE_OPERATOR 与 DO_RAMAN 存在。未修改 XML 文件或目标版本。

## 验证范围

新增测试使用明确标注的周期水分子超胞静态配置，不把该配置当作材料光谱数值基准。覆盖 NONE/XYZ × 频率及强度组合、部分周期限制、占据限制、模式切换、语义错误注入、项目/预设/INP 往返、目录/ZIP 导出、双语实时提示、综合检查与相机状态。

修改前捕获的 7 份输入（ENERGY、GEO_OPT、CELL_OPT、MD，以及 NONE 的三个振动模式）修改后逐字一致。新增组合通过项目内目标 **2026.1 XML** 解析。本机实际安装的是 **2026.2**，另用该可执行程序的 `--xml` 输出解析新增 IR/Raman，再分别运行 `cp2k.psmp --check -i ...`，两者均返回 0。这些只验证输入解析，不运行 SCF、位移 Hessian 或光谱计算；未安装的 2026.1 可执行程序没有做运行测试。没有更换项目目标 XML。

**周期 Raman 及周期 IR 的完整数值强度计算尚未验证**。未确认任意 CP2K 编译均支持；未确认具体材料有能隙、达到驻点或响应收敛。实际计算时应检查 CP2K 日志、极化/极化率响应及有限差分稳定性。Windows/Linux 原生界面未实机验证。

### 自动化测试结果

首次接入周期光谱时覆盖全套 **1097 项测试**，采用 Qt offscreen 分批执行；独立开关改造后的最新结果见 [independent-spectra.md](independent-spectra.md)。当时新增周期光谱测试 **42 项**。振动与周期光谱专项共 **125 passed**。其余六批分别覆盖 200、170、146、166、177、113 项。第二、三批各发现一处既有测试预期过时，修正后对应数据库模块 **17 passed**、工作流模块 **11 passed**；其他用例原已通过，按唯一用例计数，全套均通过。未对这些测试重复计数。

两种语言各 **966 项翻译完成，0 项未完成**；TS/QM 已重新编译。`compileall` 通过。中英文界面经离屏截图检查，模式提示正常显示，无水平溢出。测试产生的警告来自既有 cp2k-input-tools/ASE/Pydantic 等依赖或非法输入测试，与软件综合检查中的 Warning 等级不同。

## 修改文件

- `core/vibrational.py`、`core/generator.py`：统一计算路径、科学适用性和最终输入语义核对。
- `core/input_import.py`、`core/input_export.py`、`core/project_io.py`、`core/comprehensive_check.py`：复用路径检查，保持各保存/导出流程。
- `core/export_notes_generator.py`：去除旧的“不支持周期光谱”说明，写入实际路径和实验性验证范围。
- `ui/vibrational_panel.py`、`ui/main_window.py`：当前周期上下文、紧凑模式提示及 HelpIcon。
- `i18n/catalog_sources.py`、中英文 TS/QM：沿用现有翻译机制。
- `tests/test_periodic_spectra.py`、`tests/test_periodic_spectra_ui.py`、`tests/test_vibrational.py`：新增回归，原周期拦截测试改为部分周期拦截。
- `tests/test_databases.py`、`tests/test_layout_workflow.py`：全套回归中修正两处旧测试预期：同内容的 Homebrew 数据文件不必与内置文件有相同路径；顶栏应包含此前新增的环境检测入口。未修改相应生产逻辑。
- `README.md`、`docs/vibrational-analysis.md`、本文：更新当前支持范围。
