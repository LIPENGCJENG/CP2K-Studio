"""Language changes are presentation-only, including live dialogs/reports."""
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from PySide6 import QtWidgets as W
from PySide6.QtCore import QTimer, Qt
from i18n.language_manager import language_manager
from i18n.messages import Message, i18n_msg, i18n_render, i18n_join
from i18n import qt
from ui.main_window import MainWindow
from ui.coordinate_range_dialog import CoordinateRangeDialog
from ui.xml_dialog import XMLDialog
from ui.preset_dialogs import SavePresetDialog, ManagePresetsDialog
from ui.database_dialog import DatabaseDialog
from ui.recommendation_dialog import RecommendationDialog
from ui.widgets.help_icon import HelpIcon
from core.generator import generate_input
from core.project_io import save_project, load_project, export_bundle
from core.input_export import export_input
from core.comprehensive_check import ComprehensiveResult
from tests.test_layout_workflow import wait_for_worker

ROOT = Path(__file__).resolve().parents[1]
HAN = re.compile(r'[\u4e00-\u9fff]')


@pytest.fixture
def english(app):
    manager = language_manager().attach(app)
    manager.set_language('en_US')
    yield manager
    manager.set_language('zh_CN')  # Existing UI regressions assert Chinese labels.


@pytest.fixture
def window(english, water, tmp_path, app):
    value = MainWindow(preset_directory=tmp_path / 'presets')
    value.load_into_ui(water)
    value.show()
    app.processEvents()
    yield value
    wait_for_worker(app, value)
    value.dirty = False
    value.close()
    app.processEvents()


