# 振动分析与光谱

在第 02 页 GLOBAL 选择原生 `RUN_TYPE VIBRATIONAL_ANALYSIS`，第 06 页随即切换为振动分析。ENERGY、GEO_OPT 和振动分析共用同一套 DFT/SCF、结构和 KIND 配置；几何优化与振动设置分别保存，切换任务不会清空参数。

## 支持范围

| 计算内容 / 独立开关 | 生成内容 | 当前适用范围 |
|---|---|---|
| Frequencies & Normal Modes（始终计算） | 顶层 VIBRATIONAL_ANALYSIS；两个强度开关均关闭时 INTENSITIES F | 完整有限差分 Hessian，分子或周期超胞 Γ 点 |
| IR Intensities | INTENSITIES T；DFT/PRINT/MOMENTS ON，MAX_MOMENT 1、PERIODIC F、REFERENCE COM | NONE：孤立分子；XYZ：Berry-phase 周期偶极算符（实验性） |
| Raman Intensities | INTENSITIES T；FORCE_EVAL/PROPERTIES/LINRES/POLAR TRUE、DO_RAMAN T、PERIODIC_DIPOLE_OPERATOR F | NONE 分子或 XYZ 绝缘体 Γ 点超胞（周期路径为实验性）；闭壳层、OT、无展宽且 ADDED_MOS=0 |

XYZ 现已增加周期 IR/Raman 路径：IR 使用 MOMENTS/PERIODIC T，MAX_MOMENT 1；Raman 使用 POLAR/PERIODIC_DIPOLE_OPERATOR T。表中的 F 是 NONE 分子路径，周期路径改为 T。IR 与 Raman 现为两个独立复选框，可单独或同时启用，共用一次 Hessian 流程。部分周期 IR/Raman 和显式 k 点不在本版支持范围。不适用配置会阻止生成和导出，不会静默改变周期性或 SCF。详情与验证范围见[周期光谱支持](periodic-spectra.md)。

## 参数与检查

- DX 默认 `0.01`，使用 CP2K 原生单位 **bohr**；不将结构坐标的 Å 单位套用于位移。
- NPROC_REP 默认 `1`，是**每副本的 MPI 进程数**，不是副本数量。必须为正整数、不超过第 07 页的 MPI 总进程数并整除该总数。OpenMP 线程不计入此关系。CP2K 会调整不均匀的副本划分；Studio 要求整除，以保持用户请求和实际分配一致。标签旁的红色圆形感叹号仅作帮助标记，不代表配置错误；Tooltip 说明 16 个 MPI 进程下的 4/8/16 设置示例及并行副本的内存建议，支持中英文。旧项目缺少字段时采用 1；项目或预设已保存的数值保留。OpenMP-only 时 NPROC_REP 必须为 1。手动填写的 NPROC_REP 与 MPI 总数不兼容时会报告错误，不自动调整任何并行参数，也不根据 Studio 所在操作系统锁定参数。
- PROC_DIST_TYPE 支持 BLOCKED / INTERLEAVED。
- FULLY_PERIODIC 默认关闭，保持手动选择。其含义是保留 Hessian 中的转动自由度，不是设置晶胞周期性；周期晶胞使用 FULLY_PERIODIC F 时给出 Info，不计入警告或阻止导出，不自动开启。
- INTENSITIES 从 `ir_enabled or raman_enabled` 推导；界面已移除重复的只读 INTENSITIES 控件。两个强度开关默认均关闭。
- THERMOCHEMISTRY 默认关闭；仅在用户确认适用的孤立气相分子、FULLY_PERIODIC F 下允许。温度默认 `273.15 K`、压力默认 `101325 Pa`，来自 2026.1 XML 默认值；可明确修改。
- Molden 输出默认开启，Hessian 文件输出默认关闭，均显式生成 ON/OFF；Hessian 文件为 CP2K 二进制格式。Raman 可调整 LINRES EPS（默认 `1e-8`）、MAX_ITER（默认 `200`）、PRECONDITIONER（默认 `NONE`）与 ENERGY_GAP（默认 `0.2 Ha`）。该卡片始终显示，仅在勾选 Raman 时允许编辑；NONE 下能隙输入灰显并保留数值。取消 Raman 后四项均禁用且保留原数值。详见[线性响应预条件器](raman-linres.md)。

EPS_SCF 仅在严格大于 `1E-7` 时产生 Warning；等于或小于该值不触发此项警告，不修改已有 SCF 参数。结构充分优化、残余力和虚频的确认提示作为 Info；MT 的盒大小、电子密度及真空收敛说明也作为 Info。Info 完整显示于实时和综合检查报告，中文前缀为“提示”，不计入 Warning/Error 或步骤完成状态。仅有 Info 且四阶段通过时，第 08 页显示绿色完成。其他独立警告（例如 WAVELET 密度边界、保存的固定原子不参与完整 Hessian）及真实错误保持原等级。Raman 响应尚未数值验证及周期光谱的实验性状态使用 Info；不导致黄色感叹号。该阈值是 Studio 的提示策略，不代表所有体系已达到频率精度或收敛要求。

已保存的 GEO_OPT 固定原子记录仍存在项目中，但不用于此完整振动分析：不会生成 MOTION/CONSTRAINT 或局部 Hessian。返回 GEO_OPT 后原约束恢复生效。选择原子、相机操作及表格显示精度不改变真实坐标或振动输入。

