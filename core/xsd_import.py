"""Materials Studio boundary: ASE XSD reader plus guarded symmetry adaptation.

ASE's reader consumes one IdentityMapping and ignores space-group operators.
For asymmetric/multi-family files, expand source operators with ASE, then feed
a minimal in-memory P1 document back to the same ASE XSD reader. Original files,
cell vectors, and ordinary P1/molecular coordinates are never rewritten.
"""
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from ase.data import atomic_numbers
from ase.io import read
from ase.spacegroup import Spacegroup
from ase.spacegroup.spacegroup import spacegroup_from_data, SpacegroupError
from i18n.messages import i18n_msg


def _unsupported():
    return ValueError(i18n_msg('Unsupported XSD layout: expected one Molecule or SymmetrySystem with explicit Atom3d elements and one cell. Modified symmetry images, mixed occupancies and nested systems are not supported.', code='xsd.unsupported'))


def _numbers(text, size):
    try:
        values = np.array([float(value) for value in text.split(',')])
    except (AttributeError, ValueError) as exc:
        raise _unsupported() from exc
    if values.shape != (size,) or not np.isfinite(values).all():
        raise ValueError(i18n_msg('XSD coordinates, cell vectors and symmetry operators must contain the expected number of finite values.', code='xsd.finite'))
    return values


def _sites(nodes, *, periodic):
    symbols, coordinates = [], []
    for node in nodes:
        symbol = node.get('Components')
        if symbol not in atomic_numbers or symbol == 'X' or node.get('ImageOf'):
            raise _unsupported()
        if node.get('Occupancy') and float(node.get('Occupancy')) != 1:
            raise _unsupported()
        xyz = node.get('XYZ')
        # The ASE XSD periodic reader defines omitted XYZ as the origin. A
        # molecule has no such fallback; missing molecular positions are errors.
        if xyz is None and periodic:
            xyz = '0,0,0'
        coordinates.append(_numbers(xyz, 3))
        symbols.append(symbol)
    if not symbols:
        raise ValueError(i18n_msg('XSD contains no readable atoms.', code='xsd.empty'))
    return symbols, np.array(coordinates)


def _operators(spacegroup):
    raw = spacegroup.get('Operators')
    if not raw:
        if spacegroup.get('ITNumber', '1') != '1':
            raise _unsupported()
        raw = '1,0,0,0,0,1,0,0,0,0,1,0'
    matrices = np.array([_numbers(value, 12).reshape(3, 4) for value in raw.split(':')])
    rotations, translations = matrices[:, :, :3], matrices[:, :, 3]
    if (not np.allclose(rotations, np.rint(rotations), rtol=0, atol=1e-10)
            or not np.allclose(np.abs(np.linalg.det(rotations)), 1, rtol=0, atol=1e-10)):
        raise _unsupported()
    try:
        number = int(spacegroup.get('ITNumber', '1'))
        counts = set()
        for setting in [1, 2]:
            try:
                counts.add(len(Spacegroup(number, setting=setting).get_symop()))
            except (ValueError, SpacegroupError):
                pass
    except (ValueError, TypeError) as exc:
        raise _unsupported() from exc
    operations = {(tuple(rotation.astype(int).flat), tuple(np.round(translation % 1, 10)))
                  for rotation, translation in zip(rotations, translations)}
    if len(rotations) not in counts or len(operations) != len(rotations):
        raise ValueError(i18n_msg('XSD symmetry operators are incomplete or duplicated for the declared space group; expansion was refused.', code='xsd.symmetry_count'))
    return rotations.astype(int), translations


def _p1_document(symbols, scaled, cell):
    root = ET.Element('XSD')
    atr = ET.SubElement(root, 'AtomisticTreeRoot')
    system = ET.SubElement(atr, 'SymmetrySystem')
    mappings = ET.SubElement(system, 'MappingSet')
    family = ET.SubElement(mappings, 'MappingFamily')
    identity = ET.SubElement(family, 'IdentityMapping')
    for symbol, position in zip(symbols, scaled):
        ET.SubElement(identity, 'Atom3d', Components=symbol,
                      XYZ=','.join(format(value, '.17g') for value in position))
    ET.SubElement(identity, 'SpaceGroup', **{
        key: ','.join(format(value, '.17g') for value in vector)
        for key, vector in zip(['AVector', 'BVector', 'CVector'], cell)})
    return ET.tostring(root, encoding='utf-8')


