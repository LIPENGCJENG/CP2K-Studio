"""Persistent AIMD controls and presentation-only language/task switching."""
import numpy as np
import pytest
from PySide6.QtWidgets import QFileDialog
from core.generator import generate_input
from core.project_io import save_project, load_project, export_bundle
from core.presets import capture_preset, apply_preset
from i18n.language_manager import language_manager
from tests.test_poisson_reference_ui import window
from tests.test_layout_workflow import wait_for_worker
from tests.test_md import restart_text


def select_md(w):
    combo = w.global_panel.fields['global_settings.run_type'][0]
    combo.setCurrentIndex(combo.findData('MD'))
    w.refresh()
    w.nav.setCurrentRow(5)
    return w.md_panel


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
@pytest.mark.parametrize('width', [1050,1480])
def test_md_task_four_cards_default_fields_and_bilingual_layout(window, app, language, width):
    w = window
    language_manager().set_language(language)
    w.resize(width,900)
    panel = select_md(w)
    for _ in range(8): app.processEvents()
    assert w.nav.count() == 8 and w.task_panel.stack.currentWidget() is panel
    assert w.nav.item(5).text() == ('06  Molecular Dynamics' if language == 'en_US' else '06  分子动力学')
    assert len(panel.cards) == 4 and all(c.help_icon.toolTip() for c in panel.cards)
    assert panel.cards[0].title_label.text() == ('MD Basic Settings' if language == 'en_US' else 'MD 基本设置')
    assert panel.ensemble.currentData() == 'NVT'
    assert [panel.ensemble.itemData(i) for i in range(panel.ensemble.count())] == ['NVT','NVE']
    assert panel.steps.text() == '2000' and panel.timestep.text() == '0.5'
    assert '1.000 ps' in panel.total_time.text()
    assert panel.write_trajectory.isChecked() and panel.write_restart.isChecked()
    assert panel.trajectory_interval.text() == '10' and panel.restart_interval.text() == '100'
    assert panel.backups.text() == '2' and panel.trajectory_format.currentData() == 'XYZ'
    assert not panel.continue_restart.isChecked() and not panel.restart_file.isEnabled()
    assert w.stack.widget(5).horizontalScrollBar().maximum() == 0
    assert w.preview.toPlainText() == generate_input(w.project)


def test_ensemble_outputs_and_simulation_time_update_without_losing_drafts(window, app):
    w = window;panel = select_md(w)
    panel.timecon.setText('73.125')
    panel.steps.setText('3333');panel.timestep.setText('0.6')
    assert '2.000 ps' in panel.total_time.text()
    panel.ensemble.setCurrentIndex(panel.ensemble.findData('NVE'))
    w.refresh()
    assert not panel.thermostat_card.isEnabled() and '&THERMOSTAT' not in w.preview.toPlainText()
    assert w.project.md.timecon == 73.125
    panel.ensemble.setCurrentIndex(panel.ensemble.findData('NVT'));w.refresh()
    assert panel.timecon.isEnabled() and panel.timecon.text() == '73.125'
    assert 'TIMECON 73.125' in w.preview.toPlainText()
    panel.write_trajectory.setChecked(False);panel.write_restart.setChecked(False);w.refresh()
    assert not panel.trajectory_interval.isEnabled() and not panel.restart_interval.isEnabled()
    assert '&TRAJECTORY OFF' in w.preview.toPlainText() and '&RESTART OFF' in w.preview.toPlainText()
    panel.timestep.setText('bad');w.refresh()
    assert not w._validation.ok and panel.timestep.property('invalid')
    assert '—' in panel.total_time.text()
    combo = w.global_panel.fields['global_settings.run_type'][0]
    combo.setCurrentIndex(combo.findData('ENERGY'));w.refresh()
    assert w._validation.ok and panel.timestep.text() == 'bad'


