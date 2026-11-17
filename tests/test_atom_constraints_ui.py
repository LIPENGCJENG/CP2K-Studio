"""Selection is presentation-only; fixed components are persistent project data."""
import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QDialog, QAbstractItemView
from core.atom_constraints import COMPONENTS, fixed_atom_groups, select_coordinate_range
from core.models import Project
from ui.main_window import MainWindow
from ui.structure_panel import ATOM_ID_ROLE, FIXED_COLUMN
from ui.coordinate_range_dialog import CoordinateRangeDialog
from tests.test_layout_workflow import wait_for_worker


@pytest.fixture
def window(app, water, tmp_path):
    water.global_settings.run_type = 'GEO_OPT'
    window = MainWindow(preset_directory=tmp_path / 'presets')
    window.load_into_ui(water)
    window.nav.setCurrentRow(0)
    window.show()
    app.processEvents()
    yield window
    wait_for_worker(app, window)
    window.dirty = False
    window.close()


def row_for(panel, atom_id):
    return next(row for row in range(panel.coords.rowCount()) if panel.coords.item(row, 0).data(ATOM_ID_ROLE) == atom_id)


@pytest.mark.parametrize('components', COMPONENTS)
def test_fix_selection_immediately_updates_model_preview_and_view(window, components):
    panel = window.structure_panel
    panel.select_atom_ids([1, 3])
    assert panel.view.selected_atom_ids == {1, 3}
    assert panel.fixed_count.text() == '已固定 0 个原子 · 已选择 2 个原子'
    assert not hasattr(panel, 'selection_status')
    assert panel.action_status.isHidden()
    assert not window.project.structure.fixed_atoms
    panel.components.setCurrentText(components)
    panel.fix_button.click()
    assert fixed_atom_groups(window.project.structure) == {components: [1, 3]}
    assert f'COMPONENTS_TO_FIX {components}' in window.preview.toPlainText()
    assert 'LIST 1 3' in window.preview.toPlainText()
    assert panel.view.fixed_atom_ids == {1, 3}
    assert panel.coords.item(row_for(panel, 1), FIXED_COLUMN).text() == components
    assert '已固定 2 个原子' in panel.fixed_count.text()


def test_multiselect_shift_ctrl_and_unfix_clear_preserve_coordinates_and_kinds(window, app):
    panel = window.structure_panel
    table = panel.coords
    assert table.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection
    assert [table.horizontalHeaderItem(i).text() for i in range(table.columnCount()) if not table.isColumnHidden(i)] == ['元素', 'x', 'y', 'z', '固定']
    window.stack.widget(0).ensureWidgetVisible(table)
    app.processEvents()
    before = window.project.structure.model_dump()
    def click(row, modifier=Qt.KeyboardModifier.NoModifier):
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, modifier,
                         table.visualItemRect(table.item(row, 0)).center())
    click(0)
    click(2, Qt.KeyboardModifier.ControlModifier)
    assert panel.selected_atom_ids() == {1, 3}
    click(0)
    click(2, Qt.KeyboardModifier.ShiftModifier)
    assert panel.selected_atom_ids() == {1, 2, 3}
    panel.fix_button.click()
    panel.select_atom_ids([2])
    panel.components.setCurrentText('XY')
    panel.fix_button.click()
    assert fixed_atom_groups(window.project.structure) == {'XYZ': [1, 3], 'XY': [2]}
    panel.unfix_button.click()
    assert fixed_atom_groups(window.project.structure) == {'XYZ': [1, 3]}
    panel.clear_fixed_button.click()
    assert not window.project.structure.fixed_atoms and not panel.view.fixed_atom_ids
    assert '&CONSTRAINT' not in window.preview.toPlainText()
    assert window.project.structure.model_dump() == before


@pytest.mark.parametrize('axis,components', [('X', 'XYZ'), ('Y', 'Z'), ('Z', 'XY')])
def test_range_dialog_selection_is_independent_of_fixed_components(window, monkeypatch, axis, components):
    panel = window.structure_panel
    before = window.project.model_dump()
    panel.components.setCurrentText(components)
    def choose(dialog):
        assert dialog.axis.currentText() == 'Z'
        dialog.axis.setCurrentText(axis)
        dialog.minimum.setText('-1e-1')
        dialog.maximum.setText('1e-1')
        dialog.accept()
        return dialog.result()
    monkeypatch.setattr(CoordinateRangeDialog, 'exec', choose)
    panel.range_button.click()
    expected = set(select_coordinate_range(window.project.structure, axis, -.1, .1))
    assert panel.selected_atom_ids() == expected
    assert panel.view.selected_atom_ids == expected
    assert panel.components.currentText() == components
    assert window.project.model_dump() == before
    panel.fix_button.click()
    assert set(fixed_atom_groups(window.project.structure)) == {components}


def test_bad_range_stays_open_empty_range_replaces_selection_and_cancel_preserves_it(window, monkeypatch):
    panel = window.structure_panel
    dialog = CoordinateRangeDialog(window.project.structure, window)
    dialog.show()
    for low, high in [('8', '3'), ('NaN', '3'), ('bad', '3')]:
        dialog.minimum.setText(low)
        dialog.maximum.setText(high)
        dialog.accept()
        assert dialog.result() != QDialog.DialogCode.Accepted
        assert dialog.error.text()
    dialog.reject()
    panel.select_atom_ids([1, 3])
    monkeypatch.setattr(CoordinateRangeDialog, 'exec', lambda dialog: QDialog.DialogCode.Rejected)
    panel.range_button.click()
    assert panel.selected_atom_ids() == {1, 3}
    def empty(dialog):
        dialog.minimum.setText('999')
        dialog.maximum.setText('1000')
        dialog.accept()
        return dialog.result()
    monkeypatch.setattr(CoordinateRangeDialog, 'exec', empty)
    panel.range_button.click()
    assert not panel.selected_atom_ids() and not panel.view.selected_atom_ids
    assert '没有符合条件' in panel.action_status.text()
    assert not window.project.structure.fixed_atoms


