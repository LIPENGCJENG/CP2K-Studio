"""Blank clicks clear selection, while atom actions keep their stable targets."""
import pytest
from PySide6.QtCore import Qt, QPoint, QRect, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QBoxLayout, QVBoxLayout, QLineEdit, QAbstractScrollArea, QScrollArea
from core.atom_constraints import fixed_atom_groups
from core.project_io import load_project
from ui.main_window import MainWindow
from ui.coordinate_range_dialog import CoordinateRangeDialog
from tests.test_layout_workflow import wait_for_worker


def settle(app):
    for _ in range(5):
        app.processEvents()


@pytest.fixture
def window(app, water, tmp_path):
    water.global_settings.run_type = 'GEO_OPT'
    window = MainWindow(preset_directory=tmp_path / 'presets')
    window.load_into_ui(water)
    window.nav.setCurrentRow(0)
    window.show()
    window.stack.widget(0).ensureWidgetVisible(window.structure_panel.coords)
    settle(app)
    yield window
    wait_for_worker(app, window)
    window.dirty = False
    window.close()


def action_controls(panel):
    return [panel.direction_label, panel.components, panel.fix_button, panel.unfix_button,
            panel.range_button, panel.clear_fixed_button]


def assert_actions_fit(panel):
    bar = panel.actions_bar
    controls = action_controls(panel)
    rects = [QRect(control.mapTo(bar, QPoint(0, 0)), control.size()) for control in controls]
    assert not isinstance(bar, QAbstractScrollArea)
    assert not bar.findChildren(QScrollArea)  # the combo's popup list may still scroll
    assert not hasattr(bar, 'horizontalScrollBar')
    assert len({control.height() for control in controls}) == 1
    assert all(control.width() >= control.sizeHint().width() for control in controls)
    assert all(bar.rect().contains(rect) for rect in rects)
    assert all(not first.intersects(second) for index, first in enumerate(rects) for second in rects[index+1:])
    assert bar.height() == max(rect.bottom() for rect in rects) + 1
    assert rects[0].y() == rects[1].y()
    assert rects[2].y() == rects[3].y()
    assert rects[4].y() > max(rect.bottom() for rect in rects[:4])
    return rects


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
@pytest.mark.parametrize('width,height', [(1480, 920), (1050, 650)])
def test_two_action_rows_full_labels_and_no_scroll_container(window, app, width, height, language):
    from i18n.language_manager import language_manager
    panel = window.structure_panel
    bar = panel.actions_bar
    try:
        language_manager().set_language(language)
        window.resize(width, height)
        settle(app)
        assert isinstance(bar.layout(), QVBoxLayout) and bar.layout().spacing() == 8
        assert bar.layout().count() == 2
        assert [bar.direction_group.layout().itemAt(i).widget() for i in range(2)] == action_controls(panel)[:2]
        assert [bar.fixed_group.layout().itemAt(i).widget() for i in range(2)] == action_controls(panel)[2:4]
        assert [bar.rows[1].itemAt(i).widget() for i in range(2)] == action_controls(panel)[4:]
        assert panel.direction_label.buddy() is panel.components
        assert not bar.autoFillBackground()
        rects = assert_actions_fit(panel)
        if width == 1480:
            assert len({rect.y() for rect in rects}) == 2
            assert all(row.direction() == QBoxLayout.Direction.LeftToRight for row in bar.rows)
        assert window.stack.widget(0).horizontalScrollBar().maximum() == 0
    finally:
        language_manager().set_language('zh_CN')


