# CP2K Studio UI/UX 优化交付

本次只调整 PySide6 界面及交互。`core/` 中全部 Python 模块与优化前源码包逐字节一致，统一模型、CP2K 输入生成、XML、文件引用修复、依赖检查、运行脚本和预设数据格式没有改写。没有新增依赖，也未添加现有模型尚不支持的科学功能。

## 设计规范与复用组件

- `ui/theme.py` 管理色彩及基础尺寸，`ui/styles.qss` 管理整个应用、Qt 对话框和弹出列表的外观。沿用深海蓝和青色；使用系统字体、Qt Fusion 控件及清晰的焦点/禁用/错误状态。主题按需安装一次，避免每次创建窗口都重置整个应用样式。
- 页面边距 20px、卡片内边距 16px、卡片间距 16px、字段间距 12px，采用 4px 基准。卡片为 8px 圆角、低对比边框，标题处于内部，不切断外框。
- `SectionCard` 用 QFrame 统一八页容器；`AdaptiveGrid` 在空间足够时双列，在较窄时单列，标签位于控件上方。下拉框/路径可填充，普通数值框推荐宽度 220px、上限 240px；右侧预览保留至少 340px，设置区至少 360px。
- `NumericField` 仍是 QLineEdit，保留原来的 float/int 解析及 Pydantic 校验，不改精度，不使用会限制科学计数法的默认 DoubleSpinBox。只读单位标签预留独立边距，不接收焦点和鼠标输入，不参与 text()/collect()/项目或预设序列化。重新加载项目时清除旧字段错误样式，包含当前停用的几何优化或外层 SCF 字段。
- 表格 `StatusBadgeDelegate` 与导航 `StepIndicatorDelegate` 只绘制图形/文本，不新增逐行状态 Widget。状态同时有文字/符号与颜色，表格状态的完整说明使用 Tooltip。后续按要求移除顶部工具栏与左侧导航的悬停提示，导航详情保留在无障碍说明和配置报告中；其他参数帮助不变。

单位沿用既有含义，不提供切换或隐式换算：CUTOFF/REL_CUTOFF 为 Ry，EPS_SCF 为 Ha，电子温度为 K，力阈值为 Ha/Bohr，位移阈值为 Bohr；EPS_DEFAULT、整数计数等不加单位。结构表格仍明确标注 Å。

## 九项问题的处理

| 项目 | 实际实现 |
|---|---|
| 1. 统一设计系统 | 样式从主窗口迁移到主题模块/QSS，统一背景、边框、字体、卡片、间距、聚焦、Hover、Pressed、Disabled、Error 与提示样式。 |
| 2. 原生滚动条 | 水平/垂直均为 8px，圆角滑块，无箭头、无重复外框、无 add/sub-page 色块；覆盖设置区、代码、表格、树、下拉及完成列表。滚轮和滑块拖动经过测试。 |
| 3. 预设箭头错位 | InstantPopup 不变；仅一个 SVG menu-indicator，定位到文字右侧垂直居中、距边缘 10px；按钮额外预留 30px。点击整个按钮或箭头都走原菜单。 |
| 4. 页面功能卡片 | 八页使用相同 SectionCard。GLOBAL 分基本信息与任务；DFT 分电子状态/方法/MGRID/Poisson；SCF 分基本/方法及活动 OT/DIAGONALIZATION、混合/展宽；几何优化分优化器与阈值；运行环境分平台/资源/统计/命令；导出分状态/交付/预设。结构、数据库也按现有功能分组。 |
| 5. 数值宽度与响应式 | CHARGE/MULTIPLICITY、CUTOFF/REL_CUTOFF、MAX_FORCE/RMS_FORCE、MAX_DR/RMS_DR 等采用双列。窄设置栏退回单列，必要时纵向滚动，不挤掉预览。SCF 活动栈按当前页计算高度，避免隐藏的对角化卡片撑出空白。SpinBox 上下按钮有 22px 点击宽度及统一图标。 |
| 6. 单位与科学计数法 | 单位为不可编辑的独立标签，标签只保留参数名。科学计数法和浮点精度、保存和生成流程保持一致，错误草稿仍能看到并修正。 |
| 7. 结构视图 | 保留 QPainter/NumPy 引擎，默认关闭元素标签。右上角固定小工具栏控制标签、实际晶胞 A/B/C 视角及复位；后续按要求移除投影切换按钮，保留渲染投影逻辑。增加滚轮缩放、左下角随相机旋转而不随缩放变形的 XYZ 指示器；无有效晶胞时禁用 ABC。结构页移除晶胞与坐标卡片说明，坐标表隐藏 KIND 列但保留映射，元素列按内容定宽，坐标列分配剩余宽度。所有相机操作不改原子、坐标或晶胞。 |
| 8. 基组与赝势 | 数据库管理卡片通过标题旁 ⓘ 展示动态加载信息；候选筛选与 KIND 表格合并为「基组与赝势配置」卡片，保留内部小标题和分隔线。筛选控件支持四/二/一列重排。KIND 窄列，基组/赝势分配主要宽度，状态为短徽章和完整 Tooltip，表格高度随实际行数调整。推荐窗口右侧「当前已选配置」卡片按实际 KIND 展示基组及赝势，支持自然换行、完整名称 Tooltip 和独立滚动；左右外框等高、顶部对齐，保留 16px 可拖动间距。推荐表格的说明列填满剩余宽度。被筛选排除的已选记录仍固定保留，并显示边框/说明；等价记录去重不误报为筛选排除。 |
| 9. 左侧状态导航 | 前七步复用实时本地校验报告，区分 Ready、Warning、Error/Incomplete、Not applicable、Not checked。ENERGY 时几何优化为不适用且停用编辑，保留已有值；GEO_OPT 时可编辑。第 08 步仅在主动点击「综合检查」后显示四阶段结果；配置、XML、依赖文件变更或项目/预设加载即恢复未检查，标记不持久化。状态不以“访问过页面”为依据，综合检查调用 XML 服务但不运行 CP2K。 |

