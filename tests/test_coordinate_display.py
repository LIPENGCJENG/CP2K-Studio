"""Four-decimal painting must not round edits, structures, or exported inputs."""
import numpy as np
import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest, QSignalSpy
from PySide6.QtWidgets import QLineEdit, QStyleOptionViewItem, QDialog
from core.generator import generate_input
from core.input_export import export_input
from core.models import Project
from core.project_io import export_bundle, load_project
from core.validator import InputValidator
from ui.coordinate_range_dialog import CoordinateRangeDialog
from ui.main_window import MainWindow
from tests.test_layout_workflow import wait_for_worker


def settle(app):
    for _ in range(5):
        app.processEvents()


@pytest.fixture
def window(app, water, tmp_path):
    water.global_settings.run_type = 'GEO_OPT'
    water.structure.positions = [(3.263799999999994, 6.527576199999995, .00004999),
                                (0., 2.967, -.00004999),
                                (24.7914123456789, 2.967056789123, -2.000000000000001)]
    water.structure.cell = ((26.123456789123, 0., 0.), (0., 27.987654321987, 0.), (0., 0., 30.12345678))
    value = MainWindow(preset_directory=tmp_path / 'presets')
    value.load_into_ui(water)
    value.nav.setCurrentRow(0)
    value.show()
    settle(app)
    yield value
    wait_for_worker(app, value)
    value.dirty = False
    value.close()


def painted_text(table, row, column):
    option = QStyleOptionViewItem()
    index = table.model().index(row, column)
    table.itemDelegateForIndex(index).initStyleOption(option, index)
    assert option.displayAlignment == Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    return option.text


def begin_edit(window, app, table, row, column):
    window.stack.widget(0).ensureWidgetVisible(table)
    item = table.item(row, column)
    table.scrollToItem(item)
    table.setCurrentItem(item)
    settle(app)
    pos = table.visualItemRect(item).center()
    QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=pos)
    QTest.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=pos)
    settle(app)
    editor = next(editor for editor in table.findChildren(QLineEdit) if editor.isVisible())
    assert editor.text() == item.data(Qt.ItemDataRole.EditRole) == item.text()
    return editor


def test_four_decimal_painting_keeps_raw_values_camera_input_and_check(window, app):
    panel = window.structure_panel
    expected_cells = [['26.1235', '0.0000', '0.0000'], ['0.0000', '27.9877', '0.0000'],
                      ['0.0000', '0.0000', '30.1235']]
    expected_positions = [['3.2638', '6.5276', '0.0000'], ['0.0000', '2.9670', '-0.0000'],
                          ['24.7914', '2.9671', '-2.0000']]
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[7].state == 'ready'
    before = window.project.model_dump()
    text = window.preview.toPlainText()
    revision = window._revision
    points = panel.view._points.copy()
    for table, columns, expected, raw in [
            (panel.cell, range(3), expected_cells, window.project.structure.cell),
            (panel.coords, range(1, 4), expected_positions, window.project.structure.positions)]:
        for row in range(3):
            for axis, column in enumerate(columns):
                assert painted_text(table, row, column) == expected[row][axis]
                assert table.item(row, column).text() == str(raw[row][axis])
        assert not table.grab().isNull()
    window.resize(1050, 800)
    settle(app)
    window.refresh()
    assert window.project.model_dump() == before and not window.dirty
    assert window._revision == revision and window._step_states[7].state == 'ready'
    assert window.preview.toPlainText() == text == generate_input(window.project)
    assert np.array_equal(panel.view._points, points)


@pytest.mark.parametrize('surface', ['cell', 'coords'])
@pytest.mark.parametrize('finish', ['enter', 'escape', 'focus_out', 'tab'])
def test_opening_editor_and_leaving_unchanged_does_not_round_or_dirty(window, app, surface, finish):
    panel = window.structure_panel
    table = getattr(panel, surface)
    before = window.project.model_dump()
    text = window.preview.toPlainText()
    revision = window._revision
    spy = QSignalSpy(panel.changed)
    editor = begin_edit(window, app, table, 0, 0 if surface == 'cell' else 1)
    assert len(editor.text()) > 8  # the editor receives the full value, not four decimals
    if finish == 'focus_out':
        QTest.mouseClick(table.parentWidget(), Qt.MouseButton.LeftButton, pos=QPoint(4, 4))
    else:
        QTest.keyClick(editor, {'enter': Qt.Key.Key_Return, 'escape': Qt.Key.Key_Escape, 'tab': Qt.Key.Key_Tab}[finish])
    settle(app)
    window.refresh()
    assert spy.count() == 0
    assert window.project.model_dump() == before and not window.dirty and window._revision == revision
    assert window.preview.toPlainText() == text


