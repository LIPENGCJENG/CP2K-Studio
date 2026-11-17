"""XSD uses the shared native import entry, model, view and project lifecycle."""
from pathlib import Path
import shutil
import numpy as np
import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog as NativeFileDialog
from ui.simulation_box_dialog import SimulationBoxDialog
from i18n.messages import i18n_str
from i18n.language_manager import language_manager
from tests.simulation_box_helpers import mock_box_dialog
from ui.main_window import MainWindow
from core.generator import generate_input
from tests.test_layout_workflow import wait_for_worker

FIXTURES = Path(__file__).parent / 'fixtures' / 'xsd'


@pytest.fixture
def window(app, water, tmp_path):
    value = MainWindow(preset_directory=tmp_path / 'presets')
    value.load_into_ui(water)
    value.show()
    app.processEvents()
    yield value
    wait_for_worker(app, value)
    value.dirty = False
    value.close()
    app.processEvents()
    language_manager().set_language('zh_CN')


def import_file(window, monkeypatch, filename):
    path = FIXTURES / filename
    monkeypatch.setattr(NativeFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    window.import_structure()
    return path


@pytest.mark.parametrize('filename,count,periodic', [('rutile_ms23.xsd', 6, 'XYZ'),
    ('slab_ms23.xsd', 22, 'XYZ'), ('h2o_ms23.xsd', 3, 'NONE')])
def test_real_files_update_shared_view_tables_kinds_and_reset_old_constraints(window, monkeypatch, filename, count, periodic):
    w = window
    w.structure_panel.select_atom_ids([1])
    w.structure_panel.fix_button.click()
    dft, global_settings = w.project.dft.model_dump(), w.project.global_settings.model_dump()
    path = import_file(w, monkeypatch, filename)
    st = w.project.structure
    assert len(st.symbols) == count and st.periodic == periodic
    assert st.source == str(path.resolve())
    assert w.structure_panel.coords.rowCount() == count
    table = w.kind_panel.table
    assert {table.item(row, 0).text() for row in range(table.rowCount())} == set(st.kind_elements)
    assert w.nav.currentRow() == 0 and w.dirty
    assert not st.fixed_atoms and not w.structure_panel.selected_atom_ids()
    assert w.structure_panel.view.structure is st
    assert not w.structure_panel.view.fixed_atom_ids and not w.structure_panel.view.selected_atom_ids
    for i in range(3):
        for j in range(3):
            assert float(w.structure_panel.cell.item(i, j).text()) == st.cell[i][j]
    assert w.project.dft.model_dump() == dft
    assert w.project.global_settings.model_dump() == global_settings
    assert w.structure_panel.import_notice.isVisible()
    if filename == 'rutile_ms23.xsd':
        assert '6' in w.structure_panel.import_notice.text()
    if periodic == 'NONE':
        assert w.structure_panel.box_button.isVisible()
        assert 'CELL' in w.report.toPlainText()
    else:
        assert not w.structure_panel.box_button.isVisible()
        assert '确认周期性' in w.structure_panel.import_notice.text()


def test_slab_periodicity_can_be_confirmed_manually_without_altering_geometry_or_solver(window, monkeypatch):
    import_file(window, monkeypatch, 'slab_ms23.xsd')
    st = window.project.structure
    points, cell = st.positions, st.cell
    solver = window.project.dft.poisson_solver
    window.structure_panel.periodic.setCurrentText('XY')
    window.refresh()
    assert window.project.structure.periodic == 'XY'
    assert window.project.structure.positions == points and window.project.structure.cell == cell
    assert window.project.dft.poisson_solver == solver == 'PERIODIC'
    assert any('POISSON' in str(error) for error in window._validation.errors)
    assert 'XY' in window.structure_panel.import_notice.text()
    window.structure_panel.periodic.setCurrentText('NONE')
    window.refresh()
    assert '确认周期性' in window.structure_panel.import_notice.text()
    assert '非周期分子' not in window.structure_panel.import_notice.text()


def test_explicit_box_cancel_and_accept_preserve_constraints_and_require_manual_poisson(window, monkeypatch):
    import_file(window, monkeypatch, 'h2o_ms23.xsd')
    panel = window.structure_panel
    panel.select_atom_ids([2])
    panel.components.setCurrentText('Z')
    panel.fix_button.click()
    before = window.project.model_dump_json(), window._revision, window.dirty
    mock_box_dialog(monkeypatch, margin=4, accepted=False)
    panel.box_button.click()
    assert (window.project.model_dump_json(), window._revision, window.dirty) == before
    coordinates = np.array(window.project.structure.positions)
    mock_box_dialog(monkeypatch, margin=4)
    panel.box_button.click()
    boxed = window.project.structure
    assert boxed.periodic == 'NONE' and boxed.fixed_atoms[0].components == 'Z'
    assert boxed.fixed_atoms[0].atom_id == 2 and panel.selected_atom_ids() == {2}
    assert np.allclose(np.array(boxed.positions).min(axis=0), 4)
    assert np.allclose(np.array(boxed.positions) - coordinates, np.array(boxed.positions)[0] - coordinates[0])
    assert panel.box_button.isVisible()
    assert boxed.box_vacuum_margin == 4.0
    assert window.project.dft.poisson_solver == 'PERIODIC'  # Never silently adjust physics.
    assert window._revision > before[1] and window._step_states[7].state == 'unchecked'
    assert panel.view.fixed_atom_ids == {2} and panel.view.selected_atom_ids == {2}


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_native_file_filter_entry_and_numeric_dialog_captions_are_translated(window, app, monkeypatch, language):
    manager = language_manager()
    manager.set_language(language)
    button = window.structure_panel.import_button
    arguments = []
    def choose(*args, **kwargs):
        arguments.append((args, kwargs))
        return str(FIXTURES / 'h2o_ms23.xsd'), ''
    monkeypatch.setattr(NativeFileDialog, 'getOpenFileName', choose)
    button.click()
    args, kwargs = arguments[0]
    assert len(args[3].split(';;')) == 6
    assert all(pattern in args[3] for pattern in ['*.xsd', '*.XSD', '*.cif', '*.xyz', '*.extxyz'])
    assert not kwargs.get('options', NativeFileDialog.Option(0)) & NativeFileDialog.Option.DontUseNativeDialog
    assert not app.testAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)
    received = []
    def inspect(dialog):
        received.append(dialog.windowTitle())
        assert dialog.padding.value() == 10
        assert dialog.mode.count() == 3
    mock_box_dialog(monkeypatch, accepted=False, on_open=inspect)
    window.structure_panel.box_button.click()
    assert received == [('Generate Simulation Box' if language == 'en_US' else '生成计算盒')]
    assert manager.language == language


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_real_box_dialog_accepts_padding_and_applies_only_on_confirmation(window, app, monkeypatch, language):
    language_manager().set_language(language)
    import_file(window, monkeypatch, 'h2o_ms23.xsd')
    errors, seen = [], []
    def accept_dialog():
        dialog = app.activeModalWidget()
        try:
            assert isinstance(dialog, SimulationBoxDialog)
            assert dialog.windowTitle() == ('Generate Simulation Box' if language == 'en_US' else '生成计算盒')
            spin = dialog.padding
            assert spin.value() == 10.0
            assert spin.decimals() == 3
            assert spin.minimum() == 0.01 and spin.maximum() == 1000.0
            spin.setValue(2.25)
            seen.append(spin.value())
            dialog.accept()
        except Exception as exc:
            errors.append(exc)
            if dialog:
                dialog.reject()
    QTimer.singleShot(0, accept_dialog)
    window.structure_panel.box_button.click()
    assert not errors, errors
    assert seen == [2.25]
    assert np.allclose(np.min(window.project.structure.positions, axis=0), 2.25)