def test_action_rows_reflow_live_without_changing_selection_constraints_or_input(window, app):
    from i18n.language_manager import language_manager
    panel = window.structure_panel
    panel.select_atom_ids([1, 3])
    panel.components.setCurrentText('XY')
    panel.fix_button.click()
    before, inp = window.project.model_dump_json(), window.preview.toPlainText()
    revision, dirty = window._revision, window.dirty
    controls = action_controls(panel)
    window.resize(1700, 920)
    try:
        for width in [720, 280, 430, 320, 720]:
            panel.actions_bar.setFixedWidth(width)
            for language in ['en_US', 'zh_CN']:
                language_manager().set_language(language)
                settle(app)
                assert_actions_fit(panel)
                assert action_controls(panel) == controls
                assert panel.selected_atom_ids() == panel.view.selected_atom_ids == {1, 3}
                assert panel.view.fixed_atom_ids == {1, 3}
                assert window.project.model_dump_json() == before
                assert window.preview.toPlainText() == inp
                assert (window._revision, window.dirty) == (revision, dirty)
    finally:
        language_manager().set_language('zh_CN')


@pytest.mark.parametrize('surface', ['card_padding', 'page_margin', 'right_padding'])
def test_external_blank_click_clears_both_highlights_but_keeps_fixed_project(window, app, surface):
    panel = window.structure_panel
    panel.select_atom_ids([1, 3])
    panel.fix_button.click()
    before = window.project.model_dump()
    preview = window.preview.toPlainText()
    if surface == 'card_padding':
        target = panel.coords.parentWidget()
    elif surface == 'page_margin':
        target = panel
    else:
        target = window.input_preview_pane
    QTest.mouseClick(target, Qt.MouseButton.LeftButton, pos=QPoint(4, 4))
    settle(app)
    assert not panel.selected_atom_ids()
    assert not panel.view.selected_atom_ids
    assert panel.view.fixed_atom_ids == {1, 3}
    assert '已选择 0 个原子' in panel.fixed_count.text()
    assert not panel.fix_button.isEnabled() and not panel.unfix_button.isEnabled()
    assert panel.clear_fixed_button.isEnabled()
    assert not panel.action_status.isVisible()
    assert window.project.model_dump() == before
    assert window.preview.toPlainText() == preview


def test_real_combo_popup_fix_unfix_and_clear_buttons_keep_selected_targets(window, app):
    panel = window.structure_panel
    panel.select_atom_ids([1, 3])
    QTest.mouseClick(panel.components, Qt.MouseButton.LeftButton)
    QTest.keyClick(panel.components, Qt.Key.Key_End)  # YZ, the final option
    QTest.keyClick(panel.components, Qt.Key.Key_Return)
    settle(app)
    assert panel.components.currentText() == 'YZ'
    assert panel.selected_atom_ids() == {1, 3}
    QTest.mouseClick(panel.fix_button, Qt.MouseButton.LeftButton)
    assert fixed_atom_groups(window.project.structure) == {'YZ': [1, 3]}
    assert panel.selected_atom_ids() == {1, 3}
    QTest.mouseClick(panel.unfix_button, Qt.MouseButton.LeftButton)
    assert not window.project.structure.fixed_atoms
    assert panel.selected_atom_ids() == {1, 3}
    QTest.mouseClick(panel.fix_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(panel.clear_fixed_button, Qt.MouseButton.LeftButton)
    assert not window.project.structure.fixed_atoms
    assert panel.selected_atom_ids() == {1, 3}


def test_real_range_dialog_keeps_selection_until_accept_and_allows_subsequent_fix(window, app):
    panel = window.structure_panel
    panel.select_atom_ids([1])
    errors = []
    def fill_dialog():
        try:
            dialog = QApplication.activeModalWidget()
            assert isinstance(dialog, CoordinateRangeDialog)
            assert panel.selected_atom_ids() == {1}
            QTest.mouseClick(dialog.minimum, Qt.MouseButton.LeftButton)
            QTest.keyClicks(dialog.minimum, '0.5')
            QTest.mouseClick(dialog.maximum, Qt.MouseButton.LeftButton)
            QTest.keyClicks(dialog.maximum, '0.6')
            assert panel.selected_atom_ids() == {1}
            QTest.mouseClick(dialog.buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton)
        except Exception as exc:
            errors.append(exc)
            dialog = QApplication.activeModalWidget()
            if dialog:
                dialog.reject()
    QTimer.singleShot(20, fill_dialog)
    QTest.mouseClick(panel.range_button, Qt.MouseButton.LeftButton)
    assert not errors
    assert panel.selected_atom_ids() == {2, 3}
    assert panel.view.selected_atom_ids == {2, 3}
    assert not window.project.structure.fixed_atoms
    QTest.mouseClick(panel.fix_button, Qt.MouseButton.LeftButton)
    assert fixed_atom_groups(window.project.structure) == {'XYZ': [2, 3]}


def test_view_mouse_interaction_and_table_multiselect_do_not_clear_selection(window, app):
    panel = window.structure_panel
    table = panel.coords
    window.stack.widget(0).ensureWidgetVisible(table)
    settle(app)
    def click(row, modifiers=Qt.KeyboardModifier.NoModifier):
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, modifiers,
                         table.visualItemRect(table.item(row, 0)).center())
    click(0)
    click(2, Qt.KeyboardModifier.ControlModifier)
    assert panel.selected_atom_ids() == {1, 3}
    click(0)
    click(2, Qt.KeyboardModifier.ShiftModifier)
    assert panel.selected_atom_ids() == {1, 2, 3}
    QTest.mousePress(panel.view, Qt.MouseButton.LeftButton, pos=QPoint(120, 110))
    QTest.mouseMove(panel.view, QPoint(150, 135), delay=10)
    QTest.mouseRelease(panel.view, Qt.MouseButton.LeftButton, pos=QPoint(150, 135))
    QTest.mouseClick(panel.view.labels_button, Qt.MouseButton.LeftButton)
    assert panel.selected_atom_ids() == {1, 2, 3}
    assert panel.view.selected_atom_ids == {1, 2, 3}