@pytest.mark.parametrize('surface', ['cell', 'coords'])
def test_explicit_coordinate_edit_retains_all_entered_digits_and_other_structure_fields(window, app, surface):
    panel = window.structure_panel
    panel.select_atom_ids([1])
    panel.components.setCurrentText('Z')
    panel.fix_button.click()
    table = getattr(panel, surface)
    expected = window.project.structure.model_dump()
    editor = begin_edit(window, app, table, 0, 0 if surface == 'cell' else 1)
    editor.selectAll()
    QTest.keyClicks(editor, '6.123456789012345')
    QTest.keyClick(editor, Qt.Key.Key_Escape)
    settle(app)
    window.refresh()
    assert window.project.structure.model_dump() == expected
    editor = begin_edit(window, app, table, 0, 0 if surface == 'cell' else 1)
    editor.selectAll()
    QTest.keyClicks(editor, '6.123456789012345')
    QTest.keyClick(editor, Qt.Key.Key_Return)
    settle(app)
    window.refresh()
    field = 'cell' if surface == 'cell' else 'positions'
    vector = list(expected[field][0])
    vector[0] = 6.123456789012345
    if surface == 'cell':
        expected[field] = (tuple(vector), *expected[field][1:])
    else:
        expected[field][0] = tuple(vector)
    assert window.project.structure.model_dump() == expected
    assert painted_text(table, 0, 0 if surface == 'cell' else 1) == '6.1235'
    assert panel.view.fixed_atom_ids == {1}
    assert np.array_equal(panel.view._points[0], window.project.structure.positions[0])


@pytest.mark.parametrize('axis,low,high,ids', [('X', 24.79141, 24.79142, {3}),
    ('Y', 6.52757, 6.52758, {1}), ('Z', .00004, .00006, {1})])
def test_coordinate_range_uses_full_values_instead_of_painted_values(window, monkeypatch, axis, low, high, ids):
    panel = window.structure_panel
    before = window.project.model_dump()
    def choose(dialog):
        dialog.axis.setCurrentText(axis)
        dialog.minimum.setText(str(low))
        dialog.maximum.setText(str(high))
        dialog.accept()
        assert dialog.result() == QDialog.DialogCode.Accepted
        return dialog.result()
    monkeypatch.setattr(CoordinateRangeDialog, 'exec', choose)
    panel.range_button.click()
    assert panel.selected_atom_ids() == panel.view.selected_atom_ids == ids
    assert window.project.model_dump() == before and not window.project.structure.fixed_atoms
    panel.fix_button.click()
    assert panel.view.fixed_atom_ids == ids


def test_save_reload_and_exports_match_the_full_precision_reference(window, app, tmp_path):
    panel = window.structure_panel
    panel.select_atom_ids([1, 3])
    panel.components.setCurrentText('Z')
    panel.fix_button.click()
    reference = window.project.model_copy(deep=True)
    expected = generate_input(reference)
    expected_bundle = export_bundle(reference, tmp_path / 'reference')
    window.project_path = tmp_path / 'project.json'
    assert window.save()
    assert load_project(window.project_path).structure == reference.structure
    window.load_into_ui(Project())
    window._open_path(window.project_path)
    settle(app)
    assert window.project.structure == reference.structure
    assert window.preview.toPlainText() == expected
    single = export_input(window.project, tmp_path / 'single.inp').path
    assert single.read_text() == expected
    bundle = export_bundle(window.project, tmp_path / 'actual')
    for name in ['input.inp', 'structure.xyz', 'run.sh']:
        assert (bundle.parent / name).read_bytes() == (expected_bundle.parent / name).read_bytes()
    result = InputValidator().parse(bundle.read_text(), bundle.parent)
    assert result.ok
    assert result.tree['+motion']['+constraint']['+fixed_atoms'][0]['list'] == [(1, 3)]
