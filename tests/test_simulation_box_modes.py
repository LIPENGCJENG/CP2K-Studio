"""Three box modes share centering, persistent settings and atomic commit."""
import numpy as np
import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QDialogButtonBox
from core.models import Structure, BoxGenerationSettings
from core.structure import generate_simulation_box, load_structure
from core.validator import validate_project
from core.generator import generate_input, GenerationError
from core.project_io import save_project, load_project, export_bundle
from i18n.language_manager import language_manager
from ui.simulation_box_dialog import SimulationBoxDialog
from tests.test_xsd_ui import window, import_file, FIXTURES
from tests.simulation_box_helpers import mock_box_dialog
from tests.test_layout_workflow import wait_for_worker


@pytest.fixture
def molecule():
    st = load_structure(FIXTURES / 'h2o_ms23.xsd')
    st.positions = [(-2.1234567890123, -1., -3.), (2.8765432109877, 1., -3.), (0., 0., -2.)]
    return st


@pytest.mark.parametrize('mode,expected', [('VACUUM_PADDING',(25.,22.,21.)), ('CUBIC',(25.,25.,25.)), ('MANUAL',(12.,14.,16.))])
def test_modes_use_cartesian_bounds_and_center_without_distortion(molecule, mode, expected):
    settings = BoxGenerationSettings(mode=mode, manual_lengths=(12,14,16))
    snapshot = molecule.model_dump_json()
    points = np.array(molecule.positions)
    result = generate_simulation_box(molecule, settings)
    assert molecule.model_dump_json() == snapshot
    np.testing.assert_allclose(result.cell, np.diag(expected), rtol=0, atol=1e-13)
    actual = np.array(result.positions)
    np.testing.assert_allclose((actual.min(axis=0)+actual.max(axis=0))/2, np.array(expected)/2, atol=1e-13)
    np.testing.assert_allclose(actual-actual[0], points-points[0], atol=1e-13)
    assert result.periodic == 'NONE' and result.periodicity_locked
    assert result.symbols == molecule.symbols and result.atom_ids == molecule.atom_ids
    if mode == 'CUBIC':
        assert result.cell[0][0] == result.cell[1][1] == result.cell[2][2]
        assert np.all(actual.min(axis=0) >= 10 - 1e-13)
        assert np.all(np.array(expected)-actual.max(axis=0) >= 10 - 1e-13)


def test_alternating_modes_never_add_old_vacuum_or_change_constraints(molecule):
    from core.atom_constraints import set_fixed_atoms
    set_fixed_atoms(molecule, [2], 'XZ')
    molecule.kind_labels = ['O1','H1','H2']
    original = molecule.model_copy(deep=True)
    st = molecule
    for mode, margin, lengths in [('VACUUM_PADDING',10,None), ('CUBIC',15,None),
                                  ('MANUAL',10,(25,25,25)), ('VACUUM_PADDING',8,None),
                                  ('CUBIC',10,None), ('CUBIC',10,None)]:
        settings = st.box_generation.model_dump()
        settings.update(mode=mode, vacuum_margin=margin, cubic_margin=margin, manual_lengths=lengths)
        st = generate_simulation_box(st, BoxGenerationSettings.model_validate(settings))
        np.testing.assert_allclose(np.array(st.positions)-st.positions[0],
                                   np.array(original.positions)-original.positions[0], atol=1e-13)
        expected = (np.array([5,2,1])+2*margin if mode == 'VACUUM_PADDING' else
                    np.full(3,5+2*margin) if mode == 'CUBIC' else lengths)
        np.testing.assert_allclose(st.cell, np.diag(expected), atol=1e-13)
        assert st.fixed_atoms == original.fixed_atoms and st.labels == original.labels


@pytest.mark.parametrize('lengths,axis', [((4,10,10),'X'), ((10,1,10),'Y'), ((10,10,.5),'Z')])
def test_manual_too_small_identifies_direction_and_leaves_source_unchanged(molecule, lengths, axis):
    before = molecule.model_dump_json()
    with pytest.raises(ValueError, match=axis):
        generate_simulation_box(molecule, BoxGenerationSettings(mode='MANUAL', manual_lengths=lengths))
    assert molecule.model_dump_json() == before


