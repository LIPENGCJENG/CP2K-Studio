from pathlib import Path
import json
import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest, QSignalSpy
from PySide6.QtWidgets import QFileDialog, QMessageBox, QAbstractItemView
from tests.simulation_box_helpers import mock_box_dialog
from i18n.language_manager import language_manager
from ui.widgets.poisson_reference import PoissonReference
from ui.main_window import MainWindow
from core.generator import generate_input
from tests.test_layout_workflow import wait_for_worker

FIXTURES = Path(__file__).parent / 'fixtures' / 'xsd'


@pytest.fixture
def window(app, water, tmp_path):
    w = MainWindow(preset_directory=tmp_path / 'presets')
    w.load_into_ui(water)
    w.show()
    app.processEvents()
    yield w
    wait_for_worker(app, w)
    w.dirty = False
    w.close()
    app.processEvents()
    language_manager().set_language('zh_CN')


def import_file(window, monkeypatch, filename):
    path = FIXTURES / filename
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    window.import_structure()


def test_reference_content_placement_read_only_and_no_parameter_changes(window, app):
    manager = language_manager()
    manager.set_language('en_US')
    w = window
    w.nav.setCurrentRow(2)
    table = w.dft_panel.poisson_reference
    card = w.dft_panel.poisson_card
    assert card.content.itemAt(1).widget() is table
    assert table.rowCount() == 6 and table.columnCount() == 4
    assert [table.item(r, 0).text() for r in range(6)] == ['PERIODIC','WAVELET','MT','ANALYTIC','MULTIPOLE','IMPLICIT']
    assert [table.item(r, 1).text() for r in range(6)] == ['XYZ','NONE, XZ, XYZ','NONE, XY, XZ, YZ','NONE, Z, XY','NONE','ANY']
    assert 'FFTSG' in table.item(1, 3).text()
    assert table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    assert not table.verticalHeader().isVisible()
    assert table.selectionMode() == QAbstractItemView.SelectionMode.NoSelection
    solver = w.dft_panel.fields['dft.poisson_solver'][0]
    assert [solver.itemData(i) for i in range(solver.count())] == [None, 'PERIODIC', 'MT', 'WAVELET', 'ANALYTIC']
    w.check_current_configuration()
    wait_for_worker(app, w)
    snapshot = w.project.model_dump_json(), w._revision, w.dirty, w.preview.toPlainText()
    checked = w._comprehensive_result
    spy = QSignalSpy(w.dft_panel.changed)
    w.stack.widget(2).ensureWidgetVisible(table)
    for _ in range(4): app.processEvents()
    QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=table.visualItemRect(table.item(2, 2)).center())
    QTest.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=table.visualItemRect(table.item(2, 2)).center())
    assert table.state() != QAbstractItemView.State.EditingState
    assert spy.count() == 0
    assert (w.project.model_dump_json(), w._revision, w.dirty, w.preview.toPlainText()) == snapshot
    assert w._comprehensive_result is checked
    manager.set_language('zh_CN')
    app.processEvents()
    assert [table.horizontalHeaderItem(i).text() for i in range(4)] == ['POISSON_SOLVER','PERIODIC','推荐适用场景','核心约束与注意事项']
    assert table.item(1, 1).text() == 'NONE, XZ, XYZ'
    assert '带净电荷的孤立团簇' in table.item(2, 2).text()
    assert (w.project.model_dump_json(), w._revision, w.dirty, w.preview.toPlainText()) == snapshot


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
@pytest.mark.parametrize('width', [280, 360, 620, 980])
def test_reference_elides_single_line_text_with_fixed_rows_without_scrollbars(app, language, width):
    manager = language_manager()
    manager.set_language(language)
    table = PoissonReference()
    try:
        table.resize(width, 200)
        table.show()
        for _ in range(6): app.processEvents()
        assert table.viewport().width() == sum(table.columnWidth(i) for i in range(4))
        assert not table.wordWrap() and table.textElideMode() == Qt.TextElideMode.ElideRight
        assert not table.horizontalScrollBar().isVisible() and not table.verticalScrollBar().isVisible()
        assert table.height() == table.horizontalHeader().height() + sum(table.rowHeight(r) for r in range(6)) + 2 * table.frameWidth()
        assert table.horizontalHeader().height() == table.HEADER_HEIGHT
        assert [table.rowHeight(row) for row in range(6)] == [table.ROW_HEIGHT] * 6
        for row in range(6):
            for column in range(4):
                text = table.item(row, column).text()
                assert '\n' not in text and '\r' not in text
                assert table.item(row, column).toolTip()
        original = table.item(1, 3).text()
        elided = table.fontMetrics().elidedText(original, table.textElideMode(), table.columnWidth(3)-8)
        assert elided.endswith('…') and len(elided) < len(original)
        assert table.item(1, 3).text() == original
        table.resizeRowsToContents()
        app.processEvents()
        assert [table.rowHeight(row) for row in range(6)] == [table.ROW_HEIGHT] * 6
    finally:
        table.close()
        table.deleteLater()
        app.processEvents()
        manager.set_language('zh_CN')


