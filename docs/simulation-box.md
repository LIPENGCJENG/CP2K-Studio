# 非周期计算盒：三种生成模式

第 01 页原有“生成计算盒…”按钮打开一个共享弹窗。模式使用稳定内部值，界面名称随 English/简体中文切换，其他页面布局不改变。

| 模式 | 参数 | 计算规则 |
|---|---|---|
| 每侧真空边距 / Vacuum Padding | 每侧 d，首次 10.000 Å | 每轴长度为该轴原子跨度 + 2d |
| 立方体 / Cubic Box | 独立保存的每侧 d，首次 10.000 Å | 三轴长度统一为最大原子跨度 + 2d |
| 手动输入 / Manual Input | A、B、C 正尺寸 | 生成对角矩阵 diag(A, B, C) |

手动模式尚无保存值时，读取有效现有晶胞的矢量长度；没有有效晶胞时按原子跨度和默认边距给出建议。模式切换保留本弹窗的输入；确认成功后分别保存两种边距、手动尺寸和当前模式。手动盒不能小于任一方向的原子跨度，错误会列出 X/Y/Z 方向并留在弹窗内。正交手动盒不替代页面下方的完整晶胞矢量编辑。

三种模式共用 `generate_simulation_box()`：从当前真实笛卡尔坐标计算包围盒中心，将其平移到新盒长的一半，不使用旧盒长叠加真空。元素、顺序、KIND、原子 ID、相对位置、约束和周期性保持不变；生成器返回新结构，不就地修改源对象。确认成功后才更新项目、3D、坐标/晶胞表格、INP、修改标记及综合检查状态。取消或失败不应用修改。按钮对非空 PERIODIC NONE 结构持续可见。

项目 JSON 的 `structure.box_generation` 保存 `mode`、`vacuum_margin`、`cubic_margin`、`manual_lengths`；旧 `box_vacuum_margin` 字段继续兼容并对应真空边距模式。旧项目只保存该边距时迁移到真空模式；没有模式字段时不重算实际晶胞或平移坐标。旧 `generate_nonperiodic_box(structure, vacuum)` API 保留，委托同一引擎处理真空模式。

## 求解器检查范围

非周期 WAVELET 新增正交立方盒的配置错误，并提示“生成计算盒 → 立方体”，不静默更改求解器或晶胞。已有正向轴对齐限制、FFTSG 和密度边界提示保留。新立方限制只作用于 PERIODIC NONE，不扩大到 XZ/XYZ 等周期分支。

依据是 [CP2K v2026.1 的 ps_wavelet_methods.F](https://raw.githubusercontent.com/cp2k/cp2k/v2026.1/src/pw/ps_wavelet_methods.F)：WAVELET0D 分支检查三个实空间网格间距并会中止非等距情形。Studio 的立方几何检查用于提前发现此类配置；不代表已执行 CP2K、验证电子密度边界或完成收敛测试。MT 的非立方正交盒仍允许使用，其电子密度尺寸要求继续以 Info 提醒，不影响检查状态；原子包围盒的真空边距不等于电子密度范围验证。周期性范围及 FFTSG 参考 [CP2K 2026.1 Poisson 文档](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/DFT/POISSON.html)。

## 修改文件与验证

- `core/models.py`：三模式可序列化状态与旧边距迁移。
- `core/structure.py`：统一长度计算、手动尺寸检查与居中；保留旧 API。
- `core/validator.py`：非周期 WAVELET 立方盒兼容性错误。
- 新增 `ui/simulation_box_dialog.py`；调整 `ui/structure_panel.py` 的原按钮入口。
- 同步更新 catalog、中英文 TS/QM（696 项已完成翻译）、README 和 XSD/Poisson 说明。
- 新增 `tests/test_simulation_box_modes.py` 的 16 项测试和 `tests/simulation_box_helpers.py`；迁移原计算盒、XSD、周期性及标签测试到统一弹窗，并将验证 WAVELET 的结构明确生成为立方盒。

针对性测试先通过原有相关 143 项和新增 16 项，覆盖三种几何、居中/重复生成、过小方向错误、旧项目迁移、独立参数恢复、取消、双语言、真实模态确认、原子选择/固定、三个计算任务、XML 检查和计算包导出。Qt offscreen 检查中英文三种模式截图；未实际运行 CP2K 数值计算，未进行 Windows/Linux 原生界面实机检查。

完整回归：**700 passed，963 warnings，431.29 秒**。警告来自现有 XML/ASE 弃用提示及故意构造非法数据的测试，没有失败用例。中英文 TS/QM 均为 696 项已完成翻译。