def test_legacy_margin_is_migrated_without_altering_existing_structure(molecule):
    data = molecule.model_dump()
    data.pop('box_generation')
    data['box_vacuum_margin'] = 15
    restored = Structure.model_validate(data)
    assert restored.box_generation.mode == 'VACUUM_PADDING'
    assert restored.box_generation.vacuum_margin == 15 and restored.box_generation.cubic_margin == 10
    assert restored.cell == molecule.cell and restored.positions == molecule.positions


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
def test_one_dialog_switches_compact_pages_and_translates_without_changing_values(app, molecule, language):
    language_manager().set_language(language)
    dialog = SimulationBoxDialog(molecule)
    try:
        dialog.show()
        app.processEvents()
        assert [dialog.mode.itemData(i) for i in range(3)] == ['VACUUM_PADDING','CUBIC','MANUAL']
        assert dialog.padding.value() == dialog.cubic_padding.value() == 10
        assert dialog.padding.decimals() == 3
        padding_height = dialog.height()
        dialog.padding.setValue(12)
        dialog.mode.setCurrentIndex(1)
        dialog.cubic_padding.setValue(15)
        assert not dialog.pages[0].isVisible() and dialog.pages[1].isVisible()
        dialog.mode.setCurrentIndex(2)
        app.processEvents()
        assert dialog.height() > padding_height
        assert dialog.pages[2].isVisible() and not dialog.pages[1].isVisible()
        # No cell: proposed lengths follow the current molecular span + padding.
        assert [spin.value() for spin in dialog.lengths] == [25,22,21]
        for spin in dialog.lengths: spin.setValue(30)
        before = molecule.model_dump_json()
        language_manager().set_language('zh_CN' if language == 'en_US' else 'en_US')
        app.processEvents()
        assert dialog.mode.currentData() == 'MANUAL'
        assert dialog.padding.value() == 12 and dialog.cubic_padding.value() == 15
        assert [spin.value() for spin in dialog.lengths] == [30,30,30]
        assert molecule.model_dump_json() == before
        language_manager().set_language(language)
        dialog.mode.setCurrentIndex(0)
        app.processEvents()
        assert dialog.height() == padding_height
        dialog.reject()
        assert dialog.generated_structure is None
    finally:
        dialog.close()
        app.processEvents()
        language_manager().set_language('zh_CN')


def test_manual_initial_lengths_read_current_cell_and_reject_invalid_box_inline(app, molecule):
    molecule.cell = ((26,0,0),(0,27,0),(0,0,28))
    dialog = SimulationBoxDialog(molecule)
    dialog.show()
    dialog.mode.setCurrentIndex(2)
    assert [spin.value() for spin in dialog.lengths] == [26,27,28]
    dialog.lengths[0].setValue(1)
    dialog.accept()
    assert dialog.isVisible() and dialog.generated_structure is None
    assert 'X' in dialog.error.text()
    dialog.lengths[0].setValue(26)
    dialog.accept()
    assert dialog.generated_structure.cell == molecule.cell
    app.processEvents()


def test_each_mode_parameters_persist_on_success_and_cancel_is_atomic(window, app, monkeypatch, tmp_path):
    import_file(window, monkeypatch, 'h2o_ms23.xsd')
    panel = window.structure_panel
    for mode, margin, lengths in [('VACUUM_PADDING',12,None), ('CUBIC',15,None), ('MANUAL',None,(25,26,27))]:
        mock_box_dialog(monkeypatch, mode=mode, margin=margin, lengths=lengths)
        panel.box_button.click()
        assert window.project.structure.box_generation.mode == mode and panel.box_button.isVisible()
    settings = window.project.structure.box_generation
    assert (settings.vacuum_margin, settings.cubic_margin, settings.manual_lengths) == (12,15,(25,26,27))
    window.dirty = False
    path = tmp_path / 'three-modes.json'
    save_project(window.project, path)
    window.new_project()
    window._open_path(path)
    assert window.project.structure.box_generation == settings
    assert window.project.structure.cell == ((25,0,0),(0,26,0),(0,0,27))
    snapshot = window.project.model_dump_json(), window._revision, window.dirty
    def inspect(dialog):
        assert dialog.mode.currentData() == 'MANUAL'
        assert dialog.padding.value() == 12 and dialog.cubic_padding.value() == 15
        assert [spin.value() for spin in dialog.lengths] == [25,26,27]
    mock_box_dialog(monkeypatch, mode='CUBIC', margin=40, accepted=False, on_open=inspect)
    panel.box_button.click()
    assert (window.project.model_dump_json(), window._revision, window.dirty) == snapshot