## 保存、预设和导出

项目使用独立 `vibrational` 配置；旧项目缺少此字段时使用上述安全默认值。旧 mode 字段在加载时迁移为两个布尔开关，参数及预设的兼容规则见[独立 IR/Raman 开关](independent-spectra.md)。预设保存和恢复振动参数，默认仍不包含具体结构或固定原子编号；振动任务预设默认归为“自定义”。预览、单文件 INP 和计算包共用统一 Section 生成器。

完整计算包继续包括 input.inp、structure.xyz、基组和赝势数据、项目 JSON、run.sh 和 EXPORT_NOTES.txt。run.sh 沿用第 07 页 MPI/OpenMP 配置。新增任务说明以中英双语写入 EXPORT_NOTES.txt，描述运行后 output.out 中的频率/强度、Molden 模式文件和可选 .hess 文件；不生成或伪造结果，也不绘制展宽后的光谱图。

可导入 Studio 自身生成的四种振动组合 INP（仅频率、IR、Raman、IR+Raman）。缺少必要物性设置或 MODE_SELECTIVE 输入会拒绝导入；其他未支持参数会提示，任意 INP 不保证完整往返。项目 JSON 是完整工作配置的保存形式。

## 规范与回归依据

- [CP2K 2026.1 VIBRATIONAL_ANALYSIS](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/VIBRATIONAL_ANALYSIS.html)
- [2026.1 MOMENTS](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/DFT/PRINT/MOMENTS.html)
- [2026.1 LINRES](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/PROPERTIES/LINRES.html) 及项目内官方 XML 的 POLAR / DO_RAMAN 定义
- [官方 N2 Raman 振动回归输入](https://github.com/cp2k/cp2k/blob/v2026.1/tests/QS/regtest-gpw-2-1/N2_raman.inp)
- [2026.1 振动驱动与副本划分源代码](https://github.com/cp2k/cp2k/blob/v2026.1/src/motion/vibrational_analysis.F)

自动化测试覆盖 XML、生成树、独立强度组合、资源检查、结构约束隔离、项目/预设/支持的 INP 往返、综合检查、双语言 UI 及目录/ZIP 导出。它们不运行 CP2K，不验证频率数值、Raman 收敛或实际材料的物理适用性。

最初接入振动模块时的完整回归记录：**566 passed，835 warnings，277.93 秒**；其中新增 53 项振动与界面测试。使用隔离的数据库缓存和 Qt offscreen 平台；警告主要来自上游 XML 解析器、ASE/NumPy 弃用提示和故意构造非法值的 Pydantic 测试。另已检查中英文 Qt 窗口截图，以及 ENERGY/GEO_OPT 与修改前输入基准逐字一致。未执行真实 CP2K 数值计算，Windows/Linux 原生桌面未实机验证。

## 修改文件

- 模型与生成：`core/models.py`、`core/generator.py`。
- 统一配置检查：新增 `core/vibrational.py`，接入 `core/validator.py`；综合检查沿用原有四阶段服务。
- 保存、导入与导出：`core/presets.py`、`core/input_import.py`、`core/export_notes_generator.py`；项目 JSON 和计算包复用原有序列化和依赖复制逻辑。
- 界面：新增 `ui/vibrational_panel.py`，调整 `ui/main_window.py`、`ui/validation_state.py`、`ui/export_panel.py` 和 `ui/preset_dialogs.py`。
- 翻译：`i18n/catalog_sources.py`、中英文 TS 与 QM。
- 测试：新增 `tests/test_vibrational.py`、`tests/test_vibrational_ui.py` 及官方 Raman 输入夹具；更新 `tests/conftest.py`、`tests/test_navigation_order.py` 和夹具说明。
- 说明：`README.md` 与本文。运行脚本生成器、现有结构/基组数据库解析及 3D 渲染器未改动。

## NPROC_REP 默认值与帮助图标调整（早期记录）

本次仅在 `core/models.py` 把默认值改为整数 4，并在 `ui/vibrational_panel.py` 的原标签旁复用 16px HelpIcon。使用水平标签行，按图标与标签的高度差补偿原标签/输入框间距，保持输入框原有位置；HelpIcon 继续使用深色原生 Tooltip。中英文内容完整包含副本数公式、16 MPI 进程的三种示例及 OOM 建议，实际截图宽度均为 378px，英文高 368px、中文高 319px。

同步更新 catalog、两种语言 TS/QM（697 项翻译均完成），新增 `tests/test_nproc_help.py` 的 15 项测试；原 `tests/test_vibrational_ui.py` 将模拟编辑从输入 4 改为 8，避免把未改变的新默认值误判为一次编辑。未修改输入生成器、MPI 校验器、运行脚本或其他页面。

最终相关回归为 **174 passed，285 warnings，41.85 秒**。覆盖默认值、旧项目与预设保留、手动修改及 INP 更新、MPI=1/2 不兼容和不整除报错、帮助图标位置/完整 Tooltip/双语言、保存加载、运行脚本和计算包；含 ENERGY/GEO_OPT 原输入基准回归。警告来自既有 XML 解析器弃用提示。使用 Qt offscreen 检查界面及 Tooltip，未执行真实 CP2K 数值计算。
