"""Task forms, localization, dirty/check state and generated properties agree."""
from tests.vibrational_helpers import set_model_spectra, set_ui_spectra
from pathlib import Path
import pytest
from PySide6.QtWidgets import QFileDialog, QLabel
from core.generator import generate_input
from core.presets import capture_preset
from i18n.language_manager import language_manager
from ui.main_window import MainWindow
from ui.widgets.status_badge import STATUS_ROLE
from tests.test_layout_workflow import wait_for_worker


@pytest.fixture
def window(app, vib_project, tmp_path):
    value = MainWindow(preset_directory=tmp_path / 'presets')
    value.load_into_ui(vib_project)
    value.show()
    value.nav.setCurrentRow(5)
    app.processEvents()
    yield value
    wait_for_worker(app, value)
    value.dirty = False
    value.close()
    app.processEvents()
    language_manager().set_language('zh_CN')


def choose_task(window, task):
    combo = window.global_panel.fields['global_settings.run_type'][0]
    combo.setCurrentIndex(combo.findData(task))
    window.refresh()


def test_three_tasks_reuse_step_six_and_preserve_independent_settings(window):
    w = window
    geometry, vibration = w.motion_panel, w.vibrational_panel
    combo = w.global_panel.fields['global_settings.run_type'][0]
    assert [combo.itemData(i) for i in range(combo.count())] == ['ENERGY', 'GEO_OPT', 'CELL_OPT', 'MD', 'VIBRATIONAL_ANALYSIS']
    assert w.stack.count() == w.nav.count() == 8
    assert w.stack.widget(5).widget() is w.task_panel
    assert w.task_panel.stack.currentWidget() is vibration
    assert w.nav.item(5).text() == '06  振动分析'
    choose_task(w, 'GEO_OPT')
    geometry.fields['motion.max_iter'][0].setText('325')
    # Switch before the debounce timer: valid inactive edits are retained.
    combo.setCurrentIndex(combo.findData('VIBRATIONAL_ANALYSIS'))
    w.refresh()
    assert w.project.motion.max_iter == 325 and w.task_panel.stack.currentWidget() is vibration
    vibration.fields['vibrational.dx'][0].setText('0.005')
    choose_task(w, 'ENERGY')
    assert w.project.vibrational.dx == .005
    assert not geometry.isEnabled() and w._step_states[5].state == 'na'
    choose_task(w, 'GEO_OPT')
    assert geometry.fields['motion.max_iter'][0].text() == '325'
    assert w.task_panel.stack.currentWidget() is geometry and geometry.isEnabled()
    choose_task(w, 'VIBRATIONAL_ANALYSIS')
    assert vibration.fields['vibrational.dx'][0].text() == '0.005'
    assert w._step_states[5].state != 'na'


@pytest.mark.parametrize('mode,section', [('FREQUENCIES', None), ('IR', '&MOMENTS ON'), ('RAMAN', '&POLAR TRUE')])
def test_mode_and_derived_intensities_update_preview(window, mode, section):
    w = window
    panel = w.vibrational_panel
    set_ui_spectra(panel, mode)
    w.refresh()
    assert w.project.vibrational.spectra_label == mode
    assert not hasattr(panel, 'mode') and not hasattr(panel, 'intensities')
    assert panel.ir_enabled.isChecked() is (mode == 'IR')
    assert panel.raman_enabled.isChecked() is (mode == 'RAMAN')
    assert w.preview.toPlainText() == generate_input(w.project, catalog=w.kind_panel.catalog)
    if section:
        assert section in w.preview.toPlainText()
    else:
        assert '&MOMENTS' not in w.preview.toPlainText() and '&POLAR' not in w.preview.toPlainText()
    assert not panel.raman_card.isHidden()
    assert panel.fields['vibrational.linres_eps'][0].isEnabled() is (mode == 'RAMAN')


def test_invalid_draft_blocks_export_and_inactive_draft_does_not_block_energy(window):
    field = window.vibrational_panel.fields['vibrational.dx'][0]
    field.setText('invalid')
    assert not window.export_action.isEnabled()
    window.refresh()
    assert window._validation.errors and field.property('invalid')
    assert window.nav.item(5).data(STATUS_ROLE) == 'error'
    choose_task(window, 'ENERGY')
    assert window.export_action.isEnabled()
    assert field.text() == 'invalid'  # Never silently reset the draft.
    choose_task(window, 'VIBRATIONAL_ANALYSIS')
    assert window._validation.errors and not window.export_action.isEnabled()
    field.setText('.01')
    window.refresh()
    assert window.export_action.isEnabled()


@pytest.mark.parametrize('optional', ['thermochemistry', 'linres'])
def test_disabled_optional_fields_keep_drafts_without_blocking_other_modes(window, optional):
    panel = window.vibrational_panel
    if optional == 'thermochemistry':
        panel.thermo.setChecked(True)
        field = panel.fields['vibrational.tc_temperature'][0]
    else:
        set_ui_spectra(panel, 'RAMAN')
        field = panel.fields['vibrational.linres_eps'][0]
    field.setText('invalid')
    window.refresh()
    assert not window.export_action.isEnabled()
    if optional == 'thermochemistry':
        panel.thermo.setChecked(False)
    else:
        set_ui_spectra(panel, 'FREQUENCIES')
    window.refresh()
    assert window.export_action.isEnabled() and field.text() == 'invalid'
    assert window.project.vibrational.spectra_label == 'FREQUENCIES'
    field.setText('301.5' if optional == 'thermochemistry' else '2e-9')
    window.refresh()
    assert (window.project.vibrational.tc_temperature == 301.5 if optional == 'thermochemistry'
            else window.project.vibrational.linres_eps == 2e-9)


