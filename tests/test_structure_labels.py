"""Visible glyph centering, depth occlusion, and bilingual import captions."""
import numpy as np
import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QImage, QFontMetricsF, QPainter, QFont, QColor
from PySide6.QtWidgets import QStyleOptionButton, QStyle
from core.models import Structure
from core.generator import generate_input
from core.structure import SUPPORTED_STRUCTURE_EXTENSIONS, structure_file_filter
from i18n.messages import i18n_render
from i18n.language_manager import language_manager
from ui.structure_view import StructureView
from ui.widgets.structure_import_button import StructureImportButton
from tests.test_xsd_ui import window, import_file
from tests.test_structure_view_pan import drag


def pixels(view, labels):
    view.set_labels_visible(labels)
    image = view.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    data = np.frombuffer(image.constBits(), dtype=np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)
    return data[:, :image.width(), :3].copy()


@pytest.mark.parametrize('symbol', ['H','O','Ti','Ba','Li'])
def test_element_glyphs_use_bold_at_the_existing_pixel_size(app, monkeypatch, symbol):
    import ui.structure_view as module
    original = module.QPainterPath
    fonts = []
    class PathSpy(original):
        def addText(self, point, font, text):
            fonts.append((QFont(font),text))
            return super().addText(point,font,text)
    monkeypatch.setattr(module,'QPainterPath',PathSpy)
    image = QImage(100,100,QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.white)
    painter = QPainter(image)
    before = QFont(painter.font())
    try:
        module.StructureView._paint_atom_label(painter,QPointF(50,50),20,symbol,QColor('white'))
        assert len(fonts)==1 and fonts[0][1]==symbol
        assert fonts[0][0].bold() and fonts[0][0].pixelSize()==12
        assert painter.font()==before  # Axis/status text is unaffected.
    finally:
        painter.end()


@pytest.fixture
def view(app):
    value = StructureView()
    value.resize(720, 480)
    value.set_structure(Structure(symbols=['H','O','Ti','N'],
        positions=[(0,3,3),(2,3,3),(4,3,3),(6,3,3)], cell=((6,0,0),(0,6,0),(0,0,6))))
    value.show()
    app.processEvents()
    yield value
    value.close()
    value.deleteLater()
    app.processEvents()


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
@pytest.mark.parametrize('width', [260, 346, 600])
def test_import_caption_fits_without_changing_button_height(app, language, width):
    manager = language_manager()
    manager.set_language(language)
    from i18n.messages import i18n_msg
    button = StructureImportButton(i18n_msg('Import Structure （{formats}）', code='structure.import_button',
                                           formats=' / '.join(SUPPORTED_STRUCTURE_EXTENSIONS)))
    try:
        button.resize(width, 34)
        button.show()
        app.processEvents()
        option = QStyleOptionButton()
        button.initStyleOption(option)
        contents = button.style().subElementRect(QStyle.SubElement.SE_PushButtonContents, option, button)
        assert QFontMetricsF(button.caption_font(contents.width())).horizontalAdvance(button.text()) <= contents.width()
        assert button.height() == 34 and not button.grab().isNull()
        expected = ('Import Structure （' if language == 'en_US' else '导入结构（') + ' / '.join(SUPPORTED_STRUCTURE_EXTENSIONS) + '）'
        assert button.text() == expected
    finally:
        button.close()
        button.deleteLater()
        app.processEvents()
        manager.set_language('zh_CN')


@pytest.mark.parametrize('perspective', [False, True])
@pytest.mark.parametrize('action', ['initial', 'rotate', 'pan', 'zoom', 'reset'])
def test_rendered_labels_are_centered_inside_each_sphere_after_camera_actions(view, perspective, action):
    view.rotation = np.eye(3)
    view.set_perspective(perspective)
    view.zoom = 2
    if action == 'rotate':
        view._rotate(QPointF(12, -8))
    elif action == 'pan':
        drag(view, Qt.MouseButton.RightButton, 23, -15)
    elif action == 'zoom':
        view.zoom = 1.5
    elif action == 'reset':
        view.pan_offset = np.array([.2, -.2, 0])
        view.reset_button.click()
    before_structure = view.structure.model_dump_json()
    before = pixels(view, False)
    after = pixels(view, True)
    _, screen, factors, scale = view.screen_projection()
    for index in range(4):
        x, y = screen[index]
        radius = view.atom_radius(index, scale, factors[index])
        left, top = int(x-radius-2), int(y-radius-2)
        right, bottom = int(x+radius+3), int(y+radius+3)
        mask = np.any(before[top:bottom, left:right] != after[top:bottom, left:right], axis=2)
        ys, xs = np.nonzero(mask)
        assert len(xs), (action, index)
        assert abs((xs.min()+xs.max())/2 + left - x) <= 1.1
        assert abs((ys.min()+ys.max())/2 + top - y) <= 1.1
        assert np.all((xs+left-x)**2 + (ys+top-y)**2 <= (radius+.8)**2)
        colors = after[top:bottom, left:right][mask]
        if index in [0, 1, 2]:  # H/O/Ti have light enough fills for dark glyphs.
            assert np.any(colors.max(axis=1) < 100)
        else:
            assert np.any(colors.min(axis=1) > 200)
    assert view.structure.model_dump_json() == before_structure
    assert np.array_equal(pixels(view, False), before)


