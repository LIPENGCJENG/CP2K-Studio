"""Two aligned LINRES rows, conditional editing and no coupling to OT."""
import numpy as np
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QFileDialog

from core.models import LINRES_PRECONDITIONERS
from core.generator import generate_input
from core.validator import InputValidator
from core.presets import capture_preset
from i18n.language_manager import language_manager
from tests.test_vibrational_ui import window
from tests.test_layout_workflow import wait_for_worker


def controls(panel):
    return [panel.fields['vibrational.' + key][0] for key in
            ['linres_eps','linres_max_iter','linres_preconditioner','linres_energy_gap']]


def prepare(window):
    project = window.project.model_copy(deep=True)
    project.dft.poisson_solver = 'MT'
    project.dft.scf.preconditioner = 'FULL_KINETIC'
    project.dft.scf.energy_gap = .08
    window.load_into_ui(project)
    return window.vibrational_panel


def test_defaults_and_raman_none_full_all_enablement_preserve_values(window):
    panel = prepare(window)
    eps, maximum, preconditioner, gap = controls(panel)
    assert not panel.raman_enabled.isChecked()
    assert all(not control.isEnabled() for control in controls(panel))
    assert [preconditioner.itemData(i) for i in range(preconditioner.count())] == list(LINRES_PRECONDITIONERS)
    assert float(eps.text()) == 1e-7 and maximum.text() == '200'
    assert preconditioner.currentData() == 'FULL_ALL' and gap.text() == '0.1' and gap.unit_label.text() == 'Ha'
    panel.ir_enabled.setChecked(True)
    assert all(not control.isEnabled() for control in controls(panel))
    panel.raman_enabled.setChecked(True)
    assert eps.isEnabled() and maximum.isEnabled() and preconditioner.isEnabled()
    assert gap.isEnabled()
    gap.setText('7.654321098765432e-3')
    window.refresh()
    assert window.project.vibrational.linres_energy_gap == .007654321098765432
    preconditioner.setCurrentIndex(preconditioner.findData('NONE'))
    assert not gap.isEnabled() and gap.text() == '7.654321098765432e-3'
    window.refresh()
    tree = InputValidator().parse(window.preview.toPlainText()).tree
    assert 'energy_gap' not in tree['+force_eval'][0]['+properties']['+linres']
    preconditioner.setCurrentIndex(preconditioner.findData('FULL_SINGLE'))
    assert gap.isEnabled() and gap.text() == '7.654321098765432e-3'
    panel.raman_enabled.setChecked(False)
    assert all(not control.isEnabled() for control in controls(panel))
    window.refresh()
    assert '&LINRES' not in window.preview.toPlainText() and '&MOMENTS ON' in window.preview.toPlainText()
    panel.raman_enabled.setChecked(True)
    window.refresh()
    assert all(control.isEnabled() for control in controls(panel))
    assert preconditioner.currentData() == 'FULL_SINGLE' and window.project.vibrational.linres_energy_gap == .007654321098765432
    assert window.project.dft.scf.preconditioner == 'FULL_KINETIC' and window.project.dft.scf.energy_gap == .08


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_new_project_defaults_language_and_task_switch_are_state_neutral(window, app, language):
    window.dirty = False
    window.new_project()
    panel = window.vibrational_panel
    eps, maximum, preconditioner, gap = controls(panel)
    assert float(eps.text()) == 1e-7 and maximum.text() == '200'
    assert preconditioner.currentData() == 'FULL_ALL' and gap.text() == '0.1'
    assert all(not control.isEnabled() for control in controls(panel))
    snapshot = window.project.model_dump_json(), window._revision, window.dirty
    language_manager().set_language(language)
    app.processEvents()
    assert (window.project.model_dump_json(), window._revision, window.dirty) == snapshot
    assert not window.dirty
    task = window.global_panel.fields['global_settings.run_type'][0]
    task.setCurrentIndex(task.findData('VIBRATIONAL_ANALYSIS'))
    panel.raman_enabled.setChecked(True)
    window.refresh()
    assert all(control.isEnabled() for control in controls(panel))
    expected = window.project.vibrational.model_dump()
    for run_type in ['ENERGY', 'GEO_OPT', 'CELL_OPT', 'MD', 'VIBRATIONAL_ANALYSIS']:
        task.setCurrentIndex(task.findData(run_type))
        window.refresh()
        assert window.project.vibrational.model_dump() == expected


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_default_threshold_check_passes_and_looser_value_warns(window, app, language):
    panel = prepare(window)
    language_manager().set_language(language)
    panel.raman_enabled.setChecked(True)
    window.refresh()
    assert window.project.vibrational.linres_eps == 1e-7
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[5].state == window._step_states[7].state == 'ready'
    assert all(m.code != 'vib.linres_warning' for m in window._comprehensive_result.validation.warnings)
    panel.fields['vibrational.linres_eps'][0].setText('1e-6')
    window.refresh()
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[5].state == window._step_states[7].state == 'warning'
    assert '1e-7' in window.report.toPlainText()


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
@pytest.mark.parametrize('width', [1500,1366])
def test_two_rows_two_columns_and_help_icons_align(window, app, language, width):
    panel = prepare(window)
    panel.raman_enabled.setChecked(True)
    panel.linres_preconditioner.setCurrentIndex(panel.linres_preconditioner.findData('FULL_ALL'))
    language_manager().set_language(language)
    window.resize(width, 940)
    for _ in range(6):
        app.processEvents()
    eps, maximum, preconditioner, gap = controls(panel)
    points = [control.mapTo(panel, QPoint()) for control in controls(panel)]
    assert points[0].x() == points[2].x() and points[1].x() == points[3].x()
    assert abs(points[0].y() - points[1].y()) <= 1
    assert abs(points[2].y() - points[3].y()) <= 1 and points[2].y() > points[0].y()
    assert max(c.width() for c in controls(panel)) - min(c.width() for c in controls(panel)) <= 1
    assert max(c.height() for c in controls(panel)) - min(c.height() for c in controls(panel)) <= 1
    for label, icon, control in [(panel.linres_preconditioner_label, panel.linres_preconditioner_help, preconditioner),
                                  (panel.linres_energy_gap_label, panel.linres_energy_gap_help, gap)]:
        a, b = label.mapTo(panel, label.rect().center()), icon.mapTo(panel, icon.rect().center())
        assert abs(a.y() - b.y()) <= 1 and b.x() > a.x()
        assert icon.parentWidget() is control.parentWidget()
    assert window.stack.widget(5).horizontalScrollBar().maximum() == 0
    assert panel.raman_card is panel.cards[3] and not panel.raman_card.isHidden()


