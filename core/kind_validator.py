"""Element-aware database selection validation and source resolution."""
from i18n.messages import i18n_msg, i18n_str
from dataclasses import dataclass, field
from pathlib import Path
from hashlib import sha256
from core.database_manager import default_catalog, scan_databases
from core.models import DatabaseSettings, DatabaseReference


@dataclass(frozen=True)
class KindIssue:
    severity: str
    label: str
    message: str


@dataclass
class KindValidation:
    issues: list[KindIssue] = field(default_factory=list)
    selected: dict = field(default_factory=dict)

    @property
    def errors(self):
        return [i18n_msg('KIND {p0}：{p1}', p0=i.label, p1=i.message) for i in self.issues if i.severity=='Error']


def project_catalog(project, *, force_reload=False):
    refs = [(category,ref) for kind in project.kinds.values()
            for category,ref in [('basis',kind.basis_ref),('potential',kind.potential_ref)] if ref]
    explicit = [('basis',p) for p in project.dft.basis_files] + [
        ('potential',p) for p in project.dft.potential_files or ([project.dft.potential_file] if project.dft.potential_file else [])]
    refs += [(category,DatabaseReference(path=p,version='')) for category,p in explicit if Path(p).expanduser().is_file()]
    if project.databases == DatabaseSettings() and not refs:
        return scan_databases() if force_reload else default_catalog()
    return scan_databases(project.databases,refs)


def active_kinds(project):
    return project.structure.kind_elements if project.structure else {}


def configured_kind_labels(project, catalog=None):
    """Resolve real selections, including stale references and on-disk sources.

    Compatibility warnings remain warnings; completion is not a convergence
    claim. Read each selected source once without reparsing the database.
    """
    catalog = catalog or project_catalog(project)
    validation = validate_kinds(project, catalog)
    invalid = {issue.label for issue in validation.issues if issue.severity == 'Error'}
    digests, configured = {}, set()
    for label, entries in validation.selected.items():
        if label in invalid or len(entries) != 2:
            continue
        available = True
        for entry in entries.values():
            if entry.path not in digests:
                try:
                    digests[entry.path] = sha256(Path(entry.path).read_bytes()).hexdigest()
                except OSError:
                    digests[entry.path] = None
            if entry.version != project.cp2k_version or digests[entry.path] != entry.file_sha256:
                available = False
        if available:
            configured.add(label)
    return configured


def element_configuration_progress(project, catalog=None):
    """Count elements only when all of their active KINDs are configured."""
    mapping = active_kinds(project)
    if not mapping:
        return 0, 0
    configured = configured_kind_labels(project, catalog)
    elements = set(mapping.values())
    completed = sum(all(label in configured for label, actual in mapping.items() if actual == element)
                    for element in elements)
    return completed, len(elements)


def resource_paths(project,catalog=None):
    catalog = catalog or project_catalog(project)
    basis, potential = [], []
    for category, values, dest in [('basis',project.dft.basis_files,basis),
                                  ('potential',project.dft.potential_files or ([project.dft.potential_file] if project.dft.potential_file else []),potential)]:
        for value in values:
            resolved = catalog.path_for(value,category)
            if resolved:
                dest.append(resolved)
    for label in active_kinds(project):
        kind = project.kinds.get(label)
        if kind:
            if kind.basis_ref:
                basis.append(i18n_str(Path(kind.basis_ref.path).expanduser().resolve()))
            if kind.potential_ref:
                potential.append(i18n_str(Path(kind.potential_ref.path).expanduser().resolve()))
    return list(dict.fromkeys(basis)),list(dict.fromkeys(potential))


