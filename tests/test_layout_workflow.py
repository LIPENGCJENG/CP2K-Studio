import time
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QMessageBox, QPushButton, QToolBar, QToolButton
from core.models import Project
from core.presets import capture_preset
from core.project_io import save_project, load_project
from core.schema import BUNDLED_XML
from ui.main_window import MainWindow
from ui.xml_dialog import XMLDialog
from ui.preset_dialogs import SavePresetDialog, ManagePresetsDialog


def wait_for_worker(app, window):
    deadline = time.monotonic() + 30
    while window._busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert not window._busy


def close_window(window):
    window.dirty = False
    window.close()


def test_eight_pages_toolbar_global_and_preview_are_stable(app, water, tmp_path):
    window = MainWindow(preset_directory=tmp_path)
    window.load_into_ui(water)
    assert window.nav.count() == 8 and window.stack.count() == 8
    assert window.nav.item(7).text() == '08  导出与预设'
    assert window.stack.widget(7).widget() is window.export_panel
    assert not hasattr(window, 'schema_panel')
    assert not hasattr(window, 'preview_status')
    assert window.input_preview_pane.layout().itemAt(1).widget() is window.tabs
    assert not window.global_panel.findChildren(QPushButton)
    toolbar = window.findChild(QToolBar)
    buttons = [toolbar.widgetForAction(action).text() for action in toolbar.actions() if isinstance(toolbar.widgetForAction(action), QToolButton)]
    assert buttons == ['项目管理', '预设管理', 'XML 规范', '环境检测', '本地运行', '使用说明']
    assert [action.text() for action in window.project_menu.actions()] == ['新建项目', '打开项目...', '保存项目']
    assert window.preset_button.text() == '预设管理'
    before = window.project.model_dump()
    preview = window.preview.toPlainText()
    for index in range(8):
        window.nav.setCurrentRow(index)
        app.processEvents()
        assert window.stack.currentIndex() == index
        assert window.project.model_dump() == before
        assert window.preview.toPlainText() == preview
    close_window(window)


def test_export_page_lists_errors_and_locates_modules(app, tmp_path):
    window = MainWindow(preset_directory=tmp_path)
    window.nav.setCurrentRow(7)
    window.export_panel.check_button.click()
    wait_for_worker(app, window)
    assert window.tabs.currentIndex() == 1
    assert window.export_panel.errors.count() > 0
    structure_error = next(window.export_panel.errors.item(i) for i in range(window.export_panel.errors.count())
                           if window.export_panel.errors.item(i).data(Qt.ItemDataRole.UserRole) == 0)
    window.export_panel.locate_error(structure_error)
    assert window.nav.currentRow() == 0
    close_window(window)


def test_xml_dialog_rejects_old_version_and_can_restore_default(app, tmp_path):
    old = tmp_path / 'old.xml'
    old.write_text('<CP2K_INPUT><CP2K_VERSION>CP2K version 2025.2</CP2K_VERSION></CP2K_INPUT>')
    dialog = XMLDialog(str(old))
    assert not dialog.check_schema()[1]
    dialog.accept()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert '2026.1' in dialog.status.text()
    dialog.restore_default()
    dialog.accept()
    assert dialog.result() == QDialog.DialogCode.Accepted and dialog.selected_path is None


