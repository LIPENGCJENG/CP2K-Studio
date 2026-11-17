"""The translation adapter delegates to Qt without opting out of native panels."""
from contextlib import contextmanager
import numpy as np
import pytest
from ase import Atoms
from ase.io import write
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog as NativeFileDialog, QApplication
from i18n import qt
from i18n.language_manager import language_manager
from i18n.messages import i18n_msg
from ui.main_window import MainWindow


@pytest.fixture(params=['en_US', 'zh_CN'])
def language(app, request):
    manager = language_manager().attach(app)
    manager.set_language(request.param)
    yield manager
    manager.set_language('zh_CN')


@pytest.mark.parametrize('method', ['getOpenFileName', 'getOpenFileNames', 'getSaveFileName', 'getExistingDirectory'])
def test_all_picker_helpers_preserve_native_defaults_and_translate_arguments(language, method, tmp_path, monkeypatch):
    calls = []
    expected = str(tmp_path) if method == 'getExistingDirectory' else ([str(tmp_path/'结构 (1 1 0).cif')], '') if method == 'getOpenFileNames' else (str(tmp_path/'结构 (1 1 0).cif'), '')
    def native(*args, **kwargs):
        calls.append((args, kwargs))
        return expected
    monkeypatch.setattr(NativeFileDialog, method, native)
    @contextmanager
    def no_retranslation(*args, **kwargs):
        pytest.fail('native file panels must not be inspected or retranslated while open')
        yield
    monkeypatch.setattr(language, 'dialog', no_retranslation)
    title = i18n_msg('Import Structure', code='studio.0336447acd3a1674')
    filters = i18n_msg('Structures (*.cif *.xyz *.extxyz);;All Files (*)', code='studio.cd4a7cca3b34944b')
    parent = object()
    result = getattr(qt.QFileDialog, method)(parent, title, str(tmp_path), **({} if method == 'getExistingDirectory' else {'filter':filters}))
    args, kwargs = calls[0]
    assert result is expected and args == (parent, title.render(), str(tmp_path))
    assert 'options' not in kwargs
    if method != 'getExistingDirectory':
        assert kwargs['filter'] == filters.render()
        assert all(suffix in kwargs['filter'] for suffix in ['*.cif', '*.xyz', '*.extxyz'])
    assert not QApplication.testAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)
    assert language.language in ['en_US', 'zh_CN']


@pytest.mark.parametrize('method', ['getOpenFileName', 'getOpenFileNames', 'getSaveFileName', 'getExistingDirectory'])
def test_explicit_options_are_forwarded_without_adding_non_native_flag(app, method, monkeypatch):
    calls = []
    monkeypatch.setattr(NativeFileDialog, method, lambda *args, **kwargs: calls.append((args, kwargs)))
    options = NativeFileDialog.Option.DontResolveSymlinks
    getattr(qt.QFileDialog, method)(None, 'Pick file', options=options)
    assert calls[0][1]['options'] == options
    assert not calls[0][1]['options'] & NativeFileDialog.Option.DontUseNativeDialog
    # Positional options retain Qt's signature as well; no duplicate keyword.
    args = ('', options) if method == 'getExistingDirectory' else ('', '*', '', options)
    getattr(qt.QFileDialog, method)(None, 'Pick file', *args)
    assert calls[1][0][2:] == args and not calls[1][1]


@pytest.fixture
def window(language, water, tmp_path, app):
    value = MainWindow(preset_directory=tmp_path / 'presets')
    value.load_into_ui(water)
    yield value
    value.timer.stop()
    value.dirty = False
    value.close()
    app.processEvents()


@pytest.mark.parametrize('suffix', ['cif', 'xyz', 'extxyz'])
def test_structure_import_with_spaces_parentheses_and_cancel(window, language, suffix, tmp_path, monkeypatch):
    atoms = Atoms('TiO2', positions=[(0,0,0),(1.125,2,3),(2,1,3)], cell=[4.6,4.6,7.1], pbc=True)
    path = tmp_path / f'TiO2_rutile (1 1 0).{suffix}'
    write(path, atoms, format=suffix)
    # An old structure's fixed IDs must not leak into the imported structure.
    window.structure_panel.select_atom_ids([1])
    window.structure_panel.fix_button.click()
    before = window.project.model_dump_json()
    revision, dirty = window._revision, window.dirty
    preview = window.preview.toPlainText()
    monkeypatch.setattr(NativeFileDialog, 'getOpenFileName', lambda *args, **kwargs: ('', ''))
    window.import_structure()
    assert window.project.model_dump_json() == before
    assert (window._revision, window.dirty) == (revision, dirty)
    assert window.preview.toPlainText() == preview
    selected = []
    def choose(*args, **kwargs):
        selected.append(args)
        return str(path), ''
    monkeypatch.setattr(NativeFileDialog, 'getOpenFileName', choose)
    current_language = language.language
    dft = window.project.dft.model_dump()
    window.import_structure()
    structure = window.project.structure
    assert structure.source == str(path.resolve())
    assert structure.symbols == ['Ti','O','O']
    assert np.allclose(structure.positions, atoms.positions, rtol=0, atol=1e-10)
    if suffix != 'xyz':
        assert np.allclose(structure.cell, atoms.cell)
        assert structure.periodic == 'XYZ'
    assert not structure.fixed_atoms
    assert not window.structure_panel.selected_atom_ids()
    assert not window.structure_panel.view.fixed_atom_ids
    assert window.structure_panel.view.structure is structure
    assert window.structure_panel.coords.rowCount() == 3
    assert window.project.dft.model_dump() == dft
    assert language.language == current_language
    assert all(ext in selected[0][3] for ext in ['*.cif','*.xyz','*.extxyz'])
    # Ti has not been configured: preview must report it rather than invent data.
    assert window.preview.toPlainText() != preview
    assert window.dirty


def test_import_failure_keeps_existing_structure_and_reports_error(window, language, tmp_path, monkeypatch):
    path = tmp_path / 'invalid (structure).cif'
    path.write_text('not a CIF file', encoding='utf-8')
    monkeypatch.setattr(NativeFileDialog, 'getOpenFileName', lambda *args, **kwargs: (str(path), ''))
    errors = []
    monkeypatch.setattr(window, '_error', lambda title, details: errors.append((title.render(), str(details))))
    before = window.project.model_dump_json()
    window.import_structure()
    assert errors and errors[0][0] == ('Structure Import Failed' if language.language=='en_US' else '结构导入失败')
    assert window.project.model_dump_json() == before