def validate_kinds(project,catalog=None):
    catalog = catalog or project_catalog(project)
    result = KindValidation()
    paths = dict(zip(['basis','potential'],resource_paths(project,catalog)))
    for label, element in active_kinds(project).items():
        kind = project.kinds.get(label)
        def issue(severity,message):
            result.issues.append(KindIssue(severity,label,message))
        if not kind or not kind.basis_set or not kind.potential:
            issue('Error',i18n_msg('Explicitly select both a basis set and a pseudopotential', code='studio.c1c1399a7e3a8dd0'))
            continue
        if kind.element and kind.element != element:
            issue('Error',i18n_msg('ELEMENT {p0} differs from the actual structure element {p1}', code='studio.f99304f78a38574e', p0=kind.element, p1=element))
        selected = {}
        for category,name,ref in [('basis',kind.basis_set,kind.basis_ref),('potential',kind.potential,kind.potential_ref)]:
            search_paths = [i18n_str(Path(ref.path).expanduser().resolve())] if ref else paths[category]
            matches = [entry for path in search_paths for entry in catalog.find(category,element,name,path)]
            if not matches:
                issue('Error',i18n_msg('{p0} was not found in the loaded {p1} database for this element, or its source is missing / has an unknown version', code='studio.864dee99194af37a', p0=name, p1=category))
                continue
            entry = matches[0]
            selected[category] = entry
            if ref:
                if ref.version != project.cp2k_version:
                    issue('Error',i18n_msg('The recorded version {p1} for {p0} does not match the target', code='studio.ecc1d42b3538a37c', p0=name, p1=ref.version or i18n_msg('Unknown', code='studio.4d8c1c5b42830791')))
                if ref.sha256 and ref.sha256 != entry.file_sha256:
                    issue('Error',i18n_msg('The database fingerprint for {p0} changed; the original selection was preserved. Review and reselect it.', code='studio.98026d6a5b4e1862', p0=name))
                if ref.entry_sha256 and ref.entry_sha256 != entry.content_sha256:
                    issue('Error',i18n_msg('The entry contents for {p0} changed', code='studio.4e7e13f5909ec162', p0=name))
            # For basis files CP2K uses ordered lookup. Reject shadowing rather
            # than silently using a different entry than the selected one.
            ordered = [e for path in paths[category] for e in catalog.find(category,element,name,path)]
            if category=='basis' and ordered and ordered[0].content_sha256 != entry.content_sha256:
                issue('Error',i18n_msg('A higher-priority basis with the same name shadows {p0}; adjust library order or exclude the conflict', code='studio.0ffce5de7709947b', p0=name))
            if any(e.content_sha256 != entry.content_sha256 for e in ordered):
                issue('Warning',i18n_msg('{p0} has different contents under the same name; resolved using the recorded file / priority', code='studio.2968c01f2f57b28a', p0=name))
        if len(selected) != 2:
            continue
        basis,potential = selected['basis'],selected['potential']
        result.selected[label] = selected
        if basis.q is not None and potential.q is not None:
            if basis.q != potential.q:
                issue('Error',i18n_msg('Basis q{p0} differs from pseudopotential q{p1}', code='studio.fe1a31a6ced795a1', p0=basis.q, p1=potential.q))
        else:
            issue('Warning',i18n_msg('Missing q information; valence electron compatibility cannot be confirmed automatically', code='studio.b3684135c1beed9b'))
        xc = project.dft.xc_functional
        if potential.xc and xc and potential.xc != xc:
            issue('Warning',i18n_msg('Pseudopotential XC={p0} differs from the current functional {p1}; please review', code='studio.4f5014984d8ce4ea', p0=potential.xc, p1=xc))
        elif not potential.xc or not xc:
            issue('Warning',i18n_msg('XC label is unknown; functional compatibility cannot be confirmed automatically', code='studio.3f8e745f847d07f5'))
        if any(n.upper() in {'ALL','ALLELECTRON'} for n in potential.names) or not potential.name.upper().startswith('GTH-'):
            issue('Error',i18n_msg('The current method is GPW/GTH; all-electron and non-GTH potentials are not supported', code='studio.a85b961961646612'))
        if 'GTH' not in basis.tags:
            issue('Warning',i18n_msg('The basis is not explicitly tagged GTH; suitability for GPW/GTH cannot be confirmed automatically', code='studio.f064f75b7d13f10c'))
        if 'ALL' in basis.tags or any(n.lower().endswith('-ae') or 'ALLELECTRON' in n.upper() for n in basis.names):
            issue('Error',i18n_msg('The current GPW/GTH workflow does not support all-electron bases; GAPW/all-electron calculations are not implemented', code='studio.afbe1290da67b26c'))
        if basis.xc and xc and basis.xc != xc:
            issue('Warning',i18n_msg('Basis label XC={p0} differs from the current functional {p1}; please review', code='studio.a0b9a0e806c1036f', p0=basis.xc, p1=xc))
        if basis.family == 'UZH' or potential.family == 'UZH':
            issue('Warning',i18n_msg('UZH protocol matching is not independently verified; matching q/XC names does not prove protocol compatibility', code='studio.23d5410b387d104b'))
            if basis.family != potential.family:
                issue('Error',i18n_msg('UZH bases and non-UZH pseudopotentials cannot be treated as one protocol; select a matching source family or conventional library', code='studio.2b5bacc5adced7b1'))
    # A merged potential cannot contain ambiguous names for one element.
    lookup = {}
    for label,selected in result.selected.items():
        k = project.kinds[label]
        key = (selected['potential'].element,k.potential)
        old = lookup.get(key)
        if old and old != selected['potential'].content_sha256:
            result.issues.append(KindIssue('Error',label,i18n_msg('The same element / pseudopotential name has different selected contents and cannot be merged unambiguously', code='studio.cd405a7b1d8fb5d5')))
        lookup[key] = selected['potential'].content_sha256
    return result
