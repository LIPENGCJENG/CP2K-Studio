# Poisson 参考表与孤立分子周期性

第 03 页的 Poisson 卡片在现有下拉框正下方显示四列六行只读参考表：POISSON_SOLVER、PERIODIC、推荐适用场景、核心约束与注意事项。数据按下表顺序排列，单元格和表头严格单行，长文本由 Qt 绘制为末尾省略号，原始内容不被缩短。数据行固定 28px、表头 28px，含边框总高度 198px；列宽随可用空间分配，约 18/17/27/38，窄窗口优先保留名称和周期性列表空间。没有内部水平或垂直滚动条。

| 求解器 | PERIODIC | 场景概要 | 约束概要 |
|---|---|---|---|
| PERIODIC | XYZ | 三维晶体、无定形体相、固液界面超胞 | 不对称 Slab 偶极；三维晶胞优化需应力支持 |
| WAVELET | NONE, XZ, XYZ | 孤立分子/团簇/离子对、Y 法向二维正交表面 | NONE 立方盒、XZ 几何条件、密度衰减、FFT 网格限制及 FFTSG |
| MT | NONE, XY, XZ, YZ | 带电团簇、有限聚合物链段、二维表面 | 电子密度范围参考 L > 2D；非周期方向正交要求 |
| ANALYTIC | NONE, Z, XY | 一维周期体系 | 密度范围、截面形状和非周期方向几何条件 |
| MULTIPOLE | NONE | QM 区域静电退耦，如 QM/MM | 正交 QM 盒及特定边界需求；当前仅供参考 |
| IMPLICIT | ANY | 隐式溶剂、恒电势电极及界面 | 依赖具体模型的边界和网格；当前仅供参考 |

每种求解器在 `ui/widgets/poisson_reference.py` 的统一不可变数据结构中保存周期性、场景和约束消息。单行完整文本及富文本 Tooltip 从同一份数据生成，翻译沿用 QTranslator 和 TS/QM。悬停场景/约束列可查看粗体标题和完整列表；实际检查中原生 Tooltip 宽 400px，WAVELET 约束英文高 215px、中文高 143px。移出后由 Qt 自动隐藏。表头及名称/周期性单元格也提供完整文本提示。页面不增加表格外的说明。

## 规范核对与既有校验差异

- [CP2K 2026.1 官方 Poisson 规范](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/DFT/POISSON.html)明确 WAVELET 支持 NONE、XZ、XYZ，要求 FFTSG；MT 为 0D/2D、MULTIPOLE 为 0D、IMPLICIT 覆盖各维度。WAVELET 非周期立方盒条件也与 v2026.1 `src/pw/ps_wavelet_methods.F` 的非立方盒报错一致。
- **ANALYTIC 的方向不是本次新增的排他限制**：表中按需求展示 NONE/Z/XY 参考取向，官方总览概括为 0D/1D/2D。现有应用校验按维度判断，仍允许 NONE/X/Y/Z/XY/XZ/YZ，拒绝 XYZ；它没有完整实现所有具体几何条件。本次不收紧或放宽该校验。Tooltip 明确说明这一差异，具体方向与几何应继续核对实际版本规范。
- MULTIPOLE、IMPLICIT 仅作参考，现有下拉仍只提供 PERIODIC、MT、WAVELET、ANALYTIC；没有新增 QM/MM、隐式溶剂或恒电势配置流程。Tooltip 对未开放选项有说明。
- ANY 是参考覆盖范围标识，不是可写入 CP2K PERIODIC 的枚举。表格不会把该值写入配置。

本次只修改表格组件、翻译资源及相应测试和本文，未修改 DFT 面板控件、数据模型、生成器、Poisson 校验、原子数据或其他页面。表格无参数写回信号，点击不选择求解器，也不使综合检查失效。原表没有所选求解器行高亮绑定，本次保持原交互。

## 原有分子周期性功能（保持不变）

第 01 页使用持久化结构类型判断 NONE 锁定：明确的 XSD Molecule 或用户明确确认的孤立分子才锁定。周期晶体和 Slab 仍可选择周期方向，旧项目和普通 XYZ 不凭 NONE 值自动锁定。计算盒、晶胞和原子编辑不因锁定禁用。详细的项目、预设和导入行为见 [XSD 导入说明](xsd-import.md#周期性和计算盒)。

计算盒已增加真空边距、立方体和手动三种模式。PERIODIC NONE 下 WAVELET 对非立方盒报告兼容性错误，用户可明确选择立方体模式重新生成；MT 不增加该限制。参见[计算盒模式和检查范围](simulation-box.md)。

早期加入参考表和分子锁定时曾调整 DFT、结构、模型及预设模块；这些内容不是本次四列表格改造的修改范围。相应历史测试覆盖真实 H₂O/rutile/Slab XSD、未分类 XYZ 确认、锁定后的编辑和项目重开及预设冲突。

早期升级的历史完整测试记录为 636 passed；不代表本次改造的测试数量。本次测试使用 Qt offscreen，未进行 Windows/Linux 原生桌面实机检查，也未运行 CP2K 数值计算。

## 本次修改文件

本次相关回归为 **139 passed，335 warnings，96.23 秒**，另以 `QT_SCALE_FACTOR=2` 执行 **12 项布局/原生 Tooltip 测试，全部通过**。专项表格与工作流测试共 23 项。覆盖 280/360/620/980px、两种语言、28px 固定行高、原文保留与省略绘制、原生提示完整显示及移出自动隐藏，以及 ENERGY/GEO_OPT/CELL_OPT/VIBRATIONAL_ANALYSIS 的检查状态、相机、保存、预设和导出不变。768 项中英翻译全部完成并编译。警告来自既有解析器弃用提示及故意非法 MPI 测试。GUI 使用 Qt offscreen；未做 Windows/Linux 原生桌面实机显示验证。

- `ui/widgets/poisson_reference.py`：统一六种求解器数据、四列单行布局、固定高度、动态列宽和完整 Tooltip。
- `i18n/catalog_sources.py`、中英文 TS/QM：新表头、场景、约束和参考范围说明。
- `tests/test_poisson_reference_ui.py`：更新旧的三列/自动换行断言，保留原有分子周期性测试。
- 新增 `tests/test_poisson_reference_redesign.py`：数据与 Tooltip 一致性、原生提示显示/离开隐藏、表格点击、四种任务、语言与分栏变化、保存/预设/导出不变。
- 本文：新布局及规范差异说明。
