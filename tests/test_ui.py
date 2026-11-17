import time
from core.models import Project
from ui.main_window import MainWindow


def dispose(window):
    window.dirty = False
    window.close()


def test_window_starts_as_incomplete_draft(app):
    window = MainWindow()
    window.show()
    app.processEvents()
    assert window.nav.count() == 8
    assert not window.export_action.isEnabled()
    assert '未生成' in window.preview.toPlainText()
    dispose(window)


def test_invalid_field_does_not_export_stale_model(app, water):
    window = MainWindow()
    window.load_into_ui(water)
    assert window.export_action.isEnabled()
    field = window.dft_panel.fields['dft.cutoff'][0]
    field.setText('not a number')
    # Export is immediately disabled even before the debounce timer fires.
    assert not window.export_action.isEnabled()
    window.refresh()
    assert not window.export_action.isEnabled()
    assert '有效数字' in window.preview.toPlainText()
    field.setText('500')
    window.refresh()
    assert window.project.dft.cutoff == 500
    assert window.export_action.isEnabled()
    field.setText('NaN')
    window.refresh()
    assert not window.export_action.isEnabled()
    dispose(window)


def test_scf_switch_only_generates_active_sections(app, water):
    window = MainWindow()
    window.load_into_ui(water)
    window.scf_panel.method.setCurrentIndex(1)
    window.refresh()
    assert '&DIAGONALIZATION' in window.preview.toPlainText()
    assert '&MIXING' in window.preview.toPlainText()
    assert '&OT' not in window.preview.toPlainText()
    window.scf_panel.method.setCurrentIndex(0)
    window.refresh()
    assert '&OT' in window.preview.toPlainText()
    assert '&DIAGONALIZATION' not in window.preview.toPlainText()
    dispose(window)


def test_edit_coordinates_and_preview(app, water):
    window = MainWindow()
    window.load_into_ui(water)
    window.structure_panel.coords.item(0, 3).setText('1.25')
    window.refresh()
    assert window.project.structure.positions[0][2] == 1.25
    assert 'O 0 0 1.25' in window.preview.toPlainText()
    window.structure_panel.cell.item(0, 0).setText('bad')
    window.refresh()
    assert not window.export_action.isEnabled()
    dispose(window)


def test_background_xml_validation(app, water):
    window = MainWindow()
    window.load_into_ui(water)
    window.check_current_configuration()
    deadline = time.monotonic() + 30
    while window._busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert not window._busy
    assert window._comprehensive_result.stages[1].state == 'ready'
    assert 'CP2K 2026.1 XML 校验通过' in window.report.toPlainText()
    dispose(window)


def test_render_structure_does_not_crash(app, water, tmp_path):
    window = MainWindow()
    window.load_into_ui(water)
    window.nav.setCurrentRow(0)
    window.show()
    app.processEvents()
    pixmap = window.grab()
    assert pixmap.width() > 1000
    assert pixmap.save(str(tmp_path/'window.png'))
    dispose(window)


def test_gui_save_and_reopen_complete_project(app, water, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog, QLabel
    window = MainWindow()
    window.load_into_ui(water)
    name = window.global_panel.fields['global_settings.project_name'][0]
    assert name.accessibleName() == '项目名称'
    assert not any(label.text() == 'PROJECT' for label in window.global_panel.cards[0].findChildren(QLabel))
    name.setText('edited_project')
    window.dft_panel.fields['dft.cutoff'][0].setText('600')
    window.dft_panel.fields['dft.charge'][0].setText('1')
    window.dft_panel.fields['dft.multiplicity'][0].setText('2')
    window.dft_panel.fields['dft.uks'][0].setChecked(True)
    path = tmp_path/'saved.json'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(path), ''))
    assert window.save()
    window.load_into_ui(Project())
    window._open_path(path)
    assert window.project.dft.cutoff == 600
    assert window.project.dft.charge == 1 and window.project.dft.multiplicity == 2
    assert window.project.dft.uks and window.dft_panel.fields['dft.uks'][0].isChecked()
    assert window.project.global_settings.project_name == name.text() == 'edited_project'
    assert 'PROJECT edited_project' in window.preview.toPlainText()
    assert window.structure_panel.coords.rowCount() == 3
    assert window.preview.toPlainText().count('&KIND ') == 2
    dispose(window)


def test_invalid_project_and_structure_leave_existing_state(app, water, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    window = MainWindow()
    window.load_into_ui(water)
    before=window.project.model_copy(deep=True)
    errors = []
    monkeypatch.setattr(window, '_error', lambda title, error: errors.append(str(error)))
    path = tmp_path/'broken.json'
    path.write_text('invalid')
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    window.project_actions['open'].trigger()
    assert window.project == before
    bad_structure = tmp_path/'broken.xyz'
    bad_structure.write_text('invalid')
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(bad_structure), ''))
    window.import_structure()
    assert window.project == before
    assert len(errors) == 2
    dispose(window)


def test_import_new_element_preserves_existing_kind_and_never_guesses(app, water, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    window = MainWindow()
    window.load_into_ui(water)
    path = tmp_path/'ammonia.xyz'
    path.write_text('2\npartial example\nN 0 0 0\nH 0 0 1\n')
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    window.import_structure()
    rows = {window.kind_panel.table.item(i, 0).text(): i for i in range(2)}
    assert window.kind_panel._records['H']['basis_set'] == 'DZVP-MOLOPT-GTH'
    assert window.kind_panel._records['N']['basis_set'] == ''
    assert window.kind_panel.table.cellWidget(rows['H'],1).currentData().element=='H'
    assert not window.export_action.isEnabled()
    assert window.project.dft.charge == 0  # preserves explicit user choice
    assert 'KIND N' in window.preview.toPlainText()
    dispose(window)