q 匹配仅显示 `✓ q=N 匹配`，其他警告/错误优先。Tooltip 明确说明这不是物理适用性、数值精度或收敛验证。导航的 Ready 也是本地配置完整，不代表已经执行计算或完成收敛测试。

## 文件清单

新增：

- `ui/theme.py`、`ui/styles.qss`。
- `ui/widgets/__init__.py`、`section_card.py`、`numeric_field.py`、`status_badge.py`。
- `ui/assets/chevron.svg`、`chevron-up.svg`、`check.svg`（原生 SVG，无图片或新渲染依赖）。
- `ui/validation_state.py`。
- `tests/test_ui_ux.py`。
- `scripts/capture_ui.py`：可重复生成截图及总览。
- 本说明及 `docs/images/ui-ux/` 截图。

修改：

- `ui/main_window.py`：接入主题、卡片分组、数值单位、导航 delegate/状态、草稿字段反馈及模块适用性。
- `ui/forms.py`：复用原字段映射/信号/解析，支持卡片与自适应栅格、单位显示，减少不必要的样式重绘。
- `ui/dft_panel.py`、`ui/scf_panel.py`：按现有参数分卡片，SCF 只显示活动分支、停用未启用的外层/温度输入。
- `ui/structure_panel.py`、`ui/structure_view.py`：结构分组、相机与标签、投影、缩放、ABC 与 XYZ 控件。
- `ui/kind_panel.py`：独立筛选卡片、保留选择的提示、表格列宽/高度和状态绘制。
- `ui/run_environment_panel.py`、`ui/export_panel.py`：统一容器、紧凑资源/命令预览及主题状态色。
- `tests/test_layout_workflow.py`：增加 XML 校验结果同步到导航的断言。
- `README.md`：当前界面、测试、截图与使用行为说明。

`requirements.txt` 不变。完整源码包为 `dist/CP2K-Studio-source.zip`，优化前版本保留为 `dist/CP2K-Studio-source-before-ux.zip`。

## 测试与视觉验收

完整自动化测试：**210 passed**，没有失败或跳过（原有 187 项 + 本次 23 项）。145 条警告来自原有 cp2k-input-tools ElementTree 弃用提示（144）及 ASE/NumPy 弃用提示（1）。`python -m pip check` 通过；`python main.py` 进入 GUI 事件循环并运行 3 秒后由烟测终止。