def test_task_language_project_and_preset_roundtrips_preserve_aimd_and_check_state(window, app, tmp_path):
    w = window;panel = select_md(w)
    panel.timecon.setText('88.5');panel.steps.setText('1234')
    panel.trajectory_format.setCurrentIndex(panel.trajectory_format.findData('EXTXYZ'));w.refresh()
    w.check_current_configuration();wait_for_worker(app,w)
    assert w._step_states[5].state == w._step_states[7].state == 'ready'
    checked = w._comprehensive_result
    view = w.structure_panel.view
    view.zoom = 1.7;view.pan_offset = np.array([.1,.2,.3])
    before = w.project.model_dump_json(),w._revision,w.dirty,w.preview.toPlainText()
    for lang in ['en_US','zh_CN','en_US']:
        language_manager().set_language(lang);app.processEvents()
        assert (w.project.model_dump_json(),w._revision,w.dirty,w.preview.toPlainText()) == before
        assert w._comprehensive_result is checked and view.zoom == 1.7
        assert np.array_equal(view.pan_offset,[.1,.2,.3])
    combo = w.global_panel.fields['global_settings.run_type'][0]
    for task in ['GEO_OPT','CELL_OPT','VIBRATIONAL_ANALYSIS','ENERGY','MD']:
        combo.setCurrentIndex(combo.findData(task));w.refresh()
        assert w.project.md.steps == 1234 and w.project.md.timecon == 88.5
    panel.steps.setText('3000')
    assert w._step_states[7].state == 'unchecked'
    w.refresh()
    path = tmp_path/'md.json';save_project(w.project,path)
    reopened = load_project(path);w.load_into_ui(reopened)
    assert panel.steps.text() == '3000' and panel.timecon.text() == '88.5'
    preset = capture_preset(reopened,'MD settings')
    assert apply_preset(reopened,preset).project.md == reopened.md
    package = export_bundle(reopened,tmp_path/'md-job')
    assert 'RUN_TYPE MD' in package.read_text() and 'FORMAT EXTXYZ' in package.read_text()


def test_restart_picker_cancel_choose_and_invalid_state_never_clobber_project(window, app, monkeypatch, tmp_path):
    w = window;panel = select_md(w)
    state = w.project.model_dump_json()
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k: ('',''))
    panel.choose_restart()
    assert w.project.model_dump_json() == state and not panel.restart_file.text()
    file = tmp_path/'水 (MD).restart';file.write_text(restart_text(w.project))
    panel.continue_restart.setChecked(True)
    assert panel.restart_file.isEnabled() and panel.browse.isEnabled()
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k: (str(file),''))
    panel.choose_restart();w.refresh()
    assert w.project.md.continue_from_restart and w.project.md.restart_file == str(file)
    assert w._validation.ok  # A complete package can normalize this unsafe path.
    assert w.project.structure.model_dump_json() == load_project_data_structure(state)
    file.unlink();w.refresh()
    assert not w._validation.ok and w._step_states[5].state == 'error'
    panel.continue_restart.setChecked(False);w.refresh()
    assert w._validation.ok and w.project.md.restart_file == str(file)
    assert '&EXT_RESTART' not in w.preview.toPlainText()


def load_project_data_structure(text):
    from core.models import Project
    return Project.model_validate_json(text).structure.model_dump_json()


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
def test_invalid_numeric_bounds_report_in_current_language_without_adjustment(window, app, language):
    w = window;panel = select_md(w)
    language_manager().set_language(language)
    panel.steps.setText('0');w.refresh()
    assert panel.steps.text() == '0' and not w._validation.ok
    report = w.report.toPlainText()
    assert ('must be an integer' if language == 'en_US' else '必须为大于或等于') in report
    assert panel.steps.property('invalid')
    panel.steps.setText('2000');panel.timestep.setText('-0.5');w.refresh()
    assert ('finite positive number' if language == 'en_US' else '有限正数') in w.report.toPlainText()
