# DFT 初始电子态与界面提示精简

新建项目的统一 `DFTConfig` 使用 CHARGE=0、MULTIPLICITY=1，UKS 初始值仍为 False。这些是可编辑的起始设置，不代表对任意体系的物理适用性判断。原有整数解析、正多重度、价电子数/自旋奇偶性和 UKS 检查保持不变。默认值加载时不触发控件修改信号或项目未保存标记。

旧项目缺少电子态字段时使用新默认值；已保存的电荷、多重度和 UKS 不覆盖。显式空值或用户清空的字段仍保持未设置，并由原校验器提示。可复用预设继续只覆盖其明确包含的字段；已有 INP 导入仍保留其原有“缺少 CHARGE/MULTIPLICITY 时明确要求确认”的行为。

删除 `FormPanel.add()` 中将内部配置路径设为 Tooltip 的统一代码；控件 objectName、绑定和校验路径保留。审核 01–08 页后保留结构来源/数据库文件路径、筛选状态、固定分量含义、分子周期性锁定、振动强度依赖及标题信息图标等有用提示，不使用全局 Tooltip 禁用。

DFT 的 Poisson 卡片删除表格下方说明 QLabel，保留原下拉框及六行参考表。导出卡片删除振动任务专用的追加 UI 文案，只保留带 `"bash run.sh"` 的原有提示 QLabel；EXPORT_NOTES.txt、Molden/Hessian 配置及实际导出流程不改动。中英文 TS/QM 同步移除四条无用文案，剩余 687 项翻译均已完成。

修改文件：`core/models.py`、`ui/forms.py`、`ui/dft_panel.py`、`ui/export_panel.py`、`i18n/catalog_sources.py`、中英文 TS/QM、README。更新 `tests/test_models.py`、`tests/test_presets.py`、`tests/test_ui_ux.py`、`tests/test_layout_workflow.py`，新增 `tests/test_dft_defaults_help.py` 的 16 项测试。

已单独通过现有相关 104 项测试及新增 16 项测试，覆盖初始值、旧项目与显式空值、项目/预设恢复、整数约束、电子数/UKS 一致性、八页字段提示、有用帮助保留、中英切换时项目/INP/检查状态/3D/导航不变、三个任务的导出及振动包内实际说明文件。使用 Qt offscreen 检查中英文 DFT/Poisson/导出页面截图，未执行实际 CP2K 数值计算。

完整回归覆盖 684 项：首次运行 683 passed、1 failed、930 warnings（398.78 秒）；唯一失败是旧导出保护测试仍假定新项目缺少 CHARGE。将该断言更新为检查缺失的 SUBSYS，并确认不再错误提示已填写的 CHARGE/MULTIPLICITY 后，项目工作流与新增测试合计 **27 passed、32 warnings（9.91 秒）**，本次发现的失败已复测解决。修正未涉及应用代码，其余 683 项结果仍适用；未重复运行整套测试。警告来自既有 XML/ASE 弃用提示及非法数据测试。
