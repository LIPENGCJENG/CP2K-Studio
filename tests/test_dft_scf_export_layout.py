"""Targeted bilingual layouts keep the existing field/model bindings intact."""
import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QLabel, QCheckBox
from i18n.language_manager import language_manager
from core.generator import generate_input
from core.project_io import save_project, load_project, export_bundle
from ui.main_window import MainWindow
from tests.test_layout_workflow import wait_for_worker


def settle(app):
    for _ in range(6):
        app.processEvents()


@pytest.fixture(params=['en_US', 'zh_CN'])
def window(app, water, tmp_path, request):
    manager = language_manager()
    manager.set_language(request.param)
    window = MainWindow(preset_directory=tmp_path/'presets')
    window.load_into_ui(water)
    window.show()
    settle(app)
    yield window
    wait_for_worker(app, window)
    window.dirty = False
    window.close()
    app.processEvents()
    manager.set_language('zh_CN')


def rect_in(widget, parent):
    return QRect(widget.mapTo(parent, QPoint()), widget.size())


def assert_single_line_title(card):
    title, icon = card.title_label, card.help_icon
    assert not title.wordWrap() and '\n' not in title.text()
    assert title.width() >= title.sizeHint().width()
    assert title.height() == title.sizeHint().height()
    assert abs(title.geometry().center().y() - icon.geometry().center().y()) <= 1
    assert icon.x() - title.geometry().right() - 1 == 6
    assert card.rect().contains(title.geometry()) and card.rect().contains(icon.geometry())


@pytest.mark.parametrize('width', [1050, 1480])
def test_dft_inline_uks_and_single_line_method_title(window, app, width):
    window.resize(width, 900)
    window.nav.setCurrentRow(2)
    settle(app)
    panel = window.dft_panel
    assert_single_line_title(panel.cards[1])
    assert panel.cards[1].title_label.text() in ['DFT Method & XC Functional', 'DFT 方法与 XC 泛函']
    charge, multiplicity, uks = [panel.fields['dft.'+path][0] for path in ['charge','multiplicity','uks']]
    assert isinstance(uks, QCheckBox)
    assert uks.text() in ['Spin-polarized UKS', '自旋极化 UKS']
    grid = panel.cards[0].content.itemAt(0).widget()
    assert grid.columns == 3
    assert grid.items[2].layout().count() == 1
    assert grid.items[2].layout().itemAt(0).widget() is uks
    assert not any(label.text() == uks.text() for label in panel.cards[0].findChildren(QLabel))
    assert uks.width() >= uks.sizeHint().width()
    assert rect_in(charge, grid).right() < rect_in(multiplicity, grid).x()
    assert rect_in(multiplicity, grid).right() < rect_in(uks, grid).x()
    assert max(rect_in(field, grid).center().y() for field in [charge, multiplicity, uks]) - min(
        rect_in(field, grid).center().y() for field in [charge, multiplicity, uks]) <= 1
    assert window.stack.currentWidget().horizontalScrollBar().maximum() == 0


@pytest.mark.parametrize('width', [1050, 1480])
def test_scf_two_columns_equal_widths_and_inline_outer_toggle(window, app, width):
    window.resize(width, 900)
    window.nav.setCurrentRow(3)
    settle(app)
    panel = window.scf_panel
    eps, maximum, guess, outer_max, outer = [panel.fields['dft.scf.'+path][0] for path in
        ['eps_scf','max_scf','guess','outer_max_scf','outer_scf']]
    grid = panel.cards[0].content.itemAt(0).widget()
    assert grid.columns == 2 and len(grid.items) == 4
    rects = [rect_in(field, grid) for field in [eps, maximum, guess, outer_max, outer]]
    assert eps.width() == guess.width()
    assert maximum.width() == outer_max.width()
    assert rects[0].x() == rects[2].x()
    assert rects[1].x() == rects[3].x() == rects[4].x()
    assert rects[0].y() == rects[1].y()
    assert rects[2].y() == rects[3].y()
    assert rects[4].y() > rects[3].bottom()
    assert rects[2].x() < rects[3].x()
    assert [guess.itemData(i) for i in range(guess.count())] == ['ATOMIC','CORE','RANDOM']
    assert outer.text() in ['Enable OUTER_SCF', '启用 OUTER_SCF']
    assert not outer_max.isEnabled() and outer.isEnabled()
    assert outer.width() >= outer.sizeHint().width()
    outer_max.setText('17')
    outer.setChecked(True)
    assert outer_max.isEnabled() and outer_max.text() == '17'
    outer.setChecked(False)
    assert not outer_max.isEnabled() and outer_max.text() == '17'
    assert window.stack.currentWidget().horizontalScrollBar().maximum() == 0


