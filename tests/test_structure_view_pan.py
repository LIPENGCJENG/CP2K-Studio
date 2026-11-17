"""Camera-only panning and depth-correct atom picking in the existing renderer."""
import numpy as np
import pytest
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent
from PySide6.QtGui import QMouseEvent, QWheelEvent, QContextMenuEvent, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from core.models import Structure
from core.generator import generate_input
from core.project_io import export_bundle, load_project
from core.input_export import export_input
from core.validator import InputValidator
from ui.structure_view import StructureView
from ui.main_window import MainWindow
from tests.test_layout_workflow import wait_for_worker


def settle(app):
    for _ in range(4):
        app.processEvents()


def drag(view, button, dx, dy, start=QPoint(150, 120)):
    QTest.mousePress(view, button, pos=start)
    for part in [1/3, 2/3, 1]:
        QTest.mouseMove(view, start + QPoint(round(dx*part), round(dy*part)), delay=1)
    QTest.mouseRelease(view, button, pos=start + QPoint(dx, dy))


@pytest.fixture
def view(app, water):
    value = StructureView()
    value.resize(640, 480)
    value.set_structure(water.structure)
    value.show()
    settle(app)
    yield value
    value.close()


@pytest.mark.parametrize('perspective', [False, True])
@pytest.mark.parametrize('dx,dy', [(-30, 0), (30, 0), (0, -30), (0, 30), (-24, 18), (24, -18)])
def test_pan_follows_all_screen_directions_without_rotation_or_structure_change(view, perspective, dx, dy):
    view.set_perspective(perspective)
    before_structure = view.structure.model_dump()
    before_points = view._points.copy()
    before_rotation = view.rotation.copy()
    before_center = view._center.copy()
    _, before_screen, factors, _ = view.screen_projection()
    drag(view, Qt.MouseButton.RightButton, dx, dy)
    _, after_screen, after_factors, _ = view.screen_projection()
    # Perspective uses the same camera-plane displacement at each depth.
    # At the target plane (factor=1) the sensitivity is exactly one pixel/pixel.
    assert np.allclose(after_screen-before_screen, np.array([dx, dy])*factors[:, None])
    assert np.allclose(factors, after_factors)
    assert np.array_equal(view.rotation, before_rotation)
    assert np.array_equal(view._points, before_points)
    assert np.array_equal(view._center, before_center)
    assert view.structure.model_dump() == before_structure
    assert view.last_pos is None and view._drag_button == Qt.MouseButton.NoButton


@pytest.mark.parametrize('zoom', [.2, 1, 5])
@pytest.mark.parametrize('perspective', [False, True])
def test_pan_sensitivity_is_consistent_across_zoom_and_resize(view, zoom, perspective):
    view.zoom = zoom
    view.set_perspective(perspective)
    for width, height in [(420, 300), (800, 600)]:
        view.resize(width, height)
        before = view.screen_projection()
        drag(view, Qt.MouseButton.RightButton, 20, 12)
        after = view.screen_projection()
        assert np.allclose(after[1]-before[1], np.array([20, 12])*before[2][:, None])
        assert view.zoom == zoom


def test_release_and_button_conflicts_never_rotate_or_select_during_pan(view, app):
    clicks = []
    view.atom_clicked.connect(lambda *args: clicks.append(args))
    view.set_selected_atoms([1, 3])
    rotation = view.rotation.copy()
    QTest.mousePress(view, Qt.MouseButton.RightButton, pos=QPoint(150, 120))
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=QPoint(150, 120))
    QTest.mouseMove(view, QPoint(180, 140), delay=1)
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=QPoint(180, 140))
    assert view._drag_button == Qt.MouseButton.RightButton
    QTest.mouseRelease(view, Qt.MouseButton.RightButton, pos=QPoint(180, 140))
    offset = view.pan_offset.copy()
    event = QMouseEvent(QEvent.Type.MouseMove, QPointF(250, 180), QPointF(250, 180),
                       Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    app.sendEvent(view, event)
    assert np.array_equal(view.pan_offset, offset)
    assert np.array_equal(view.rotation, rotation)
    assert view.selected_atom_ids == {1, 3} and not clicks
    assert view.last_pos is None
    assert view.contextMenuPolicy() == Qt.ContextMenuPolicy.PreventContextMenu
    app.sendEvent(view, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(100, 100),
                                        view.mapToGlobal(QPoint(100, 100))))
    assert QApplication.activePopupWidget() is None


