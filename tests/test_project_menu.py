"""Project actions keep their handlers and window shortcuts inside a popup."""
import numpy as np
import pytest
from ase import Atoms
from ase.io import write
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest, QSignalSpy
from PySide6.QtWidgets import QFileDialog, QMessageBox
from core.project_io import load_project, save_project
from ui.main_window import MainWindow


def settle(app):
    for _ in range(5):
        app.processEvents()


@pytest.fixture
def window(app, water, tmp_path):
    value = MainWindow(preset_directory=tmp_path / 'presets')
    value.load_into_ui(water)
    value.show()
    value.activateWindow()
    settle(app)
    yield value
    value.project_menu.close()
    value.dirty = False
    value.close()


def choose_menu(window, app, operation):
    errors = []
    action = window.project_actions[operation]
    triggered = QSignalSpy(action.triggered)
    def choose():
        try:
            menu = window.project_menu
            assert menu.isVisible()
            QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())
        except Exception as exc:
            errors.append(exc)
        finally:
            window.project_menu.close()
    QTimer.singleShot(0, choose)
    QTest.mouseClick(window.project_button, Qt.MouseButton.LeftButton)
    settle(app)
    assert not errors
    assert triggered.count() == 1


@pytest.mark.parametrize('part', ['left', 'middle', 'arrow'])
def test_whole_project_button_opens_same_menu_without_changing_project(window, app, part):
    before = window.project.model_dump()
    button = window.project_button
    assert button.popupMode() == window.preset_button.popupMode() == button.ToolButtonPopupMode.InstantPopup
    assert button.height() == window.preset_button.height()
    positions = {'left': QPoint(4, button.height()//2), 'middle': button.rect().center(),
                 'arrow': QPoint(button.width()-8, button.height()//2)}
    visible = []
    def close_menu():
        visible.append(window.project_menu.isVisible())
        window.project_menu.close()
    QTimer.singleShot(0, close_menu)
    QTest.mouseClick(button, Qt.MouseButton.LeftButton, pos=positions[part])
    settle(app)
    assert visible == [True]
    assert window.project.model_dump() == before and not window.dirty


def test_menu_save_new_open_restores_project_panels_preview_and_title(window, app, tmp_path, monkeypatch):
    path = tmp_path / 'menu-project.json'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(path), ''))
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    window.global_panel.fields['global_settings.project_name'][0].setText('menu_project')
    window.dft_panel.fields['dft.cutoff'][0].setText('612.123456')
    window.run_panel.mpi_processes.setValue(8)
    window.run_panel.omp_threads.setValue(2)
    choose_menu(window, app, 'save')
    expected = window.project.model_dump()
    preview = window.preview.toPlainText()
    assert load_project(path).model_dump() == expected
    assert window.project_path == path and not window.dirty and '*' not in window.windowTitle()
    choose_menu(window, app, 'new')
    assert window.project.structure is None and window.project_path is None
    choose_menu(window, app, 'open')
    assert window.project.model_dump() == expected and not window.dirty
    assert window.preview.toPlainText() == preview
    assert window.global_panel.fields['global_settings.project_name'][0].text() == 'menu_project'
    assert window.dft_panel.fields['dft.cutoff'][0].text() == '612.123456'
    assert window.structure_panel.coords.rowCount() == 3
    assert window.run_panel.mpi_processes.value() == 8 and window.run_panel.omp_threads.value() == 2
    assert window.structure_panel.view.structure is window.project.structure
    assert path.name in window.windowTitle() and '*' not in window.windowTitle()


@pytest.mark.parametrize('operation,standard', [('new', QKeySequence.StandardKey.New),
    ('open', QKeySequence.StandardKey.Open), ('save', QKeySequence.StandardKey.Save)])
def test_window_shortcuts_work_before_menu_has_ever_opened(window, app, water, tmp_path, monkeypatch, operation, standard):
    path = tmp_path / 'shortcut.json'
    incoming = water.model_copy(deep=True)
    incoming.global_settings.project_name = 'shortcut_opened'
    save_project(incoming, path)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(path), ''))
    action = window.project_actions[operation]
    assert action.shortcut() == QKeySequence(standard) and action in window.actions()
    spy = QSignalSpy(action.triggered)
    window.activateWindow()
    window.nav.setCurrentRow(1)
    field = window.global_panel.fields['global_settings.project_name'][0]
    field.setFocus()
    settle(app)
    assert not window.project_menu.isVisible()
    QTest.keySequence(field, QKeySequence(standard))
    settle(app)
    assert spy.count() == 1 and not window.project_menu.isVisible()
    if operation == 'new':
        assert window.project.structure is None
    elif operation == 'open':
        assert field.text() == window.project.global_settings.project_name == 'shortcut_opened'
    else:
        assert load_project(path).model_dump() == window.project.model_dump()


@pytest.mark.parametrize('operation', ['new', 'open'])
@pytest.mark.parametrize('answer', [QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Discard,
                                  QMessageBox.StandardButton.Save])
def test_project_actions_keep_original_unsaved_save_discard_cancel(window, water, tmp_path, monkeypatch, operation, answer):
    incoming_path, save_path = tmp_path / 'incoming.json', tmp_path / 'unsaved.json'
    incoming = water.model_copy(deep=True)
    incoming.global_settings.project_name = 'incoming_project'
    save_project(incoming, incoming_path)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(incoming_path), ''))
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(save_path), ''))
    questions = []
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: questions.append(a[1]) or answer)
    window.global_panel.fields['global_settings.project_name'][0].setText('unsaved_current')
    window.dft_panel.fields['dft.cutoff'][0].setText('602')
    window.refresh()
    before = window.project.model_dump()
    assert window.dirty and '*' in window.windowTitle()
    window.project_actions[operation].trigger()
    assert questions == ['未保存的项目']
    if answer == QMessageBox.StandardButton.Cancel:
        assert window.project.model_dump() == before and window.dirty
        assert '*' in window.windowTitle() and window.project_path is None
    else:
        assert not window.dirty and '*' not in window.windowTitle()
        if operation == 'new':
            assert window.project.structure is None and window.project_path is None
        else:
            assert window.project.global_settings.project_name == 'incoming_project'
            assert window.project_path == incoming_path
    if answer == QMessageBox.StandardButton.Save:
        assert load_project(save_path).model_dump() == before
    else:
        assert not save_path.exists()


@pytest.mark.parametrize('format', ['cif', 'xyz'])
def test_structure_page_button_still_imports_and_updates_single_view(window, app, tmp_path, monkeypatch, format):
    atoms = Atoms('HO', positions=[(.125, .25, .375), (1.5, 1.75, 2.)], cell=[6, 7, 8], pbc=True)
    path = tmp_path / f'structure.{format}'
    write(path, atoms, format=format)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    window.nav.setCurrentRow(0)
    button = window.structure_panel.import_button
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    settle(app)
    structure = window.project.structure
    assert structure.symbols == ['H', 'O'] and window.structure_panel.coords.rowCount() == 2
    assert np.allclose(structure.positions, atoms.positions)
    assert window.structure_panel.view.structure is structure
    assert np.allclose(window.structure_panel.view._points[:2], atoms.positions)
    assert np.allclose(structure.cell, atoms.cell if format == 'cif' else np.zeros((3, 3)))
    assert window.dirty and window.nav.currentRow() == 0
