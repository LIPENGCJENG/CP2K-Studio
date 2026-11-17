"""Severity is assigned at the rule, then propagated without UI suppression."""
import numpy as np
import pytest
from core.validator import validate_project
from core.comprehensive_check import comprehensive_check
from core.generator import generate_input
from core.project_io import export_bundle, load_project
from ui.main_window import MainWindow
from ui.validation_state import step_states
from ui.widgets.status_badge import STATUS_ROLE
from i18n.language_manager import language_manager
from tests.test_layout_workflow import wait_for_worker


@pytest.fixture
def mt_project(vib_project):
    vib_project.dft.poisson_solver = 'MT'
    vib_project.structure.cell = ((20,0,0),(0,24,0),(0,0,28))
    vib_project.dft.scf.eps_scf = 1e-7
    return vib_project


def codes(messages):
    return {getattr(message, 'code', '') for message in messages}


@pytest.mark.parametrize('eps,warning', [(1e-8,False), (1e-7,False), (5e-8,False), (1e-6,True),
    (float(np.nextafter(1e-7, np.inf)),True), (float(np.nextafter(1e-7, 0)),False)])
def test_scf_warning_threshold_is_strict_and_never_changes_parameters(mt_project, eps, warning):
    mt_project.dft.scf.eps_scf = eps
    before = mt_project.model_dump_json(), generate_input(mt_project)
    result = validate_project(mt_project)
    assert ('vib.scf_warning' in codes(result.warnings)) is warning
    assert len(result.warnings) == int(warning) and not result.errors
    if warning:
        message = next(item for item in result.warnings if item.code == 'vib.scf_warning')
        assert '1E-7' in message.render('en_US') and '1E-7' in message.render('zh_CN')
    assert (mt_project.model_dump_json(), generate_input(mt_project)) == before


def test_info_only_comprehensive_check_passes_and_keeps_every_info(mt_project):
    before = mt_project.model_dump_json()
    local = validate_project(mt_project)
    assert not local.errors and not local.warnings
    assert {'poisson.mt_info','vib.stationary_info'} <= codes(local.infos)
    assert step_states(mt_project, local, checked=True)[5].state == 'ready'
    assert step_states(mt_project, local, checked=True)[7].state == 'ready'
    checked = comprehensive_check(mt_project)
    assert [stage.state for stage in checked.stages] == ['ready'] * 4
    assert not checked.validation.errors and not checked.validation.warnings
    assert set(local.infos) <= set(checked.stages[0].infos)
    assert {'poisson.mt_info','vib.stationary_info'} <= codes(checked.validation.infos)
    for language in ['en_US','zh_CN']:
        report = checked.report().render(language)
        assert ('Warnings: 0' if language == 'en_US' else '警告：0') in report
        assert ('Validation Passed' if language == 'en_US' else '综合检查通过') in report
        assert ('Info · MT requires' if language == 'en_US' else '提示 · MT 求解器需要') in report
        assert ('Info · VIBRATIONAL_ANALYSIS: Ensure' if language == 'en_US'
                else '提示 · VIBRATIONAL_ANALYSIS：请确认') in report
        assert ('Warnings present' if language == 'en_US' else '存在警告') not in report
    assert mt_project.model_dump_json() == before


def test_independent_wavelet_warning_and_invalid_cell_are_not_downgraded(mt_project):
    mt_project.dft.poisson_solver = 'WAVELET'
    mt_project.structure.cell = ((24,0,0),(0,24,0),(0,0,24))
    result = validate_project(mt_project)
    assert not result.errors and result.warnings
    assert 'studio.24d25b06c30f6626' in codes(result.warnings)
    assert step_states(mt_project, result, checked=True)[7].state == 'warning'
    mt_project.dft.poisson_solver = 'MT'
    mt_project.structure.cell = ((0,0,0),)*3
    result = validate_project(mt_project)
    assert result.errors and 'poisson.mt_info' in codes(result.infos)
    assert step_states(mt_project, result, checked=True)[0].state == 'error'
    assert step_states(mt_project, result, checked=True)[7].state == 'error'


@pytest.mark.parametrize('task', ['ENERGY','GEO_OPT'])
def test_other_tasks_have_no_vibration_warning_and_keep_payload(water, tmp_path, task):
    water.global_settings.run_type = task
    water.dft.scf.eps_scf = 1e-6
    before = water.model_dump_json(), generate_input(water)
    result = validate_project(water)
    assert not result.errors and not result.warnings
    assert 'vib.stationary_info' not in codes(result.infos)
    assert 'vib.scf_warning' not in codes(result.warnings)
    folder = export_bundle(water, tmp_path / task).parent
    restored = load_project(folder / 'project.cp2kstudio.json')
    # Portable packages normalize dependency paths; scientific settings stay exact.
    dependencies = {'basis_files','potential_file','potential_files'}
    assert restored.dft.model_dump(exclude=dependencies) == water.dft.model_dump(exclude=dependencies)
    assert (water.model_dump_json(), generate_input(water)) == before


