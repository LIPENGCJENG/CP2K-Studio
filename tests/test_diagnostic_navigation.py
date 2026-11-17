"""Task-context warnings navigate to the parameter that needs editing."""
import pytest
from core.validator import validate_project
from core.generator import generate_input
from i18n.messages import i18n_msg, i18n_join
from i18n.language_manager import language_manager
from ui.export_panel import error_page
from ui.validation_state import step_states


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
@pytest.mark.parametrize('wrapper', ['none', 'stage', 'nested', 'join'])
def test_scf_warning_routes_by_identity_through_localized_wrappers(vib_project, app, language, wrapper):
    language_manager().set_language(language)
    vib_project.dft.poisson_solver = 'MT'
    vib_project.dft.scf.eps_scf = 1e-6
    before = vib_project.model_dump_json(), generate_input(vib_project)
    result = validate_project(vib_project)
    warning = next(m for m in result.warnings if m.code == 'vib.scf_warning')
    if wrapper in {'stage', 'nested'}:
        warning = i18n_msg('[{p0}] {p1}', p0='configuration', p1=warning)
    if wrapper == 'nested':
        warning = i18n_msg('{p0}: {p1}', p0='summary', p1=warning)
    if wrapper == 'join':
        warning = i18n_join('\n', ['summary', warning])
    assert error_page(warning) == (3, '04 SCF')
    assert 'EPS_SCF' in warning.render(language)
    result.warnings = [warning]
    states = step_states(vib_project, result, checked=True)
    assert states[3].state == states[7].state == 'warning'
    assert states[5].state == 'ready'
    assert states[3].warnings == states[7].warnings == [warning]
    assert not states[5].warnings
    assert (vib_project.model_dump_json(), generate_input(vib_project)) == before


@pytest.mark.parametrize('code,text', [
    ('vib.linres_warning', 'VIBRATIONAL_ANALYSIS / Raman: LINRES EPS is too loose'),
    ('vib.replica_error', 'VIBRATIONAL_ANALYSIS / NPROC_REP: invalid MPI ranks'),
    ('vib.raman_solver_error', 'VIBRATIONAL_ANALYSIS / Raman: SCF method is unsupported'),
])
def test_other_task_diagnostics_still_belong_to_step_six(code, text):
    message = i18n_msg(text, code=code)
    assert error_page(message)[0] == 5
    assert error_page(i18n_msg('[{p0}] {p1}', p0='configuration', p1=message))[0] == 5


def test_scf_and_raman_warnings_can_mark_both_pages_and_clear_independently(vib_project):
    p = vib_project
    p.dft.poisson_solver = 'MT'
    p.vibrational.raman_enabled = True
    p.vibrational.linres_eps = 1e-6
    p.dft.scf.eps_scf = 1e-6
    result = validate_project(p)
    assert len(result.warnings) == 2
    states = step_states(p, result, checked=True)
    assert all(states[i].state == 'warning' for i in [3, 5, 7])
    p.dft.scf.eps_scf = 1e-7
    states = step_states(p, validate_project(p), checked=True)
    assert states[3].state == 'ready' and states[5].state == states[7].state == 'warning'
    p.vibrational.linres_eps = 1e-7
    states = step_states(p, validate_project(p), checked=True)
    assert all(states[i].state == 'ready' for i in [3, 5, 7])
