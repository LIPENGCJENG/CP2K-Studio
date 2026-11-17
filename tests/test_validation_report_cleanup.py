"""Report rules retain real problems and never change scientific input."""
import numpy as np
import pytest
from core.comprehensive_check import comprehensive_check
from core.generator import generate_input, GenerationError
from core.input_export import export_input
from core.kind_validator import validate_kinds
from core.project_io import export_bundle
from core.validator import validate_project
from i18n.language_manager import language_manager
from tests.test_databases import catalog, bind
from tests.test_layout_workflow import wait_for_worker
from ui.main_window import MainWindow
from ui.validation_state import step_states


def codes(messages):
    return {getattr(m, 'code', '') for m in messages}


@pytest.fixture
def periodic_vibration(water):
    water.global_settings.run_type = 'VIBRATIONAL_ANALYSIS'
    water.dft.scf.eps_scf = 1e-7
    water.vibrational.fully_periodic = False
    return water


@pytest.mark.parametrize('basis_name', ['DZVP-MOLOPT-GTH', 'TZVP-MOLOPT-GTH',
    'TZV2P-MOLOPT-GTH', 'TZV2PX-MOLOPT-GTH', 'QZV2P-GTH-q6', 'QZV3P-GTH-q6'])
def test_real_basis_qualities_and_q_matches_produce_no_success_info(water, catalog, basis_name):
    basis = catalog.find('basis', 'O', basis_name)[0]
    potential = catalog.find('potential', 'O', 'GTH-PBE-q6')[0]
    bind(water, 'O', basis, potential)
    checked = validate_kinds(water, catalog)
    assert not checked.errors
    assert checked.selected['O']['basis'].q == checked.selected['O']['potential'].q == 6
    assert not [i for i in checked.issues if i.severity == 'Info']
    assert not [m for m in validate_project(water, catalog).infos if str(m).startswith('KIND ')]


@pytest.mark.parametrize('task', ['ENERGY', 'GEO_OPT', 'CELL_OPT', 'MD', 'VIBRATIONAL_ANALYSIS'])
def test_multielement_success_is_silent_for_every_task(water, task):
    water.global_settings.run_type = task
    before = water.model_dump_json(), generate_input(water)
    checked = validate_kinds(water)
    assert set(checked.selected) == {'H', 'O'}
    assert not checked.issues
    assert not [m for m in validate_project(water).infos if str(m).startswith('KIND ')]
    assert (water.model_dump_json(), generate_input(water)) == before


@pytest.mark.parametrize('field,value,severity', [
    ('basis_set', '', 'Error'), ('potential', '', 'Error'),
    ('basis_set', 'NOT-A-BASIS', 'Error'), ('potential', 'NOT-A-POTENTIAL', 'Error'),
    ('potential', 'GTH-BLYP-q6', 'Warning'),
])
def test_actual_kind_problems_keep_their_severity(water, field, value, severity):
    setattr(water.kinds['O'], field, value)
    result = validate_kinds(water)
    assert any(i.label == 'O' and i.severity == severity for i in result.issues)
    assert not [i for i in result.issues if i.severity == 'Info']
    checked = validate_project(water)
    assert (checked.errors if severity == 'Error' else checked.warnings)
    assert step_states(water, checked, checked=True)[4].state == severity.lower()
    if severity == 'Error':
        with pytest.raises(GenerationError):
            generate_input(water)


@pytest.mark.parametrize('boundary', ['NONE', 'XYZ'])
@pytest.mark.parametrize('fully', [False, True])
def test_periodic_detection_condition_and_severity_are_precise(periodic_vibration, boundary, fully):
    p = periodic_vibration
    p.structure.periodic = boundary
    p.dft.poisson_solver = 'MT' if boundary == 'NONE' else 'PERIODIC'
    p.vibrational.fully_periodic = fully
    before = p.model_dump_json(), generate_input(p)
    result = validate_project(p)
    assert ('vib.periodic_info' in codes(result.infos)) is (boundary == 'XYZ' and not fully)
    assert not any('FULLY_PERIODIC F' in str(m) for m in result.warnings + result.errors)
    if boundary == 'XYZ' and not fully:
        assert not result.errors and not result.warnings
        for step in [5, 7]:
            assert step_states(p, result, checked=True)[step].state == 'ready'
    assert (p.model_dump_json(), generate_input(p)) == before