def read_xsd(path: str | Path):
    """Return ASE Atoms and import notes; never create a separate structure model."""
    try:
        raw = Path(path).read_bytes()
        root = ET.fromstring(raw)
        atrs = root.findall('AtomisticTreeRoot')
        if root.tag != 'XSD' or len(atrs) != 1:
            raise _unsupported()
        systems = [node for node in atrs[0] if node.tag in {'Molecule', 'SymmetrySystem'}]
        if len(systems) != 1:
            raise _unsupported()
        system = systems[0]
        periodic = system.tag == 'SymmetrySystem'
        notes = []
        if not periodic:
            if len(root.findall('.//Molecule')) != 1 or root.findall('.//SymmetrySystem') or root.findall('.//SpaceGroup'):
                raise _unsupported()
            symbols, coordinates = _sites(system.findall('Atom3d'), periodic=False)
            if len(system.findall('Atom3d')) != len(root.findall('.//Atom3d')):
                raise _unsupported()
            atoms = read(BytesIO(raw), format='xsd')
            expected = coordinates
            expected_cell = np.zeros((3, 3))
        else:
            if len(root.findall('.//SymmetrySystem')) != 1 or root.findall('.//Molecule'):
                raise _unsupported()
            if system.get('Normalized', '1') != '1':
                raise _unsupported()
            families = system.findall('MappingSet/MappingFamily')
            identities = [node for family in families for node in family.findall('IdentityMapping')]
            if not identities or len(identities) != len(families):
                raise _unsupported()
            if any(family.findall('.//Vacancy') for family in families
                   if family.findall('IdentityMapping/Atom3d')):
                raise _unsupported()
            groups = [node for identity in identities for node in identity.findall('SpaceGroup')]
            if len(groups) != 1 or len(root.findall('.//SpaceGroup')) != 1:
                raise _unsupported()
            group = groups[0]
            expected_cell = np.array([_numbers(group.get(key), 3) for key in ['AVector', 'BVector', 'CVector']])
            if abs(np.linalg.det(expected_cell)) < 1e-8:
                raise ValueError(i18n_msg('XSD periodic cell is missing or degenerate; no cell will be invented.', code='xsd.cell'))
            nodes = [node for identity in identities for node in identity.findall('Atom3d')]
            symbols, coordinates = _sites(nodes, periodic=True)
            ids = {node.get('ID') for node in nodes if node.get('ID')}
            for identity in identities:
                if identity.get('Element') and not np.allclose(_numbers(identity.get('Element'), 12),
                        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0], rtol=0, atol=1e-10):
                    raise _unsupported()
            for node in system.findall('.//ImageMapping/Atom3d'):
                if node.get('Components') or node.get('XYZ') or node.get('ImageOf') not in ids:
                    raise _unsupported()
            if len(nodes) + len(system.findall('.//ImageMapping/Atom3d')) != len(root.findall('.//Atom3d')):
                raise _unsupported()
            rotations, translations = _operators(group)
            is_p1 = len(rotations) == 1 and np.array_equal(rotations[0], np.eye(3)) and np.allclose(translations[0], 0)
            if is_p1 and group.get('ITNumber', '1') != '1':
                raise _unsupported()
            expanded = False
            if not is_p1:
                sg = spacegroup_from_data(no=1, setting=1, sitesym=[], centrosymmetric=False,
                    subtrans=[[0, 0, 0]], rotations=rotations, translations=translations)
                sites, kinds = sg.equivalent_sites(coordinates, onduplicates='keep', symprec=1e-8)
                # A complete, explicitly listed unit cell keeps its original
                # order and coordinates. Partially expanded/mixed site lists
                # are rejected instead of silently discarding duplicate sites.
                if len(sites) == len(coordinates):
                    matched = []
                    for symbol, point in zip(symbols, coordinates):
                        delta = sites - point
                        delta -= np.rint(delta)
                        indices = np.flatnonzero(np.max(np.abs(delta), axis=1) < 1e-8)
                        if len(indices) != 1 or symbols[kinds[int(indices[0])]] != symbol:
                            raise _unsupported()
                        matched.append(int(indices[0]))
                    if len(set(matched)) != len(matched):
                        raise _unsupported()
                else:
                    sites, kinds = sg.equivalent_sites(coordinates, onduplicates='error', symprec=1e-8)
                    original_count = len(symbols)
                    symbols = [symbols[index] for index in kinds]
                    coordinates = sites
                    expanded = True
                    notes.append(i18n_msg('Expanded source XSD symmetry with ASE: {sites} asymmetric sites → {atoms} unit-cell atoms. Display images were excluded; the original cell vectors are unchanged.', code='xsd.expanded', sites=original_count, atoms=len(symbols)))
            if len(identities) == 1 and not expanded:
                atoms = read(BytesIO(raw), format='xsd')
            else:
                atoms = read(BytesIO(_p1_document(symbols, coordinates, expected_cell)), format='xsd')
            expected = coordinates @ expected_cell
        positions, cell = atoms.get_positions(), atoms.cell.array
        if (len(atoms) == 0 or atoms.get_chemical_symbols() != symbols
                or positions.shape != (len(symbols), 3) or cell.shape != (3, 3)
                or not np.isfinite(positions).all() or not np.isfinite(cell).all()
                or not np.allclose(positions, expected, rtol=1e-12, atol=1e-12)
                or not np.allclose(cell, expected_cell, rtol=1e-12, atol=1e-12)
                or (not periodic and atoms.pbc.any())):
            raise ValueError(i18n_msg('ASE XSD output does not match the validated elements, coordinate order or cell; import was cancelled.', code='xsd.mismatch'))
        notes.append(i18n_msg('XSD imports elements, coordinates, cell and readable PBC only. Force fields, bond orders, formal charges, source constraints and display settings are not imported.', code='xsd.properties'))
        atoms.info['cp2k_studio_structure_type'] = 'periodic_structure' if periodic else 'isolated_molecule'
        return atoms, notes
    except Exception as exc:
        raise ValueError(i18n_msg('Cannot import Materials Studio XSD: {detail}', code='xsd.failed', detail=exc)) from exc
