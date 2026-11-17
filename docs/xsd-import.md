# Materials Studio XSD 导入

第 01 页的“Import Structure / 导入结构”按钮直接列出 `.xsd / .cif / .xyz / .extxyz`，仍打开原有系统文件选择窗口。可选择 XSD、CIF、XYZ、EXTXYZ 或所有文件；后缀识别不区分大小写，支持中文、空格、括号路径。按钮说明、文件过滤器和解析入口共用 `core/structure.py` 的支持格式列表。按钮保持原有尺寸及样式，窄窗口只按可用文字宽度适度缩小字体，不改动页面布局。

## 解析和数据边界

当前实际测试环境使用 **ASE 3.29.0**，项目原有依赖已包含 `ase>=3.23,<4`，不新增另一套坐标模型或新的运行依赖。

`core/xsd_import.py` 负责 XSD 适配和校验，使用官方 `ase.io.read(..., format='xsd')`。普通 Molecule/P1 显式晶胞由 ASE 直接读取原始 XML 字节；保留 ASE 的元素顺序、真实笛卡尔坐标、完整 3×3 晶胞和 PBC。没有导入时的居中、平移、截断真空、按长度重建正交晶胞或猜测低维周期性。

ASE 3.29.0 的 XSD 读取器只读取第一个 IdentityMapping，不会展开源空间群。用户的 rutile 文件有多个 MappingFamily，原生读取会失败。因此适配层先校验源 SpaceGroup 的算符和晶胞，对不对称位点调用 ASE 的 spacegroup 等价位点展开，再把完整晶胞写为**内存中的**最小 P1 文档，交给同一 ASE XSD 读取器转换为 Atoms。原文件不修改，也不创建用户必须操作的中间转换文件。返回数据仍转换成原有 `Structure` 模型。

对称展开采用源文件完整算符，检查其数量与声明空间群的 ASE 设置相符，并拒绝重复、不完整算符。常规显式晶胞保留原顺序和坐标；不对称表示的最终顺序由 ASE 等价位点和最终 XSD 读取顺序确定。周期 Atom3d 缺省 XYZ 沿用 ASE 定义的原点，分子缺失坐标则报错。显示镜像不作为额外原子加入。

## 真实文件验证

| 文件 | 解析结果 | 周期性和晶胞 |
|---|---|---|
| TiO2_rutile.xsd | 2 个独立位点展开为 6 个晶胞原子，Ti₂O₄ | XYZ；A/B/C 为原始 4.6157、4.6157、2.967 Å 基矢 |
| TiO2 slab.xsd | 22 个原子，Ti₈O₁₄；顺序、坐标与 ASE 原生结果一致 | 保留经过旋转的原始三个基矢；初始 XYZ，不根据真空改为 XY |
| h2o.xsd | O、H、H 三原子，原始负坐标不变 | NONE，零晶胞；提示创建非周期计算盒 |

原始文件及 SHA-256 在 `tests/fixtures/xsd/README.md`。另有合成三斜晶胞、多元素、大小写和损坏文件测试，和真实文件兼容性验证分开记录。

## 周期性和计算盒

XSD 周期结构显示“确认周期性”，仍使用原有 PERIODIC 下拉框，用户可选择 XYZ、XY、XZ、YZ、X、Y、Z、NONE。当前 ASE 不保证从 Slab/链 XSD 识别部分周期性；程序不会按真空、文件名或表面方向自动改变边界条件。改变 PERIODIC 也不自动改变 Poisson 求解器。

明确的 XSD `Molecule` 导入后记录 `structure_type=isolated_molecule`，PERIODIC 固定为 NONE，下拉框禁用并显示双语言原因提示。`SymmetrySystem` 记录为 `periodic_structure`，仍允许修改周期方向；重新导入周期结构会解除分子锁定。普通 XYZ/CIF/EXTXYZ 和缺少该字段的旧项目默认为 `unclassified`，不会根据文件扩展名、源路径或 NONE 值推断锁定。未分类结构在选择 NONE 后可通过“确认为孤立分子…”明确确认；取消保持原状。