@pytest.mark.parametrize('bad_content', ['<XSD', '<XSD><AtomisticTreeRoot/></XSD>'])
def test_import_failure_and_cancel_keep_entire_existing_project_selection_and_view(window, monkeypatch, tmp_path, bad_content):
    window.structure_panel.select_atom_ids([1, 3])
    window.structure_panel.fix_button.click()
    path = tmp_path / '损坏文件 (1).XSD'
    path.write_text(bad_content)
    original = window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()
    view = window.structure_panel.view
    previous = view.structure
    errors = []
    monkeypatch.setattr(window, '_error', lambda title, detail: errors.append((title, i18n_str(detail))))
    monkeypatch.setattr(NativeFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    window.import_structure()
    assert errors
    assert (window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()) == original
    assert view.structure is previous and view.selected_atom_ids == {1, 3} and view.fixed_atom_ids == {1, 3}
    monkeypatch.setattr(NativeFileDialog, 'getOpenFileName', lambda *a, **k: ('', ''))
    window.import_structure()
    assert (window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()) == original


def test_language_switch_save_reopen_and_input_preserve_xsd_coordinates(window, app, monkeypatch, tmp_path):
    path = tmp_path / '中文 H2O (分子).XsD'
    shutil.copyfile(FIXTURES / 'h2o_ms23.xsd', path)
    monkeypatch.setattr(NativeFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    window.import_structure()
    mock_box_dialog(monkeypatch, margin=5, mode='CUBIC')
    window.structure_panel.box_button.click()
    solver = window.dft_panel.fields['dft.poisson_solver'][0]
    solver.setCurrentIndex(solver.findData('WAVELET'))
    window.refresh()
    window.check_current_configuration()
    wait_for_worker(app, window)
    snapshot = window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText().encode()
    for language in ['en_US', 'zh_CN', 'en_US']:
        window.language_selector.setCurrentIndex(window.language_selector.findData(language))
        app.processEvents()
        assert (window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText().encode()) == snapshot
        assert ('Non-periodic Molecule' if language == 'en_US' else '非周期分子') in window.structure_panel.import_notice.text()
    saved = tmp_path / 'saved.json'
    monkeypatch.setattr(NativeFileDialog, 'getSaveFileName', lambda *a, **k: (str(saved), ''))
    assert window.save(force_dialog=True)
    original = window.project.model_dump_json(), generate_input(window.project)
    path.unlink()  # Reopening a project must not require the original XSD.
    window.new_project()
    window._open_path(saved)
    assert (window.project.model_dump_json(), generate_input(window.project)) == original
    assert window.structure_panel.view.structure is window.project.structure
