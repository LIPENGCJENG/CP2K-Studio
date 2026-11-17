# 表面偶极校正

第 03 页 DFT 的 Poisson 求解器参考表下方新增独立卡片 **Surface Dipole Correction / 表面偶极校正**，只包含启用开关和 SURF_DIP_DIR 下拉框，标题旁复用现有 HelpIcon。中英文标题保持单行，方向标签和下拉框水平对齐。

## 配置及生成

- `dft.surface_dipole_correction` 默认为 `false`。
- `dft.surf_dip_dir` 默认为 `Z`，仅允许 X/Y/Z，对应笛卡尔表面法向。默认 Z 是初始配置，不是自动识别的真空方向。
- 开关只控制方向控件是否可编辑；关闭后方向值继续保留，重新开启会恢复原选择。
- 启用时由统一 Section 生成器直接在 FORCE_EVAL/DFT 写入：

```text
SURFACE_DIPOLE_CORRECTION T
SURF_DIP_DIR Z
```

方向使用用户实际选定的 X/Y/Z。它们不在 POISSON 子节中，不新增校正 Section。关闭时两个关键字都不输出，四种任务的默认输入保持逐字不变。

不新增 SURF_DIP_POS、SURF_DIP_SWITCH 或其他控制参数，校正位置等沿用 CP2K 默认行为。开关不改变 CELL/PERIODIC、POISSON/PERIODIC、POISSON_SOLVER、原子坐标或晶胞。

## 校验与适用范围

[CP2K 2026.1 官方 DFT 规范](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/DFT.html)将这两个关键字定义在 DFT 根层，表面法向须平行笛卡尔轴。功能用于非对称周期 Slab 的人工电场补偿，不代表关闭法向周期性。

方向枚举由统一模型校验；非法值是 Error。关闭时没有新增适用性提示。启用后：

- XYZ + PERIODIC 正常生成；Info 提醒用户确认非对称 Slab、正确法向和足够真空。
- NONE 的孤立分子显示 Info，说明通常不适合此类校正，请复核是否关闭。
- 一维/二维部分周期性显示 Info，要求复核 Poisson 边界处理与校正的兼容性；这不表示已证明组合可运行。
- XYZ 下使用其他求解器时显示 Info，请复核组合；不静默改为 PERIODIC。

这些是一般物理适用性提示，不计入 Warning/Error，也不触发黄色感叹号。已有 Poisson、晶胞和其他真实错误/警告继续按原规则汇总，不因新功能而降级。软件不判断 Slab 是否对称、哪个方向有真空，也不验证实际电子密度在真空中的衰减；XML 通过不等于物理适用性或数值收敛已验证。

## 保存及导出

两个字段随 DFT 配置自动进入项目 JSON 和个人预设，旧项目缺少字段时采用关闭/Z 默认值。未包含新字段的预设沿用现有补丁合并语义，不清空当前未指定的设置。支持导入 Studio 自身生成的这两个 DFT 关键字。

实时预览、独立 INP 和完整计算包复用同一生成器；脚本、依赖复制及 MPI/OpenMP 配置不变。语言切换只更新标题、复选框文字、帮助和既有 Info 报告，不改变开关、方向、INP、Dirty 状态、检查结果或相机。

## 修改文件

- `core/models.py`：新增两个 DFT 配置字段。
- `ui/dft_panel.py`：新卡片、复用控件和帮助图标、加载及启用状态同步；为原 Poisson 卡片提供稳定属性引用。
- `core/generator.py`：启用时只追加两个 DFT 根层关键字。
- `core/validator.py`：新增条件式 Info 提示，保留已有严重等级汇总逻辑。
- `core/input_import.py`：读取两个受支持字段。
- `i18n/catalog_sources.py`、中英文 TS/QM：标题、帮助和校验信息。
- `tests/test_surface_dipole.py`、`tests/test_surface_dipole_ui.py`：新增专项测试。
- `tests/test_poisson_reference_ui.py`、`tests/test_dft_defaults_help.py`：从“最后一张卡片”改为稳定 Poisson 卡片引用，保留原断言。
- README 及本文。

专项测试覆盖默认值、三种方向、四种任务、关闭后保留设置、根层关键字、额外参数缺席、Info 等级与原错误保留、历史项目/预设、支持的 INP 往返、完整计算包、中英切换、卡片布局和检查状态。当前本机 PATH 未发现 CP2K，未执行真实 Slab 数值计算；使用目标 2026.1 XML 和 Qt offscreen 验证。Windows/Linux 原生桌面未实机检查。

本次新增 42 项专项测试。相关回归为 **316 passed，733 warnings，212.64 秒**，使用隔离数据库缓存，覆盖本功能、原 Poisson 表、DFT/SCF 布局、模型、四种任务生成、目标 XML、综合检查、保存/预设/导出及双语界面。英文标题调整为单行后的最终 UI 复测为 **9 passed，54 warnings，15.62 秒**。775 项中英翻译全部编译完成；人工检查了中英文卡片截图。四种任务默认关闭时的输出均与本次修改前逐字一致。警告来自既有解析器/NumPy 弃用提示以及故意构造的非法值测试。
