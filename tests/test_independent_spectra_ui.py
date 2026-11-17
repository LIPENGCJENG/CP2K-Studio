"""Real checkboxes drive previews and validation without rebuilding state."""
import numpy as np
import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QComboBox, QCheckBox, QFileDialog

from core.generator import generate_input
from core.input_export import export_input
from core.presets import capture_preset
from i18n.language_manager import language_manager
from ui.theme import COLORS
from tests.test_vibrational_ui import window
from tests.test_layout_workflow import wait_for_worker


def prepare(window, periodic='NONE'):
    project = window.project.model_copy(deep=True)
    project.structure.periodic = periodic
    project.dft.poisson_solver = 'MT' if periodic == 'NONE' else 'PERIODIC'
    project.vibrational.fully_periodic = periodic == 'XYZ'
    window.load_into_ui(project)
    return window.vibrational_panel


def test_new_ui_has_permanent_frequencies_two_switches_and_no_legacy_controls(window):
    panel = window.vibrational_panel
    assert not hasattr(panel, 'mode') and not hasattr(panel, 'intensities')
    assert panel.findChild(QComboBox, 'vibrational.mode') is None
    assert all(control.text() != 'INTENSITIES' for control in panel.findChildren(QCheckBox))
    assert not panel.ir_enabled.isChecked() and not panel.raman_enabled.isChecked()
    assert panel.frequencies_label.text().startswith('✓')
    assert COLORS['success'] in panel.frequencies_label.styleSheet()
    assert not panel.raman_card.isHidden()
    for path in ['vibrational.linres_eps', 'vibrational.linres_max_iter']:
        assert not panel.fields[path][0].isEnabled()


@pytest.mark.parametrize('ir,raman', [(False,False),(True,False),(False,True),(True,True)])
def test_all_checkbox_combinations_sync_live_preview_export_and_raman_editability(window, app, tmp_path, ir, raman):
    for periodic in ['NONE', 'XYZ']:
        panel = prepare(window, periodic)
        before_fully_periodic = window.project.vibrational.fully_periodic
        panel.ir_enabled.setChecked(ir)
        panel.raman_enabled.setChecked(raman)
        QTest.qWait(280)  # Exercise the actual UI debounce, not a manual refresh.
        assert window.project.vibrational.ir_enabled is ir
        assert window.project.vibrational.raman_enabled is raman
        assert window.project.vibrational.fully_periodic is before_fully_periodic
        assert panel.fields['vibrational.linres_eps'][0].isEnabled() is raman
        assert panel.fields['vibrational.linres_max_iter'][0].isEnabled() is raman
        assert not panel.raman_card.isHidden()
        text = window.preview.toPlainText()
        assert text == generate_input(window.project, catalog=window.kind_panel.catalog)
        assert ('&MOMENTS ON' in text) is ir and ('&POLAR TRUE' in text) is raman
        assert ('INTENSITIES TRUE' in text) is (ir or raman)
        assert text.count('&VIBRATIONAL_ANALYSIS\n') == 1
        single = tmp_path / (periodic + '.inp')
        export_input(window.project, single)
        assert single.read_text() == text


def test_raman_input_keeps_values_when_disabled_ir_does_not_control_it(window, app):
    panel = prepare(window)
    eps = panel.fields['vibrational.linres_eps'][0]
    maximum = panel.fields['vibrational.linres_max_iter'][0]
    panel.raman_enabled.setChecked(True)
    assert eps.isEnabled() and maximum.isEnabled()
    eps.setText('2.345e-10')
    maximum.setText('432')
    window.refresh()
    panel.raman_enabled.setChecked(False)
    assert not eps.isEnabled() and not maximum.isEnabled()
    panel.ir_enabled.setChecked(True)
    assert not eps.isEnabled() and not maximum.isEnabled()
    window.refresh()
    assert eps.text() == '2.345e-10' and maximum.text() == '432'
    assert window.project.vibrational.linres_eps == 2.345e-10
    panel.raman_enabled.setChecked(True)
    assert eps.isEnabled() and maximum.isEnabled()
    assert eps.text() == '2.345e-10' and maximum.text() == '432'
    window.refresh()
    assert '&MOMENTS ON' in window.preview.toPlainText() and '&POLAR TRUE' in window.preview.toPlainText()
    panel.ir_enabled.setChecked(False)
    assert eps.isEnabled() and maximum.isEnabled()


