"""Pinned real CP2K inputs, plus a semantic comparison of supported fields.

These do not claim to reproduce upstream numerical energies without CP2K.
Unsupported print keys / test-only convergence bypasses remain upstream only.
"""
from pathlib import Path
import pytest
from core.models import Project, Structure, DFTConfig, GlobalConfig, Kind
from core.generator import generate_input

FIXTURES = Path(__file__).parent/'fixtures'


@pytest.mark.parametrize('filename', ['upstream_energy.inp', 'upstream_geo_opt.inp'])
def test_official_2026_1_input_parses(filename, validator):
    result = validator.parse((FIXTURES/filename).read_text(), FIXTURES)
    assert result.ok, result.errors


@pytest.mark.parametrize('mode', ['energy', 'geo_opt'])
def test_generated_supported_fields_match_upstream(mode, validator):
    source = validator.parse((FIXTURES/f'upstream_{mode}.inp').read_text()).tree
    glob = source['+global']
    fe = source['+force_eval'][0]
    dft, sub = fe['+dft'], fe['+subsys']
    symbols, positions = [], []
    for line in sub['+coord']['*']:
        fields = line.split()
        symbols.append(fields[0])
        positions.append(tuple(map(float, fields[1:4])))
    # Explicit fixture author decisions: source He2 is a doublet cation;
    # source water is neutral singlet. These are never application defaults.
    p = Project(global_settings=GlobalConfig(project_name=glob['project_name'],
            run_type=glob['run_type'].upper(), print_level=glob['print_level'].upper()),
        structure=Structure(symbols=symbols, positions=positions,
            cell=tuple(tuple(length if i == j else 0 for j in range(3)) for i,length in enumerate(sub['+cell']['abc'])), periodic='XYZ'),
        dft=DFTConfig(charge=1 if mode == 'energy' else 0, multiplicity=2 if mode == 'energy' else 1,
            uks=mode == 'energy', basis_files=dft['basis_set_file_name'], potential_file=dft['potential_file_name'],
            xc_functional='PADE', cutoff=dft['+mgrid']['cutoff'],
            eps_default=dft['+qs']['eps_default'], poisson_solver='PERIODIC'),
        kinds={k['_']: Kind(basis_set=k['basis_set'][0], potential=k['potential']) for k in sub['+kind']})
    p.dft.scf.eps_scf = dft['+scf']['eps_scf']
    p.dft.scf.max_scf = dft['+scf']['max_scf']
    if mode == 'geo_opt':
        p.motion.max_iter = source['+motion']['+geo_opt']['max_iter']
    parsed = validator.parse(generate_input(p))
    assert parsed.ok, parsed.errors
    output = parsed.tree
    assert output['+global'] == glob
    out_dft = output['+force_eval'][0]['+dft']
    for key in ['basis_set_file_name', 'potential_file_name']:
        actual=out_dft[key]
        assert ([Path(p).name for p in actual] if isinstance(actual,list) else Path(actual).name)==dft[key]
    assert out_dft['+scf']['eps_scf'] == dft['+scf']['eps_scf']
    assert out_dft['+scf']['max_scf'] == dft['+scf']['max_scf']
    assert out_dft['+mgrid']['cutoff'] == dft['+mgrid']['cutoff']
    assert out_dft['+xc'] == dft['+xc']
    out_sub = output['+force_eval'][0]['+subsys']
    assert {k['_']: (k['basis_set'], k['potential']) for k in out_sub['+kind']} == {
        k['_']: (k['basis_set'], k['potential']) for k in sub['+kind']}
    actual_coords = [(line.split()[0], tuple(map(float, line.split()[1:4]))) for line in out_sub['+coord']['*']]
    assert actual_coords == list(zip(symbols, positions))
    assert [out_sub['+cell'][axis][i] for i,axis in enumerate(['a','b','c'])] == list(sub['+cell']['abc'])
    if mode == 'geo_opt':
        assert output['+motion']['+geo_opt']['max_iter'] == source['+motion']['+geo_opt']['max_iter']
        assert output['+motion']['+geo_opt']['optimizer'] == source['+motion']['+geo_opt']['optimizer']