@pytest.fixture
def window(app, mt_project, tmp_path):
    value = MainWindow(preset_directory=tmp_path / 'presets')
    value.load_into_ui(mt_project)
    value.nav.setCurrentRow(5)
    value.show()
    app.processEvents()
    yield value
    wait_for_worker(app, value)
    value.dirty = False
    value.close()
    app.processEvents()
    language_manager().set_language('zh_CN')


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
@pytest.mark.parametrize('level', ['info','warning','error'])
def test_live_and_comprehensive_status_respects_real_severity_and_translates(window, app, language, level):
    if level == 'warning':
        window.scf_panel.fields['dft.scf.eps_scf'][0].setText('1e-6')
    elif level == 'error':
        window.vibrational_panel.fields['vibrational.nproc_rep'][0].setText('32')
    window.refresh()
    state = {'info':'ready','warning':'warning','error':'error'}[level]
    task_state = 'ready' if level == 'warning' else state
    scf_state = 'warning' if level == 'warning' else 'ready'
    assert window.nav.item(3).data(STATUS_ROLE) == scf_state
    assert window.nav.item(5).data(STATUS_ROLE) == task_state
    assert window.nav.item(7).data(STATUS_ROLE) == 'unchecked'
    # Info is present in the live report, before starting comprehensive validation.
    assert 'MT' in window.report.toPlainText()
    window.export_panel.check_button.click()
    wait_for_worker(app, window)
    assert window.nav.item(3).data(STATUS_ROLE) == scf_state
    assert window.nav.item(5).data(STATUS_ROLE) == task_state
    assert window.nav.item(7).data(STATUS_ROLE) == state
    checked = window._comprehensive_result
    assert len(checked.validation.warnings) == int(level == 'warning')
    assert bool(checked.validation.errors) is (level == 'error')
    assert window.export_action.isEnabled() is (level != 'error')
    before = window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()
    for selected in [language, 'zh_CN' if language == 'en_US' else 'en_US', language]:
        language_manager().set_language(selected)
        app.processEvents()
        report = window.report.toPlainText()
        assert ('Info · MT requires' if selected == 'en_US' else '提示 · MT 求解器需要') in report
        assert ('Info · VIBRATIONAL_ANALYSIS: Ensure' if selected == 'en_US'
                else '提示 · VIBRATIONAL_ANALYSIS：请确认') in report
        assert window._comprehensive_result is checked
        assert window.nav.item(3).data(STATUS_ROLE) == scf_state
        assert window.nav.item(5).data(STATUS_ROLE) == task_state
        assert window.nav.item(7).data(STATUS_ROLE) == state
        assert (window.project.model_dump_json(), window._revision, window.dirty) == before[:3]
        if level != 'error':  # Invalid-draft diagnostics translate; valid INP is language-independent.
            assert window.preview.toPlainText() == before[3]
    if level == 'warning':
        window.scf_panel.fields['dft.scf.eps_scf'][0].setText('1e-7')
        window.refresh()
        assert window._step_states[3].state == window._step_states[5].state == 'ready'
        assert window._step_states[7].state == 'unchecked'
        window.check_current_configuration()
        wait_for_worker(app, window)
        assert window._step_states[7].state == 'ready'


def test_info_only_save_reopen_recheck_and_export_are_consistent(window, app, tmp_path):
    snapshot = window.project.model_dump_json(), generate_input(window.project)
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[7].state == 'ready'
    window.project_path = tmp_path / 'info-only.json'
    assert window.save()
    assert window._step_states[7].state == 'ready'
    window._open_path(window.project_path)
    assert window._step_states[5].state == 'ready' and window._step_states[7].state == 'unchecked'
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[7].state == 'ready'
    folder = export_bundle(window.project, tmp_path / 'info-package').parent
    assert window.project.model_dump_json() == snapshot[0]
    assert generate_input(window.project) == snapshot[1]
    assert (folder / 'run.sh').is_file() and (folder / 'EXPORT_NOTES.txt').is_file()
    assert load_project(folder / 'project.cp2kstudio.json').vibrational == window.project.vibrational


@pytest.mark.parametrize('value', ['', 'invalid', 'nan'])
def test_invalid_scf_fields_still_block_comprehensive_check(window, app, value):
    window.scf_panel.fields['dft.scf.eps_scf'][0].setText(value)
    window.refresh()
    assert window._validation.errors and not window.export_action.isEnabled()
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._comprehensive_result.validation.errors
    assert window._step_states[7].state == 'error'
    assert 'EPS_SCF' in window.report.toPlainText().upper()