def test_wavelet_nonperiodic_requires_cubic_but_mt_allows_rectangular(water):
    water.structure.periodic = 'NONE'
    water.structure.cell = ((20,0,0),(0,21,0),(0,0,22))
    water.dft.poisson_solver = 'WAVELET'
    snapshot = water.model_dump_json()
    result = validate_project(water)
    assert any(getattr(error,'code','') == 'box.wavelet_cubic' for error in result.errors)
    assert water.model_dump_json() == snapshot
    with pytest.raises(GenerationError): generate_input(water)
    water.dft.poisson_solver = 'MT'
    assert validate_project(water).ok
    assert any(getattr(info,'code','') == 'poisson.mt_info' for info in validate_project(water).infos)
    assert not validate_project(water).warnings
    water.dft.poisson_solver = 'WAVELET'
    water.structure.cell = ((21,0,0),(0,21,0),(0,0,21))
    assert validate_project(water).ok
    assert any('FFTSG' in str(warning) for warning in validate_project(water).warnings)
    water.structure.cell = ((21,0,0),(1,21,0),(0,0,21))
    assert not validate_project(water).ok  # Equal diagonals do not make a skew cell cubic.


@pytest.mark.parametrize('run_type', ['ENERGY','GEO_OPT','VIBRATIONAL_ANALYSIS'])
def test_real_modal_cubic_generation_updates_view_check_and_exports(window, app, monkeypatch, tmp_path, run_type):
    import_file(window, monkeypatch, 'h2o_ms23.xsd')
    tasks = window.global_panel.fields['global_settings.run_type'][0]
    tasks.setCurrentIndex(tasks.findData(run_type))
    solver = window.dft_panel.fields['dft.poisson_solver'][0]
    solver.setCurrentIndex(solver.findData('WAVELET'))
    window.refresh()
    panel = window.structure_panel
    panel.select_atom_ids([2])
    panel.components.setCurrentText('Z')
    panel.fix_button.click()
    before_dft = window.project.dft.model_dump()
    errors = []
    def choose():
        dialog = app.activeModalWidget()
        try:
            assert isinstance(dialog, SimulationBoxDialog)
            dialog.mode.setCurrentIndex(1)
            dialog.cubic_padding.setValue(10)
            dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).click()
        except Exception as exc:
            errors.append(exc)
            dialog.reject()
    QTimer.singleShot(0, choose)
    panel.box_button.click()
    assert not errors, errors
    st = window.project.structure
    assert st.cell[0][0] == st.cell[1][1] == st.cell[2][2]
    assert st.periodic == 'NONE' and st.box_generation.mode == 'CUBIC'
    assert window.project.dft.model_dump() == before_dft
    assert panel.view.structure is st and panel.view.selected_atom_ids == {2} and panel.view.fixed_atom_ids == {2}
    assert window.preview.toPlainText() == generate_input(window.project)
    assert window._step_states[7].state == 'unchecked'
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._comprehensive_result is not None
    assert not window._comprehensive_result.validation.errors
    bundle = export_bundle(window.project, tmp_path / run_type).parent
    restored = load_project(bundle / 'project.cp2kstudio.json')
    assert restored.structure.cell == st.cell and restored.structure.box_generation == st.box_generation
    text = (bundle / 'input.inp').read_text()
    assert 'PREFERRED_FFT_LIBRARY FFTSG' in text and 'PERIODIC NONE' in text
