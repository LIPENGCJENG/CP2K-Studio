"""Explicit, session-only step-eight checks must never be inferred from readiness."""
import json
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from core.models import Project
from tests.test_layout_workflow import wait_for_worker
from ui.main_window import MainWindow
from ui.widgets.section_card import SectionCard
from ui.widgets.status_badge import STATUS_ROLE


@pytest.fixture
def window(app, water, tmp_path):
    water.global_settings.run_type = 'GEO_OPT'
    window = MainWindow(preset_directory=tmp_path / 'presets')
    window.load_into_ui(water)
    window.show()
    app.processEvents()
    yield window
    window.dirty = False
    window.close()


def state(window, expected):
    assert window._step_states[7].state == expected
    assert window.nav.item(7).data(STATUS_ROLE) == expected


def check(window):
    QTest.mouseClick(window.export_panel.check_button, Qt.MouseButton.LeftButton)
    from PySide6.QtWidgets import QApplication
    wait_for_worker(QApplication.instance(), window)


def test_ready_or_new_projects_require_explicit_check(window):
    assert not window._validation.errors and not window._validation.warnings
    state(window, 'unchecked')
    original = [status.state for status in window._step_states[:7]]
    for index in range(8):
        window.nav.setCurrentRow(index)
    window.refresh()
    state(window, 'unchecked')
    check(window)
    state(window, 'ready')
    assert original == [status.state for status in window._step_states[:7]]
    window.refresh()
    state(window, 'ready')
    window.new_project()
    assert window.project.structure is None
    state(window, 'unchecked')
    check(window)
    state(window, 'error')


def test_explicit_error_repair_and_recheck(window):
    field = window.dft_panel.fields['dft.cutoff'][0]
    field.setText('invalid')
    state(window, 'unchecked')
    check(window)
    state(window, 'error')
    assert '有效数字' in window.report.toPlainText()
    field.setText('500')
    state(window, 'unchecked')
    window.refresh()
    state(window, 'unchecked')
    check(window)
    state(window, 'ready')


def test_warning_only_explicit_check_is_yellow(window):
    panel = window.kind_panel
    potential = panel.catalog.find('potential', 'O', 'GTH-BLYP-q6')[0]
    panel.choose('O', 'potential', potential)
    assert not window._validation.errors and window._validation.warnings
    state(window, 'unchecked')
    check(window)
    state(window, 'warning')
    assert '警告' in window.export_panel.status.text()
    assert 'XC' in window.report.toPlainText()


@pytest.mark.parametrize('page', ['GLOBAL', 'structure', 'DFT', 'SCF', 'KIND', 'motion', 'run'])
def test_all_configuration_pages_immediately_invalidate_check(window, page):
    check(window)
    state(window, 'ready')
    if page == 'GLOBAL':
        window.global_panel.fields['global_settings.project_name'][0].setText('changed_project')
    elif page == 'structure':
        window.structure_panel.coords.item(0, 1).setText('0.25')
    elif page == 'DFT':
        window.dft_panel.fields['dft.cutoff'][0].setText('500')
    elif page == 'SCF':
        window.scf_panel.fields['dft.scf.max_scf'][0].setText('99')
    elif page == 'KIND':
        panel = window.kind_panel
        basis = panel.catalog.find('basis', 'O', 'TZV2P-MOLOPT-GTH')[0]
        panel.choose('O', 'basis', basis)
    elif page == 'motion':
        window.motion_panel.fields['motion.max_iter'][0].setText('220')
    else:
        window.run_panel.mpi_processes.setValue(8)
    state(window, 'unchecked')
    window.refresh()
    state(window, 'unchecked')
    check(window)
    state(window, 'ready')


def test_save_open_and_preset_never_restore_a_saved_check(window, tmp_path, monkeypatch):
    check(window)
    state(window, 'ready')
    path = tmp_path / 'saved.json'
    window.project_path = path
    assert window.save()
    assert not any('check_revision' in key or 'check_snapshot' in key for key in json.loads(path.read_text()))
    state(window, 'ready')
    window._open_path(path)
    state(window, 'unchecked')
    check(window)
    state(window, 'ready')
    monkeypatch.setattr(window, 'confirm_preset_application', lambda *args: True)
    assert window.apply_preset('single_point')
    state(window, 'unchecked')


def test_signalless_collected_changes_invalidate_permanently(window):
    check(window)
    state(window, 'ready')
    field = window.dft_panel.fields['dft.cutoff'][0]
    field.blockSignals(True)
    field.setText('500')
    field.blockSignals(False)
    window.refresh()
    state(window, 'unchecked')
    field.blockSignals(True)
    field.setText('400')
    field.blockSignals(False)
    window.refresh()
    state(window, 'unchecked')


def test_export_buttons_position_style_and_signals(window, app):
    window.nav.setCurrentRow(7)
    app.processEvents()
    panel = window.export_panel
    card = next(card for card in panel.findChildren(SectionCard) if card.title_label.text() == '导出 CP2K Input')
    assert card.content.itemAt(0).widget() is panel.bundle_button
    row = card.content.itemAt(1).layout()
    assert row.itemAt(0).widget() is panel.input_button
    assert row.itemAt(1).widget() is panel.directory_button
    assert panel.bundle_button.objectName() == 'primary'
    assert panel.input_button.objectName() != 'primary'
    assert panel.bundle_button.width() > panel.input_button.width()
    assert panel.bundle_button.y() < panel.input_button.y() == panel.directory_button.y()
    signals = []
    # Isolate UI signal routing; real INP and ZIP exports remain covered by
    # test_layout_workflow and test_run_environment_ui.
    panel.bundle_requested.disconnect()
    panel.input_requested.disconnect()
    panel.directory_requested.disconnect()
    panel.bundle_requested.connect(lambda: signals.append('bundle'))
    panel.input_requested.connect(lambda: signals.append('inp'))
    panel.directory_requested.connect(lambda: signals.append('directory'))
    panel.directory_button.setEnabled(True)
    for button in [panel.bundle_button, panel.input_button, panel.directory_button]:
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert signals == ['bundle', 'inp', 'directory']
    state(window, 'unchecked')