def test_default_english_in_each_fresh_process(tmp_path):
    code = '''
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from i18n.language_manager import language_manager
app=QApplication([])
w=MainWindow(preset_directory=__import__('sys').argv[1])
assert language_manager().language == 'en_US'
assert w.project_button.text() == 'Project'
assert w.language_selector.currentText() == 'English'
language_manager().set_language('zh_CN')
assert w.project_button.text() == '项目管理'
w.close()
'''
    for _ in range(2):
        result = subprocess.run([sys.executable, '-c', code, str(tmp_path)], cwd=ROOT, capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, result.stderr


def test_toolbar_navigation_pages_tooltips_and_menu_switch_in_place(window, english, app):
    w = window
    toolbar = w.findChild(W.QToolBar)
    assert toolbar.widgetForAction(toolbar.actions()[-1]) is w.language_control
    assert 140 <= w.language_selector.width() <= 170
    assert [w.language_selector.itemText(i) for i in range(2)] == ['English', '简体中文']
    widgets = (w.stack, w.structure_panel.view, w.preview, w.tabs)
    english_nav = [w.nav.item(i).text() for i in range(8)]
    assert english_nav[4] == '05  Basis Sets & Pseudopotentials'
    assert w.tabs.tabText(1) == 'Validation Report'
    assert w.project_actions['save'].text() == 'Save Project'
    tooltip = w.structure_view_card.help_icon.toolTip()
    assert 'Right-drag' in tooltip or 'right' in tooltip.lower()
    for lang in ['zh_CN', 'en_US']:
        w.language_selector.setCurrentIndex(w.language_selector.findData(lang))
        app.processEvents()
        for i in range(8):
            w.nav.setCurrentRow(i)
            app.processEvents()
            assert w.stack.currentIndex() == i
        assert widgets == (w.stack, w.structure_panel.view, w.preview, w.tabs)
        assert not w.project_button.toolTip() and not w.nav.item(4).toolTip()
    assert [w.nav.item(i).text() for i in range(8)] == english_nav
    assert w.structure_view_card.help_icon.toolTip() == tooltip
    english.set_language('zh_CN')
    assert w.project_button.text() == '项目管理'
    assert w.preset_button.text() == '预设管理'
    assert w.tabs.tabText(1) == '校验报告'
    assert w.language_label.text() == '语言：'
    assert w.nav.item(7).text() == '08  导出与预设'
    assert w.project_actions['save'].text() == '保存项目'


def test_all_pages_have_no_untranslated_chinese_in_english(window, app):
    for i in range(8):
        window.nav.setCurrentRow(i)
        app.processEvents()
        for child in window.findChildren(W.QWidget):
            if isinstance(child, (W.QLabel, W.QAbstractButton)) and child.isVisibleTo(window):
                assert not HAN.search(child.text()), (i, child.objectName(), child.text())
    assert not HAN.search(window.report.toPlainText())
    assert not HAN.search(window.structure_panel.summary.text())


def test_model_camera_draft_selection_and_input_unchanged(window, english, app):
    w = window
    tasks = w.global_panel.fields['global_settings.run_type'][0]
    tasks.setCurrentIndex(tasks.findData('GEO_OPT'))
    p = w.structure_panel
    p.select_atom_ids([1, 3])
    p.components.setCurrentText('XY')
    p.fix_button.click()
    w.refresh()
    view = p.view
    view.align_cell_axis('B')
    view.zoom = 1.7
    view.pan_offset = np.array([.2, -.4, .6])
    view.set_labels_visible(True)
    rotation = view.rotation.copy()
    before = w.project.model_dump_json()
    inp = generate_input(w.project).encode()
    preview = w.preview.toPlainText()
    revision, dirty = w._revision, w.dirty
    # A partially typed field must survive too; switching must not collect it.
    field = w.dft_panel.fields['dft.charge'][0]
    field.setText('-')
    w.timer.stop()
    revision, dirty = w._revision, w.dirty
    for lang in ['zh_CN', 'en_US', 'zh_CN', 'en_US']:
        english.set_language(lang)
        app.processEvents()
        assert field.text() == '-'
        assert w.project.model_dump_json() == before
        assert generate_input(w.project).encode() == inp
        assert w.preview.toPlainText() == preview
        assert (w._revision, w.dirty) == (revision, dirty)
        assert view.zoom == 1.7 and np.array_equal(view.rotation, rotation)
        assert np.array_equal(view.pan_offset, [.2, -.4, .6])
        assert view.selected_atom_ids == {1, 3} and view.fixed_atom_ids == {1, 3}
    field.setText('0')
    w.timer.stop()


def test_report_rerenders_without_revalidation_and_keeps_result(window, english, app, monkeypatch):
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[7].state == 'ready'
    result = window._comprehensive_result
    before = window.report.toPlainText()
    assert 'Configuration Completeness' in before and not HAN.search(before)
    status = [s.state for s in result.stages]
    monkeypatch.setattr(window, 'refresh', lambda: pytest.fail('language change refreshed/revalidated configuration'))
    monkeypatch.setattr('ui.main_window.comprehensive_check', lambda *a, **k: pytest.fail('check reran'))
    english.set_language('zh_CN')
    assert '[1] 配置完整性' in window.report.toPlainText()
    assert '错误：0' in window.report.toPlainText()
    assert window._comprehensive_result is result
    english.set_language('en_US')
    assert window.report.toPlainText() == before
    assert [s.state for s in result.stages] == status
    assert window._step_states[7].state == 'ready'


def test_structured_dynamic_errors_fallback_and_user_parameters(english):
    text = i18n_msg('Input file already exists: {p0}', code='studio.dd30262c49175ad0', p0='/tmp/我的计算.inp')
    assert text.code and text.params['p0'] == '/tmp/我的计算.inp'
    assert text.to_dict()['parameters']['p0'] == '/tmp/我的计算.inp'
    assert text.render() == 'Input file already exists: /tmp/我的计算.inp'
    english.set_language('zh_CN')
    assert '输入文件已存在' in text.render()
    assert '/tmp/我的计算.inp' in text.render()
    assert i18n_msg('Missing translation: {path}', code='test.missing', path='file.inp').render() == 'Missing translation: file.inp'
    joined = i18n_join('\n', [text, i18n_msg('Validation Failed', code='studio.cea8aae4ccdfeba2')])
    assert isinstance(joined, Message) and joined.render('en_US').endswith('Validation Failed')


def test_open_dialogs_and_native_buttons_change_without_losing_drafts(window, english, app):
    w = window
    dialogs = [XMLDialog(None, w), CoordinateRangeDialog(w.project.structure, w),
               SavePresetDialog(w.preset_store, w.project, w), ManagePresetsDialog(w.preset_store, w.project, w),
               DatabaseDialog(w.project.databases, w)]
    range_dialog, preset = dialogs[1:3]
    range_dialog.minimum.setText('-1.23456789e-2')
    preset.name.setText('用户预设 my draft')
    titles = [d.windowTitle() for d in dialogs]
    for d in dialogs:
        d.show()
    app.processEvents()
    english.set_language('zh_CN')
    assert all(d.windowTitle() != old for d, old in zip(dialogs, titles))
    assert range_dialog.buttons.button(W.QDialogButtonBox.StandardButton.Ok).text() == '选择原子'
    english.set_language('en_US')
    assert [d.windowTitle() for d in dialogs] == titles
    assert range_dialog.buttons.button(W.QDialogButtonBox.StandardButton.Ok).text() == 'Select Atoms'
    assert 'Cancel' in range_dialog.buttons.button(W.QDialogButtonBox.StandardButton.Cancel).text()
    assert preset.name.text() == '用户预设 my draft' and range_dialog.minimum.text() == '-1.23456789e-2'
    assert preset.category.currentData() == 'single_point'
    for d in dialogs:
        d.close()


def test_static_native_dialog_changes_while_open(english, app):
    seen = []
    def change():
        box = app.activeModalWidget()
        assert isinstance(box, W.QMessageBox)
        english.set_language('zh_CN')
        seen.append((box.windowTitle(), box.text()))
        box.accept()
    QTimer.singleShot(20, change)
    qt.QMessageBox.information(None, i18n_msg('Export Complete', code='studio.3e6886d17a1cf43c'),
        i18n_msg('Exported:\n{p0}', code='studio.4a1fb92e018434dd', p0='/tmp/用户.zip'))
    assert len(seen) == 1 and seen[0][1] == '已导出：\n/tmp/用户.zip'


def test_recommendations_live_translation_keeps_selection_and_continuous_apply(window, english, app, monkeypatch):
    dialog = RecommendationDialog(window.kind_panel)
    dialog.show()
    app.processEvents()
    dialog.element_filter.setCurrentIndex(dialog.element_filter.findData('O'))
    rows = [r for r in range(dialog.table.rowCount()) if not dialog.table.isRowHidden(r)]
    assert rows
    dialog.table.selectRow(rows[0])
    selected = dialog.selected_option()
    monkeypatch.setattr('ui.recommendation_dialog.recommend', lambda *a: pytest.fail('recommendations recalculated'))
    before = window.project.model_dump_json()
    english.set_language('zh_CN')
    assert dialog.progress.text() == '已配置 2/2 种元素'
    assert dialog.apply_button.text() == '应用'
    assert dialog.selected_option() == selected
    assert dialog.element_filter.currentData() == 'O'
    assert dialog.chosen_card.title_label.text() == '当前已选配置'
    assert window.project.model_dump_json() == before
    english.set_language('en_US')
    dialog.apply_button.click()
    assert dialog.isVisible() and dialog.status.text().startswith('Applied to KIND O')
    assert 'Basis Set:' in dialog.chosen_views['O'].basis.text()
    assert 'Pseudopotential:' in dialog.chosen_views['O'].potential.text()
    assert 'Configured 2/2 elements' == dialog.progress.text()
    dialog.close()


def test_project_and_export_artifacts_are_byte_identical_in_both_languages(window, english, tmp_path):
    w = window
    from core.atom_constraints import set_fixed_atoms
    w.project.global_settings.run_type = 'GEO_OPT'
    set_fixed_atoms(w.project.structure, [1], 'Z')
    content = []
    for lang in ['en_US', 'zh_CN']:
        english.set_language(lang)
        target = tmp_path / lang
        target.mkdir()
        save_project(w.project, target / 'project.json')
        restored = load_project(target / 'project.json')
        assert restored.model_dump() == w.project.model_dump()
        exported = export_input(restored, target / 'single.inp')
        export_bundle(restored, target / 'package')
        content.append({name:(target / 'package' / name).read_bytes() for name in ['input.inp','structure.xyz','run.sh','EXPORT_NOTES.txt','project.cp2kstudio.json']})
        assert exported.path.read_bytes() == generate_input(restored).encode()
    assert content[0] == content[1]


def test_ts_resources_complete_placeholders_and_qm_loading(english):
    from scripts.build_translations import templates
    sources = set(templates())
    for lang in ['en_US', 'zh_CN']:
        path = ROOT / 'i18n' / f'cp2kstudio_{lang}.ts'
        entries = {(m.findtext('comment'),m.findtext('source')):m.find('translation') for m in ET.parse(path).findall('.//message')}
        assert set(entries) == sources
        assert not language_manager().translator(lang).isEmpty()
        for (code, source), target in entries.items():
            assert target is not None and target.text and target.get('type') != 'unfinished', (code, source)
            assert set(re.findall(r'\{\w+\}', source)) == set(re.findall(r'\{\w+\}', target.text)), code


def test_input_options_retranslate_without_changing_value(english, app):
    captured = []
    title = i18n_msg('Open CP2K Studio Project', code='studio.a41dc714971719a0')
    options = [i18n_msg('Custom', code='studio.4eafa9e925b30bcd'), i18n_msg('Single Point', code='studio.6257cf612978bdc4')]
    def change_input():
        dialog = app.activeModalWidget()
        assert isinstance(dialog, W.QInputDialog)
        combo = dialog.findChild(W.QComboBox)
        combo.setCurrentIndex(1)
        english.set_language('zh_CN')
        captured.append([combo.itemText(i) for i in range(combo.count())])
        dialog.accept()
    QTimer.singleShot(30, change_input)
    value, accepted = qt.QInputDialog.getItem(None, title, title, options, 0, False)
    assert accepted and value == options[1]
    assert captured[-1] == ['自定义', '单点能']


def test_error_report_and_range_errors_retranslate_without_rechecking(window, english, app):
    from core.models import Project
    window.load_into_ui(Project())
    before = window.project.model_dump_json()
    assert 'import a nonempty structure' in window.report.toPlainText()
    english.set_language('zh_CN')
    assert '请导入非空结构' in window.report.toPlainText()
    english.set_language('en_US')
    assert window.project.model_dump_json() == before
    dialog = CoordinateRangeDialog(None, window)
    dialog.minimum.setText('not a number')
    dialog.maximum.setText('5')
    dialog.accept()
    assert dialog.result() == 0 and not HAN.search(dialog.error.text())
    english.set_language('zh_CN')
    assert HAN.search(dialog.error.text())
    assert dialog.minimum.text() == 'not a number'
    dialog.close()


def test_3d_paint_and_dynamic_tooltip_update_without_recreating_scene(window, english, app):
    view = window.structure_panel.view
    window.structure_panel.select_atom_ids([1])
    view.update()
    app.processEvents()
    image_before = view.grab().toImage()
    points = view._points.copy()
    help_before = window.kind_panel.database_card.help_icon.accessibleDescription()
    english.set_language('zh_CN')
    app.processEvents()
    assert view.grab().toImage() != image_before  # translated atom/selected count
    assert '已选择' in window.structure_panel.fixed_count.text()
    assert '条记录' in window.kind_panel.database_card.help_icon.accessibleDescription()
    assert np.array_equal(points, view._points)
    assert not view.toolTip()
    english.set_language('en_US')
    assert window.kind_panel.database_card.help_icon.accessibleDescription() == help_before


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_narrow_window_keeps_database_buttons_inside_card(window, english, app, language):
    english.set_language(language)
    window.resize(1050, 650)
    window.nav.setCurrentRow(4)
    for _ in range(6):
        app.processEvents()
    scroll = window.stack.currentWidget()
    assert scroll.horizontalScrollBar().maximum() == 0
    card = window.kind_panel.database_card
    buttons = [button for button in card.findChildren(W.QPushButton) if button.isVisibleTo(card)]
    assert len(buttons) == 2
    for button in buttons:
        assert button.width() >= button.minimumSizeHint().width()
        assert card.rect().contains(button.mapTo(card, button.rect().topLeft()))
        assert card.rect().contains(button.mapTo(card, button.rect().bottomRight()))


def test_simplified_import_units_and_quoted_run_hint_switch_live(window, english, app):
    from ui.widgets.section_card import SectionCard
    from core.run_script_generator import generate_run_script
    card = window.structure_panel.findChildren(SectionCard)[0]
    hint = window.input_preview_pane.layout().itemAt(2).widget()
    editor, scrollbar = window.preview, window.preview.verticalScrollBar()
    before = window.project.model_dump_json()
    inp = editor.toPlainText()
    script = generate_run_script(window.project.run_environment)
    dirty, revision = window.dirty, window._revision
    for language, title, units, note in [
        ('en_US', 'Structure Import', 'Coordinates in Å',
         'Packages include run.sh; run "bash run.sh" in the target terminal. Standalone INP export does not generate a script.'),
        ('zh_CN', '结构导入', '坐标单位 Å',
         '计算包自动包含 run.sh；在目标终端执行 "bash run.sh"。单独导出 INP 不生成脚本。'),
        ('en_US', 'Structure Import', 'Coordinates in Å',
         'Packages include run.sh; run "bash run.sh" in the target terminal. Standalone INP export does not generate a script.')]:
        english.set_language(language)
        app.processEvents()
        assert card.title_label.text() == title
        assert hint.text() == units
        assert window.export_panel.run_note.text() == note
        assert note.count('"') == 2
        assert editor is window.preview and editor.isReadOnly()
        assert editor.verticalScrollBar() is scrollbar
        assert editor.highlighter.document() is editor.document()
        assert editor.toPlainText() == inp == generate_input(window.project)
        assert window.project.model_dump_json() == before
        assert (window.dirty, window._revision) == (dirty, revision)
        assert generate_run_script(window.project.run_environment) == script
        assert window.structure_panel.summary.text()
