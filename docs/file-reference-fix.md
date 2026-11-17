# CP2K 2026.1 外部文件引用修复

## 原因与代码位置

之前 `core/generator.py` 第 22 行的 `quoted(path)` 使用 `return '"' + expanduser(path) + '"'`，无条件给文件引用添加双引号。它用于原第 70/71 行的 DFT 基组/赝势关键字和原第 85 行的 TOPOLOGY/COORD_FILE_NAME。`core/project_io.py` 原第 120–125 行还导入它来重建计算包的 DFT 文件引用。

这会生成 `COORD_FILE_NAME "structure.xyz"`。用户已在 CP2K 2026.1 实际运行中确认，改为不带引号即可正常读取。原来的 XML 解析器会把引号去掉后返回路径，不能发现这个文件读取问题；新回归测试明确复现这一差异。

## 修复规则与范围

新增 `core/file_references.py`，只为当前生成器实际输出的三个文件关键字维护规则：

- `FORCE_EVAL/SUBSYS/TOPOLOGY/COORD_FILE_NAME`
- `FORCE_EVAL/DFT/BASIS_SET_FILE_NAME`
- `FORCE_EVAL/DFT/POTENTIAL_FILE_NAME`

普通路径原样输出：

```text
&TOPOLOGY
  COORD_FILE_FORMAT XYZ
  COORD_FILE_NAME structure.xyz
&END TOPOLOGY
```

DFT 中同样生成 `BASIS_SET_FILE_NAME data/1_BASIS_MOLOPT` 和 `POTENTIAL_FILE_NAME data/2_GTH_POTENTIALS`，不加任何 Shell 引号。

规则依据 CP2K 2026.1 对应关键字定义及长字符解析方式：

