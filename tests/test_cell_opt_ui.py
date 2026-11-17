"""Live task switching, bilingual cell optimization, checks and saved state."""
import pytest
from PySide6.QtWidgets import QLabel, QFileDialog
from core.generator import generate_input
from core.presets import capture_preset
from i18n.language_manager import language_manager
from ui.widgets.status_badge import STATUS_ROLE
from tests.test_cell_optimization import crystal
from tests.test_vibrational_ui import window, choose_task
from tests.test_layout_workflow import wait_for_worker


@pytest.fixture
def cell_window(window, crystal, app):
    window.load_into_ui(crystal)
    window.nav.setCurrentRow(5)
    app.processEvents()
    return window


def test_task_dropdown_and_independent_page_drafts(cell_window):
    w = cell_window
    panel = w.cell_opt_panel
    combo = w.global_panel.fields['global_settings.run_type'][0]
    assert [combo.itemData(i) for i in range(combo.count())] == ['ENERGY', 'GEO_OPT', 'CELL_OPT', 'MD', 'VIBRATIONAL_ANALYSIS']
    assert w.nav.count() == w.stack.count() == 8
    assert w.task_panel.stack.currentWidget() is panel
    assert 'cell_opt.type' not in panel.fields
    assert panel.cards[0].findChild(QLabel, 'fieldLabel').buddy() is panel.fields['cell_opt.optimizer'][0]
    assert 'TYPE DIRECT_CELL_OPT' not in w.preview.toPlainText()
    panel.fields['cell_opt.max_iter'][0].setText('350')
    choose_task(w, 'GEO_OPT')
    assert w.project.cell_opt.max_iter == 350
    w.motion_panel.fields['motion.max_iter'][0].setText('222')
    choose_task(w, 'VIBRATIONAL_ANALYSIS')
    w.vibrational_panel.fields['vibrational.dx'][0].setText('0.005')
    choose_task(w, 'CELL_OPT')
    assert w.project.motion.max_iter == 222 and w.project.vibrational.dx == .005
    assert panel.fields['cell_opt.max_iter'][0].text() == '350'
    panel.fields['cell_opt.max_force'][0].setText('invalid')
    w.refresh()
    assert not w.export_action.isEnabled()
    choose_task(w, 'ENERGY')
    assert w.export_action.isEnabled() and w._step_states[5].state == 'na'
    assert panel.fields['cell_opt.max_force'][0].text() == 'invalid'
    choose_task(w, 'CELL_OPT')
    assert not w.export_action.isEnabled() and w._step_states[5].state == 'error'


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
@pytest.mark.parametrize('width', [1050,1480])
def test_cell_page_localization_and_resizing_keep_parameters_and_view(cell_window, app, language, width):
    w = cell_window
    before = w.project.model_dump_json(), w.preview.toPlainText(), w.dirty, w._revision
    panel = w.cell_opt_panel
    identities = {key:id(value[0]) for key,value in panel.fields.items()}
    for target in [language, 'zh_CN' if language == 'en_US' else 'en_US', language]:
        language_manager().set_language(target)
        w.resize(width, 900)
        for _ in range(5): app.processEvents()
        assert w.nav.item(5).text() == ('06  Cell Optimization' if target == 'en_US' else '06  晶胞优化')
        assert panel.findChild(QLabel, 'heading').text() == ('06 · Cell Optimization' if target == 'en_US' else '06 · 晶胞优化')
        assert len(panel.cards) == 3
        assert panel.cards[0].title_label.text() == ('Optimization Settings' if target == 'en_US' else '优化设置')
        assert panel.cards[2].help_icon.toolTip()
        field = panel.fields['cell_opt.external_pressure'][0]
        assert field.parentWidget().layout().itemAt(0).widget().text() == (
            'EXTERNAL_PRESSURE' if target == 'en_US' else '外部压力')
        assert panel.fields['cell_opt.keep_angles'][0].text() == ('KEEP_ANGLES' if target == 'en_US' else '保持夹角')
        symmetry = panel.fields['cell_opt.initial_symmetry'][0]
        assert symmetry.currentData() == 'NONE'
        assert symmetry.itemText(symmetry.findData('CUBIC')) == ('CUBIC' if target == 'en_US' else '立方（CUBIC）')
        assert w.stack.widget(5).horizontalScrollBar().maximum() == 0
        assert w.nav.currentRow() == 5 and w.task_panel.stack.currentWidget() is panel
        assert w.structure_panel.view is w.structure_view_card.content.itemAt(0).widget()
        assert {key:id(value[0]) for key,value in panel.fields.items()} == identities
        assert (w.project.model_dump_json(), w.preview.toPlainText(), w.dirty, w._revision) == before


