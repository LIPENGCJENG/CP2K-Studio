import pytest
from pydantic import ValidationError
from core.models import Project, Structure
from core.validator import validate_project
from core.generator import generate_input, GenerationError


def test_new_project_has_initial_electronic_state_but_is_still_a_draft():
    p = Project()
    assert p.structure is None and p.dft.charge == 0
    assert p.dft.multiplicity == 1 and not p.kinds
    assert p.dft.xc_functional is None and not p.dft.basis_files
    assert not validate_project(p).ok
    with pytest.raises(GenerationError):
        generate_input(p)


@pytest.mark.parametrize('value', [0, -1, float('inf'), float('nan')])
def test_invalid_cutoff(water, value):
    with pytest.raises(ValidationError):
        water.dft.cutoff = value


def test_invalid_nested_data_and_unknown_fields():
    with pytest.raises(ValidationError):
        Structure(symbols=['H'], positions=[])
    with pytest.raises(ValidationError):
        Project(format_version=99)
    with pytest.raises(ValidationError):
        Project(unknown=True)
    with pytest.raises(ValidationError):
        Structure(symbols=['X'], positions=[(0, 0, 0)])


def test_cell_and_spin(water):
    water.structure.cell = ((0,0,0),)*3
    assert any('CELL' in e for e in validate_project(water).errors)
    water.structure.cell = ((6,0,0),(0,6,0),(0,0,6))
    water.dft.charge = 1
    assert any('奇偶' in e for e in validate_project(water).errors)
    water.dft.multiplicity = 2
    assert any('UKS' in e for e in validate_project(water).errors)
    water.dft.uks = True
    assert validate_project(water).ok


@pytest.mark.parametrize('periodic,solver,ok', [
    ('XYZ','PERIODIC',True),('NONE','PERIODIC',False),('X','MT',False),
    ('XY','MT',True),('NONE','MT',True),('XYZ','ANALYTIC',False),
    ('Z','ANALYTIC',True),('XY','WAVELET',False),('XZ','WAVELET',True)])
def test_poisson_compatibility(water, periodic, solver, ok):
    water.structure.periodic = periodic
    water.dft.poisson_solver = solver
    assert validate_project(water).ok == ok


def test_kind_and_path_injection(water):
    water.kinds['H'].basis_set = 'DZVP #comment'
    assert not validate_project(water).ok
    water.kinds['H'].basis_set = 'DZVP'
    water.dft.basis_files = ['BASIS\n&END DFT']
    assert not validate_project(water).ok


def test_missing_resource_path_and_lookup_name(water, tmp_path):
    water.dft.basis_files = [str(tmp_path/'missing')]
    assert not validate_project(water).ok
    water.dft.basis_files = ['BASIS_MOLOPT']
    result = validate_project(water)
    assert result.ok and any('已定位' in i for i in result.infos)
    water.dft.basis_files = ['NO_SUCH_DATABASE']
    assert not validate_project(water).ok


def test_mutated_container_is_revalidated(water):
    water.structure.positions[0] = (float('nan'), 0, 0)
    assert not validate_project(water).ok