def test_small_spheres_do_not_have_overflowing_or_offset_glyphs(view):
    view.rotation = np.eye(3)
    view.zoom = .15
    before, after = pixels(view, False), pixels(view, True)
    _, screen, factors, scale = view.screen_projection()
    changed = np.any(before != after, axis=2)
    tools = view.tools.geometry()
    changed[tools.top():tools.bottom()+1, tools.left():tools.right()+1] = False
    ys, xs = np.nonzero(changed)
    assert len(xs)
    inside = np.zeros(len(xs), dtype=bool)
    for index in range(4):
        radius = view.atom_radius(index, scale, factors[index])
        assert 3 <= radius <= 4.5
        inside |= (xs-screen[index,0])**2 + (ys-screen[index,1])**2 <= (radius+.8)**2
    assert inside.all()


def test_front_sphere_occludes_back_labels_and_picking_stays_on_front_atom(view):
    def render(back_symbol, labels):
        view.set_structure(Structure(symbols=[back_symbol, 'H'], positions=[(3,3,2),(3,3,4)],
            cell=((6,0,0),(0,6,0),(0,0,6)), atom_ids=[11,22]))
        view.rotation = np.eye(3)
        view.zoom = 4
        view.set_selected_atoms([22])
        image = pixels(view, labels)
        _, screen, factors, scale = view.screen_projection()
        center = QPointF(*screen[1])
        assert view.atom_at(center) == 22
        half = int(view.atom_radius(1, scale, factors[1]) / 1.5)
        x, y = int(center.x()), int(center.y())
        return image[y-half:y+half, x-half:x+half]
    oxygen = render('O', True)
    titanium = render('Ti', True)
    hidden = render('Ti', False)
    assert np.array_equal(oxygen, titanium)
    assert not np.array_equal(titanium, hidden)


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
def test_import_hints_and_language_switch_preserve_selection_view_box_and_input(window, app, monkeypatch, language):
    import_file(window, monkeypatch, 'h2o_ms23.xsd')
    panel, view = window.structure_panel, window.structure_panel.view
    panel.select_atom_ids([2])
    panel.fix_button.click()
    view.set_labels_visible(True)
    view.zoom = 1.4
    view.pan_offset = np.array([.2, .1, 0])
    rotation = view.rotation.copy()
    snapshot = window.project.model_dump_json(), window._revision, window.dirty
    language_manager().set_language(language)
    app.processEvents()
    expected = ('Non-periodic Molecule. Check vacuum and Poisson boundaries.\nEnter a simulation box manually or generate one using the button below.' if language == 'en_US'
                else '非周期分子。请检查真空及 Poisson 边界要求。\n请手动填写计算盒，或使用下方按钮生成。')
    assert panel.import_notice.text() == expected
    assert 'h2o_ms23.xsd' in panel.summary.text()
    assert panel.box_button.isVisible()
    assert (window.project.model_dump_json(), window._revision, window.dirty) == snapshot
    assert view.show_labels and view.zoom == 1.4 and np.array_equal(view.rotation, rotation)
    assert np.array_equal(view.pan_offset, [.2,.1,0])
    assert view.selected_atom_ids == {2} and view.fixed_atom_ids == {2}
    filters = i18n_render(structure_file_filter()).split(';;')
    assert len(filters) == 6
    for extension in SUPPORTED_STRUCTURE_EXTENSIONS:
        assert f'*{extension}' in filters[0] and f'*{extension.upper()}' in filters[0]
    assert all('(' in item and ')' in item for item in filters)
    from tests.simulation_box_helpers import mock_box_dialog
    mock_box_dialog(monkeypatch, margin=10, mode='CUBIC')
    panel.box_button.click()
    solver = window.dft_panel.fields['dft.poisson_solver'][0]
    solver.setCurrentIndex(solver.findData('WAVELET'))
    window.refresh()
    assert window.preview.toPlainText() == generate_input(window.project)
    assert not window._validation.errors and panel.box_button.isVisible()
    inp = window.preview.toPlainText()
    language_manager().set_language('zh_CN' if language == 'en_US' else 'en_US')
    app.processEvents()
    assert window.preview.toPlainText() == inp == generate_input(window.project)