def test_xml_switch_updates_service_and_report_without_changing_input(app, water, tmp_path):
    # A deliberately restrictive 2026.1 XML proves that the next parse uses
    # the selected file, rather than a stale bundled validator.
    custom = tmp_path / 'restricted.xml'
    custom.write_text('''<CP2K_INPUT><CP2K_VERSION>CP2K version 2026.1</CP2K_VERSION>
<SECTION><NAME>GLOBAL</NAME></SECTION>
<SECTION><NAME>FORCE_EVAL</NAME><SECTION><NAME>DFT</NAME><SECTION><NAME>SCF</NAME></SECTION></SECTION></SECTION>
<SECTION><NAME>MOTION</NAME><SECTION><NAME>GEO_OPT</NAME></SECTION></SECTION></CP2K_INPUT>''')
    window = MainWindow(preset_directory=tmp_path / 'presets')
    window.load_into_ui(water)
    before = window.preview.toPlainText()
    original_service = window.validation_service(window.project)
    window.set_xml_spec(str(custom))
    assert window.preview.toPlainText() == before
    assert window.project.xml_spec == str(custom)
    assert window.validation_service(window.project) is not original_service
    assert window.validation_service(window.project).schema.path == custom
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._comprehensive_result.stages[1].state == 'error'
    assert '[2] XML 语法检查\n× 失败' in window.report.toPlainText()
    assert window._step_states[7].state == 'error'
    assert 'PROJECT' in window.report.toPlainText().upper()
    project_file = tmp_path / 'project.json'
    save_project(window.project, project_file)
    assert load_project(project_file).xml_spec == str(custom)
    window.set_xml_spec(None)
    assert window.preview.toPlainText() == before
    assert window.validation_service(window.project).schema.path == BUNDLED_XML
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._comprehensive_result.stages[1].state == 'ready'
    assert 'CP2K 2026.1 XML 校验通过' in window.report.toPlainText()
    assert window._step_states[7].state == 'ready'
    close_window(window)


def test_save_preset_from_step_eight_updates_menu_without_changing_project(app, water, tmp_path, monkeypatch):
    window = MainWindow(preset_directory=tmp_path)
    window.load_into_ui(water)
    before = window.project.model_dump()
    def save_dialog(dialog):
        dialog.name.setText('我的新预设')
        dialog.description.setPlainText('描述\n第二行')
        dialog.accept()
        return dialog.result()
    monkeypatch.setattr(SavePresetDialog, 'exec', save_dialog)
    window.nav.setCurrentRow(7)
    window.export_panel.preset_button.click()
    assert window.project.model_dump() == before
    saved = window.preset_store.list().presets[0]
    assert saved.name == '我的新预设' and saved.coordinates is None
    assert saved.parameters['kinds']['O']['basis_ref']['sha256']
    assert any('我的新预设' in action.text() for action in window.my_presets_menu.actions())
    close_window(window)


def test_preset_application_can_be_cancelled_then_syncs_all_panels(app, water, tmp_path, monkeypatch):
    source = water.model_copy(deep=True)
    source.dft.cutoff = 600
    source.dft.scf.method = 'DIAGONALIZATION'
    source.global_settings.run_type = 'GEO_OPT'
    window = MainWindow(preset_directory=tmp_path)
    saved = window.preset_store.save(capture_preset(source, '几何优化参数'))
    target = water.model_copy(deep=True)
    target.structure.positions[0] = (1, 2, 3)
    window.load_into_ui(target)
    before = window.project.model_copy(deep=True)
    monkeypatch.setattr(window, 'confirm_preset_application', lambda *args: False)
    assert not window.apply_preset('user:' + saved.id)
    assert window.project == before
    monkeypatch.setattr(window, 'confirm_preset_application', lambda *args: True)
    assert window.apply_preset('user:' + saved.id)
    assert window.project.structure == before.structure
    assert window.dft_panel.fields['dft.cutoff'][0].text() == '600.0'
    assert window.scf_panel.method.currentData() == 'DIAGONALIZATION'
    assert window.global_panel.fields['global_settings.run_type'][0].currentData() == 'GEO_OPT'
    assert '&MOTION' in window.preview.toPlainText() and '&DIAGONALIZATION' in window.preview.toPlainText()
    assert window.project.xml_spec == before.xml_spec
    close_window(window)


