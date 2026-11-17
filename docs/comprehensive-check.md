# 第 08 页综合检查

顶部独立「XML 校验」入口已移除。「XML 规范」仍管理内置 CP2K 2026.1、自定义 XML、版本检查及恢复默认；未修改 XML 解析器或科学计算参数。

## 修改文件

- 新增 `core/comprehensive_check.py`：四阶段协调、报告、文件签名。
- 新增 `core/bundle_checks.py`：最终依赖条目及运行文件核对。
- 修改 `core/project_io.py`：提取可复用的计算包文件准备步骤，导出前核对最终落盘文件。
- 修改 `core/input_export.py`、`core/kind_validator.py`：导出时重新加载源库，并核对实际依赖内容。
- 修改 `core/schema.py`：XML 缓存使用完整文件签名，识别原路径上的文件替换。
- 修改 `ui/main_window.py`、`ui/export_panel.py`、`ui/validation_state.py`：入口整合、后台执行、报告及检查失效同步。
- 新增 `tests/test_comprehensive_check.py`、`tests/test_comprehensive_check_ui.py`；更新 `tests/test_export_check_state.py`、`tests/test_layout_workflow.py`、`tests/test_ui.py`、`tests/test_ui_ux.py`、`tests/test_file_references.py` 的异步流程和入口断言。
- 更新 `README.md`、本说明及 `docs/ui-layout-upgrade.md`、`docs/ui-ux-upgrade.md`、`docs/file-reference-fix.md`。

## 实际执行的阶段

1. **配置完整性**：重新读取当前模型和字段错误，复用 `validate_project`、`validate_kinds` 与 Pydantic 校验 GLOBAL、结构、晶胞、周期性、DFT、实际启用的 SCF、GEO_OPT、运行参数，以及 KIND 条目、q/XC 和源库指纹。没有结构、电荷、泛函或必需 KIND 时不推断补齐。
2. **XML 语法**：复用 `InputValidator` / `cp2k-input-tools`，检查当前生成的计算包 INP 和单独 INP。XML 必须是 2026.1；缺失、损坏或版本不匹配时失败。前置错误阻止生成时，明确标注未执行。
3. **实际依赖**：使用同一个导出准备函数在临时目录中生成真实的 input.inp、structure.xyz、数据副本和必要的合并赝势。读取落盘 INP 的三个当前受支持文件关键字，按计算包运行目录打开引用，拒绝包外路径、绝对路径及字面引号，重新用现有数据库解析器核对元素、名称/Alias 和条目内容。多个源库的合并文件也接受相同检查。单独 INP 使用内嵌坐标，源库保持可访问，必要 sidecar 与 INP 一起生成；源路径不能安全写入 INP 时显示警告，建议导出完整包。
4. **运行配置及计算包**：校验 MPI/OpenMP 正整数与乘积，核对实际 run.sh 的工作目录、input.inp、output.out 和命令；核对 EXPORT_NOTES.txt 的命令、资源参数与入口文件。Linux、macOS、WSL2 沿用现有 Bash 生成器。

临时目录自动清理，不修改源结构、源数据库或当前模型，不在用户导出目录留下检查文件。报告分阶段展示错误、警告、信息和未执行原因，只有四个必需阶段执行且无错误、无警告才通过。

## 状态与导出

第 08 步只记录当前会话中主动检查的结果。字段编辑、结构/预设/项目加载、XML 改动使其恢复灰色。检查后监视实际源库和 XML 的文件与父目录；删除、写入或替换会使结果失效。接受后台结果前还会比对模型版本、快照及文件签名，拒绝过期结果。无关页面、滚动、标签切换及保存不影响状态。

已检查且存在阻断错误时，界面拒绝导出。警告保留黄色状态，按现有策略允许导出并提示。未检查或失效后的导出不会使用先前结论，实际导出函数会独立重读源库、验证 XML、最终引用、条目和脚本，再发布计算包。单独 INP、计算包与预设保存仍使用各自原有入口。

## 验证范围

这是静态完整性和语法检查，不运行 Bash、MPI 或 CP2K，不要求开发机安装这些程序。不检测远程机器的程序、MPI ABI、系统库或可用硬件，不验证数值能量、物理适用性和 SCF 收敛。

`tests/test_comprehensive_check.py` 覆盖真实 XML、缺失参数、损坏/错误版本 XML、落盘引用、文件缺失、条目缺失、多源合并、脚本和说明不一致、最新输入和失败清理。`tests/test_comprehensive_check_ui.py` 覆盖统一入口、现有服务接线、异步期间编辑、文件替换失效、错误导出拦截、无关 UI 操作与保存/重新打开。原有项目、预设、推荐和导出回归测试继续执行。

本次 macOS / Python 3.12 全量结果：**298 passed，452 warnings，168.54 秒**，包含新增 39 项。测试使用临时 `XDG_CACHE_HOME`，结束自动清理，不触碰现有用户缓存。Qt offscreen 截图确认顶部按钮、第 08 页、分阶段报告及导航状态；Windows/Linux 实机界面和真实 CP2K 数值计算未验证。
