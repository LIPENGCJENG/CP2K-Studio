"""Stable-ID selection and fixed-atom editing; never move or center atoms."""
from i18n.messages import i18n_msg
import math
from core.models import FixedAtom, Structure

COMPONENTS = ('XYZ', 'X', 'Y', 'Z', 'XY', 'XZ', 'YZ')
RANGE_TOLERANCE = 1e-9  # absolute Angstrom tolerance, independent of cell axes


def select_coordinate_range(structure, axis, minimum, maximum):
    if axis not in ('X', 'Y', 'Z'):
        raise ValueError(i18n_msg('Coordinate axis must be X, Y, or Z', code='studio.8537e7a03aeab99a'))
    try:
        minimum, maximum = float(minimum), float(maximum)
    except (ValueError, TypeError) as exc:
        raise ValueError(i18n_msg('Minimum and maximum must be valid numbers (scientific notation is supported)', code='studio.f0902162e8a7f393')) from exc
    if not math.isfinite(minimum) or not math.isfinite(maximum):
        raise ValueError(i18n_msg('Coordinate range must be finite', code='studio.0406fe44a28c5977'))
    if minimum > maximum:
        raise ValueError(i18n_msg('Minimum cannot exceed maximum', code='studio.94dcd65668a3a126'))
    if structure is None:
        return []
    index = 'XYZ'.index(axis)
    return [atom_id for atom_id, position in zip(structure.atom_ids, structure.positions)
            if minimum - RANGE_TOLERANCE <= position[index] <= maximum + RANGE_TOLERANCE]


def set_fixed_atoms(structure, atom_ids, components=None):
    """Replace selected atoms' components, or remove them when None."""
    ids = set(atom_ids)
    if not ids <= set(structure.atom_ids):
        raise ValueError(i18n_msg('Selected atoms are no longer in the current structure; select them again', code='studio.8b9d8370a584c569'))
    if components is not None and components not in COMPONENTS:
        raise ValueError(i18n_msg('Unsupported fixed components', code='studio.be445cf0961ef93e'))
    fixed = {atom.atom_id: atom.components for atom in structure.fixed_atoms}
    for atom_id in ids:
        if components is None:
            fixed.pop(atom_id, None)
        else:
            fixed[atom_id] = components
    data = structure.model_dump()
    data['fixed_atoms'] = [FixedAtom(atom_id=i, components=fixed[i]).model_dump()
                           for i in structure.atom_ids if i in fixed]
    return Structure.model_validate(data)


def fixed_atom_groups(structure):
    """Convert stable identity to CP2K's current 1-based coordinate order."""
    fixed = {atom.atom_id: atom.components for atom in structure.fixed_atoms}
    groups = {}
    for number, atom_id in enumerate(structure.atom_ids, 1):
        if atom_id in fixed:
            groups.setdefault(fixed[atom_id], []).append(number)
    return {components: groups[components] for components in COMPONENTS if components in groups}