def test_sorting_editing_and_kind_mapping_use_identity_not_visible_row(window):
    panel = window.structure_panel
    table = panel.coords
    panel.select_atom_ids([1])
    panel.fix_button.click()
    original = window.project.structure.model_dump()
    table.sortItems(3, Qt.SortOrder.DescendingOrder)
    assert panel.selected_atom_ids() == {1}
    row = row_for(panel, 1)
    assert row != 0
    assert table.verticalHeaderItem(row).text() == '1'
    table.item(row, 1).setText('1.2345678912345')
    window.refresh()
    assert window.project.structure.atom_ids == original['atom_ids']
    assert window.project.structure.positions[0][0] == 1.2345678912345
    assert window.project.structure.labels == original['symbols']
    assert fixed_atom_groups(window.project.structure) == {'XYZ': [1]}
    assert 'O 1.23456789123' in window.preview.toPlainText()
    panel.select_atom_ids([2])
    panel.components.setCurrentText('Z')
    panel.fix_button.click()
    assert fixed_atom_groups(window.project.structure) == {'XYZ': [1], 'Z': [2]}
    assert table.item(row_for(panel, 2), FIXED_COLUMN).text() == 'Z'
    panel.unfix_button.click()
    assert fixed_atom_groups(window.project.structure) == {'XYZ': [1]}


def test_invalid_coordinate_prevents_fix_without_crash_or_stale_model_update(window):
    panel = window.structure_panel
    panel.select_atom_ids([1])
    panel.coords.item(0, 1).setText('bad')
    panel.fix_button.click()
    assert not window.project.structure.fixed_atoms
    assert '无效数字' in panel.action_status.text()
    window.refresh()
    assert not window.export_action.isEnabled()


def test_fixed_state_preserves_camera_and_changes_rendering_only(window, app):
    panel = window.structure_panel
    view = panel.view
    view.resize(540, 300)
    view.rotation = np.eye(3)
    view.zoom = 1.7
    geometry = view._points.copy()
    before = view.grab().toImage()
    panel.select_atom_ids([1])
    selected = view.grab().toImage()
    panel.fix_button.click()
    fixed = view.grab().toImage()
    assert before != selected and selected != fixed
    assert np.array_equal(view._points, geometry)
    assert np.array_equal(view.rotation, np.eye(3)) and view.zoom == 1.7
    assert view.fixed_atom_ids == {1} and view.selected_atom_ids == {1}


def test_check_invalidation_save_reload_and_fresh_import(window, app, tmp_path, monkeypatch):
    panel = window.structure_panel
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[7].state == 'ready'
    panel.select_atom_ids([1])
    assert window._step_states[7].state == 'ready'  # selection alone is not a model edit
    panel.fix_button.click()
    assert window._step_states[7].state == 'unchecked'
    path = tmp_path / 'saved.json'
    window.project_path = path
    assert window.save()
    window.load_into_ui(Project())
    window._open_path(path)
    assert fixed_atom_groups(window.project.structure) == {'XYZ': [1]}
    assert panel.coords.item(0, FIXED_COLUMN).text() == 'XYZ'
    assert panel.view.fixed_atom_ids == {1}
    xyz = tmp_path / 'new.xyz'
    xyz.write_text('1\nnew structure\nO 1 2 3\n')
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args, **kwargs: (str(xyz), ''))
    window.import_structure()
    assert window.project.structure.atom_ids == [1]
    assert not window.project.structure.fixed_atoms
    assert not panel.selected_atom_ids() and not panel.view.fixed_atom_ids


def test_sorted_fixed_column_and_model_reorder_keep_identity_and_kind(window, app):
    panel = window.structure_panel
    panel.coords.sortItems(FIXED_COLUMN, Qt.SortOrder.AscendingOrder)
    panel.select_atom_ids([2])
    panel.fix_button.click()
    assert panel.selected_atom_ids() == {2}
    assert fixed_atom_groups(window.project.structure) == {'XYZ': [2]}
    assert panel.coords.item(row_for(panel, 2), FIXED_COLUMN).text() == 'XYZ'
    project = window.project.model_copy(deep=True)
    project.structure = project.structure.reordered([3, 2])
    window.load_into_ui(project)
    assert panel.coords.rowCount() == 2
    assert panel.view.fixed_atom_ids == {2}
    assert fixed_atom_groups(window.project.structure) == {'XYZ': [2]}
    assert set(window.project.structure.atom_ids) == {2, 3}
    assert 'H' == panel.coords.item(row_for(panel, 2), 4).text()


@pytest.mark.parametrize('width,height', [(1050, 650), (1480, 920)])
def test_constraint_tools_fit_the_existing_scroll_page(window, app, width, height):
    window.resize(width, height)
    app.processEvents()
    page = window.stack.widget(0)
    page.ensureWidgetVisible(window.structure_panel.coords)
    app.processEvents()
    assert page.horizontalScrollBar().maximum() == 0
    assert window.structure_panel.coords.columnWidth(FIXED_COLUMN) >= 40
    assert not window.structure_panel.coords.grab().isNull()