def test_mpi_changes_and_vibration_edits_invalidate_comprehensive_check(window, app):
    w = window
    w.check_current_configuration()
    wait_for_worker(app, w)
    assert w.nav.item(7).data(STATUS_ROLE) == 'warning'  # WAVELET's density-boundary warning remains.
    w.vibrational_panel.fields['vibrational.nproc_rep'][0].setText('8')
    assert w.nav.item(5).data(STATUS_ROLE) == 'unchecked'
    assert w.nav.item(7).data(STATUS_ROLE) == 'unchecked'
    w.refresh()
    w.run_panel.mpi_processes.setValue(3)
    w.refresh()
    assert w.nav.item(5).data(STATUS_ROLE) == 'error'
    assert not w.export_action.isEnabled() and 'NPROC_REP' in w.report.toPlainText()
    w.run_panel.mpi_processes.setValue(16)
    w.refresh()
    assert w.export_action.isEnabled() and w._step_states[7].state == 'unchecked'


def test_live_languages_preserve_mode_data_dirty_check_and_input(window, app):
    w = window
    set_ui_spectra(w.vibrational_panel, 'RAMAN')
    w.refresh()
    w.check_current_configuration()
    wait_for_worker(app, w)
    before = w.project.model_dump_json(), w.dirty, w._revision, w.preview.toPlainText().encode()
    result = w._comprehensive_result
    for language in ['en_US', 'zh_CN', 'en_US']:
        w.language_selector.setCurrentIndex(w.language_selector.findData(language))
        app.processEvents()
        panel = w.vibrational_panel
        assert panel is w.task_panel.stack.currentWidget()
        assert panel.raman_enabled.isChecked() and not panel.ir_enabled.isChecked()
        assert panel.raman_enabled.text() == ('Raman Intensities' if language == 'en_US' else '拉曼强度（Raman）')
        assert w.nav.item(5).text() == ('06  Vibrational Analysis' if language == 'en_US' else '06  振动分析')
        assert panel.findChild(QLabel, 'heading').text() == ('06 · Vibrational Analysis' if language == 'en_US' else '06 · 振动分析')
        assert (w.project.model_dump_json(), w.dirty, w._revision, w.preview.toPlainText().encode()) == before
        assert w._comprehensive_result is result and w._step_states[7].state == 'warning'
        assert w.preview.toPlainText() == generate_input(w.project, catalog=w.kind_panel.catalog)


def test_project_and_preset_restore_task_mode_and_step_six(window, app, tmp_path, monkeypatch):
    w = window
    set_ui_spectra(w.vibrational_panel, 'IR')
    w.vibrational_panel.fields['vibrational.hessian'][0].setChecked(True)
    w.refresh()
    preset = w.preset_store.save(capture_preset(w.project, 'IR preset', category='custom'))
    path = tmp_path / 'vibrational.cp2kstudio.json'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(path), ''))
    assert w.save(force_dialog=True)
    expected = w.project.model_dump_json(), w.preview.toPlainText()
    w.new_project()
    w._open_path(path)
    assert (w.project.model_dump_json(), w.preview.toPlainText()) == expected
    assert w.vibrational_panel.ir_enabled.isChecked() and not w.vibrational_panel.raman_enabled.isChecked()
    assert w.task_panel.stack.currentWidget() is w.vibrational_panel
    choose_task(w, 'GEO_OPT')
    monkeypatch.setattr(w, 'confirm_preset_application', lambda *args: True)
    assert w.apply_preset('user:' + preset.id)
    assert w.project.global_settings.run_type == 'VIBRATIONAL_ANALYSIS'
    assert w.vibrational_panel.ir_enabled.isChecked() and not w.vibrational_panel.raman_enabled.isChecked()
    assert w.nav.item(5).text() == '06  振动分析'
    assert w.project.vibrational.hessian and '&MOMENTS ON' in w.preview.toPlainText()


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_vibrational_page_scrolls_without_horizontal_overflow(window, app, language):
    language_manager().set_language(language)
    set_ui_spectra(window.vibrational_panel, 'RAMAN')
    window.resize(1366, 768)
    for _ in range(5):
        app.processEvents()
    scroll = window.stack.widget(5)
    assert all(not card.title_label.wordWrap() for card in window.vibrational_panel.cards)
    assert scroll.horizontalScrollBar().maximum() == 0
    assert scroll.verticalScrollBar().maximum() > 0
    scroll.ensureWidgetVisible(window.vibrational_panel.fields['vibrational.linres_eps'][0])
    app.processEvents()
    assert window.vibrational_panel.fields['vibrational.linres_eps'][0].isVisibleTo(window)