- [2026.1 TOPOLOGY 定义](https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/SUBSYS/TOPOLOGY.html#COORD_FILE_NAME)
- [v2026.1 TOPOLOGY 源码：COORD_FILE_NAME 使用 lchar_t](https://github.com/cp2k/cp2k/blob/v2026.1/src/input_cp2k_subsys.F#L1491)
- [v2026.1 DFT 文件关键字定义](https://github.com/cp2k/cp2k/blob/v2026.1/src/input_cp2k_dft.F#L127)
- [v2026.1 长字符输入解析](https://github.com/cp2k/cp2k/blob/v2026.1/src/input/input_parsing.F#L509)

这三种值使用整行长字符语义，直接生成时允许普通路径字符和单个内部空格，保留其字面值；生成器仅将本机路径分隔符规范化为正斜线；最终文件检查按 INP 字面值验证。不使用 Bash、JSON 或 Python repr 来转义 INP。引号、预处理/注释字符、非 ASCII 字符、反斜杠、首尾/重复空白和控制字符等不能安全直接表示的值会明确拒绝，并提示导出计算包或重命名源文件。此保守规则没有承诺支持 CP2K 所有可能的文件名写法。

完整计算包始终重新生成 `structure.xyz`，不直接引用用户原 CIF/XYZ 路径。基组、赝势来源复制到 `data/`，basename 中非 ASCII 字母、数字、下划线、点、连字符转换为下划线，添加唯一序号，限制名称长度，避免同名或规范化后重名。原文件和原项目保持不变；包内项目引用同步更新，可以重新打开及再次导出。合并赝势仍使用 `studio_potentials.dat`。

`build_sections` 接收最终资源绑定，在 Section 树中直接序列化正确路径，避免先生成错误路径再替换文本。没有对整个 INP 做替换或删除引号；其他 Section、科学参数和通用字符串渲染保持原样。目前没有生成 WFN/其他重启文件引用，本次没有新增这些功能或对其套用未经确认的规则。

`core/run_script_generator.py` 的源码逐字节保持不变，MPI / OpenMP 参数继续由第 07 页提供。Bash 的 shlex 转义只用于运行脚本，不参与 INP。

## 最终导出检查与界面

完整包生成依赖和最终 input.inp、通过 XML 校验后，重新读取落盘的 input.inp：只提取受支持 Section 内的三个文件引用，保留字面引号，按暂存计算包的实际运行目录解析并逐一以二进制方式打开。

默认完整包要求所有 INP 引用为包内相对路径，拒绝上级路径和解析到包外的符号链接。坐标、复制后的基组/赝势或合并赝势缺失/不可读时，报告具体 Section、关键字、路径及运行目录，清理暂存目录，不交付不完整文件夹/ZIP。核心 API `copy_resources=False` 仍可显式依赖外部文件，但同样检查它们可访问且能安全序列化，说明文件继续明确标记为非自包含。

单文件 INP 保留既有的内嵌 COORD 行为，内容与 GUI 预览一致；不强行引入外部坐标。它与计算包共用相同文件引用序列化，额外检查实际基组/赝势/自动合并文件可访问。完整包允许改用安全相对名称，但对应坐标和数据内容保持一致。

如果源路径只能经复制规范化才能使用，GUI 会明确显示“文件路径需规范化 · 可导出完整计算包”，不展示貌似可运行的错误 INP；第 08 页综合检查报告单独 INP 路径警告，并继续检查规范化后的完整计算包。单独导出时给出具体原因，不抛出未捕获异常。

## 文件清单

- 新增 `core/file_references.py`、`tests/test_file_references.py`、本说明。
- 修改 `core/generator.py`、`core/project_io.py`、`core/input_export.py`、`core/validator.py`：统一文件值序列化、包内命名与最终文件检查。
- 修改 `ui/main_window.py`：针对需要规范化的文件路径显示说明，保留完整包导出并捕获直接校验错误。
- 修改 `tests/test_project_io.py`，更新两个本地生成快照 `tests/fixtures/generated_ot.inp`、`generated_diagonalization.inp` 中的文件名行。官方原始 ENERGY/GEO_OPT 回归输入不变。
- 更新 `README.md`、`docs/run-environment.md` 的文件规则/最新验证说明，以及 `docs/images/` 两张截图中的预览内容。
- 更新 `dist/CP2K-Studio-source.zip`，修复前版本保存在 `dist/CP2K-Studio-source-before-file-reference-fix.zip`。

## 验证

- macOS / Python 3.12 / Qt offscreen：`python -m pytest -q`，**187 passed**，无失败、无跳过（此前 156 项继续通过，本次新增 31 项）。
- 145 条警告：144 条来自 cp2k-input-tools 上游 ElementTree 弃用提示，1 条来自 ASE 与 NumPy 的数组 shape 弃用提示。
- `python -m pip check` 通过；`python main.py` 进入 GUI 事件循环并运行 3 秒，随后由烟测终止。
- 确认运行脚本生成器与修复前源码包逐字节一致。

新增 31 项针对性测试覆盖：无引号普通路径、长字符空格、非法直接引用、通用字符串不变、XML 与字面文件名检查的区别；XYZ/EXTXYZ/CIF 特殊源文件名导入并导出规范 XYZ；基组/赝势安全命名和冲突、源内容不变及重开重导；模拟最终文件复制/生成失败后的具体报错与清理；实际运行目录解析、包外引用拒绝；GUI/单独 INP 一致、完整包坐标对应；移动并解压 ZIP 后运行原 run.sh，用模拟 CP2K 按字面值打开全部文件，且人为恢复错误引号后确实失败。

真实 CP2K 数值计算未执行：本开发环境没有 cp2k.psmp、cp2k.popt 或 cp2k。运行脚本测试使用模拟 MPI/CP2K，仅验证启动、文件读取与错误返回；不证明数值精度或收敛。Linux/WSL2 未实机验证。本修复依据用户已完成的 CP2K 2026.1 实际复现，并通过文件系统及自动化回归验证生成结果。
