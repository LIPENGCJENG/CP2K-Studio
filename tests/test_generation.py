import pytest
from core.generator import generate_input, GenerationError


def scf(tree):
    return tree['+force_eval'][0]['+dft']['+scf']


def test_ot_and_motion_branches(water, validator):
    text = generate_input(water)
    result = validator.parse(text)
    assert result.ok, result.errors
    assert '+ot' in scf(result.tree)
    assert '+diagonalization' not in scf(result.tree)
    assert '+mixing' not in scf(result.tree)
    assert '+motion' not in result.tree
    water.global_settings.run_type = 'GEO_OPT'
    water.dft.scf.outer_scf = True
    result = validator.parse(generate_input(water))
    assert result.ok, result.errors
    assert result.tree['+motion']['+geo_opt']['optimizer'] == 'bfgs'
    assert scf(result.tree)['+outer_scf']['max_scf'] == 10


def test_diagonalization_smearing(water, validator):
    water.dft.scf.method = 'DIAGONALIZATION'
    water.dft.scf.smearing = True
    water.dft.scf.added_mos = 12
    result = validator.parse(generate_input(water))
    assert result.ok, result.errors
    section = scf(result.tree)
    assert '+ot' not in section
    assert section['+diagonalization']['algorithm'] == 'standard'
    assert section['+mixing']['method'] == 'broyden_mixing'
    assert section['+smear']['electronic_temperature'] == 300


def test_ot_rejects_unsupported_smearing(water):
    water.dft.scf.smearing = True
    with pytest.raises(GenerationError):
        generate_input(water)


def test_triclinic_coordinates_are_preserved(water, validator):
    water.structure.cell = ((6,0,0),(1.5,5,0),(.8,.2,7))
    tree = validator.parse(generate_input(water)).tree
    cell = tree['+force_eval'][0]['+subsys']['+cell']
    assert cell['b'] == (1.5,5,0)
    assert cell['c'] == (.8,.2,7)
    assert tree['+force_eval'][0]['+subsys']['+coord']['*'][0] == 'O 0 0 -0.065587'


def test_wavelet_sets_required_fft_library(water, validator):
    water.dft.poisson_solver = 'WAVELET'
    water.structure.periodic = 'NONE'
    result = validator.parse(generate_input(water))
    assert result.ok, result.errors
    assert result.tree['+global']['preferred_fft_library'] == 'fftsg'


def test_xml_rejects_invalid_keyword_and_enum(validator):
    assert not validator.parse('&GLOBAL\n INVALID_KEY 1\n&END GLOBAL\n').ok
    assert not validator.parse('&GLOBAL\n RUN_TYPE MAGIC\n&END GLOBAL\n').ok
    assert not validator.parse('&GLOBAL\n').ok


@pytest.mark.parametrize('method', ['OT', 'DIAGONALIZATION'])
def test_golden_input(water, method):
    from pathlib import Path
    from core.database_manager import BUNDLED_DATA
    # Pin the original official fixture libraries; newly installed local CP2K
    # versions must not change the golden input's machine-independent paths.
    water.dft.basis_files = [str(BUNDLED_DATA/'BASIS_MOLOPT')]
    water.dft.potential_file = str(BUNDLED_DATA/'GTH_POTENTIALS')
    water.dft.scf.method = method
    if method == 'DIAGONALIZATION':
        water.global_settings.run_type = 'GEO_OPT'
    expected = Path(__file__).parent/'fixtures'/f'generated_{method.lower()}.inp'
    # The generator emits POSIX separators even when BUNDLED_DATA is a
    # WindowsPath. Remove only that known library prefix, not INP content.
    normalized = generate_input(water).replace(BUNDLED_DATA.as_posix() + '/', '')
    assert normalized == expected.read_text(encoding='utf-8')
