# IR / Raman 独立开关

第 06 页 Calculation Mode 已改为固定绿色 `✓ Frequencies & Normal Modes`、`Always included` 以及两个独立复选框。频率和简正模式始终计算，IR/Raman 默认均关闭，可以只开启其中一个或同时开启。重复的只读 INTENSITIES 控件已删除。没有新增任务或页面。

| IR | Raman | 生成的强度配置 |
|---|---|---|
| F | F | INTENSITIES F，无专用 MOMENTS/POLAR |
| T | F | INTENSITIES T，DFT/PRINT/MOMENTS |
| F | T | INTENSITIES T，FORCE_EVAL/PROPERTIES/LINRES/POLAR |
| T | T | INTENSITIES T，同时生成上述两套物性配置，共用一次 Hessian 流程 |

所有组合均为 RUN_TYPE VIBRATIONAL_ANALYSIS，只有一个顶层 VIBRATIONAL_ANALYSIS，不生成第二份 Hessian 驱动。CP2K 2026.1 [手册](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/VIBRATIONAL_ANALYSIS.html)及[振动驱动源代码](https://github.com/cp2k/cp2k/blob/v2026.1/src/motion/vibrational_analysis.F)分别定义强度入口，并在同一位移循环中独立读取偶极矩、极化率结果。

NONE 沿用原分子算符；XYZ 沿用 Berry-phase 算符。部分周期、显式 k 点、整数占据及 Raman 闭壳层 OT 等限制保持原有范围。开启 IR 不会触发未请求的 Raman 求解器或 LINRES 精度检查；联合开启时两套检查均执行。实验性周期响应及尚未实际计算的信息仍使用 Info，不会被 XML 通过替代为数值验证通过。不会自动修改 FULLY_PERIODIC、Poisson、晶胞、原子坐标或并行参数。

Raman Linear Response 卡片始终显示。只有 Raman 复选框勾选时，LINRES/EPS、LINRES/MAX_ITER 和 LINRES/PRECONDITIONER 可以编辑；LINRES/ENERGY_GAP 还要求预条件器不是 NONE；IR 开关不控制它们。取消 Raman 后禁用输入，但保留用户已填数值和原来的无效编辑草稿处理方式，再次启用可继续编辑。LINRES EPS/MAX_ITER 默认值仍为 **1e-8 / 200**。新增的响应预条件器及其独立能隙估计见[配置说明](raman-linres.md)，不覆盖用户原有 EPS/MAX_ITER。

## 保存与迁移

新项目和预设保存：

```json
{
  "vibrational": {
    "ir_enabled": true,
    "raman_enabled": true,
    "linres_eps": 1e-8,
    "linres_max_iter": 200
  }
}
```

不序列化 mode、INTENSITIES 或显示标签。INTENSITIES 始终由两个开关求或得到。

| 旧 mode | ir_enabled | raman_enabled |
|---|---|---|
| FREQUENCIES | false | false |
| IR | true | false |
| RAMAN | false | true |

同时兼容大小写/首尾空白，以及 Frequencies & Normal Modes、IR_INTENSITIES、Raman Intensities 等等价名称。未知旧枚举会明确报错，不会默认为纯频率。若文档同时包含旧 mode 和显式新开关，以显式新开关为准。

迁移对完整项目和部分预设 patch 使用同一函数，保留 DX、LINRES 等其他字段，不修改原始文档。预设在与当前配置合并**之前**规范化旧字段，避免当前的默认 False 遮蔽旧 IR/RAMAN 模式；规范化不会为未提供的参数注入默认值。仅保存一个新开关的部分 patch 也不会重置另一个开关。项目及预设格式版本号保持兼容。

## 生成与导出

Section 树逐项启用所需设置，不做全局字符串替换。共享的 DFT/PRINT、PROPERTIES/LINRES 与 POLAR 通过 get-or-add 合并，保留独立功能原有的其他关键字和子 Section，不产生重复节点；取消某开关不会删除其他功能拥有的配置。

INP 导入现可识别 MOMENTS 与 POLAR 同时启用的组合，仍拒绝 INTENSITIES T 但无所需物性的输入。导入、综合检查、单独 INP、计算包继续核对最终解析树的两个请求，任一个缺失或算符错误均不会通过。预览和导出共用相同生成器。run.sh、MPI/OpenMP、依赖文件复制、结构精度及结果文件处理不变，EXPORT_NOTES.txt 已更新为独立或联合强度说明，不生成任何伪造结果。

## 验证范围

新增 37 项核心和 9 项 Qt UI 测试，覆盖四组合 × NONE/XYZ、旧项目和部分预设迁移、重复 Section 防护、独立功能内容保留、条件校验、联合 INP 往返、目录/ZIP 导出、Raman 输入禁用/恢复、实际预览去抖更新、双语切换、综合检查状态及相机保持。修改前捕获的 **10 份 INP**（其他四任务，以及 NONE/XYZ 的原三种互斥选择）经迁移后逐字一致。

NONE 和 XYZ 联合输入已通过项目内目标 **2026.1 XML**，另通过本机 **CP2K 2026.2** 可执行程序刚生成的 XML 和 `--check`，两个输入解析返回码均为 0。2026.1 可执行程序未安装，未做该版本实际运行测试。**没有运行 SCF、有限差分 Hessian 或实际 IR/Raman 强度计算**；尤其周期联合 Raman 仍为实验性输入支持。中英文 Qt 界面经过 offscreen 截图检查，Windows/Linux 原生桌面未实机验证。

独立开关改造时全套 **1143 项测试分批通过**：振动相关原有 125 项、新增核心 37 项及 Qt UI 9 项，其余六批分别 200、170、146、166、177、113 项。迁移测试后来增加的旧预设磁盘读取路径已单独重跑 7 个对应用例通过，未重复计入全套总数。两种语言各 **968 项翻译完成，0 项未完成**，TS/QM 已重新编译；compileall 与页面初始化检查通过。pytest 的警告来自既有 cp2k-input-tools/ASE 等依赖的弃用提示及故意构造非法状态的测试，与软件配置 Warning 等级不同。

## 修改文件

- `core/models.py`：布尔开关、派生强度及旧 mode 迁移。
- `core/presets.py`：部分预设在合并前迁移。
- `core/generator.py`：独立/联合物性生成与共享 Section 合并。
- `core/vibrational.py`：两套条件校验和最终 INP 语义检查。
- `core/input_import.py`、`core/export_notes_generator.py`：联合输入导入和说明。
- `ui/vibrational_panel.py`：固定基础模式、两个复选框及 Raman 控件启用逻辑。
- `i18n/catalog_sources.py`、`i18n/cp2kstudio_en_US.ts/.qm`、`i18n/cp2kstudio_zh_CN.ts/.qm`：双语资源。
- 新增 `tests/test_independent_spectra.py`、`tests/test_independent_spectra_ui.py`、`tests/vibrational_helpers.py`；更新原振动/周期光谱四个测试文件及 `tests/test_dft_defaults_help.py`。
- `README.md`、`docs/vibrational-analysis.md`、`docs/periodic-spectra.md`、本文：更新现行说明。
