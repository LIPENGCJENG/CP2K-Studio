"""Periodic context, live hints and saved models remain independent of locale."""
from tests.vibrational_helpers import set_model_spectra, set_ui_spectra
import numpy as np
import pytest

from core.generator import generate_input
from i18n.language_manager import language_manager
from tests.test_layout_workflow import wait_for_worker
from tests.test_vibrational_ui import window  # Existing safe MainWindow fixture.


def choose_mode(window, mode):
    panel = window.vibrational_panel
    set_ui_spectra(panel, mode)
    window.refresh()
    return panel


@pytest.mark.parametrize('mode', ['IR', 'RAMAN'])
def test_periodic_hint_updates_on_import_cell_edits_and_mode_switch(window, app, mode):
    w = window
    panel = choose_mode(w, mode)
    assert panel.spectra_hint_row.isHidden()
    w.structure_panel.periodic.setCurrentText('XYZ')
    solver = w.dft_panel.fields['dft.poisson_solver'][0]
    solver.setCurrentIndex(solver.findData('PERIODIC'))
    w.refresh()
    assert panel.periodicity == 'XYZ' and not panel.spectra_hint_row.isHidden()
    assert not panel.fields['vibrational.fully_periodic'][0].isChecked()
    assert not w.project.vibrational.fully_periodic
    assert panel.periodic_raman_help.isHidden() is (mode != 'RAMAN')
    assert 'Berry-phase' in panel.spectra_hint.text()
    assert w.preview.toPlainText() == generate_input(w.project, catalog=w.kind_panel.catalog)
    choose_mode(w, 'FREQUENCIES')
    assert panel.spectra_hint_row.isHidden() and not w.project.vibrational.intensities
    assert '&MOMENTS' not in w.preview.toPlainText() and '&POLAR TRUE' not in w.preview.toPlainText()
    choose_mode(w, mode)
    assert not panel.spectra_hint_row.isHidden()
    w.structure_panel.periodic.setCurrentText('NONE')
    solver.setCurrentIndex(solver.findData('MT'))
    w.refresh()
    assert panel.spectra_hint_row.isHidden()
    token = 'PERIODIC FALSE' if mode == 'IR' else 'PERIODIC_DIPOLE_OPERATOR FALSE'
    assert token in w.preview.toPlainText()


@pytest.mark.parametrize('mode', ['IR', 'RAMAN'])
def test_periodic_load_locale_and_comprehensive_check_preserve_state(window, app, mode):
    w = window
    p = w.project.model_copy(deep=True)
    p.vibrational.linres_eps = 1e-8  # This test expects no precision warning.
    p.structure.periodic = 'XYZ'
    p.dft.poisson_solver = 'PERIODIC'
    set_model_spectra(p.vibrational, mode)
    p.vibrational.fully_periodic = True
    w.load_into_ui(p)
    w.check_current_configuration()
    wait_for_worker(app, w)
    assert w._step_states[5].state == w._step_states[7].state == 'ready'
    assert not w._comprehensive_result.validation.warnings
    assert not w.vibrational_panel.spectra_hint_row.isHidden()
    view = w.structure_panel.view
    view.set_labels_visible(True)
    view.zoom = 1.5
    view.pan_offset = np.array([.1, .2, .3])
    rotation = view.rotation.copy()
    before = w.project.model_dump_json(), w._revision, w.dirty, w.preview.toPlainText()
    for language in ['en_US', 'zh_CN', 'en_US']:
        language_manager().set_language(language)
        app.processEvents()
        assert (w.project.model_dump_json(), w._revision, w.dirty, w.preview.toPlainText()) == before
        hint = w.vibrational_panel.spectra_hint.text()
        assert hint.startswith(('Periodic ' if language == 'en_US' else '周期 ') + ('Raman' if mode == 'RAMAN' else 'IR'))
        help_text = w.vibrational_panel.fully_periodic_help.toolTip()
        assert ('Hessian' in help_text and ('rotational' if language == 'en_US' else '转动') in help_text)
        if mode == 'RAMAN':
            text = w.vibrational_panel.periodic_raman_help.toolTip()
            assert ('experimental' if language == 'en_US' else '实验性') in text
        assert view.show_labels and view.zoom == 1.5
        assert np.array_equal(view.rotation, rotation) and np.array_equal(view.pan_offset, [.1,.2,.3])
        assert w._step_states[7].state == 'ready'