def test_info_only_comprehensive_report_and_exports(periodic_vibration, validator, tmp_path):
    p = periodic_vibration
    snapshot = p.model_dump_json(), generate_input(p)
    local = validate_project(p)
    checked = comprehensive_check(p)
    assert not checked.validation.errors and not checked.validation.warnings
    assert all(stage.state == 'ready' for stage in checked.stages)
    assert set(local.infos) <= set(checked.validation.infos)
    assert {'vib.periodic_info', 'vib.stationary_info'} <= codes(checked.validation.infos)
    assert all(not str(m).startswith('KIND ') for m in checked.validation.infos)
    for language in ['en_US', 'zh_CN']:
        text = checked.report().render(language)
        assert ('Info · VIBRATIONAL_ANALYSIS: A periodic cell' if language == 'en_US'
                else '提示 · VIBRATIONAL_ANALYSIS：当前为周期性晶胞') in text
        assert ('Warnings: 0' if language == 'en_US' else '警告：0') in text
        assert ('Validation Passed' if language == 'en_US' else '综合检查通过') in text
    path = tmp_path / 'input.inp'
    export_input(p, path)
    assert path.read_text() == snapshot[1]
    folder = export_bundle(p, tmp_path / 'bundle').parent
    parsed = validator.parse((folder / 'input.inp').read_text(), folder)
    assert parsed.ok and parsed.tree['+vibrational_analysis']['fully_periodic'] is False
    assert (p.model_dump_json(), generate_input(p)) == snapshot


@pytest.fixture
def window(app, periodic_vibration, tmp_path):
    value = MainWindow(preset_directory=tmp_path / 'presets')
    value.load_into_ui(periodic_vibration)
    value.show()
    value.nav.setCurrentRow(5)
    app.processEvents()
    yield value
    wait_for_worker(app, value)
    value.dirty = False
    value.close()
    app.processEvents()
    language_manager().set_language('zh_CN')


@pytest.mark.parametrize('level', ['info', 'warning', 'error'])
@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_live_manual_severity_and_locales_remain_consistent(window, app, level, language):
    if level == 'warning':
        window.scf_panel.fields['dft.scf.eps_scf'][0].setText('1e-6')
    elif level == 'error':
        window.vibrational_panel.fields['vibrational.nproc_rep'][0].setText('32')
    window.refresh()
    expected = {'info': 'ready', 'warning': 'warning', 'error': 'error'}[level]
    task_state = 'ready' if level == 'warning' else expected
    scf_state = 'warning' if level == 'warning' else 'ready'
    assert window._step_states[3].state == scf_state
    assert window._step_states[5].state == task_state and window._step_states[7].state == 'unchecked'
    assert 'vib.periodic_info' in codes(window._validation.infos)
    assert not window.project.vibrational.fully_periodic
    # Successful KIND status cells remain available without success Info entries.
    if level == 'info':
        for row in range(window.kind_panel.table.rowCount()):
            assert '✓' in window.kind_panel.table.item(row, 3).text()
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert window._step_states[3].state == scf_state
    assert window._step_states[5].state == task_state and window._step_states[7].state == expected
    result = window._comprehensive_result
    assert len(result.validation.warnings) == int(level == 'warning')
    assert bool(result.validation.errors) is (level == 'error')
    assert window.export_action.isEnabled() is (level != 'error')
    view = window.structure_panel.view
    view.zoom = 1.6
    view.pan_offset = np.array([.1, .2, .3])
    view.set_labels_visible(True)
    rotation = view.rotation.copy()
    before = window.project.model_dump_json(), window.dirty, window._revision
    inp = window.preview.toPlainText()
    for selected in [language, 'zh_CN' if language == 'en_US' else 'en_US']:
        language_manager().set_language(selected)
        app.processEvents()
        report = window.report.toPlainText()
        assert ('Info · VIBRATIONAL_ANALYSIS: A periodic cell' if selected == 'en_US'
                else '提示 · VIBRATIONAL_ANALYSIS：当前为周期性晶胞') in report
        assert window._comprehensive_result is result
        assert window._step_states[3].state == scf_state
        assert window._step_states[5].state == task_state and window._step_states[7].state == expected
        assert (window.project.model_dump_json(), window.dirty, window._revision) == before
        if level != 'error':
            assert window.preview.toPlainText() == inp
        assert view.show_labels and view.zoom == 1.6
        assert np.array_equal(view.rotation, rotation) and np.array_equal(view.pan_offset, [.1, .2, .3])