def test_all_cell_parameters_bind_to_preview_and_invalidate_check(cell_window, app):
    w = cell_window
    w.check_current_configuration()
    wait_for_worker(app, w)
    assert w.nav.item(7).data(STATUS_ROLE) == 'ready'
    panel = w.cell_opt_panel
    for key, value in [('optimizer','LBFGS'), ('constraint','XY'), ('initial_symmetry','CUBIC')]:
        widget = panel.fields['cell_opt.'+key][0]
        widget.setCurrentIndex(widget.findData(value))
    for key,value in [('external_pressure','-25.5'),('pressure_tolerance','75'),('max_iter','240'),
        ('max_force','0.0003'),('rms_force','0.0002'),('max_dr','0.002'),('rms_dr','0.001')]:
        panel.fields['cell_opt.'+key][0].setText(value)
    for key in ['keep_angles','keep_symmetry']:
        panel.fields['cell_opt.'+key][0].setChecked(True)
    assert w.nav.item(7).data(STATUS_ROLE) == 'unchecked'
    w.refresh()
    assert w.preview.toPlainText() == generate_input(w.project)
    assert 'STRESS_TENSOR ANALYTICAL' in w.preview.toPlainText()
    assert 'TYPE DIRECT_CELL_OPT' not in w.preview.toPlainText()
    assert 'SYMMETRY CUBIC' in w.preview.toPlainText()
    assert w.project.cell_opt.external_pressure == -25.5 and w.project.cell_opt.max_iter == 240
    w.check_current_configuration()
    wait_for_worker(app, w)
    assert w._comprehensive_result.validation.ok and not w._comprehensive_result.validation.warnings
    assert w.nav.item(7).data(STATUS_ROLE) == 'ready'
    panel.fields['cell_opt.initial_symmetry'][0].setCurrentIndex(0)
    w.refresh()
    assert not w.export_action.isEnabled() and w.nav.item(5).data(STATUS_ROLE) == 'error'
    assert 'KEEP_SYMMETRY' in w.report.toPlainText()


def test_project_reopen_and_preset_restore_cell_settings_and_navigation(cell_window, app, tmp_path, monkeypatch):
    w = cell_window
    panel = w.cell_opt_panel
    panel.fields['cell_opt.max_iter'][0].setText('289')
    panel.fields['cell_opt.keep_angles'][0].setChecked(True)
    w.refresh()
    expected = w.project.model_dump_json(), w.preview.toPlainText()
    path = tmp_path / 'cell-project.json'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **kw:(str(path),''))
    assert w.save(force_dialog=True)
    preset = w.preset_store.save(capture_preset(w.project, 'cell parameters'))
    w.new_project()
    w._open_path(path)
    assert (w.project.model_dump_json(),w.preview.toPlainText()) == expected
    assert w.task_panel.stack.currentWidget() is panel
    assert panel.fields['cell_opt.max_iter'][0].text() == '289'
    assert panel.fields['cell_opt.keep_angles'][0].isChecked()
    assert w.nav.item(7).data(STATUS_ROLE) == 'unchecked'
    choose_task(w, 'GEO_OPT')
    monkeypatch.setattr(w, 'confirm_preset_application', lambda *args:True)
    assert w.apply_preset('user:'+preset.id)
    assert w.project.global_settings.run_type == 'CELL_OPT'
    assert w.task_panel.stack.currentWidget() is panel
    assert w.project.cell_opt.max_iter == 289
    assert w.nav.item(5).text() == '06  晶胞优化'