def test_blank_click_is_selection_only_and_does_not_invalidate_check_or_save(window, app, tmp_path):
    panel = window.structure_panel
    panel.select_atom_ids([2])
    panel.fix_button.click()
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[7].state == 'ready'
    revision = window._revision
    # Switch back without replacing the structure or selection.
    window.nav.setCurrentRow(0)
    window.stack.widget(0).ensureWidgetVisible(panel.coords)
    settle(app)
    QTest.mouseClick(panel.coords.parentWidget(), Qt.MouseButton.LeftButton, pos=QPoint(4, 4))
    assert window._revision == revision
    assert window._step_states[7].state == 'ready'
    assert not panel.selected_atom_ids() and panel.view.fixed_atom_ids == {2}
    assert 'LIST 2' in window.preview.toPlainText()
    window.project_path = tmp_path / 'preserved.json'
    assert window.save()
    assert fixed_atom_groups(load_project(window.project_path).structure) == {'XYZ': [2]}


def test_blank_click_keeps_normal_coordinate_editor_commit(window, app):
    panel = window.structure_panel
    table = panel.coords
    window.stack.widget(0).ensureWidgetVisible(table)
    settle(app)
    item = table.item(0, 1)
    table.setCurrentItem(item)
    table.editItem(item)
    editor = table.findChild(QLineEdit)
    assert editor is not None
    editor.selectAll()
    QTest.keyClicks(editor, '1.75')
    QTest.mouseClick(table.parentWidget(), Qt.MouseButton.LeftButton, pos=QPoint(4, 4))
    settle(app)
    window.refresh()
    assert window.project.structure.positions[0][0] == 1.75
    assert not panel.selected_atom_ids() and not panel.view.selected_atom_ids


def test_mouse_listener_only_runs_for_visible_windows_with_a_selection(window, app):
    panel = window.structure_panel
    assert not panel._selection_filter_active
    panel.select_atom_ids([1, 3])
    assert panel._selection_filter_active
    window.hide()
    settle(app)
    assert not panel._selection_filter_active
    assert panel.selected_atom_ids() == {1, 3}
    window.show()
    settle(app)
    assert panel._selection_filter_active
    QTest.mouseClick(panel.coords.parentWidget(), Qt.MouseButton.LeftButton, pos=QPoint(4, 4))
    assert not panel.selected_atom_ids()
    assert not panel._selection_filter_active
