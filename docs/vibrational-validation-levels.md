# 振动分析检查等级调整

本次调整检查结果，不修改参数值、模型默认值、INP 生成树、运行脚本或页面布局。

- EPS_SCF 仅在严格大于 `1E-7` 时产生 `vib.scf_warning`。`1E-8`、`5E-8`、`1E-7` 均不触发此项警告。原有格式、有限数值和取值范围校验保留。
- 统一 Poisson 校验器将 MT 的计算盒/电子密度/真空收敛说明放入 `ValidationResult.infos`，代码为 `poisson.mt_info`。此 MT 提示对使用该求解器的任务统一为 Info，周期性及无效晶胞的错误检查不变。
- 振动结构优化确认放入 `infos`，代码为 `vib.stationary_info`，不假定已优化，也不启动几何优化。其他 Warning/Error 保持原等级，包括 WAVELET 密度边界、Raman 响应、MPI 副本资源错误及固定原子不参与完整 Hessian 的提示。

现有 `ValidationResult` 和 `CheckStage` 已分别保存 errors/warnings/infos，导航、计数和第 08 页状态只依据 errors/warnings，因此没有修改图标、强制清零或按文案隐藏结果。综合检查原先仅保留以 KIND 开头的 Info；现在完整传递 Info，不按字符串筛选。实时报告和综合报告使用可翻译的 `Info · ` 前缀，中文为“提示 · ”。仅有 Info 且四阶段通过时显示通过；重新打开项目仍按现有规则要求重新主动检查。

保存、加载和检查不改变计算配置。导出器代码未改动，INP、结构/数据库依赖和 run.sh 继续使用原有生成流程。`EXPORT_NOTES.txt` 的 Configuration warnings 诊断清单按当前 Warning 集合生成，因此不再把这两项 Info 列作 Warning；该诊断段落随新等级变化，不宣称整个 ZIP 或说明文件与旧版本逐字节相同。

修改文件：`core/validator.py`、`core/vibrational.py`、`core/comprehensive_check.py`、`ui/main_window.py`；同步更新 catalog、中英文 TS/QM（698 项翻译均完成），以及振动/计算盒说明。更新 `tests/test_vibrational.py`、`tests/test_vibrational_ui.py`、`tests/test_simulation_box_modes.py`，新增 `tests/test_vibrational_severity.py` 的 20 项测试。

验证：现有相关 **125 passed**，新增 **20 passed**，其他输入基准、项目/脚本/导出回归 **87 passed**，合计 **232 项不同用例通过**。覆盖阈值及相邻浮点边界、Info 完整传递、只有 Info 时通过、其他真实 Warning/Error 保留、06/08 状态、中英文切换、保存/重新打开/重新检查、无效 EPS_SCF 输入和导出。采用隔离数据库缓存及 Qt offscreen，已检查两种语言的 Info-only 报告与绿色步骤截图。未执行真实 CP2K 数值计算，也未重跑整个测试套件。