def test_xsd_molecule_locked_but_cell_and_box_editing_remain_available(window, app, monkeypatch):
    import_file(window, monkeypatch, 'h2o_ms23.xsd')
    p = window.structure_panel
    assert window.project.structure.periodicity_locked
    assert not p.periodic.isEnabled() and p.periodic.currentText() == 'NONE'
    assert p.cell.isEnabled() and p.box_button.isVisible()
    before = window.project.model_dump_json(), window._revision, window.dirty
    p.periodic.setCurrentText('XYZ')
    QTest.keyClick(p.periodic, Qt.Key.Key_Down)
    assert p.periodic.currentText() == 'NONE'
    assert (window.project.model_dump_json(), window._revision, window.dirty) == before
    raw = window.project.structure.positions
    p.cell.item(0, 0).setText('12.3456789')
    window.refresh()
    assert window.project.structure.cell[0][0] == 12.3456789
    assert window.project.structure.positions == raw and window.project.structure.periodic == 'NONE'
    mock_box_dialog(monkeypatch, margin=5, mode='CUBIC')
    p.generate_box()
    assert window.project.structure.periodicity_locked and not p.periodic.isEnabled()
    assert np.min(window.project.structure.positions) >= 4.999999999
    for filename in ['rutile_ms23.xsd', 'slab_ms23.xsd']:
        import_file(window, monkeypatch, filename)
        assert p.periodic.isEnabled() and window.project.structure.structure_type == 'periodic_structure'
        p.periodic.setCurrentText('XY')
        window.refresh()
        assert window.project.structure.periodic == 'XY'


def test_plain_xyz_requires_explicit_confirmation_and_can_cancel(window, monkeypatch, tmp_path):
    path = tmp_path / 'plain.xyz'
    path.write_text('3\nordinary XYZ\nO 0 0 0\nH 0 .7 .5\nH 0 -.7 .5\n')
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(path), ''))
    window.import_structure()
    p = window.structure_panel
    assert p.periodic.isEnabled() and p.confirm_molecule_button.isVisible()
    assert window.project.structure.structure_type == 'unclassified'
    before = window.project.model_dump_json(), window._revision, window.dirty
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.No)
    p.confirm_molecule_button.click()
    assert (window.project.model_dump_json(), window._revision, window.dirty) == before
    positions, cell = window.project.structure.positions, window.project.structure.cell
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.Yes)
    p.confirm_molecule_button.click()
    assert window.project.structure.periodicity_locked and not p.periodic.isEnabled()
    assert window.project.structure.positions == positions and window.project.structure.cell == cell
    assert p.box_button.isVisible() and not p.confirm_molecule_button.isVisible()


def test_project_reload_and_language_switch_keep_lock_input_and_camera(window, app, monkeypatch, tmp_path):
    import_file(window, monkeypatch, 'h2o_ms23.xsd')
    mock_box_dialog(monkeypatch, margin=5, mode='CUBIC')
    window.structure_panel.generate_box()
    solver = window.dft_panel.fields['dft.poisson_solver'][0]
    solver.setCurrentIndex(solver.findData('WAVELET'))
    window.refresh()
    view = window.structure_panel.view
    view.align_cell_axis('B')
    view.zoom = 1.6
    rotation = view.rotation.copy()
    snapshot = window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText().encode()
    for language in ['en_US', 'zh_CN', 'en_US']:
        window.language_selector.setCurrentIndex(window.language_selector.findData(language))
        app.processEvents()
        assert not window.structure_panel.periodic.isEnabled()
        assert window.structure_panel.periodic.toolTip() == ('The imported structure is a non-periodic molecule. Periodicity is fixed to NONE.' if language == 'en_US' else '当前导入的是非周期孤立分子，周期性固定为 NONE。')
        assert (window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText().encode()) == snapshot
        assert view.zoom == 1.6 and np.array_equal(view.rotation, rotation)
    path = tmp_path / 'locked.json'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(path), ''))
    assert window.save(force_dialog=True)
    text = generate_input(window.project)
    window.new_project()
    window._open_path(path)
    assert not window.structure_panel.periodic.isEnabled()
    assert generate_input(window.project) == text
    old = json.loads(path.read_text())
    old['structure'].pop('structure_type')
    path.write_text(json.dumps(old))
    window._open_path(path)
    assert window.structure_panel.periodic.isEnabled()
    assert window.project.structure.structure_type == 'unclassified'
