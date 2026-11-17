# CELL_OPT 晶胞优化

第 02 页 RUN_TYPE 新增 `CELL_OPT — Cell Optimization / 晶胞优化`。第 06 页按任务切换，不增加步骤；GEO_OPT、CELL_OPT、振动分析分别保留独立草稿。

## 参数与生成

`cell_opt` 配置复用优化器和阈值模型，默认 OPTIMIZER=BFGS、MAX_ITER=200。支持 BFGS/LBFGS/CG。EXTERNAL_PRESSURE=0.0 bar、PRESSURE_TOLERANCE=100.0 bar；压力显式输出，负外部压力允许，容差必须为正。力阈值默认 MAX_FORCE=4.5e-4、RMS_FORCE=3e-4 Ha/bohr；位移阈值 MAX_DR=3e-3、RMS_DR=1.5e-3 bohr。模型和界面不再提供 TYPE 参数。

生成 `GLOBAL/RUN_TYPE CELL_OPT`、`FORCE_EVAL/STRESS_TENSOR ANALYTICAL` 及 `MOTION/CELL_OPT`，同时优化原子和晶胞。依赖 CP2K 默认的直接联合优化，不输出任何 CELL_OPT/TYPE；不生成 GEO_OPT 或 VIBRATIONAL_ANALYSIS。CELL/COORD/DFT/SCF/KIND 继续通过统一生成器输出，原始坐标精度和结构保持不变；视图不会把初始晶胞冒充为优化后的结果。

## 支持范围与约束

- 首版仅支持三维 XYZ 周期、Quickstep/GPW 与 PERIODIC Poisson 求解器的解析应力。当前泛函为原有 PBE/BLYP/PADE；未开放其他方法或应力算法。NONE/1D/2D 或其他 Poisson 组合有阻断错误，不静默转换。
- 范围限定为三维体相晶体，不是含真空的表面 Slab。当前结构元数据不能可靠区分声明为 XYZ 的体相与真空 Slab，因此不依据真空大小猜测或改写周期性；检查报告明确提醒用户确认物理模型。Slab 的应力与固定真空方向流程尚未实现，不应套用当前全晶胞优化。
- 晶胞必须具有有限正体积、线性独立的右手矢量，A 沿 +X、B 在 XY 平面，对角分量为正。方向不符合时拒绝生成，用户需将晶胞与坐标一起重新定向。程序不截断晶胞分量、不自动旋转。
- KEEP_ANGLES 与 KEEP_SYMMETRY 默认关闭；CONSTRAINT 支持官方 NONE/X/Y/Z/XY/XZ/YZ，按压力张量限制所选晶胞分量。
- 第三张卡片的 CELL / SYMMETRY 提供内置 2026.1 XML 的枚举。它是此 CELL_OPT 任务的独立配置，写入 FORCE_EVAL/SUBSYS/CELL；不会影响其他任务。KEEP_SYMMETRY 要求显式选择非 NONE 且匹配当前晶胞长度/夹角的对称性。匹配采用长度相对容差 1e-6、角度绝对容差 1e-4 度；不满足时阻止输出，避免 CP2K 强制施加错误形状。它不等于保持原子空间群。
- 已有 FIXED_ATOMS 通过原模块生成并按最终原子顺序映射，不会丢弃。此约束固定分数坐标，晶胞变化时对应笛卡尔位置可能移动；报告明确给出 Warning。
- 报告以 Info 提醒检查应力、基组、网格、SCF 和布里渊区采样收敛性。应用当前生成 Γ 点输入，不提供完整 k 点网格设置。

## 项目、预设与导出

旧项目缺少 `cell_opt` 时使用上述默认值；原有字段含义不变。项目 JSON 和个人预设均保存 CELL_OPT 设置；预设仍默认不带结构、晶胞或固定原子编号，分类为自定义。切换任务保留有效的非活动草稿，非法非活动草稿不阻塞其他任务。

旧项目和预设中的 `cell_opt.type: DIRECT_CELL_OPT` 在读取时迁移并移除，其他数值、约束和结构不变。新建或重新保存的项目及新捕获的预设不再保存该字段。其他历史 TYPE 值不被静默解释为直接优化，而是明确拒绝。

单独 INP 与预览一致；计算包含原有 input.inp、structure.xyz、依赖数据库、项目 JSON、run.sh 和 EXPORT_NOTES.txt。运行环境及脚本逻辑未修改；附加中英双语说明明确文件是初始结构，只有 CP2K 实际运行才产生优化后的晶胞和应力。

支持导入 Studio 本身生成的不含 TYPE 的 CELL_OPT INP。解析器只接受标量压力、直接联合优化和 ANALYTICAL 应力，其他方案或压力张量不会被静默映射；任意 INP 的完整往返仍不在支持范围内。

## TYPE 关键字兼容性修复

