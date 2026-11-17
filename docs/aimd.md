# Born–Oppenheimer AIMD

第 02 页 RUN_TYPE 新增 **Molecular Dynamics (AIMD) / 第一性原理分子动力学**，内部值及 INP 始终为 `MD`。第 06 页动态切换为四张卡片；八步导航、其他任务及电子结构设置不变。

## 参数与输出

| 配置 | 默认值 |
| --- | --- |
| ENSEMBLE | NVT（可切换 NVE） |
| STEPS | 2000 |
| TIMESTEP | 0.5 fs |
| TEMPERATURE | 300 K |
| INITIALIZATION_METHOD | DEFAULT（只读） |
| NVT 恒温器 | GLOBAL CSVR，TIMECON 100 fs |
| 轨迹 | 开启，XYZ，每 10 步；可选 EXTXYZ |
| Restart 输出 | 开启，每 100 步，2 份备份 |
| 从 Restart 续算 | 关闭 |

总模拟时间为 `STEPS × TIMESTEP / 1000` ps，只作显示，不生成关键字。NVE 不输出 THERMOSTAT，TEMPERATURE 仅用于缺少初始速度时的初始化。切换系综保留 CSVR 设置，切换任务保留每个任务的独立配置。

MD 在 `MOTION/MD` 下，复用 Quickstep/GPW 的 FORCE_EVAL、DFT、SCF、KIND、晶胞和坐标。不开启其他任务的优化或振动 Section。已有 FIXED_ATOMS 按相同稳定原子 ID 映射保留，其分量遵循 CP2K 的分数坐标约定。

`MOTION/PRINT/TRAJECTORY` 控制轨迹；`MOTION/PRINT/RESTART` 控制检查点和备份。关闭选项时显式输出 OFF。`MOTION/MD/PRINT/ENERGY` 每步输出能量数据，包含时间、温度、动能、势能和守恒量。NVE 可检查动能与势能之和的漂移；NVT 的守恒量还涉及恒温器贡献。文件名遵循 CP2K 项目与输出约定，例如 `project-pos-1.xyz` 和 `project-1.ener`。这些结果仅由实际 CP2K 计算生成，Studio 不伪造结果、不追加或合并旧轨迹。

## Restart 续算

选择完整的文本 `.restart`，并启用 Continue from Restart。首版保守检查：

- 文件存在、大小不超过 100 MB，且通过目标版本 XML 解析；不支持依赖预处理指令的文件。
- 一个 Quickstep FORCE_EVAL，MD 任务，以及匹配的原子数量、顺序标签和 KIND 元素定义。
- 完整的内嵌坐标、有限的速度、匹配的固定体积晶胞及周期性。
- 有效的 STEP_START_VAL、TIME_START_VAL，以及与所选 NVT/NVE 相同的系综。
- NVT 需要 GLOBAL CSVR 的 THERMOSTAT_ENERGY 和 RNG_INIT。检查并原样保留 CP2K 2026.1 的 433 字符随机数流记录。

顶层 EXT_RESTART 显式恢复坐标、速度、晶胞和计数器，使用 `RESTART_DEFAULT FALSE` 限定恢复范围；NVT 还请求恢复恒温器，并显式将源 CSVR 能量和随机数流状态加入生成的 CSVR。存在 ECONS_START_VAL 时保留该动力学状态。不会把末帧 XYZ 当成完整续算，也不会修改 SCF_GUESS。WFN 重启仍是独立机制。

STEPS 表示从恢复的计数器开始额外执行的步数。运行时 CP2K 使用 Restart 坐标；项目结构和 3D 预览不会被选择文件操作静默替换。若晶胞或 KIND 不匹配，先导入对应结构。静态检查不能证明同类原子的身份、电子结构设置及续算的物理连续性，必须核查实际运行。

完整计算包将 Restart 原样复制到 `data/`，规范化文件名、处理名称冲突，并更新 INP 和打包项目的相对引用。原文件不被覆盖。依赖检查会读取最终包中的 Restart，源文件变动会使综合检查失效。独立 INP 使用可访问的源路径，不复制 Restart；特殊路径无法直接表示时，提示导出完整计算包。

每段模拟使用新的计算包目录，独立保留上一段输出和源 Restart。

## 校验与兼容

步数和输出间隔必须为正整数；TIMESTEP、TIMECON 必须为有限正数；温度必须非负。只有 NVT/NVE 和 CSVR 可选。检查明显的原子重叠（含周期镜像）、全固定结构、过大时间步长、过松 SCF 和过强恒温器耦合。弛豫、平衡、能量漂移及取样建议使用 Info，不计入警告。

项目及预设通过独立 `md` 配置保存参数；旧项目缺少该字段时使用默认值。预设若包含续算文件设置，应用到新体系后仍须通过匹配检查。语言切换仅更新文本，不改变模型、INP、检查状态或相机。

计算包继续使用第 07 页的 MPI/OpenMP、原 run.sh 和统一导出流程，包含真实依赖、项目 JSON 及双语 EXPORT_NOTES.txt。

## 验证范围与未实现内容

自动化测试使用明确标记的合成 MD Restart 状态；随机数记录格式依据 CP2K v2026.1 的官方序列化单元测试。它们用于测试解析、状态保留和导出，不是实际轨迹或物理连续性的证据。当前环境没有找到 CP2K/MPI 可执行程序，未执行真实 AIMD 或续算运行。

本次验证：整套测试分 8 批运行，985 项通过；另补充 1 项诊断路由测试通过。新功能及相关任务页面复测 66 项通过。8 份既有任务/SCF 组合的默认 INP 与修改前逐字节一致。单进程长时间运行曾出现两项后台等待超时，单独及分批复测未复现；测试没有放宽原有超时限制。中英文界面检查使用 Qt offscreen，未将其当作 macOS 原生窗口的视觉验证。

暂不支持 NPT、其他恒温器、非 GLOBAL CSVR 重启、跨系综直接续算、拆分二进制 Restart、增强采样、Car–Parrinello/Ehrenfest、轨迹动画和结果分析。已有四种任务的生成流程保持不变。

## 修改文件

- `core/models.py`、`core/md.py`、`core/generator.py`、`core/validator.py`：独立模型、任务生成、MD 和 Restart 检查。
- `core/file_references.py`、`core/project_io.py`、`core/input_export.py`、`core/bundle_checks.py`、`core/comprehensive_check.py`：Restart 路径、复制、最终依赖校验及变更跟踪。
- `core/presets.py`、`core/input_import.py`、`core/export_notes_generator.py`：预设、受支持输入导入及导出说明。
- `ui/md_panel.py`、`ui/vibrational_panel.py`、`ui/main_window.py`、`ui/export_panel.py`：四张卡片、任务切换及状态定位。
- `i18n/catalog_sources.py`、`i18n/cp2kstudio_en_US.ts/.qm`、`i18n/cp2kstudio_zh_CN.ts/.qm`：双语资源。
- `tests/test_md.py`、`tests/test_md_ui.py`；`tests/test_cell_opt_ui.py`、`tests/test_vibrational_ui.py` 同步更新任务选项断言；`README.md`、本文档。

规范与实现参考：[MD](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/MOTION/MD.html)、[EXT_RESTART](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/EXT_RESTART.html)、[CSVR 恢复实现](https://github.com/cp2k/cp2k/blob/v2026.1/src/motion/thermostat/csvr_system_init.F)、[随机数流格式测试](https://github.com/cp2k/cp2k/blob/v2026.1/src/common/parallel_rng_types_unittest.F)。