@pytest.mark.parametrize('value', ['invalid','0','-0.1','nan','inf'])
def test_invalid_gap_draft_only_blocks_when_raman_preconditioning_is_active(window, value):
    panel = prepare(window)
    panel.raman_enabled.setChecked(True)
    panel.linres_preconditioner.setCurrentIndex(panel.linres_preconditioner.findData('FULL_ALL'))
    panel.linres_energy_gap.setText(value)
    window.refresh()
    assert window._validation.errors and not window.export_action.isEnabled()
    panel.raman_enabled.setChecked(False)
    window.refresh()
    assert not window._validation.errors and window.export_action.isEnabled()
    assert panel.linres_energy_gap.text() == value and not panel.linres_energy_gap.isEnabled()
    panel.raman_enabled.setChecked(True)
    panel.linres_preconditioner.setCurrentIndex(panel.linres_preconditioner.findData('NONE'))
    window.refresh()
    assert not window._validation.errors and not panel.linres_energy_gap.isEnabled()
    panel.linres_preconditioner.setCurrentIndex(panel.linres_preconditioner.findData('FULL_ALL'))
    window.refresh()
    assert window._validation.errors
    panel.linres_energy_gap.setText('0.01')
    window.refresh()
    assert not window._validation.errors and window.export_action.isEnabled()


