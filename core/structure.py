"""ASE import/export boundary; never invent a cell or alter coordinates."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from pathlib import Path
from dataclasses import dataclass, field
import numpy as np
from ase import Atoms
from ase.io import read, write
from core.models import Structure, BoxGenerationSettings

SUPPORTED_STRUCTURE_FORMATS = (('.xsd', 'Materials Studio XSD'), ('.cif', 'CIF'),
                               ('.xyz', 'XYZ'), ('.extxyz', 'Extended XYZ'))
SUPPORTED_STRUCTURE_EXTENSIONS = tuple(extension for extension, _ in SUPPORTED_STRUCTURE_FORMATS)


def structure_file_filter():
    patterns = ' '.join(f'*{extension} *{extension.upper()}' for extension in SUPPORTED_STRUCTURE_EXTENSIONS)
    formats = ';;'.join(f'{name} (*{extension} *{extension.upper()})'
                        for extension, name in SUPPORTED_STRUCTURE_FORMATS)
    return i18n_msg('Supported Structures ({patterns});;{formats};;All Files (*)',
                    code='structure.file_filter', patterns=patterns, formats=formats)


@dataclass
class StructureImport:
    structure: Structure
    notices: list = field(default_factory=list)


def load_structure(path: str | Path) -> Structure:
    return load_structure_with_report(path).structure


def load_structure_with_report(path: str | Path) -> StructureImport:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_STRUCTURE_EXTENSIONS:
        raise ValueError(i18n_msg('Only XSD, CIF, XYZ, and EXTXYZ files are supported', code='studio.304d6824d7aef772'))
    notices = []
    if suffix == '.xsd':
        from core.xsd_import import read_xsd
        atoms, notices = read_xsd(path)
    else:
        images = read(i18n_str(path), index=':', format='cif' if suffix == '.cif' else 'extxyz')
        if len(images) != 1:
            raise ValueError(i18n_msg('The file must contain exactly one structure; select and save the required frame separately', code='studio.cbc2777159c49897'))
        atoms = images[0]
    occupancy = atoms.info.get('occupancy', {})
    if any(len(v) != 1 or any(abs(float(n) - 1) > 1e-8 for n in v.values()) for v in occupancy.values()):
        raise ValueError(i18n_msg('Partial or mixed CIF occupancies are not supported; construct an explicit ordered structure first', code='studio.6ab570a20987cc3f'))
    structure = Structure(symbols=atoms.get_chemical_symbols(), positions=atoms.positions.tolist(),
                     cell=atoms.cell.array.tolist(),
                     periodic=i18n_join('', (a for a, p in zip('XYZ', atoms.pbc) if p)) or 'NONE',
                     structure_type=atoms.info['cp2k_studio_structure_type'] if suffix == '.xsd' else 'unclassified',
                     source=i18n_str(path.resolve()))
    return StructureImport(structure, notices)


def generate_nonperiodic_box(structure: Structure, vacuum: float) -> Structure:
    """Backward-compatible padding API, using the shared box/centering engine."""
    settings = structure.box_generation.model_dump()
    settings.update(mode='VACUUM_PADDING', vacuum_margin=vacuum)
    return generate_simulation_box(structure, BoxGenerationSettings.model_validate(settings))


def generate_simulation_box(structure: Structure, settings: BoxGenerationSettings) -> Structure:
    """Explicit, atomic operation on current Cartesian bounds, never old cells."""
    settings = BoxGenerationSettings.model_validate(settings.model_dump())
    structure = Structure.model_validate(structure.model_dump())
    if structure.periodic != 'NONE' or not structure.symbols:
        raise ValueError(i18n_msg('A simulation box can only be generated for a nonempty nonperiodic structure.', code='xsd.box_structure'))
    positions = np.asarray(structure.positions, dtype=float)
    lower = positions.min(axis=0)
    span = np.ptp(positions, axis=0)
    if settings.mode == 'VACUUM_PADDING':
        lengths = span + 2 * settings.vacuum_margin
    elif settings.mode == 'CUBIC':
        lengths = np.full(3, float(span.max() + 2 * settings.cubic_margin))
    else:
        if settings.manual_lengths is None:
            raise ValueError(i18n_msg('Enter all three A/B/C box lengths.', code='box.missing_lengths'))
        lengths = np.asarray(settings.manual_lengths, dtype=float)
        small = np.flatnonzero(lengths < span - 1e-10)
        if len(small):
            axes = ', '.join(f'{"XYZ"[i]} ({span[i]:.12g} > {lengths[i]:.12g} Å)' for i in small)
            raise ValueError(i18n_msg('The box is too small along {axes}. Increase the corresponding A/B/C lengths; no coordinates were changed.', code='box.too_small', axes=axes))
    # The bounding-box center (not the center of mass) is placed at L/2.
    centered = positions - (lower + span / 2) + lengths / 2
    data = structure.model_dump()
    data.update(positions=centered.tolist(), cell=np.diag(lengths).tolist(),
                box_vacuum_margin=settings.vacuum_margin, box_generation=settings.model_dump())
    return Structure.model_validate(data)


def to_atoms(structure: Structure) -> Atoms:
    return Atoms(symbols=structure.symbols, positions=structure.positions,
                 cell=structure.cell, pbc=[a in structure.periodic for a in 'XYZ'])


def write_structure(structure: Structure, path: str | Path):
    if structure.kind_labels:
        lines = [i18n_str(len(structure.symbols)),'CP2K KIND-labelled coordinates; Angstrom']
        lines += [label+' '+i18n_join(' ', (format(v,'.16g') for v in p)) for label,p in zip(structure.labels,structure.positions)]
        Path(path).write_text(i18n_join('\n', lines)+'\n',encoding='utf-8')
        return
    write(i18n_str(path), to_atoms(structure), format='xyz')