2026.1 历史 XML 和该分支官方文档仍允许 `MOTION/CELL_OPT/TYPE`，且其默认值为 DIRECT_CELL_OPT；较新可执行程序已移除此关键字并始终使用直接联合优化。本次统一省略 TYPE，避免触发用户实际运行时的 removed-keyword ABORT。预览、独立 INP 和计算包复用同一生成器，没有全局字符串删除或替换。

内置 XML 仍保持原始 2026.1 版本、来源和指纹，没有将旧 XML 伪装为当前可执行程序的规范。XML 版本检查机制保留；额外的兼容性规则会在解析树中精确拒绝 MOTION/CELL_OPT/TYPE，即使历史 XML 接受它也不报告通过。其他位置的合法 TYPE（例如色散 TYPE DFTD3）不受影响。省略 TYPE 的输出继续通过目标 2026.1 XML 校验。这不能证明未知版本可执行程序的其他关键字也全部兼容；应使用实际可执行程序对应的规范和运行测试确认。

本次修复修改了 `core/models.py`、`core/generator.py`、`core/validator.py`、`core/input_import.py`、`core/export_notes_generator.py`、`ui/cell_opt_panel.py`、中英文翻译和相关测试。新增 `tests/test_cell_opt_removed_type.py`，覆盖旧项目/预设迁移、精确拒绝已删除关键字及实时语言切换不恢复 TYPE。

TYPE 修复后的相关回归：**227 passed，537 warnings，91.07 秒**，使用隔离缓存避免原有数据库路径快照受本机缓存影响。新增 8 项专项回归；覆盖本任务要求的预览、独立 INP、ZIP 计算包、旧项目/预设、XML 与兼容性校验、参数和约束保留、中英切换。ENERGY/GEO_OPT/VIBRATIONAL_ANALYSIS 另与本次修复前生成的输入逐字比较一致。750 项中英文翻译全部完成并编译；已检查两种语言的优化设置卡片，没有 TYPE 控件或空白槽位。警告来自既有解析器/NumPy 及故意非法值测试。未运行真实 CP2K：本机 PATH 未发现 CP2K 或 MPI 可执行程序。

## 验证依据与限制

- [CP2K 2026.1 MOTION/CELL_OPT](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/MOTION/CELL_OPT.html)
- [FORCE_EVAL/STRESS_TENSOR](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL.html#STRESS_TENSOR)
- [CELL/SYMMETRY 与晶胞约定](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/SUBSYS/CELL.html)
- [FIXED_ATOMS 分数坐标定义](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/MOTION/CONSTRAINT/FIXED_ATOMS.html)
- 官方 v2026.1 `tests/QS/regtest-spgr-id/argon.inp` 原样作为静态语法与结构回归夹具。其额外 GEO_OPT、色散及测试设置不被当作 Studio 的生产默认配置。

测试包括 Si 常规立方晶胞的配置/生成/XML、优化器和七种约束、非正交晶胞、非法体积和方向、初始对称性、原子重排后的约束、任务隔离、项目/预设/INP 往返、最终 ZIP、综合检查、双语言与窗口尺寸。原有三种任务与修改前生成的输入逐字比较保持一致。

首次加入 CELL_OPT 时的完整回归在隔离 `XDG_CACHE_HOME` 环境下为 **814 passed，1132 warnings，497.05 秒**，其中新增 CELL_OPT 测试 72 项。该结果是本次 TYPE 修复之前的历史记录，不代表真实 CP2K 运行验证。使用隔离缓存是为了避免本机数据库缓存与内置数据库路径差异影响原有路径/快照断言，没有修改数据库发现规则。

当前本机 PATH 未发现 CP2K 或 mpirun，未执行真实 CELL_OPT 数值计算；没有验证优化步骤、应力数值或最终晶胞的实际运行输出。XML 与自动化测试通过不等于计算收敛或物理适用性已验证。界面检查使用 Qt offscreen；Windows/Linux 原生桌面未实机验证。

## 修改文件

- 新增 `core/cell_optimization.py`、`ui/cell_opt_panel.py`：任务校验、晶胞几何检查、三卡片双语言参数面板。
- 修改 `core/models.py`、`core/generator.py`、`core/validator.py`：独立配置、应力和 CELL_OPT Section、统一校验入口。
- 修改 `ui/main_window.py`、`ui/vibrational_panel.py`：RUN_TYPE、原第 06 页任务容器与导航；`ui/export_panel.py`、`ui/preset_dialogs.py`：错误定位与预设分类。
- 修改 `core/presets.py`、`core/input_import.py`、`core/export_notes_generator.py`：保存、恢复、有限 INP 导入及中英导出说明。原项目序列化、依赖复制、脚本和 MPI/OpenMP 生成器复用未改。
- 更新 `i18n/catalog_sources.py`、两种语言的 TS/QM。
- 新增 `tests/test_cell_optimization.py`、`tests/test_cell_opt_ui.py` 和官方 Argon 夹具；更新原振动测试中的 RUN_TYPE 列表及夹具说明。
- 更新 README 和本文。其他页面、3D 渲染器、基组/赝势解析器未修改。