新增交互测试覆盖样式加载、预设菜单实际点击、表单信号、科学计数法/精度/保存、单位不进入模型及预设、双列转单列、SCF 活动卡片与高度、相机旋转/投影/缩放/标签设置、非正交 ABC 数学关系、工具栏定位与缺失晶胞禁用、筛选保留、徽章 Tooltip、导航状态、草稿错误、滚轮/滑块拖动、键盘 Tab 和 SpinBox 按钮。原有 XML、结构、数据库、项目/预设、单文件/ZIP 计算包、run.sh 和文件引用回归继续通过。

截图使用明确配置的水分子示例，不是自动填充新项目。第 06 页截图使用 GEO_OPT，其他通常为 ENERGY。小窗口内容较多的页面允许滚动，02/05 补充截图展示滚动后的结构视图和表格。检查了 1366×768、1920×1080 的八页截图，以及 Qt 2× DPI 下结构、DFT、表格、运行环境的渲染；没有把自动化通过当作实体屏幕验收。

生成命令：

```bash
.venv/bin/python scripts/capture_ui.py
.venv/bin/python scripts/capture_ui.py --scale 2
```

### 页面截图

以下为步骤顺序调整前的历史截图；当前第 01 页为结构与晶胞，第 02 页为 GLOBAL。

[1366×768 总览](images/ui-ux/1366x768/overview.png) · [1920×1080 总览](images/ui-ux/1920x1080/overview.png)

| 页面 | 1366×768 | 1920×1080 |
|---|---|---|
| 01 GLOBAL | [查看](images/ui-ux/1366x768/01.png) | [查看](images/ui-ux/1920x1080/01.png) |
| 02 结构与晶胞 | [概览](images/ui-ux/1366x768/02.png) / [视图工具](images/ui-ux/1366x768/02-view.png) | [概览](images/ui-ux/1920x1080/02.png) / [视图工具](images/ui-ux/1920x1080/02-view.png) |
| 03 DFT | [查看](images/ui-ux/1366x768/03.png) | [查看](images/ui-ux/1920x1080/03.png) |
| 04 SCF | [OT](images/ui-ux/1366x768/04.png) / [对角化](images/ui-ux/1366x768/04-diagonalization.png) | [OT](images/ui-ux/1920x1080/04.png) / [对角化](images/ui-ux/1920x1080/04-diagonalization.png) |
| 05 基组与赝势 | [概览](images/ui-ux/1366x768/05.png) / [表格](images/ui-ux/1366x768/05-table.png) | [概览](images/ui-ux/1920x1080/05.png) / [表格](images/ui-ux/1920x1080/05-table.png) |
| 06 几何优化 | [查看](images/ui-ux/1366x768/06.png) | [查看](images/ui-ux/1920x1080/06.png) |
| 07 运行环境 | [查看](images/ui-ux/1366x768/07.png) | [查看](images/ui-ux/1920x1080/07.png) |
| 08 导出与预设 | [查看](images/ui-ux/1366x768/08.png) | [查看](images/ui-ux/1920x1080/08.png) |

[2× DPI DFT](images/ui-ux/retina-2x/03.png) · [2× DPI 结构视图](images/ui-ux/retina-2x/02-view.png) · [2× DPI 表格](images/ui-ux/retina-2x/05-table.png) · [2× DPI 运行环境](images/ui-ux/retina-2x/07.png)

## 尚未实测的边界

- 本次在 macOS 的 Qt offscreen 环境进行测试和截图检查；Linux 实体桌面、不同窗口管理器、真实 Retina 显示器的交互及系统原生文件选择框未进行逐机验收。2× 截图是 Qt DPR=2 渲染验证。
- macOS 启动时可能保留 Qt 的 Sans Serif 字体别名性能提示；截图中文字和单位正常，当前没有安装/替换系统字体。
- QPainter 仍只绘制原子和晶胞、不推断键；超过 3000 个原子仅限制显示数量，模型与导出保留全部。相机没有作为计算参数存入项目，标签设置在当前窗口加载其他结构时保留。
- 本环境未安装 CP2K；没有新执行数值计算。已有模拟 MPI/CP2K 启动及依赖文件读取回归通过。UI 状态不保证计算精度或收敛。