def test_explicit_structure_preset_confirmation_and_rejected_old_schema(app, water, tmp_path, monkeypatch):
    window = MainWindow(preset_directory=tmp_path)
    source = water.model_copy(deep=True)
    source.structure.cell = ((10, 0, 0), (0, 10, 0), (0, 0, 10))
    saved = window.preset_store.save(capture_preset(source, '晶胞预设', include_cell=True))
    window.load_into_ui(water)
    confirmations = []
    monkeypatch.setattr(window, 'confirm_preset_application', lambda p, plan: confirmations.append(plan.includes_structure) or False)
    window.apply_preset('user:' + saved.id)
    assert confirmations == [True] and window.project.structure.cell == water.structure.cell
    old = tmp_path / 'old.xml'
    old.write_text('<CP2K_INPUT><CP2K_VERSION>CP2K version 2025.2</CP2K_VERSION></CP2K_INPUT>')
    with pytest.raises(ValueError):
        window.set_xml_spec(old)
    assert window.project.xml_spec is None
    close_window(window)


def test_personal_preset_management_rename_overwrite_delete_and_corrupt_files(app, water, tmp_path, monkeypatch):
    window = MainWindow(preset_directory=tmp_path)
    first = window.preset_store.save(capture_preset(water, '原名'))
    editor = SavePresetDialog(window.preset_store, water, existing=first, metadata_only=True)
    editor.name.setText('重命名')
    editor.accept()
    assert editor.result() == QDialog.DialogCode.Accepted
    assert window.preset_store.load(first.id).name == '重命名'
    duplicate = SavePresetDialog(window.preset_store, water)
    assert not duplicate.buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled()
    duplicate.name.setText('重命名')
    monkeypatch.setattr(duplicate, 'confirm_overwrite', lambda name: False)
    duplicate.accept()
    assert duplicate.saved_preset is None
    monkeypatch.setattr(duplicate, 'confirm_overwrite', lambda name: True)
    duplicate.accept()
    assert duplicate.saved_preset.id == first.id
    (tmp_path / 'broken.json').write_text('broken')
    window.rebuild_preset_menu()
    assert any('不可读' in a.text() for a in window.my_presets_menu.actions())
    manager = ManagePresetsDialog(window.preset_store, water)
    manager.changed.connect(window.rebuild_preset_menu)
    assert 'broken.json' in manager.problems.toPlainText()
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    manager.delete_selected()
    assert not window.preset_store.list().presets
    assert not any(a.text() == '重命名' for a in window.my_presets_menu.actions())
    manager.close()
    close_window(window)


def test_eighth_step_exports_same_input_as_preview_and_opens_directory(app, water, tmp_path, monkeypatch):
    window = MainWindow(preset_directory=tmp_path / 'presets')
    window.load_into_ui(water)
    expected = window.preview.toPlainText()
    dest = tmp_path / 'selected.inp'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args, **kwargs: (str(dest), ''))
    notifications = []
    monkeypatch.setattr(window, 'show_export_success', lambda path, details: notifications.append((path, details)))
    window.nav.setCurrentRow(7)
    window.export_panel.input_button.click()
    wait_for_worker(app, window)
    assert dest.read_text() == expected
    assert notifications and '依赖' in notifications[0][1]
    assert window.export_panel.directory_button.isEnabled()
    opened = []
    from ui import main_window
    monkeypatch.setattr(main_window.QDesktopServices, 'openUrl', lambda url: opened.append(url.toLocalFile()) or True)
    window.export_panel.directory_button.click()
    assert opened == [str(tmp_path)]
    close_window(window)


def test_export_invalid_configuration_shows_reasons_without_file_dialog(app, tmp_path, monkeypatch):
    window = MainWindow(preset_directory=tmp_path)
    errors = []
    monkeypatch.setattr(window, '_error', lambda title, message: errors.append(str(message)))
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args, **kwargs: pytest.fail('invalid project opened save dialog'))
    window.export_panel.input_button.click()
    assert errors and 'SUBSYS' in errors[0]
    assert 'CHARGE' not in errors[0] and 'MULTIPLICITY' not in errors[0]
    close_window(window)


def test_missing_user_preset_does_not_change_project(app, water, tmp_path, monkeypatch):
    window = MainWindow(preset_directory=tmp_path)
    window.load_into_ui(water)
    before = window.project.model_dump()
    errors = []
    monkeypatch.setattr(window, '_error', lambda title, error: errors.append(str(error)))
    assert not window.apply_preset('user:missing')
    assert errors and window.project.model_dump() == before
    close_window(window)
