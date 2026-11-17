"""A two-control DFT card preserves settings, language state and preview."""
import numpy as np
import pytest
from PySide6.QtCore import Qt, QPoint, QEvent
from PySide6.QtGui import QTextDocument, QHelpEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel, QToolTip
from core.generator import generate_input
from core.project_io import save_project, load_project, export_bundle
from core.presets import capture_preset, apply_preset
from i18n.language_manager import language_manager
from tests.test_poisson_reference_ui import window
from tests.test_layout_workflow import wait_for_worker


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
@pytest.mark.parametrize('width', [1050,1480])
def test_card_placement_defaults_inline_controls_and_help(window, app, language, width):
    w = window
    language_manager().set_language(language)
    w.resize(width,900)
    w.nav.setCurrentRow(2)
    panel = w.dft_panel
    card = panel.surface_dipole_card
    master, direction = panel.surface_dipole,panel.surf_dip_dir
    w.stack.widget(2).ensureWidgetVisible(card)
    for _ in range(5):app.processEvents()
    assert panel.layout.indexOf(card) == panel.layout.indexOf(panel.poisson_card)+1
    assert panel.poisson_card.content.itemAt(1).widget() is panel.poisson_reference
    assert card.title_label.text() == ('Surface Dipole Correction' if language == 'en_US' else '表面偶极校正')
    assert not card.title_label.wordWrap()
    assert card.title_label.width() >= card.title_label.fontMetrics().horizontalAdvance(card.title_label.text())
    assert master.text() == ('Enable Surface Dipole Correction' if language == 'en_US' else '启用表面偶极校正')
    assert not master.isChecked() and direction.currentData() == 'Z' and not direction.isEnabled()
    assert [direction.itemData(i) for i in range(direction.count())] == ['X','Y','Z']
    assert master.parentWidget().layout().count() == 1
    assert master.width() >= master.sizeHint().width()
    label = next(label for label in card.findChildren(QLabel) if label.text() == 'SURF_DIP_DIR')
    assert label.buddy() is direction
    a,b = label.mapTo(card,QPoint()),direction.mapTo(card,QPoint())
    assert abs(a.y()+label.height()/2-b.y()-direction.height()/2) <= 1
    assert 144 <= direction.width() <= 240
    assert w.stack.widget(2).horizontalScrollBar().maximum() == 0
    assert not w.dirty
    document = QTextDocument();document.setHtml(card.help_icon.toolTip())
    text = document.toPlainText()
    assert ('asymmetric slab' if language == 'en_US' else '非对称表面') in text
    assert ('Does not replace nonperiodic' if language == 'en_US' else '不等同于关闭') in text
    icon = card.help_icon
    p = icon.rect().center()
    try:
        app.sendEvent(icon,QHelpEvent(QEvent.Type.ToolTip,p,icon.mapToGlobal(p)))
        assert QToolTip.isVisible() and QToolTip.text() == icon.toolTip()
    finally:
        QToolTip.hideText()


def test_toggle_and_direction_preserve_disabled_draft_and_existing_boundary_settings(window, app):
    w = window
    panel = w.dft_panel
    boundary = w.project.structure.model_dump(),w.project.dft.poisson_solver
    w.check_current_configuration();wait_for_worker(app,w)
    assert w._step_states[7].state == 'ready'
    panel.surface_dipole.setChecked(True)
    assert panel.surf_dip_dir.isEnabled() and w._step_states[7].state == 'unchecked'
    for direction in ['X','Y','Z','X']:
        panel.surf_dip_dir.setCurrentIndex(panel.surf_dip_dir.findData(direction))
        w.refresh()
        assert w.project.dft.surface_dipole_correction and w.project.dft.surf_dip_dir == direction
        assert 'SURF_DIP_DIR '+direction+'\n' in w.preview.toPlainText()
        assert w.preview.toPlainText() == generate_input(w.project)
        assert (w.project.structure.model_dump(),w.project.dft.poisson_solver) == boundary
    panel.surface_dipole.setChecked(False)
    w.refresh()
    assert not panel.surf_dip_dir.isEnabled() and panel.surf_dip_dir.currentData() == 'X'
    assert w.project.dft.surf_dip_dir == 'X'
    assert 'SURFACE_DIPOLE_CORRECTION' not in w.preview.toPlainText()
    assert 'SURF_DIP_DIR' not in w.preview.toPlainText()
    panel.surface_dipole.setChecked(True)
    w.refresh()
    assert panel.surf_dip_dir.currentData() == 'X' and 'SURF_DIP_DIR X\n' in w.preview.toPlainText()
    w.check_current_configuration();wait_for_worker(app,w)
    assert w._comprehensive_result.validation.ok and not w._comprehensive_result.validation.warnings
    assert w._step_states[2].state == w._step_states[7].state == 'ready'


@pytest.mark.parametrize('task', ['ENERGY','GEO_OPT','CELL_OPT','VIBRATIONAL_ANALYSIS'])
def test_language_save_load_preset_and_package_preserve_dipole_settings(window, app, tmp_path, task):
    w = window
    task_combo = w.global_panel.fields['global_settings.run_type'][0]
    task_combo.setCurrentIndex(task_combo.findData(task))
    panel = w.dft_panel
    panel.surface_dipole.setChecked(True)
    panel.surf_dip_dir.setCurrentIndex(panel.surf_dip_dir.findData('Y'))
    w.refresh();w.check_current_configuration();wait_for_worker(app,w)
    checked = w._comprehensive_result
    assert checked.validation.ok
    view = w.structure_panel.view
    view.zoom = 1.5
    view.pan_offset = np.array([.2,.3,.4])
    rotation = view.rotation.copy()
    snapshot = w.project.model_dump_json(),w.dirty,w._revision,w.preview.toPlainText()
    for language in ['en_US','zh_CN','en_US']:
        language_manager().set_language(language);app.processEvents()
        assert panel.surface_dipole.isChecked() and panel.surf_dip_dir.currentData() == 'Y'
        assert (w.project.model_dump_json(),w.dirty,w._revision,w.preview.toPlainText()) == snapshot
        assert w._comprehensive_result is checked and view.zoom == 1.5
        assert np.array_equal(view.rotation,rotation) and np.array_equal(view.pan_offset,[.2,.3,.4])
    path = tmp_path/'project.json';save_project(w.project,path)
    restored = load_project(path)
    assert restored == w.project
    w.load_into_ui(restored)
    assert panel.surface_dipole.isChecked() and panel.surf_dip_dir.isEnabled()
    assert panel.surf_dip_dir.currentData() == 'Y'
    preset = capture_preset(restored,'surface settings')
    assert apply_preset(restored,preset).project == restored
    package = export_bundle(restored,tmp_path/'package')
    text = package.read_text()
    assert 'SURFACE_DIPOLE_CORRECTION T\n' in text and 'SURF_DIP_DIR Y\n' in text
    assert 'SURF_DIP_POS' not in text and 'SURF_DIP_SWITCH' not in text
    assert 'POISSON_SOLVER PERIODIC' in text and 'RUN_TYPE '+task in text
