# Raman 线性响应预条件器与能隙估计

第 06 页 Raman Linear Response 保持原位置，新增第二行：左侧 LINRES / PRECONDITIONER，右侧 LINRES / ENERGY_GAP（Ha），两个标签旁均有中英文 HelpIcon。第一行仍为 EPS 和 MAX_ITER。四个控件使用相同宽度及高度，较窄空间继续由现有 AdaptiveGrid 自动调整，未修改其他页面。

## 参数与联动

| 参数 | 默认值 | 说明 |
|---|---|---|
| LINRES / EPS | 1e-7 | 原有响应收敛精度 |
| LINRES / MAX_ITER | 200 | 原有最大响应迭代次数 |
| LINRES / PRECONDITIONER | FULL_ALL | 六种官方枚举，独立于 SCF/OT |
| LINRES / ENERGY_GAP | 0.1 Ha | 有限正实数，支持科学计数法 |

PRECONDITIONER 支持 NONE、FULL_ALL、FULL_SINGLE_INVERSE、FULL_SINGLE、FULL_KINETIC、FULL_S_INVERSE。项目目标继续为 **CP2K 2026.1**；已核对 [2026.1 LINRES](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/PROPERTIES/LINRES.html) 和 [2026.2 LINRES](https://manual.cp2k.org/cp2k-2026_2-branch/CP2K_INPUT/FORCE_EVAL/PROPERTIES/LINRES.html)，两者的六种枚举及 NONE、0.2 Ha 默认值一致；这是 CP2K 原生默认值。Studio 当前显式默认选择 FULL_ALL / 0.1 Ha，不改动 XML 或目标版本。

- Raman 未勾选：四个控件均禁用，值保留；不生成 Raman 专用 LINRES/POLAR。
- Raman 勾选且 PRECONDITIONER = NONE：EPS、MAX_ITER、PRECONDITIONER 可编辑，ENERGY_GAP 灰显并保留数值；INP 显式写入 PRECONDITIONER NONE，省略无效的能隙估计。
- Raman 勾选且选择其他预条件器：ENERGY_GAP 恢复可编辑，并以用户实际值写入 INP。
- IR 开关不控制这些控件；IR+Raman 联合配置仍在同一份输入中保留 MOMENTS 与 POLAR。

无效的活动能隙字段会阻止生成/导出，禁用字段的编辑草稿按原有方式保留，不阻止纯频率或 IR 导出。模型只保存合法枚举及有限正数。未发生根据 OT 的预条件器、能隙估计或材料名称自动填值的行为。

## 输入生成与校验

```text
&FORCE_EVAL
  ...
  &PROPERTIES
    &LINRES
      EPS 1e-07
      MAX_ITER 200
      PRECONDITIONER FULL_ALL
      ENERGY_GAP 0.1
      &POLAR TRUE
        DO_RAMAN TRUE
        PERIODIC_DIPOLE_OPERATOR TRUE
      &END POLAR
    &END LINRES
  &END PROPERTIES
&END FORCE_EVAL
```

以上为 XYZ 示例；NONE 保留原 Local 偶极算符。EPS/MAX_ITER 和所需 POLAR 打印设置沿用现有生成逻辑。新增参数直接位于 FORCE_EVAL/PROPERTIES/LINRES，未改动 FORCE_EVAL/DFT/SCF/OT。能隙估计使用浮点 round-trip 序列化，保留当前浮点值的精度；未改动其他参数的全局序列化规则。

只有 Raman 启用且选择 FULL_ALL 时，综合检查增加 Info：ENERGY_GAP 应低估实际 HOMO–LUMO 能隙，应测试响应收敛性；此估计独立于 OT，预条件器不保证收敛，也不证明周期 Raman 已数值验证。Info 不计入 Warning、不导致黄色感叹号。其他原有周期性、求解器、占据和精度检查保持不变。最终输入的语义检查还核对实际 LINRES 预条件器及有效能隙值与当前配置一致。

项目及预设保存新增的 `vibrational.linres_preconditioner` 和 `vibrational.linres_energy_gap`。新建项目和旧项目缺失字段时，使用 EPS=1e-7、MAX_ITER=200、PRECONDITIONER=FULL_ALL、ENERGY_GAP=0.1 Ha；已明确保存的旧值保持不变。预设继续采用既有部分配置合并方式，未提供的字段不强制覆盖目标。支持从生成的 INP 导入这两项；NONE 的 INP 未写能隙时，导入采用 CP2K 默认 0.2，之前未参与输入的隐藏草稿值只能通过项目 JSON 恢复。

Raman 精度校验现与默认值对齐：仅在 LINRES EPS > 1e-7 时提示 Warning；等于或小于 1e-7 不触发此项警告。警告仍仅对已启用的 Raman 生效，中英文提示同步更新；参数值、生成的 INP 和其他校验规则不变。

本次默认值调整新增 7 项测试，并更新原有默认值断言。相关 384 项回归测试分组通过，覆盖模型、旧项目和预设、两种周期性及 IR/Raman 组合、目标 XML、单文件与计算包导出、UI 禁用联动、中英切换、任务切换以及 SCF/OT 独立性。用于隔离 Info 或检查语言状态的既有测试显式使用较紧的 LINRES EPS；默认值不触发 LINRES 精度警告；阈值上下相邻浮点值及 Raman 开关的行为另有专项测试。未执行真实 Raman 数值计算。

## 原预条件器功能的验证记录

新增 49 项核心测试和 12 项 Qt UI 测试：六种枚举、单位和科学计数法、非法值、全精度、NONE/XYZ、IR+Raman、OT 严格独立、Info 状态、旧项目/旧预设、INP/项目/预设/计算包往返、控件禁用恢复、两行两列布局、双语 Tooltip、相机/项目状态保持。

修改前捕获的 12 份输入中，8 份非 Raman 输入逐字不变；4 份 Raman 输入只增加显式 PRECONDITIONER NONE，其解析树去除这一个新增默认关键字后与修改前相同。Raman 默认行为、其他任务及 OT 参数未改变。

新增组合通过内置目标 **2026.1 XML**。本机安装 **CP2K 2026.2**，使用它新生成的 XML 和 `--check` 检查“六种预条件器 × NONE/XYZ”的 12 份 IR+Raman 输入，全部成功解析。没有执行实际 SCF、Hessian 或 Raman 数值响应计算；2026.1 可执行程序未安装，未做该版本运行验证。周期 Raman 仍保留实验性支持标记，不保证所选估计适合具体材料或能够收敛。

已通过中英文 Qt offscreen 截图检查，四个输入控件均为 220×32 逻辑像素；Windows/Linux 原生桌面未实机验证。

最终 **1204 项测试分批通过**：原振动/光谱相关 171 项、新增核心 49 项、新增 Qt UI 12 项，以及其余六批 200、170、146、166、177、113 项。两种语言各 **973 项翻译完成、0 项未完成**，TS/QM 已重新编译；compileall 通过。pytest 的警告为既有依赖弃用提示及非法状态测试，与配置检查中的 Warning 等级不同。

## 修改文件

- `core/models.py`：独立字段、六种枚举及双语参数有效性错误。
- `core/generator.py`：按当前 LINRES 设置输出，保持精度及现有共享 Section。
- `core/vibrational.py`：FULL_ALL 的 Info 及最终 INP 参数核对。
- `core/input_import.py`：导入并识别新增关键字，不误报为未支持设置。
- `ui/vibrational_panel.py`：第二行控件、两个 HelpIcon、Raman/NONE 联动及草稿处理。
- `i18n/catalog_sources.py`、中英文 TS/QM：新增 Tooltip 和检查信息。
- 新增 `tests/test_linres_preconditioning.py`、`tests/test_linres_preconditioning_ui.py`。
- `README.md`、`docs/vibrational-analysis.md`、`docs/independent-spectra.md`、本文：更新配置和兼容说明。

SCF/OT 模型、面板、默认值、运行脚本及导出文件结构未修改。