def test_small_pan_starts_immediately_and_new_gesture_has_no_jump(view, app):
    before = view.screen_projection()[1]
    drag(view, Qt.MouseButton.RightButton, 1, 1)
    assert np.allclose(view.screen_projection()[1]-before, [1, 1])
    previous = view.screen_projection()[1]
    drag(view, Qt.MouseButton.RightButton, -2, 1, start=QPoint(240, 150))
    assert np.allclose(view.screen_projection()[1]-previous, [-2, 1])
    QTest.mousePress(view, Qt.MouseButton.RightButton, pos=QPoint(140, 120))
    offset = view.pan_offset.copy()
    # QWidget filters buttonless moves when mouse tracking is disabled; call
    # the handler directly to exercise recovery from a missing release.
    view.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, QPointF(180, 160), QPointF(180, 160),
        Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
    assert view.last_pos is None and np.array_equal(view.pan_offset, offset)
    QTest.mouseRelease(view, Qt.MouseButton.RightButton, pos=QPoint(180, 160))


def axes_image(view):
    image = QImage(view.size(), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    view._paint_axes(painter)
    painter.end()
    return image


def test_atoms_cell_markers_move_together_and_xyz_indicator_stays_fixed(view):
    view.structure.fixed_atoms = [{'atom_id': 1, 'components': 'XYZ'}]
    view.set_structure(view.structure)
    view.set_selected_atoms([1, 3])
    image = view.grab().toImage()
    axes = axes_image(view)
    before = view.screen_projection()[1]
    drag(view, Qt.MouseButton.RightButton, 42, -24)
    after = view.screen_projection()[1]
    assert np.allclose(after-before, [42, -24])  # all atoms plus all eight cell corners
    assert image != view.grab().toImage()
    assert axes == axes_image(view)
    assert view.fixed_atom_ids == {1} and view.selected_atom_ids == {1, 3}


def test_blank_left_drag_wheel_axis_and_reset_preserve_existing_controls(view, app):
    drag(view, Qt.MouseButton.RightButton, 35, 20)
    offset = view.pan_offset.copy()
    rotation = view.rotation.copy()
    drag(view, Qt.MouseButton.LeftButton, 45, 30)
    assert not np.allclose(rotation, view.rotation)
    assert np.array_equal(view.pan_offset, offset)
    for axis in 'ABC':
        view.axis_buttons[axis].click()
        transformed = view.rotation @ np.array(view.structure.cell['ABC'.index(axis)])
        assert np.allclose(transformed[:2], 0)
        assert np.array_equal(view.pan_offset, offset)
    app.sendEvent(view, QWheelEvent(QPointF(180, 120), QPointF(180, 120), QPoint(), QPoint(0, 120),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False))
    assert view.zoom > 1
    view.reset_button.click()
    assert np.array_equal(view.pan_offset, np.zeros(3))
    assert view.zoom == 1 and np.allclose(view.rotation, view.default_rotation())


def test_hit_testing_uses_topmost_atom_and_large_stable_id_after_pan(view):
    view.set_structure(Structure(symbols=['H', 'O'], positions=[(0, 0, 0), (0, 0, 1)],
        cell=((2, 0, 0), (0, 2, 0), (0, 0, 2)), atom_ids=[10, 10_000_000_000]))
    view.rotation = np.eye(3)
    drag(view, Qt.MouseButton.RightButton, 35, -10)
    point = QPointF(*view.screen_projection()[1][1])
    assert view.atom_at(point) == 10_000_000_000
    clicks = []
    view.atom_clicked.connect(lambda atom_id, modifiers: clicks.append(atom_id))
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=point.toPoint())
    assert clicks == [10_000_000_000]
    rotation = view.rotation.copy()
    drag(view, Qt.MouseButton.LeftButton, 25, 20, start=point.toPoint())
    assert len(clicks) == 1  # dragging an atom does not select/move it or rotate the scene
    assert np.array_equal(view.rotation, rotation)


