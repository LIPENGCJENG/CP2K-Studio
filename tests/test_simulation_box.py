"""Repeatable box regeneration and the last successful, persisted margin."""
from pathlib import Path
import numpy as np
import pytest
from pydantic import ValidationError
from PySide6.QtWidgets import QFileDialog
from core.models import Structure, FixedAtom
from core.structure import load_structure, generate_nonperiodic_box
from core.generator import generate_input
from core.project_io import save_project
from i18n.language_manager import language_manager
from tests.simulation_box_helpers import mock_box_dialog
from tests.test_xsd_ui import window, import_file
from tests.test_layout_workflow import wait_for_worker

FIXTURES = Path(__file__).parent / 'fixtures' / 'xsd'


def test_repeated_generation_uses_atom_extent_and_preserves_identity_and_precision():
    original = load_structure(FIXTURES / 'h2o_ms23.xsd')
    original.fixed_atoms = [FixedAtom(atom_id=2, components='Z')]
    original.kind_labels = ['O1', 'H1', 'H2']
    snapshot = original.model_dump_json()
    reference = np.array(original.positions)
    structure = original
    generated = {}
    for margin in [10.0, 15.0, 8.0, 8.0, 10.0]:
        # A manually enlarged cell must never add vacuum to the next box.
        if structure is not original:
            structure.cell = ((101, 0, 0), (0, 102, 0), (0, 0, 103))
        structure = generate_nonperiodic_box(structure, margin)
        points = np.array(structure.positions)
        assert structure.box_vacuum_margin == margin
        assert structure.periodic == 'NONE' and structure.periodicity_locked
        assert structure.symbols == original.symbols and structure.atom_ids == original.atom_ids
        assert structure.kind_labels == original.kind_labels and structure.fixed_atoms == original.fixed_atoms
        np.testing.assert_allclose(structure.cell, np.diag(np.ptp(reference, axis=0) + 2 * margin), rtol=0, atol=1e-13)
        np.testing.assert_allclose(points, reference - reference.min(axis=0) + margin, rtol=0, atol=1e-13)
        np.testing.assert_allclose(points - points[0], reference - reference[0], rtol=0, atol=1e-13)
        if margin in generated:
            np.testing.assert_allclose(points, generated[margin], rtol=0, atol=1e-13)
        generated[margin] = points
    assert original.model_dump_json() == snapshot


def test_regeneration_uses_current_edited_coordinates():
    structure = generate_nonperiodic_box(load_structure(FIXTURES / 'h2o_ms23.xsd'), 10)
    structure.positions[1] = tuple(np.array(structure.positions[1]) + [1.1234567890123, -.1234567890123, 0])
    current = np.array(structure.positions)
    regenerated = generate_nonperiodic_box(structure, 15)
    np.testing.assert_allclose(regenerated.cell, np.diag(np.ptp(current, axis=0) + 30), rtol=0, atol=1e-13)
    np.testing.assert_allclose(regenerated.positions, current - current.min(axis=0) + 15, rtol=0, atol=1e-13)


@pytest.mark.parametrize('margin', [0, -1, float('nan'), float('inf')])
def test_invalid_persisted_margin_is_rejected(margin):
    with pytest.raises(ValidationError):
        Structure(box_vacuum_margin=margin)


def test_legacy_structure_defaults_to_ten_without_changing_cell_or_coordinates():
    legacy = load_structure(FIXTURES / 'h2o_ms23.xsd').model_dump()
    legacy.pop('box_vacuum_margin')
    restored = Structure.model_validate(legacy)
    assert restored.box_vacuum_margin == 10
    assert restored.cell == tuple(legacy['cell']) and restored.positions == legacy['positions']


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_continuous_button_updates_view_input_validation_and_remembers_margin(window, app, monkeypatch, language):
    language_manager().set_language(language)
    import_file(window, monkeypatch, 'h2o_ms23.xsd')
    panel = window.structure_panel
    solver = window.dft_panel.fields['dft.poisson_solver'][0]
    solver.setCurrentIndex(solver.findData('MT'))
    window.refresh()
    assert any('CELL' in str(error) for error in window._validation.errors)
    panel.select_atom_ids([2])
    panel.components.setCurrentText('Z')
    panel.fix_button.click()
    original = window.project.structure.model_copy(deep=True)
    chemistry = window.project.dft.model_dump(), window.project.global_settings.model_dump(), window.project.run_environment.model_dump()
    previous_margin = 10
    for margin in [10.0, 15.0, 8.0]:
        calls = []
        def inspect(dialog):
            calls.append((dialog.padding.value(), dialog.padding.minimum(),
                          dialog.padding.maximum(), dialog.padding.decimals()))
        mock_box_dialog(monkeypatch, margin=margin, on_open=inspect)
        revision = window._revision
        panel.box_button.click()
        assert calls[0] == (previous_margin, 0.01, 1000.0, 3)
        boxed = window.project.structure
        assert panel.box_button.isVisible() and boxed.box_vacuum_margin == margin
        assert boxed.periodic == 'NONE' and not panel.periodic.isEnabled()
        assert boxed.fixed_atoms == original.fixed_atoms and panel.selected_atom_ids() == {2}
        assert panel.view.structure is boxed and panel.view.fixed_atom_ids == {2}
        assert panel.view.selected_atom_ids == {2}
        np.testing.assert_allclose(boxed.cell, np.diag(np.ptp(original.positions, axis=0) + 2 * margin), rtol=0, atol=1e-13)
        np.testing.assert_allclose(np.array(boxed.positions).min(axis=0), margin, rtol=0, atol=1e-13)
        assert all(float(panel.cell.item(i, j).text()) == boxed.cell[i][j] for i in range(3) for j in range(3))
        assert not window._validation.errors
        assert window.preview.toPlainText() == generate_input(window.project)
        assert window.dirty and window._revision > revision and window._step_states[7].state == 'unchecked'
        assert (window.project.dft.model_dump(), window.project.global_settings.model_dump(), window.project.run_environment.model_dump()) == chemistry
        previous_margin = margin
        if margin == 10:
            window.check_current_configuration()
            wait_for_worker(app, window)
            assert window._comprehensive_result is not None


