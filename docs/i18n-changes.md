# 本次中英文界面开发修改清单

## 新增文件

- `i18n/__init__.py`
- `i18n/messages.py`
- `i18n/language_manager.py`
- `i18n/qt.py`
- `i18n/catalog_sources.py`
- `i18n/cp2kstudio_en_US.ts`
- `i18n/cp2kstudio_zh_CN.ts`
- `i18n/cp2kstudio_en_US.qm`
- `i18n/cp2kstudio_zh_CN.qm`
- `scripts/build_translations.py`
- `scripts/hooks/hook-i18n.py`
- `tests/test_i18n.py`
- `docs/internationalization.md`
- `docs/i18n-changes.md`

## 修改文件

### 界面及入口

- `main.py`：缺失依赖时输出默认英语启动提示。
- `README.md`：语言入口、构建和说明文档链接。
- `ui/coordinate_range_dialog.py`
- `ui/database_dialog.py`
- `ui/dft_panel.py`
- `ui/export_panel.py`
- `ui/forms.py`
- `ui/input_editor.py`
- `ui/kind_panel.py`
- `ui/main_window.py`
- `ui/preset_dialogs.py`
- `ui/recommendation_dialog.py`
- `ui/run_environment_panel.py`
- `ui/scf_panel.py`
- `ui/structure_panel.py`
- `ui/structure_view.py`
- `ui/validation_state.py`
- `ui/widgets/help_icon.py`
- `ui/widgets/numeric_field.py`
- `ui/widgets/section_card.py`
- `ui/widgets/status_badge.py`
- `ui/xml_dialog.py`

### 诊断文本与元数据

以下 core 文件仅将可见消息封装为英文模板、稳定代码与参数，保留字符串兼容层；阶段标题及运行模式标签也提供翻译。校验条件、数据库解析和推荐算法未改变。

- `core/atom_constraints.py`
- `core/basis_database.py`
- `core/bundle_checks.py`
- `core/comprehensive_check.py`
- `core/database_format.py`
- `core/database_manager.py`
- `core/database_resources.py`
- `core/file_references.py`
- `core/input_export.py`
- `core/input_import.py`
- `core/kind_recommender.py`
- `core/kind_validator.py`
- `core/models.py`
- `core/potential_database.py`
- `core/presets.py`
- `core/project_io.py`
- `core/run_config.py`
- `core/runner.py`
- `core/schema.py`
- `core/structure.py`
- `core/validator.py`

### 原有测试适配

- `tests/conftest.py`：原有中文界面断言使用中文测试上下文；应用实际启动依旧默认英语。
- `tests/test_layout_workflow.py`：工具栏按钮断言排除新增的伸缩空白和语言控件。

## 保持不变的生成模块

- `core/generator.py`
- `core/run_script_generator.py`
- `core/export_notes_generator.py`

坐标显示精度委托 `ui/widgets/coordinate_delegate.py`、科学参数默认值和 requirements.txt 均保持不变。