@pytest.mark.parametrize('width', [1050, 1480])
def test_preset_single_line_title_and_sidebar_export_reminder_only(window, app, width):
    window.resize(width, 900)
    window.nav.setCurrentRow(7)
    settle(app)
    card = window.export_panel.preset_button.parentWidget()
    assert_single_line_title(card)
    assert card.title_label.text() in ['Save Current Settings as Preset', '保存当前设置为预设']
    assert window.export_panel.preset_button.text() in ['Save as Preset', '保存为预设']
    note = window.nav.parentWidget().layout().itemAt(3).widget()
    assert note.text() in ['Complete the configuration before exporting.', '完整配置后才能导出。']
    assert 'draft' not in note.text().lower() and '草稿' not in note.text()
    assert window.nav.count() == 8
    assert window.stack.currentWidget().horizontalScrollBar().maximum() == 0


@pytest.mark.parametrize('method', ['OT', 'DIAGONALIZATION'])
def test_layout_language_roundtrip_preserves_fields_check_and_exports(window, app, tmp_path, method):
    window.dft_panel.fields['dft.uks'][0].setChecked(True)
    panel = window.scf_panel
    panel.method.setCurrentText(method)
    panel.fields['dft.scf.guess'][0].setCurrentText('CORE')
    panel.outer_max.setText('17')
    panel.fields['dft.scf.outer_scf'][0].setChecked(True)
    window.refresh()
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[7].state == 'ready'
    before, inp = window.project.model_dump_json(), window.preview.toPlainText()
    check = window._comprehensive_result
    revision, dirty = window._revision, window.dirty
    fields = {path: pair[0] for path, pair in window.scf_panel.fields.items()}
    for language in ['zh_CN','en_US','zh_CN']:
        language_manager().set_language(language)
        for page in [2,3,7]:
            window.nav.setCurrentRow(page)
            window.resize(1050, 900)
            settle(app)
        assert window.project.model_dump_json() == before
        assert generate_input(window.project) == window.preview.toPlainText() == inp
        assert window._comprehensive_result is check and window._step_states[7].state == 'ready'
        assert (window._revision, window.dirty) == (revision, dirty)
        assert {path: pair[0] for path, pair in window.scf_panel.fields.items()} == fields
        assert panel.outer_max.text() == '17' and panel.outer_max.isEnabled()
        assert window.dft_panel.fields['dft.uks'][0].isChecked()
        electronic = window.dft_panel.cards[0].content.itemAt(0).widget()
        controls = [window.dft_panel.fields['dft.'+path][0] for path in ['charge','multiplicity','uks']]
        assert max(rect_in(field, electronic).center().y() for field in controls) - min(
            rect_in(field, electronic).center().y() for field in controls) <= 1
    path = tmp_path/'settings.json'
    save_project(window.project, path)
    reopened = load_project(path)
    assert reopened.model_dump_json() == before
    window.load_into_ui(reopened)
    assert panel.outer_max.text() == '17' and panel.outer_max.isEnabled()
    assert panel.fields['dft.scf.guess'][0].currentData() == 'CORE'
    assert window.dft_panel.fields['dft.uks'][0].isChecked()
    assert window.preview.toPlainText() == inp
    artifact = export_bundle(reopened, tmp_path/'package')
    assert artifact.is_file() and 'OUTER_SCF' in artifact.read_text()
    assert (artifact.parent/'run.sh').is_file()
