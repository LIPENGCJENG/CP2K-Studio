"""Task captions are presentation; CP2K enums remain the persisted identity."""
import json
import numpy as np
import pytest
from PySide6.QtCore import Qt
from core.generator import generate_input
from core.project_io import save_project, load_project, export_bundle
from core.presets import capture_preset, apply_preset
from i18n.language_manager import language_manager
from tests.test_poisson_reference_ui import window


TASKS = ['ENERGY','GEO_OPT','CELL_OPT','MD','VIBRATIONAL_ANALYSIS']
ENGLISH = ['Energy','Geometry optimization','Cell optimization','Ab initio molecular dynamics','Vibration Analysis']
CHINESE = ['单点能计算','几何结构优化','晶胞结构优化','第一性原理分子动力学','振动分析']


@pytest.mark.parametrize('language,captions', [('en_US',ENGLISH),('zh_CN',CHINESE)])
@pytest.mark.parametrize('width', [1050,1480])
def test_exact_names_order_and_readable_popup_at_existing_control_size(window, app, language, captions, width):
    w = window
    w.resize(width,900);w.nav.setCurrentRow(1)
    language_manager().set_language(language)
    for _ in range(5):app.processEvents()
    combo = w.global_panel.fields['global_settings.run_type'][0]
    assert [combo.itemData(i) for i in range(combo.count())] == TASKS
    assert [combo.itemText(i) for i in range(combo.count())] == captions
    assert not combo.isEditable()
    original_size = combo.size()
    for task, caption in zip(TASKS,captions):
        combo.setCurrentIndex(combo.findData(task));w.refresh();app.processEvents()
        assert combo.currentText() == caption and combo.currentData() == task
        assert combo.size() == original_size
        combo.showPopup();app.processEvents()
        try:
            view = combo.view()
            for index in range(combo.count()):
                rect = view.visualRect(combo.model().index(index,0))
                assert rect.width() >= view.fontMetrics().horizontalAdvance(combo.itemText(index)) + 8
            assert view.horizontalScrollBar().maximum() == 0
        finally:
            combo.hidePopup();app.processEvents()


@pytest.mark.parametrize('task', TASKS)
def test_enum_task_page_language_save_preset_and_export_remain_consistent(window, app, validator, tmp_path, task):
    w = window
    combo = w.global_panel.fields['global_settings.run_type'][0]
    combo.setCurrentIndex(combo.findData(task));w.refresh()
    panel = {'CELL_OPT':w.cell_opt_panel,'MD':w.md_panel,'VIBRATIONAL_ANALYSIS':w.vibrational_panel}.get(task,w.motion_panel)
    assert w.task_panel.stack.currentWidget() is panel
    view = w.structure_panel.view
    view.set_labels_visible(True);view.zoom=1.7;view.pan_offset=np.array([.1,.2,.3])
    rotation = view.rotation.copy()
    snapshot = w.project.model_dump_json(),w.dirty,w._revision,w.preview.toPlainText()
    for language,captions in [('en_US',ENGLISH),('zh_CN',CHINESE),('en_US',ENGLISH)]:
        language_manager().set_language(language);app.processEvents()
        assert combo.currentData() == task and combo.currentText() == captions[TASKS.index(task)]
        assert (w.project.model_dump_json(),w.dirty,w._revision,w.preview.toPlainText()) == snapshot
        assert w.task_panel.stack.currentWidget() is panel
        assert view.show_labels and view.zoom==1.7 and np.array_equal(view.rotation,rotation)
        assert np.array_equal(view.pan_offset,[.1,.2,.3])
    assert w.preview.toPlainText() == generate_input(w.project)
    parsed = validator.parse(w.preview.toPlainText())
    assert parsed.ok,parsed.errors
    assert parsed.tree['+global']['run_type'] == task.lower()
    path = tmp_path/'project.json';save_project(w.project,path)
    assert json.loads(path.read_text())['global_settings']['run_type'] == task
    restored = load_project(path);w.load_into_ui(restored)
    assert combo.currentData() == task and w.preview.toPlainText() == snapshot[3]
    preset = capture_preset(restored,'caption-independent task')
    assert preset.parameters['global_settings']['run_type'] == task
    assert apply_preset(restored,preset).project.global_settings.run_type == task
    package = export_bundle(restored,tmp_path/'package')
    assert f'RUN_TYPE {task}\n' in package.read_text()
    assert validator.parse(package.read_text(),package.parent).ok