def test_cancel_preserves_manual_cell_and_last_successful_margin(window, monkeypatch):
    import_file(window, monkeypatch, 'h2o_ms23.xsd')
    panel = window.structure_panel
    mock_box_dialog(monkeypatch, margin=15)
    panel.box_button.click()
    panel.cell.item(0, 0).setText('45.1234567890123')
    window.refresh()
    snapshot = window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()
    cell = panel.cell.item(0, 0).text()
    def cancel(dialog):
        assert dialog.padding.value() == 15
        assert panel.cell.item(0, 0).text() == cell
        assert window.project.structure.cell[0][0] == 45.1234567890123
    mock_box_dialog(monkeypatch, margin=999, accepted=False, on_open=cancel)
    panel.box_button.click()
    assert (window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()) == snapshot
    assert panel.cell.item(0, 0).text() == cell and panel.box_button.isVisible()
    mock_box_dialog(monkeypatch, mode='MANUAL', lengths=(.01,.01,.01))
    panel.box_button.click()  # Rejected generation must not remember its invalid value.
    assert (window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()) == snapshot
    assert panel.st.box_vacuum_margin == 15


def test_project_reopen_and_language_switch_keep_margin_and_input(window, app, monkeypatch, tmp_path):
    import_file(window, monkeypatch, 'h2o_ms23.xsd')
    mock_box_dialog(monkeypatch, margin=8, mode='CUBIC')
    window.structure_panel.box_button.click()
    solver = window.dft_panel.fields['dft.poisson_solver'][0]
    solver.setCurrentIndex(solver.findData('WAVELET'))
    window.refresh()
    snapshot = window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()
    for language in ['en_US', 'zh_CN', 'en_US']:
        language_manager().set_language(language)
        app.processEvents()
        assert (window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()) == snapshot
        assert window.structure_panel.box_button.isVisible()
    path = tmp_path / 'box-project.json'
    save_project(window.project, path)
    window.dirty = False
    window.new_project()
    window._open_path(path)
    assert window.project.model_dump_json() == snapshot[0]
    assert window.preview.toPlainText() == snapshot[3]
    assert window.structure_panel.box_button.isVisible()
    received = []
    def cancel(dialog):
        assert dialog.mode.currentData() == 'CUBIC'
        received.append(dialog.cubic_padding.value())
    mock_box_dialog(monkeypatch, accepted=False, on_open=cancel)
    window.structure_panel.box_button.click()
    assert received == [8]


def test_plain_xyz_has_reusable_button_and_new_import_resets_margin(window, monkeypatch, tmp_path):
    path = tmp_path / 'molecule.xyz'
    path.write_text('3\nordinary XYZ\nO -1.1234567890123 0 0\nH 0 .7 .5\nH 0 -.7 .5\n')
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    window.import_structure()
    panel = window.structure_panel
    assert panel.box_button.isVisible() and window.project.structure.box_vacuum_margin == 10
    mock_box_dialog(monkeypatch, margin=15)
    panel.box_button.click()
    assert panel.box_button.isVisible() and window.project.structure.box_vacuum_margin == 15
    assert window.project.structure.structure_type == 'unclassified' and panel.periodic.isEnabled()
    window.import_structure()
    assert window.project.structure.box_vacuum_margin == 10 and panel.box_button.isVisible()