@pytest.mark.parametrize('periodic', ['NONE', 'XYZ'])
def test_combined_locale_check_camera_and_project_state_stay_stable(window, app, periodic):
    panel = prepare(window, periodic)
    panel.fields['vibrational.linres_eps'][0].setText('1e-8')
    panel.ir_enabled.setChecked(True)
    panel.raman_enabled.setChecked(True)
    window.refresh()
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[5].state == window._step_states[7].state == 'ready'
    view = window.structure_panel.view
    view.zoom = 1.7
    view.pan_offset = np.array([.2,.1,.3])
    view.set_labels_visible(True)
    rotation = view.rotation.copy()
    snapshot = window.project.model_dump_json(), window.preview.toPlainText(), window._revision, window.dirty
    for language in ['en_US', 'zh_CN', 'en_US']:
        language_manager().set_language(language)
        window.resize(1366, 768)
        app.processEvents()
        assert panel.ir_enabled.isChecked() and panel.raman_enabled.isChecked()
        assert panel.ir_enabled.text() == ('IR Intensities' if language == 'en_US' else '红外强度（IR）')
        assert panel.raman_enabled.text() == ('Raman Intensities' if language == 'en_US' else '拉曼强度（Raman）')
        assert panel.always_label.text() == ('Always included' if language == 'en_US' else '始终计算')
        assert panel.frequencies_label.text() == ('✓ Frequencies & Normal Modes' if language == 'en_US' else '✓ 振动频率与简正模式')
        assert window.stack.widget(5).horizontalScrollBar().maximum() == 0
        assert (window.project.model_dump_json(), window.preview.toPlainText(), window._revision, window.dirty) == snapshot
        assert view.zoom == 1.7 and view.show_labels and np.array_equal(view.rotation, rotation)
        assert np.array_equal(view.pan_offset, [.2,.1,.3])
        if periodic == 'XYZ':
            assert 'IR + Raman' in panel.spectra_hint.text()
            assert not panel.periodic_raman_help.isHidden()
            assert ('experimental' if language == 'en_US' else '实验性') in panel.periodic_raman_help.toolTip()
    panel.ir_enabled.setChecked(False)
    assert window._step_states[7].state == 'unchecked'
    window.refresh()
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[7].state == 'ready'


def test_both_switches_and_raman_parameters_restore_through_ui_project_and_preset(window, app, tmp_path, monkeypatch):
    panel = prepare(window)
    panel.ir_enabled.setChecked(True)
    panel.raman_enabled.setChecked(True)
    panel.fields['vibrational.linres_max_iter'][0].setText('333')
    window.refresh()
    preset = window.preset_store.save(capture_preset(window.project, 'Both spectra'))
    path = tmp_path / 'combined.json'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(path), ''))
    assert window.save(force_dialog=True)
    expected = window.preview.toPlainText(), window.project.model_dump_json()
    window.new_project()
    window._open_path(path)
    assert panel.ir_enabled.isChecked() and panel.raman_enabled.isChecked()
    assert panel.fields['vibrational.linres_max_iter'][0].text() == '333'
    assert (window.preview.toPlainText(), window.project.model_dump_json()) == expected
    panel.ir_enabled.setChecked(False)
    panel.raman_enabled.setChecked(False)
    window.refresh()
    monkeypatch.setattr(window, 'confirm_preset_application', lambda *a: True)
    assert window.apply_preset('user:' + preset.id)
    assert panel.ir_enabled.isChecked() and panel.raman_enabled.isChecked()
    assert window.preview.toPlainText() == expected[0]
