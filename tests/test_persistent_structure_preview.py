"""The single linked 3D widget stays above INP on every navigation page."""
import numpy as np
import pytest
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent
from PySide6.QtGui import QHelpEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget, QToolButton, QToolTip, QFileDialog, QLabel
from ase.io import write
from core.models import Project
from core.structure import to_atoms
from ui.main_window import MainWindow
from ui.structure_view import StructureView
from ui.widgets.section_card import SectionCard
from ui.widgets.help_icon import HelpIcon
from tests.test_layout_workflow import wait_for_worker


def settle(app):
    for _ in range(5):
        app.processEvents()


@pytest.fixture
def window(app, water, tmp_path):
    water.global_settings.run_type = 'GEO_OPT'
    value = MainWindow(preset_directory=tmp_path / 'presets')
    value.load_into_ui(water)
    value.show()
    settle(app)
    yield value
    wait_for_worker(app, value)
    QToolTip.hideText()
    value.dirty = False
    value.close()


def test_single_preview_is_above_input_and_structure_page_has_no_old_card(window):
    view = window.structure_panel.view
    splitter = window.preview_splitter
    assert splitter.orientation() == Qt.Orientation.Vertical
    assert splitter.count() == 2
    assert splitter.widget(0) is window.structure_view_card
    assert splitter.widget(1) is window.input_preview_pane
    assert window.structure_view_card.isAncestorOf(view)
    assert window.input_preview_pane.isAncestorOf(window.tabs)
    assert not window.structure_panel.isAncestorOf(view)
    assert window.findChildren(StructureView) == [view]
    cards = window.structure_panel.findChildren(SectionCard)
    assert [card.title_label.text() for card in cards] == ['结构导入', '晶胞与周期性', '原子坐标']
    assert window.structure_panel.layout().count() == 5  # heading, three cards, stretch
    sizes = splitter.sizes()
    assert .56 <= sizes[0] / sum(sizes) <= .64
    assert not splitter.childrenCollapsible()


def test_navigation_keeps_view_camera_selection_fixed_state_and_model(window, app):
    panel = window.structure_panel
    view = panel.view
    panel.select_atom_ids([1, 3])
    panel.components.setCurrentText('Z')
    panel.fix_button.click()
    view.align_cell_axis('B')
    view.set_labels_visible(True)
    view.set_perspective(True)
    view.zoom = 1.6
    rotation = view.rotation.copy()
    before = window.project.model_dump()
    preview = window.preview.toPlainText()
    for page in range(8):
        window.nav.setCurrentRow(page)
        settle(app)
        assert view.isVisibleTo(window) and view.height() >= view.minimumHeight()
        assert window.structure_panel.view is view
        assert window.findChildren(StructureView) == [view]
        assert np.array_equal(view.rotation, rotation)
        assert view.zoom == 1.6 and view.show_labels and view.perspective
        assert view.selected_atom_ids == {1, 3} and view.fixed_atom_ids == {1, 3}
        assert window.project.model_dump() == before
        assert window.preview.toPlainText() == preview


def test_coordinates_cell_and_import_update_the_right_view(window, app, tmp_path, monkeypatch):
    panel = window.structure_panel
    view = panel.view
    panel.coords.item(0, 1).setText('1.125')
    panel.cell.item(0, 0).setText('7.5')
    window.refresh()
    assert view.structure is window.project.structure
    assert view.structure.positions[0][0] == 1.125
    assert view.structure.cell[0][0] == 7.5
    assert np.array_equal(view._points[0], window.project.structure.positions[0])
    replacement = window.project.structure.model_copy(deep=True)
    replacement.positions[0] = (2, 1, 0)
    path = tmp_path / 'new.extxyz'
    write(path, to_atoms(replacement), format='extxyz')
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args, **kwargs: (str(path), ''))
    window.import_structure()
    settle(app)
    assert window.structure_panel.view is view
    assert view.structure.positions[0] == (2, 1, 0)
    assert view.isVisibleTo(window)
    assert not view.grab().isNull()


