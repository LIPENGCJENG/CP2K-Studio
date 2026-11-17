"""Replica default, preserved user values and a non-mutating bilingual hint."""
import json
import pytest
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QHelpEvent, QTextDocument
from PySide6.QtWidgets import QToolTip
from core.models import Project
from core.validator import validate_project
from core.generator import generate_input, GenerationError
from core.project_io import save_project, load_project, export_bundle
from core.presets import capture_preset, apply_preset
from core.run_script_generator import generate_run_script
from core.comprehensive_check import comprehensive_check
from i18n.language_manager import language_manager
from ui.widgets.help_icon import HelpIcon
from tests.test_vibrational_ui import window


def test_default_and_legacy_missing_field_use_four_but_saved_values_are_kept(vib_project, tmp_path):
    assert Project().vibrational.nproc_rep == 4
    assert vib_project.vibrational.nproc_rep == 4
    data = vib_project.model_dump()
    data['vibrational'].update(dx=.005, proc_dist_type='INTERLEAVED', fully_periodic=True)
    data['vibrational'].pop('nproc_rep')
    path = tmp_path / 'legacy.json'
    path.write_text(json.dumps(data))
    restored = load_project(path)
    assert restored.vibrational.nproc_rep == 4
    assert restored.vibrational.dx == .005 and restored.vibrational.proc_dist_type == 'INTERLEAVED'
    assert restored.vibrational.fully_periodic
    data['vibrational']['nproc_rep'] = 1
    path.write_text(json.dumps(data))
    assert load_project(path).vibrational.nproc_rep == 1
    preset = capture_preset(load_project(path), 'one rank per replica')
    assert apply_preset(vib_project, preset).project.vibrational.nproc_rep == 1
    assert vib_project.vibrational.nproc_rep == 4


@pytest.mark.parametrize('mpi,valid', [(1,False),(2,False),(3,False),(4,True),(8,True),(16,True),(18,False)])
def test_default_four_is_checked_against_actual_mpi_total_without_adjustments(vib_project, mpi, valid):
    vib_project.run_environment.mpi_processes = mpi
    snapshot = vib_project.model_dump_json()
    result = validate_project(vib_project)
    assert result.ok is valid
    assert vib_project.model_dump_json() == snapshot and vib_project.vibrational.nproc_rep == 4
    if not valid:
        assert any(getattr(error, 'code', '') == 'vib.replica_error' for error in result.errors)
        with pytest.raises(GenerationError): generate_input(vib_project)
        checked = comprehensive_check(vib_project)
        assert any('NPROC_REP' in str(error) for error in checked.validation.errors)
        assert vib_project.model_dump_json() == snapshot
    else:
        assert 'NPROC_REP 4' in generate_input(vib_project)


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
@pytest.mark.parametrize('width', [1050,1480])
def test_help_icon_stays_beside_label_and_input_keeps_original_label_gap(window, app, language, width):
    language_manager().set_language(language)
    window.resize(width, 900)
    for _ in range(5): app.processEvents()
    panel = window.vibrational_panel
    field = panel.fields['vibrational.nproc_rep'][0]
    dx = panel.fields['vibrational.dx'][0]
    icon, label = panel.nproc_help, panel.nproc_label
    assert isinstance(icon, HelpIcon) and icon.size().width() == icon.size().height() == 16
    assert label.text() == 'NPROC_REP'
    assert icon.x() - label.geometry().right() - 1 == 6
    assert abs(icon.geometry().center().y() - label.geometry().center().y()) <= 1
    assert field.y() == dx.y() and field.height() == dx.height()
    assert field.text() == '4' and not field.toolTip()
    assert not window.dirty and window.project.vibrational.nproc_rep == 4
    assert panel.fields['vibrational.dx'][0].text() == '0.01'
    assert window.project.vibrational.proc_dist_type == 'BLOCKED' and not window.project.vibrational.fully_periodic


def test_complete_bilingual_hover_help_and_language_changes_do_not_edit_configuration(window, app):
    panel = window.vibrational_panel
    icon = panel.nproc_help
    snapshot = window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()
    script = generate_run_script(window.project.run_environment)
    for language in ['en_US','zh_CN','en_US']:
        language_manager().set_language(language)
        app.processEvents()
        document = QTextDocument()
        document.setHtml(icon.toolTip())
        text = document.toPlainText()
        assert ('MPI Parallel Settings' if language == 'en_US' else 'MPI 并行设置建议') in text
        assert 'NPROC_REP = 4' in text and 'NPROC_REP = 8' in text and 'NPROC_REP = 16' in text
        assert '÷ NPROC_REP' in text and 'OOM' in text
        assert ('concurrent replicas' if language == 'en_US' else '同时运行的副本数量') in text
        assert '<table width="340"' in icon.toolTip()
        window.stack.widget(5).ensureWidgetVisible(icon)
        for _ in range(3): app.processEvents()
        position = icon.rect().center()
        try:
            app.sendEvent(icon, QHelpEvent(QEvent.Type.ToolTip, position, icon.mapToGlobal(position)))
            assert QToolTip.isVisible() and QToolTip.text() == icon.toolTip()
            tips = [widget for widget in app.topLevelWidgets() if widget.inherits('QTipLabel') and widget.isVisible()]
            assert tips and 320 <= tips[0].width() <= 420
            assert tips[0].height() <= app.primaryScreen().availableGeometry().height()
        finally:
            QToolTip.hideText()
        assert (window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()) == snapshot
        assert generate_run_script(window.project.run_environment) == script


@pytest.mark.parametrize('rep', [4,8])
def test_edits_preview_project_preset_and_package_keep_requested_ranks(window, app, tmp_path, rep):
    before = window.project.model_dump()
    field = window.vibrational_panel.fields['vibrational.nproc_rep'][0]
    field.setText(str(rep))
    window.refresh()
    assert window.project.vibrational.nproc_rep == rep
    assert f'NPROC_REP {rep}' in window.preview.toPlainText()
    assert window.preview.toPlainText() == generate_input(window.project)
    current = window.project.vibrational.model_dump(exclude={'nproc_rep'})
    assert current == {key:value for key,value in before['vibrational'].items() if key != 'nproc_rep'}
    path = tmp_path / 'replica.json'
    save_project(window.project, path)
    restored = load_project(path)
    assert restored.vibrational.nproc_rep == rep
    preset = capture_preset(restored, 'replica settings')
    assert apply_preset(Project(), preset).project.vibrational.nproc_rep == rep
    folder = export_bundle(restored, tmp_path / f'job-{rep}').parent
    assert f'NPROC_REP {rep}' in (folder / 'input.inp').read_text()
    assert (folder / 'run.sh').read_text() == generate_run_script(restored.run_environment)
    assert restored.run_environment.model_dump() == before['run_environment']