结构类型随项目 JSON 保存，计算盒生成、坐标修改和原子重排保留该标记。明确包含坐标的预设也记录结构类型；普通计算预设不更改当前结构类型。与已锁定分子冲突的周期晶胞或周期坐标预设会报告错误，保留当前项目。包含相互矛盾的分子标记与非 NONE 周期性的项目也会拒绝加载，不静默更改边界条件。锁定仅禁用 PERIODIC 下拉框，晶胞和坐标编辑仍可使用。

非周期分子若没有有效晶胞，仍可保存项目草稿，但输入生成会报告需要计算盒。用户可以手动编辑晶胞，或点击“生成计算盒…”选择每侧真空边距、立方体或手动尺寸。三种模式根据当前真实笛卡尔坐标的包围盒统一居中，保持原子间相对位置、元素、顺序、KIND、原子 ID 和已有固定约束。取消不改变项目。此操作保持 NONE，不代表已满足特定 Poisson 求解器的精度要求。详见[三种计算盒模式及保存规则](simulation-box.md)。

两种边距模式首次均使用 **10.000 Å**，各自记忆输入。真空边距模式按每轴跨度 + 2d 生成正交盒；立方体模式按最大跨度 + 2d 统一三轴长度；手动模式输入 A/B/C 正尺寸。所有非空、当前 PERIODIC NONE 的结构均可使用此按钮，包括普通 XYZ；按钮不因已经存在有效晶胞而消失。不叠加旧晶胞尺寸；取消不覆盖手动晶胞、原子坐标或上次成功的参数。

上次成功模式及各模式参数保存在 `box_generation`，随项目保存恢复，语言切换不重置；旧 `box_vacuum_margin` 保留为真空模式兼容字段。旧项目缺少模式配置时保留原边距，没有边距时采用 10 Å，既有晶胞和坐标不因此改变。新结构导入从默认模式与 10 Å 开始；晶胞编辑不更改已记忆参数。生成失败不记录本次输入。生成后沿用原有更新机制同步晶胞、坐标表格、固定标记、3D、INP 和项目修改/检查状态。

## 接入现有流程

新结构在解析和校验全部完成后才替换当前结构；失败或取消保留原项目、选择和固定状态。成功后沿用既有导入规则，重建原子 ID 并清除旧选择和固定约束，更新 KIND 行、晶胞/坐标表格、3D 视图、导航、INP 预览和检查状态。已有电荷、多重度、DFT/SCF 及可匹配的基组/赝势设置保留；缺少的新元素设置不会自动补齐。

项目 JSON 嵌入结构，重新打开不依赖源 XSD 仍然存在。计算输入继续使用原生成器的 CELL/COORD，计算包继续生成 structure.xyz，不会写 `COORD_FILE_FORMAT XSD`。ENERGY、GEO_OPT、VIBRATIONAL_ANALYSIS、run.sh 和 MPI/OpenMP 规则没有更改。

文件选择入口继续使用官方 QFileDialog 原生模式，不设置 DontUseNativeDialog，不绘制仿 Finder 窗口。新增数字输入对话框复用现有 Qt 翻译适配，支持中英文。打包资源仅新增可选 `scripts/hooks/hook-core.xsd_import.py`，收集 ASE XSD 动态读取器和 spacegroup.dat；本次未运行 PyInstaller 或创建应用包。

## 不支持或不保留的特性

- 不导入力场、键级、形式电荷、Materials Studio 原子约束或显示设置；不会据此推断 CP2K 电荷或 FIXED_ATOMS。
- 不支持多体系、嵌套分子、混合占位、显式非归一化周期表示、带覆盖坐标/元素的镜像、原子映射族中的空位或其他无法明确表示的特殊映射，遇到可识别的不支持布局会明确报错。
- 不完整/重复对称算符、无效元素、非有限坐标、缺失或退化周期晶胞、ASE 输出与校验数据不符会拒绝导入。
- 对未覆盖的 Materials Studio 文件版本和特殊扩展，不宣称完整兼容。Windows/Linux 原生文件窗口及正式打包结果尚未实机验证。

