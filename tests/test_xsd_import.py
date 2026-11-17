"""Real user-provided MS files plus explicitly synthetic negative cases."""
from collections import Counter
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from ase import Atoms
from ase.io import read, write
from core.models import Kind, FixedAtom, BoxGenerationSettings
from core.structure import load_structure, load_structure_with_report, generate_nonperiodic_box, generate_simulation_box
from core.generator import generate_input
from core.project_io import save_project, load_project, export_bundle
from core.input_export import export_input
from core.run_script_generator import generate_run_script

FIXTURES = Path(__file__).parent / 'fixtures' / 'xsd'


def test_real_h2o_cartesian_positions_and_no_invented_cell():
    path = FIXTURES / 'h2o_ms23.xsd'
    nodes = ET.parse(path).findall('.//Molecule/Atom3d')
    expected = [[float(v) for v in node.get('XYZ').split(',')] for node in nodes]
    st = load_structure(path)
    assert st.symbols == ['O', 'H', 'H'] and st.periodic == 'NONE'
    assert st.positions == list(map(tuple, expected))
    assert np.array_equal(st.cell, np.zeros((3, 3)))
    assert not st.fixed_atoms and st.atom_ids == [1, 2, 3]


def test_real_rutile_asymmetric_symmetry_expands_to_full_cell():
    path = FIXTURES / 'rutile_ms23.xsd'
    imported = load_structure_with_report(path)
    st = imported.structure
    u = .304805655805187
    expected_scaled = [[0, 0, 0], [.5, .5, .5], [u, u, 0],
                       [1-u, 1-u, 0], [.5-u, .5+u, .5], [.5+u, .5-u, .5]]
    assert st.symbols == ['Ti', 'Ti', 'O', 'O', 'O', 'O']
    assert st.periodic == 'XYZ' and len(st.positions) == 6
    assert np.array_equal(st.cell, np.diag([4.6157, 4.6157, 2.967]))
    assert np.allclose(st.positions, np.array(expected_scaled) @ st.cell, rtol=0, atol=1e-12)
    assert any(note.code == 'xsd.expanded' for note in imported.notices)


def test_real_slab_matches_ase_and_retains_rotated_vectors_and_xyz():
    path = FIXTURES / 'slab_ms23.xsd'
    original = read(path, format='xsd')
    st = load_structure(path)
    assert Counter(st.symbols) == {'Ti': 8, 'O': 14}
    assert st.symbols == original.get_chemical_symbols()
    assert np.array_equal(st.positions, original.positions)
    assert np.array_equal(st.cell, original.cell.array)
    assert st.cell[0] == (0, 0, 2.967)  # Do not reconstruct ABC lengths on XYZ axes.
    assert st.periodic == 'XYZ'  # A large vacuum is not permission to choose XY.


def test_synthetic_triclinic_cell_and_multielement_order(tmp_path):
    atoms = Atoms('SiOCH', scaled_positions=[[.1,.2,.3], [.4,.5,.6], [-.2,.1,.8], [1.2,.3,.4]],
                  cell=[[5,0,0], [1,6,0], [.5,.7,9]], pbc=True)
    path = tmp_path / 'synthetic-triclinic.xsd'
    write(path, atoms, format='xsd')
    st = load_structure(path)
    assert st.symbols == ['Si', 'O', 'C', 'H']
    assert np.allclose(st.cell, atoms.cell.array, rtol=0, atol=1e-14)
    assert np.allclose(st.positions, atoms.positions, rtol=0, atol=1e-13)
    assert st.positions[-1][0] > st.cell[0][0]  # No implicit wrapping.


@pytest.mark.parametrize('suffix', ['xsd', 'XSD', 'XsD'])
def test_unicode_spaces_parentheses_and_case_insensitive_extension(tmp_path, suffix):
    folder = tmp_path / '中文目录 (结构)'
    folder.mkdir()
    path = folder / f'水分子 (H2O).{suffix}'
    shutil.copyfile(FIXTURES / 'h2o_ms23.xsd', path)
    st = load_structure(path)
    assert st.source == str(path.resolve()) and st.symbols == ['O', 'H', 'H']


@pytest.mark.parametrize('suffix', ['CIF', 'XYZ', 'EXTXYZ'])
def test_existing_formats_also_accept_uppercase_extensions(tmp_path, suffix):
    atoms = Atoms('OH2', positions=[[0,0,0],[0,.7,.5],[0,-.7,.5]], cell=[6,7,8], pbc=True)
    path = tmp_path / ('existing.' + suffix)
    write(path, atoms, format=suffix.lower())
    st = load_structure(path)
    reference = read(path, format='cif' if suffix == 'CIF' else 'extxyz')
    assert st.symbols == atoms.get_chemical_symbols()
    assert np.allclose(st.positions, reference.positions)
    assert st.periodic == ('NONE' if suffix == 'XYZ' else 'XYZ')


@pytest.mark.parametrize('mutation', ['empty', 'bad_element', 'nan_coordinate', 'bad_cell',
    'zero_cell', 'bad_symmetry', 'incomplete_symmetry', 'duplicated_symmetry', 'changed_image',
    'normalized_false', 'multiple_systems', 'missing_molecule_xyz', 'image_vacancy'])