def test_extreme_perspective_pan_then_rotation_remains_finite_and_resettable(view):
    view.set_perspective(True)
    drag(view, Qt.MouseButton.RightButton, 1000, 500)
    view.align_cell_axis('A')
    _, screen, factor, _ = view.screen_projection()
    assert np.all(np.isfinite(screen)) and np.all(np.isfinite(factor))
    assert not view.grab().isNull()
    view.reset_button.click()
    assert np.allclose(view.pan_offset, 0)


@pytest.fixture
def window(app, water, tmp_path):
    water.global_settings.run_type = 'GEO_OPT'
    value = MainWindow(preset_directory=tmp_path / 'presets')
    value.load_into_ui(water)
    value.show()
    settle(app)
    yield value
    wait_for_worker(app, value)
    value.dirty = False
    value.close()


def visible_atom_point(view, atom_id):
    index = view.structure.atom_ids.index(atom_id)
    point = QPointF(*view.screen_projection()[1][index]).toPoint()
    assert view.atom_at(QPointF(point)) == atom_id
    return point


def test_view_click_updates_table_by_identity_and_does_not_dirty_project(window):
    panel = window.structure_panel
    view = panel.view
    window.dirty = False
    before = window.project.model_dump()
    drag(view, Qt.MouseButton.RightButton, 20, -15)
    point = visible_atom_point(view, 2)
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=point)
    assert panel.selected_atom_ids() == {2} and view.selected_atom_ids == {2}
    second = visible_atom_point(view, 3)
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, pos=second)
    assert panel.selected_atom_ids() == {2, 3}
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, pos=second)
    assert panel.selected_atom_ids() == {2}
    assert window.project.model_dump() == before and not window.dirty
    panel.components.setCurrentText('Z')
    panel.fix_button.click()
    assert 'COMPONENTS_TO_FIX Z' in window.preview.toPlainText() and 'LIST 2' in window.preview.toPlainText()


def test_pan_preserves_project_check_navigation_fixed_input_and_export(window, app, tmp_path):
    panel = window.structure_panel
    view = panel.view
    panel.select_atom_ids([1, 3])
    panel.components.setCurrentText('Z')
    panel.fix_button.click()
    window.project_path = tmp_path / 'project.json'
    assert window.save()
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[7].state == 'ready'
    before = window.project.model_dump()
    revision = window._revision
    text = window.preview.toPlainText()
    report = window.report.toPlainText()
    drag(view, Qt.MouseButton.RightButton, 40, -28)
    offset = view.pan_offset.copy()
    view.zoom = 1.4
    rotation = view.rotation.copy()
    for index in range(8):
        window.nav.setCurrentRow(index)
        settle(app)
        assert np.array_equal(view.pan_offset, offset) and view.zoom == 1.4
        assert np.array_equal(view.rotation, rotation)
    window.refresh()
    assert window.project.model_dump() == before and window._revision == revision and not window.dirty
    assert window.preview.toPlainText() == text == generate_input(window.project)
    assert window.report.toPlainText() == report and window._step_states[7].state == 'ready'
    assert view.selected_atom_ids == {1, 3} and view.fixed_atom_ids == {1, 3}
    assert window.save()
    assert load_project(window.project_path).model_dump() == before
    single = export_input(window.project, tmp_path / 'single.inp').path
    assert single.read_text() == text
    bundle = export_bundle(window.project, tmp_path / 'bundle')
    parsed = InputValidator().parse(bundle.read_text(), bundle.parent)
    assert parsed.ok
    assert parsed.tree['+motion']['+constraint']['+fixed_atoms'][0]['list'] == [(1, 3)]
    assert load_project(bundle.parent / 'project.cp2kstudio.json').structure == window.project.structure