实现依据：[ASE XSD 读取器](https://docs.ase-lib.org/_modules/ase/io/xsd.html)、[ASE spacegroup 等价位点](https://docs.ase-lib.org/_modules/ase/spacegroup/spacegroup.html)及用户提供的三份真实文件。

## 修改文件

- 新增 `core/xsd_import.py`；调整 `core/structure.py`，保留原有 load_structure() 接口。
- 调整 `ui/main_window.py`、`ui/structure_panel.py` 和 3D 空状态说明 `ui/structure_view.py`。
- `i18n/qt.py` 增加数字输入对话框的翻译适配；更新 catalog_sources、中英文 TS/QM。
- 新增可选 XSD 打包 hook、真实文件夹具及说明、`tests/test_xsd_import.py`、`tests/test_xsd_ui.py`；更新旧导入按钮测试。
- 更新 README 和本文。结构模型新增持久化类型标记；INP 生成器、数据库解析器和 3D 渲染算法未改动。

## 最终验证

完整回归 **613 passed，878 warnings，365.42 秒**，其中新增 47 项 XSD/界面测试。使用隔离缓存和 Qt offscreen；警告来自既有 XML 解析器、ASE/NumPy 弃用提示及故意构造非法数据的测试。已检查 rutile 英文、Slab 英文、H₂O 中文导入后的 Qt 窗口截图；三份用户源文件与夹具逐字节 SHA-256 一致，未修改源文件。

覆盖真实文件与合成三斜/损坏样例、大小写与中文路径、取消/失败保留项目、选择和固定状态重置、明确创建计算盒及其取消、原生文件选择配置、真实数字输入对话框、中英切换数据不变、项目重开不依赖源 XSD，以及单独 INP 和计算包导出。未实测各平台系统文件窗口的原生外观和正式打包结果，未执行真实 CP2K 数值计算。

### 计算盒重复生成优化验证

新增 `tests/test_simulation_box.py` 的 12 项测试，并更新原有 `tests/test_xsd_ui.py` 对按钮保留和真实数值弹窗的断言。覆盖默认 10.000 Å、10→15→8 Å 连续生成、重复相同边距、当前坐标编辑、手动晶胞后取消、失败不记忆输入、KIND/原子 ID/固定状态、XYZ 导入后按钮保留、新结构边距重置、项目重开、旧项目兼容、中英文切换及预览/综合检查状态更新。

本次完整回归为 **648 passed，907 warnings，379.42 秒**；相关测试先单独通过 **82 项**。警告仍来自 XML/ASE 弃用提示及故意构造的非法数据测试。通过 Qt offscreen 检查中英文弹窗及生成后按钮保留，未执行真实 CP2K 计算。代码变更仅涉及 `core/models.py`、`core/structure.py`、`ui/structure_panel.py`，没有修改 INP 生成器或运行脚本；现有翻译文本保持不变。

### 导入提示和 3D 元素标签优化

孤立分子提示精简为“非周期分子。请检查真空及 Poisson 边界要求。”缺少计算盒时追加“请手动填写计算盒，或使用下方按钮生成。”来源、原子数量和元素信息保留，坐标导入及计算盒处理未改变。

Aa 标签按球心投影位置居中绘制可见文字轮廓，字号随小球半径收缩，文字色根据原子颜色选择黑或白；球体尺寸和配色不变。标签在各原子的深度绘制过程中绘制，并裁剪到自身球体内，后方标签会被前方球体遮挡。相机、选中/固定标记和点击检测沿用原逻辑。

本次修改 `core/structure.py`、`ui/main_window.py`、`ui/structure_panel.py`、`ui/structure_view.py`，新增 `ui/widgets/structure_import_button.py`；同步更新 catalog/中英文 TS/QM、两个旧按钮测试及新增 `tests/test_structure_labels.py`。相关回归 **197 passed，181 warnings，55.15 秒**，其中新增 20 项测试；覆盖四种格式、原生文件选择配置、长按钮文字、实际标签像素位置、遮挡、小球缩放、相机操作、中英切换、选择/固定、综合检查及 INP/计算包导出。通过 Qt offscreen 检查中英文 1050px 主窗口及元素标签截图，未执行真实 CP2K 计算，未实测 Windows/Linux 原生界面。