def test_no_hover_text_anywhere_in_view_but_parameter_help_is_available(window, app):
    view = window.structure_panel.view
    for widget in [view, *view.findChildren(QWidget)]:
        assert not widget.toolTip() and not widget.statusTip()
        QToolTip.hideText()
        position = widget.rect().center()
        app.sendEvent(widget, QHelpEvent(QEvent.Type.ToolTip, position, widget.mapToGlobal(position)))
        assert not QToolTip.isVisible()
    assert all(button.accessibleName() for button in view.tools.findChildren(QToolButton))
    card = window.structure_view_card
    icon = card.help_icon
    assert icon.accessibleDescription() == '左键拖动空白旋转 · 单击原子选择 · 右键拖动平移 · 滚轮缩放；不推断化学键。'
    assert not card.toolTip() and not card.title_label.toolTip()
    assert not any(label.text() == icon.accessibleDescription() for label in card.findChildren(QLabel))
    position = icon.rect().center()
    app.sendEvent(icon, QHelpEvent(QEvent.Type.ToolTip, position, icon.mapToGlobal(position)))
    assert QToolTip.isVisible() and QToolTip.text() == icon.toolTip()
    QToolTip.hideText()
    window.nav.setCurrentRow(0)
    icon = window.structure_panel.findChild(HelpIcon)
    window.stack.widget(0).ensureWidgetVisible(icon)
    settle(app)
    assert icon.toolTip()
    position = icon.rect().center()
    app.sendEvent(icon, QHelpEvent(QEvent.Type.ToolTip, position, icon.mapToGlobal(position)))
    assert QToolTip.isVisible() and QToolTip.text() == icon.toolTip()


def test_drag_splitter_changes_heights_and_respects_minimums(window, app):
    splitter = window.preview_splitter
    before = splitter.sizes()
    view = window.structure_panel.view
    rotation = view.rotation.copy()
    height = view.height()
    handle = splitter.handle(1)
    start = handle.rect().center()
    end = start + QPoint(0, 65)
    QTest.mousePress(handle, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(handle, end, delay=20)
    QTest.mouseRelease(handle, Qt.MouseButton.LeftButton, pos=end)
    settle(app)
    after = splitter.sizes()
    assert after[0] > before[0] and after[1] < before[1]
    assert view.height() > height
    assert np.array_equal(view.rotation, rotation)
    for location in [0, splitter.height()]:
        splitter.moveSplitter(location, 1)
        settle(app)
        assert window.structure_view_card.height() >= window.structure_view_card.minimumHeight()
        assert window.input_preview_pane.height() >= window.input_preview_pane.minimumHeight()
        assert view.isVisibleTo(window) and window.tabs.isVisibleTo(window)


@pytest.mark.parametrize('width,height', [(1050, 650), (1366, 768), (1920, 1080)])
def test_resizing_keeps_both_panes_usable_and_input_scroll_independent(window, app, width, height):
    window.resize(width, height)
    settle(app)
    view = window.structure_panel.view
    splitter = window.preview_splitter
    assert sum(splitter.sizes()) + splitter.handleWidth() == splitter.height()
    assert view.width() > 200 and view.height() >= 160
    assert window.tabs.height() > 80
    assert view.tools.geometry().right() <= view.width()
    assert window.structure_view_card.geometry().bottom() < window.input_preview_pane.y()
    assert window.preview.verticalScrollBar().maximum() > 0
    rotation = view.rotation.copy()
    window.preview.verticalScrollBar().setValue(window.preview.verticalScrollBar().maximum())
    assert np.array_equal(view.rotation, rotation)
    assert window.preview.verticalScrollBar().value() > 0
    assert window.preview.horizontalScrollBar() is not window.report.horizontalScrollBar()
    assert not view.grab().isNull()


def test_right_view_mouse_controls_and_axis_tools_still_work(window, app):
    view = window.structure_panel.view
    rotation = view.rotation.copy()
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=QPoint(120, 110))
    QTest.mouseMove(view, QPoint(165, 140), delay=10)
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=QPoint(165, 140))
    assert not np.allclose(view.rotation, rotation)
    wheel = QWheelEvent(QPointF(180, 130), QPointF(180, 130), QPoint(), QPoint(0, 120),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    app.sendEvent(view, wheel)
    assert view.zoom > 1
    for axis in 'ABC':
        view.axis_buttons[axis].click()
        transformed = view.rotation @ np.asarray(window.project.structure.cell['ABC'.index(axis)])
        assert np.allclose(transformed[:2], 0)
    view.labels_button.click()
    assert view.show_labels
    view.reset_button.click()
    assert view.zoom == 1 and np.allclose(view.rotation, view.default_rotation())


def test_empty_structure_shows_view_and_keeps_input_report_tabs(window, app):
    window.load_into_ui(Project())
    settle(app)
    view = window.structure_panel.view
    assert view.structure is None and view.isVisibleTo(window)
    assert not view.grab().isNull()
    assert not window.preview.toPlainText().strip() == ''
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == ['input.inp', '校验报告']
    assert all(not button.isEnabled() for button in view.axis_buttons.values())


def test_resizing_and_navigation_keep_manual_check_report_and_preview(window, app):
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[7].state == 'ready'
    report = window.report.toPlainText()
    preview = window.preview.toPlainText()
    window.preview_splitter.setSizes([450, 350])
    for page in range(8):
        window.nav.setCurrentRow(page)
        window.tabs.setCurrentIndex(page % 2)
        settle(app)
    window.refresh()
    assert window._step_states[7].state == 'ready'
    assert window.report.toPlainText() == report
    assert window.preview.toPlainText() == preview