def test_locales_info_severity_preview_and_camera_preserve_settings(window, app):
    panel = prepare(window)
    panel.fields['vibrational.linres_eps'][0].setText('1e-8')
    panel.ir_enabled.setChecked(True)
    panel.raman_enabled.setChecked(True)
    panel.linres_preconditioner.setCurrentIndex(panel.linres_preconditioner.findData('FULL_ALL'))
    panel.linres_energy_gap.setText('0.0012345678901234567')
    window.refresh()
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[5].state == window._step_states[7].state == 'ready'
    assert not window._comprehensive_result.validation.warnings
    view = window.structure_panel.view
    view.zoom = 1.6
    view.pan_offset = np.array([.1,.2,.3])
    view.set_labels_visible(True)
    rotation = view.rotation.copy()
    before = window.project.model_dump_json(), window.preview.toPlainText(), window._revision, window.dirty
    for language in ['en_US','zh_CN','en_US']:
        language_manager().set_language(language)
        app.processEvents()
        for icon in [panel.linres_preconditioner_help, panel.linres_energy_gap_help]:
            document = QTextDocument()
            document.setHtml(icon.toolTip())
            text = document.toPlainText()
            assert 'LINRES /' in text and ('independent' if language == 'en_US' else '相互独立') in text
        assert 'FULL_SINGLE_INVERSE' in panel.linres_preconditioner_help.toolTip()
        assert '0.001–0.01' in panel.linres_energy_gap_help.toolTip()
        assert '0.2 Ha' in panel.linres_energy_gap_help.toolTip()
        assert (window.project.model_dump_json(), window.preview.toPlainText(), window._revision, window.dirty) == before
        assert view.zoom == 1.6 and view.show_labels and np.array_equal(view.rotation, rotation)
        assert np.array_equal(view.pan_offset, [.1,.2,.3])
        assert window._step_states[7].state == 'ready'
    assert window.preview.toPlainText() == generate_input(window.project, catalog=window.kind_panel.catalog)
    panel.linres_preconditioner.setCurrentIndex(panel.linres_preconditioner.findData('FULL_KINETIC'))
    assert window._step_states[7].state == 'unchecked'


def test_project_and_preset_restore_ui_independently_of_ot(window, tmp_path, monkeypatch):
    panel = prepare(window)
    panel.raman_enabled.setChecked(True)
    panel.linres_preconditioner.setCurrentIndex(panel.linres_preconditioner.findData('FULL_ALL'))
    panel.linres_energy_gap.setText('0.006')
    window.refresh()
    path = tmp_path / 'linres.json'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(path), ''))
    assert window.save(force_dialog=True)
    preset = window.preset_store.save(capture_preset(window.project, 'Raman preconditioning'))
    text = window.preview.toPlainText()
    panel.linres_preconditioner.setCurrentIndex(panel.linres_preconditioner.findData('NONE'))
    window.refresh()
    window.dirty = False
    window._open_path(path)
    assert panel.linres_preconditioner.currentData() == 'FULL_ALL' and panel.linres_energy_gap.text() == '0.006'
    assert panel.linres_energy_gap.isEnabled() and window.preview.toPlainText() == text
    panel.raman_enabled.setChecked(False)
    window.refresh()
    monkeypatch.setattr(window, 'confirm_preset_application', lambda *a: True)
    assert window.apply_preset('user:' + preset.id)
    assert panel.raman_enabled.isChecked() and panel.linres_preconditioner.currentData() == 'FULL_ALL'
    assert window.project.dft.scf.preconditioner == 'FULL_KINETIC' and window.project.dft.scf.energy_gap == .08
    assert window.preview.toPlainText() == text
