"""Display order must not change calculation data or page/status associations."""
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel, QFileDialog
from core.generator import generate_input
from core.project_io import load_project
from i18n.language_manager import language_manager
from ui.main_window import MainWindow
from ui.widgets.status_badge import STATUS_ROLE
from tests.test_layout_workflow import wait_for_worker

ROOT = Path(__file__).resolve().parents[1]


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


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_startup_structure_then_global_and_remaining_pages(app, tmp_path, language):
    manager = language_manager().attach(app)
    manager.set_language(language)
    window = MainWindow(preset_directory=tmp_path)
    try:
        window.show()
        app.processEvents()
        assert window.nav.currentRow() == window.stack.currentIndex() == 0
        expected = ['01  Structure & Cell', '02  GLOBAL', '03  DFT', '04  SCF',
                    '05  Basis Sets & Pseudopotentials', '06  Geometry Optimization',
                    '07  Runtime Settings', '08  Export & Presets'] if language == 'en_US' else [
                    '01  结构与晶胞', '02  GLOBAL', '03  DFT', '04  SCF',
                    '05  基组与赝势', '06  几何优化', '07  运行环境', '08  导出与预设']
        assert [window.nav.item(i).text() for i in range(8)] == expected
        assert window.structure_panel.findChild(QLabel, 'heading').text() == (
            '01 · Structure & Cell' if language == 'en_US' else '01 · 结构与晶胞')
        assert window.global_panel.findChild(QLabel, 'heading').text() == '02 · GLOBAL'
        pages = [window.structure_panel, window.global_panel, window.dft_panel, window.scf_panel,
                 window.kind_panel, window.task_panel, window.run_panel, window.export_panel]
        snapshot = window.project.model_dump_json(), window.dirty, window._revision
        for index, panel in enumerate(pages):
            QTest.mouseClick(window.nav.viewport(), Qt.MouseButton.LeftButton,
                             pos=window.nav.visualItemRect(window.nav.item(index)).center())
            app.processEvents()
            assert window.stack.currentIndex() == index
            assert window.stack.currentWidget().widget() is panel
            assert (window.project.model_dump_json(), window.dirty, window._revision) == snapshot
    finally:
        window.dirty = False
        window.close()
        app.processEvents()
        manager.set_language('zh_CN')


def test_live_language_switch_preserves_current_page_widgets_check_and_input(window, app):
    window.check_current_configuration()
    wait_for_worker(app, window)
    window.nav.setCurrentRow(1)
    widgets = [window.stack.widget(i).widget() for i in range(8)]
    snapshot = (window.project.model_dump_json(), window.preview.toPlainText(), window.dirty,
                window._revision, window._configuration_check_snapshot)
    statuses = [window.nav.item(i).data(STATUS_ROLE) for i in range(8)]
    for language in ['en_US', 'zh_CN', 'en_US']:
        window.language_selector.setCurrentIndex(window.language_selector.findData(language))
        app.processEvents()
        assert window.nav.item(0).text() == ('01  Structure & Cell' if language == 'en_US' else '01  结构与晶胞')
        assert window.nav.item(1).text() == '02  GLOBAL'
        assert window.stack.currentWidget().widget() is window.global_panel
        assert [window.stack.widget(i).widget() for i in range(8)] == widgets
        assert [window.nav.item(i).data(STATUS_ROLE) for i in range(8)] == statuses
        assert (window.project.model_dump_json(), window.preview.toPlainText(), window.dirty,
                window._revision, window._configuration_check_snapshot) == snapshot


def test_immediate_and_validated_states_follow_the_edited_page(window):
    name = window.global_panel.fields['global_settings.project_name'][0]
    name.setText('')
    assert window.nav.item(1).data(STATUS_ROLE) == 'unchecked'
    assert window.nav.item(0).data(STATUS_ROLE) == 'ready'
    window.refresh()
    assert window.nav.item(1).data(STATUS_ROLE) == 'error'
    assert window.nav.item(0).data(STATUS_ROLE) == 'ready'
    name.setText('navigation_test')
    window.refresh()
    window.structure_panel.cell.item(0, 0).setText('bad')
    assert window.nav.item(0).data(STATUS_ROLE) == 'unchecked'
    assert window.nav.item(1).data(STATUS_ROLE) == 'ready'
    window.refresh()
    assert window.nav.item(0).data(STATUS_ROLE) == 'error'
    assert window.nav.item(1).data(STATUS_ROLE) == 'ready'
    assert window.nav.item(7).data(STATUS_ROLE) == 'unchecked'


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_validation_error_links_locate_new_structure_and_global_steps(window, app, language):
    language_manager().set_language(language)
    window.global_panel.fields['global_settings.project_name'][0].setText('')
    window.structure_panel.cell.item(0, 0).setText('bad')
    window.check_current_configuration()
    wait_for_worker(app, window)
    for index, title in [(0, '01 Structure & Cell' if language == 'en_US' else '01 结构与晶胞'),
                         (1, '02 GLOBAL')]:
        error = next(window.export_panel.errors.item(row)
                     for row in range(window.export_panel.errors.count())
                     if window.export_panel.errors.item(row).data(Qt.ItemDataRole.UserRole) == index)
        assert title in error.text()
        window.nav.setCurrentRow(7)
        window.export_panel.locate_error(error)
        assert window.nav.currentRow() == window.stack.currentIndex() == index
        assert window.stack.currentWidget().widget() is (
            window.structure_panel if index == 0 else window.global_panel)


@pytest.mark.parametrize('preset,task', [('single_point', 'ENERGY'), ('geo_opt', 'GEO_OPT')])
def test_legacy_project_preset_save_and_reopen_preserve_input(window, app, tmp_path, monkeypatch, preset, task):
    old_project = ROOT / 'examples' / 'water.cp2kstudio.json'
    original = load_project(old_project)
    expected_input = generate_input(original)
    window._open_path(old_project)
    assert window.preview.toPlainText() == expected_input
    structure = window.project.structure.model_dump()
    monkeypatch.setattr(window, 'confirm_preset_application', lambda *args: True)
    assert window.apply_preset(preset)
    assert window.project.global_settings.run_type == task
    assert window.project.structure.model_dump() == structure
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window.nav.item(7).data(STATUS_ROLE) == 'ready'
    expected_input = window.preview.toPlainText()
    path = tmp_path / 'reordered-navigation.cp2kstudio.json'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(path), ''))
    assert window.save(force_dialog=True)
    expected = window.project.model_dump_json()
    window.new_project()
    window._open_path(path)
    assert window.project.model_dump_json() == expected
    assert window.preview.toPlainText() == generate_input(window.project) == expected_input
    assert window.stack.widget(0).widget() is window.structure_panel
    assert window.stack.widget(1).widget() is window.global_panel