def test_synthetic_invalid_or_unsupported_xsd_is_rejected(tmp_path, mutation):
    source = ('h2o_ms23.xsd' if mutation == 'missing_molecule_xyz' else
              'rutile_ms23.xsd' if mutation in {'incomplete_symmetry', 'duplicated_symmetry'} else 'slab_ms23.xsd')
    root = ET.parse(FIXTURES / source).getroot()
    identity = root.find('.//IdentityMapping')
    if mutation == 'empty':
        for node in list(identity):
            if node.tag == 'Atom3d':
                identity.remove(node)
    elif mutation == 'bad_element':
        identity.find('Atom3d').set('Components', 'Xx')
    elif mutation == 'nan_coordinate':
        identity.find('Atom3d').set('XYZ', 'nan,0,0')
    elif mutation == 'bad_cell':
        identity.find('SpaceGroup').set('AVector', '1,2')
    elif mutation == 'zero_cell':
        identity.find('SpaceGroup').set('AVector', '0,0,0')
    elif mutation == 'bad_symmetry':
        identity.find('SpaceGroup').set('Operators', '1,0')
    elif mutation in {'incomplete_symmetry', 'duplicated_symmetry'}:
        group = root.find('.//SpaceGroup')
        operators = group.get('Operators').split(':')
        group.set('Operators', ':'.join(operators[:2] if mutation == 'incomplete_symmetry' else [operators[0]] * len(operators)))
    elif mutation == 'changed_image':
        root.find('.//ImageMapping/Atom3d').set('XYZ', '0,0,0')
    elif mutation == 'image_vacancy':
        ET.SubElement(root.find('.//ImageMapping'), 'Vacancy', ID='synthetic-vacancy')
    elif mutation == 'normalized_false':
        root.find('.//SymmetrySystem').set('Normalized', '0')
    elif mutation == 'multiple_systems':
        ET.SubElement(root.find('AtomisticTreeRoot'), 'Molecule')
    else:
        root.find('.//Molecule/Atom3d').attrib.pop('XYZ')
    path = tmp_path / 'synthetic-invalid.xsd'
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
    with pytest.raises(ValueError):
        load_structure(path)


@pytest.mark.parametrize('content', ['<XSD', '<schema/>', '<XSD><AtomisticTreeRoot/></XSD>'])
def test_corrupt_or_wrong_root_is_reported(tmp_path, content):
    path = tmp_path / 'corrupt.xsd'
    path.write_text(content)
    with pytest.raises(ValueError):
        load_structure(path)


def test_ase_result_is_validated_not_trusted_blindly(monkeypatch):
    import core.xsd_import as adapter
    original = adapter.read
    calls = []
    def changed(*args, **kwargs):
        calls.append(kwargs['format'])
        atoms = original(*args, **kwargs)
        atoms.positions[0, 0] += 1
        return atoms
    monkeypatch.setattr(adapter, 'read', changed)
    with pytest.raises(ValueError):
        load_structure(FIXTURES / 'h2o_ms23.xsd')
    assert calls == ['xsd']


def test_explicit_box_translation_preserves_identity_geometry_and_constraints():
    original = load_structure(FIXTURES / 'h2o_ms23.xsd')
    original.fixed_atoms = [FixedAtom(atom_id=2, components='XY')]
    snapshot = original.model_dump_json()
    boxed = generate_nonperiodic_box(original, 4.5)
    points, before = np.array(boxed.positions), np.array(original.positions)
    assert original.model_dump_json() == snapshot
    assert boxed.periodic == 'NONE' and boxed.fixed_atoms == original.fixed_atoms
    assert boxed.atom_ids == original.atom_ids and boxed.symbols == original.symbols
    assert np.allclose(points - before, points[0] - before[0], atol=1e-13)
    assert np.allclose(points.min(axis=0), 4.5)
    assert np.allclose(np.diag(boxed.cell) - points.max(axis=0), 4.5)
    assert np.allclose(np.diag(boxed.cell), np.ptp(before, axis=0) + 9)


@pytest.mark.parametrize('vacuum', [0, -1, float('nan'), float('inf')])
def test_invalid_box_margin_is_rejected(vacuum):
    st = load_structure(FIXTURES / 'h2o_ms23.xsd')
    with pytest.raises(ValueError):
        generate_nonperiodic_box(st, vacuum)


@pytest.mark.parametrize('filename', ['rutile_ms23.xsd', 'slab_ms23.xsd', 'h2o_ms23.xsd'])
def test_real_structure_json_inp_and_package_roundtrip(water, filename, validator, tmp_path):
    p = water
    p.structure = load_structure(FIXTURES / filename)
    if p.structure.periodic == 'NONE':
        p.structure = generate_simulation_box(p.structure, BoxGenerationSettings(mode='CUBIC', cubic_margin=5))
        p.dft.poisson_solver = 'WAVELET'
    else:
        # Explicit test chemistry, not an application default/recommendation.
        p.kinds = {'O': p.kinds['O'], 'Ti': Kind(element='Ti', basis_set='DZVP-MOLOPT-SR-GTH', potential='GTH-PBE-q12')}
    snapshot = p.structure.model_dump()
    path = tmp_path / 'xsd-project.json'
    save_project(p, path)
    assert load_project(path).structure.model_dump() == snapshot
    text = generate_input(p)
    assert 'COORD_FILE_FORMAT XSD' not in text and validator.parse(text).ok
    inp = tmp_path / 'structure.inp'
    export_input(p, inp)
    assert inp.read_text() == text
    folder = export_bundle(p, tmp_path / 'package').parent
    bundled = (folder / 'input.inp').read_text()
    assert 'COORD_FILE_FORMAT XYZ' in bundled and 'COORD_FILE_NAME structure.xyz' in bundled
    assert validator.parse(bundled, folder).ok
    assert (folder / 'run.sh').read_text() == generate_run_script(p.run_environment)
    assert np.allclose(load_structure(folder / 'structure.xyz').positions, p.structure.positions, rtol=0, atol=1e-12)
    assert load_project(folder / 'project.cp2kstudio.json').structure.cell == p.structure.cell
