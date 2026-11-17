"""Resolve selected files and prepare the single CP2K potential-file artifact."""
from i18n.messages import i18n_join
from core.kind_validator import project_catalog, resource_paths, validate_kinds

MERGED_POTENTIAL = 'studio_potentials.dat'


def selected_resources(project,catalog=None):
    catalog = catalog or project_catalog(project)
    basis,potential = resource_paths(project,catalog)
    return basis,potential


def required_artifacts(project,catalog=None):
    catalog = catalog or project_catalog(project)
    _,paths = selected_resources(project,catalog)
    if len(paths) <= 1:
        return {}
    checked = validate_kinds(project,catalog)
    if checked.errors:
        raise ValueError(i18n_join('\n', checked.errors))
    blocks = ['# CP2K Studio: selected records from pinned/explicit source databases.\n']
    seen = set()
    for label,entries in checked.selected.items():
        entry = entries['potential']
        chosen = project.kinds[label].potential
        key = (entry.element,chosen)
        if key in seen:
            continue
        seen.add(key)
        # Keep only the chosen identifier. Removing unrelated aliases prevents
        # two valence variants from sharing an ambiguous generic alias.
        blocks.append(f'# Source: {entry.path}\n# File SHA256: {entry.file_sha256}\n')
        blocks.append(entry.render((chosen,)))
    return {MERGED_POTENTIAL:i18n_join('\n', blocks)}
