import pytest
import numpy as np
from ase import Atoms
from ase.io import write
from core.structure import load_structure, to_atoms


def test_xyz_keeps_absent_cell(tmp_path):
    path = tmp_path/'water.xyz'
    path.write_text('3\nwater\nO 0 0 0\nH 0 .7 .5\nH 0 -.7 .5\n')
    st = load_structure(path)
    assert st.elements == ['H', 'O']
    assert st.periodic == 'NONE'
    assert np.allclose(st.cell, 0)
    assert len(to_atoms(st)) == 3


def test_cif_roundtrip_triclinic(tmp_path):
    atoms = Atoms('Si2', scaled_positions=[(0,0,0),(.25,.25,.25)],
                  cell=[(5,0,0),(1,5,0),(.5,.2,6)], pbc=True)
    path = tmp_path/'silicon.cif'
    write(path, atoms)
    st = load_structure(path)
    assert st.periodic == 'XYZ'
    assert st.symbols == ['Si','Si']
    assert np.allclose(st.cell, atoms.cell, atol=1e-6)
    assert np.allclose(st.positions, atoms.positions, atol=1e-6)


def test_multiframe_and_corrupt_rejected(tmp_path):
    path = tmp_path/'trajectory.xyz'
    path.write_text('1\na\nH 0 0 0\n1\nb\nH 1 0 0\n')
    with pytest.raises(ValueError, match='恰好'):
        load_structure(path)
    path.write_text('invalid xyz')
    with pytest.raises(Exception):
        load_structure(path)


def test_partial_occupancy_rejected(tmp_path):
    path = tmp_path/'partial.cif'
    path.write_text('''data_partial
_cell_length_a 5
_cell_length_b 5
_cell_length_c 5
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_symmetry_space_group_name_H-M 'P 1'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
Si1 Si 0 0 0 0.5
''')
    with pytest.raises(ValueError, match='占位'):
        load_structure(path)
