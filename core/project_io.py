"""JSON projects are self-contained; exports are validated, staged bundles."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile
from core.models import Project
from core.generator import GenerationError
from core.validator import InputValidator, validate_project
from core.structure import write_structure
from core.kind_validator import project_catalog
from core.database_resources import selected_resources, required_artifacts
from core.file_references import safe_resource_name
from core.run_config import migrate_run_environment
from core.run_script_generator import generate_run_script
from core.export_notes_generator import generate_export_notes
from core.resources import relocated_database


def relocate_project_resources(project):
    """Rebind verified, missing built-in library paths after an App move.

    Leave custom paths, existing files, unknown fingerprints and all scientific
    fields untouched. The original project/preset document is never rewritten.
    """
    data = project.model_dump()
    mapping = {}
    for kind in data['kinds'].values():
        for key in ['basis_ref', 'potential_ref']:
            ref = kind[key]
            if ref:
                current = relocated_database(ref['path'], ref['sha256'])
                if current:
                    mapping[ref['path']] = current
    if not mapping:
        return project
    for key in ['basis_files', 'potential_files']:
        data['dft'][key] = [mapping.get(p, p) for p in data['dft'][key]]
    data['dft']['potential_file'] = mapping.get(data['dft']['potential_file'], data['dft']['potential_file'])
    for kind in data['kinds'].values():
        for key in ['basis_ref', 'potential_ref']:
            if kind[key]:
                kind[key]['path'] = mapping.get(kind[key]['path'], kind[key]['path'])
    for entry in data['databases']['custom_files']:
        entry['path'] = mapping.get(entry['path'], entry['path'])
    return Project.model_validate(data)


def _atomic_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _resolved_resources(project: Project, base: Path):
    project = relocate_project_resources(project)
    data = project.model_dump()
    def resolved(p):
        if not p:
            return p
        path = Path(p).expanduser()
        if not path.is_absolute() and ((base / path).is_file() or '/' in p or '\\' in p):
            return i18n_str((base / path).resolve())
        return i18n_str(path) if path.is_absolute() else p
    data['dft']['basis_files'] = [resolved(p) for p in data['dft']['basis_files']]
    data['dft']['potential_file'] = resolved(data['dft']['potential_file'])
    data['dft']['potential_files'] = [resolved(p) for p in data['dft']['potential_files']]
    if data['md']['restart_file']:
        data['md']['restart_file'] = i18n_str((base / Path(data['md']['restart_file']).expanduser()).resolve())
    for kind in data['kinds'].values():
        for name in ['basis_ref','potential_ref']:
            if kind[name]:
                kind[name]['path'] = resolved(kind[name]['path'])
    if data['databases']['data_directory']:
        data['databases']['data_directory'] = resolved(data['databases']['data_directory'])
    for item in data['databases']['custom_files']:
        item['path'] = resolved(item['path'])
    if data['xml_spec']:
        data['xml_spec'] = resolved(data['xml_spec'])
    return Project.model_validate(data)


def save_project(project: Project, path: str | Path):
    # Resolve actual local files against the current working directory before saving.
    normalized = _resolved_resources(project, Path.cwd())
    _atomic_text(Path(path), normalized.model_dump_json(indent=2) + '\n')


def load_project(path: str | Path) -> Project:
    path = Path(path)
    if path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError(i18n_msg('Project file exceeds the 100 MB limit', code='studio.d6a7040604825764'))
    data, notices = migrate_run_environment(json.loads(path.read_text(encoding='utf-8')))
    project = _resolved_resources(Project.model_validate(data), path.resolve().parent)
    project._migration_warnings = notices
    return project


def _write_bundle_files(project, staged, catalog, result, copy_resources=True):
    """Prepare the same export artifacts for delivery or temporary checks."""
    exported = project.model_copy(deep=True)
    copied = {}
    def resource(value):
        source = Path(value).expanduser()
        if not copy_resources or not source.is_file():
            return value
        source = source.resolve()
        if source not in copied:
            folder = staged / 'data'
            folder.mkdir(exist_ok=True)
            name = f'{len(copied)+1}_{safe_resource_name(source.name)}'
            shutil.copy2(source, folder / name)
            copied[source] = 'data/' + name
        return copied[source]
    basis_paths,potential_paths = selected_resources(project,catalog)
    exported.dft.basis_files = [resource(p) for p in basis_paths]
    exported.dft.potential_files = [resource(p) for p in potential_paths]
    exported.dft.potential_file = exported.dft.potential_files[0] if exported.dft.potential_files else ''
    for kind in exported.kinds.values():
        for name in ['basis_ref','potential_ref']:
            ref = getattr(kind,name)
            if ref:
                ref.path = resource(ref.path)
    # Preserve the explicit source classification and version for copied files.
    from core.models import CustomDatabase
    exported.databases.data_directory = ''
    exported.databases.declared_version = ''
    exported.databases.custom_files = [CustomDatabase(path=resource(p),category=category,version=project.cp2k_version)
        for category,paths in [('basis',basis_paths),('potential',potential_paths)] for p in paths]
    # Serialize the final safe bindings directly; never serialize unsafe
    # source filenames first or rewrite the completed INP as text.
    from core.generator import build_sections
    bindings = dict(zip(basis_paths, exported.dft.basis_files))
    bindings.update(zip(potential_paths, exported.dft.potential_files))
    if project.global_settings.run_type == 'MD' and project.md.continue_from_restart:
        exported.md.restart_file = resource(project.md.restart_file)
        bindings[project.md.restart_file] = exported.md.restart_file
    sections = build_sections(project, 'structure.xyz', catalog, file_bindings=bindings)
    inp = i18n_join('\n\n', (i18n_join('\n', s.render()) for s in sections)) + '\n'
    for name,text in required_artifacts(project,catalog).items():
        (staged/name).write_text(text,encoding='utf-8')
    write_structure(project.structure, staged / 'structure.xyz')
    (staged / 'input.inp').write_text(inp, encoding='utf-8')
    # Use the bundled XML after reopening an export unless a custom XML was supplied.
    if project.xml_spec:
        shutil.copy2(project.xml_spec, staged / 'cp2k_input.xml')
        exported.xml_spec = './cp2k_input.xml'
    (staged / 'project.cp2kstudio.json').write_text(exported.model_dump_json(indent=2)+'\n', encoding='utf-8')
    script = staged / 'run.sh'
    script.write_text(generate_run_script(project.run_environment), encoding='utf-8', newline='\n')
    try:
        script.chmod(0o755)
    except OSError:
        pass  # bash run.sh does not require an executable permission bit.
    files = [p.relative_to(staged).as_posix() for p in staged.rglob('*') if p.is_file()]
    external = [p for p in basis_paths + potential_paths if Path(p).expanduser().resolve() not in copied]
    if project.global_settings.run_type == 'MD' and project.md.continue_from_restart and not copy_resources:
        external.append(project.md.restart_file)
    (staged / 'EXPORT_NOTES.txt').write_text(generate_export_notes(
        project, files + ['EXPORT_NOTES.txt'], result.warnings, external), encoding='utf-8', newline='\n')
    return inp


def export_bundle(project: Project, destination: str | Path, copy_resources: bool = True,
                  *, archive: bool = False) -> Path:
    """Create a new directory or ZIP; return the input path or the ZIP path.

    Existing destinations are never overwritten. ZIP entries are relative to
    the package root so the extracted folder can be moved as a whole.
    """
    project = _resolved_resources(project, Path.cwd())
    catalog = project_catalog(project, force_reload=True)
    result = validate_project(project,catalog)
    if not result.ok:
        raise GenerationError(i18n_join('\n', result.errors))
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(i18n_msg('Export folder already exists; choose a new folder: {p0}', code='studio.ca0a92650f6bc7e0', p0=destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix='.cp2k-studio-', dir=destination.parent))
    try:
        inp = _write_bundle_files(project, staged, catalog, result, copy_resources)
        inp = (staged / 'input.inp').read_text(encoding='utf-8')
        checked = InputValidator(project.xml_spec).parse(inp, staged)
        if checked.ok:
            from core.vibrational import validate_spectroscopy_input
            checked.errors.extend(validate_spectroscopy_input(project, checked.tree))
        if not checked.ok:
            raise GenerationError(i18n_join('\n', checked.errors))
        from core.bundle_checks import check_input_dependencies, check_run_files
        dependency_errors = check_input_dependencies(project, inp, staged, catalog, require_relative=copy_resources)
        run_errors = check_run_files(project, staged)
        if dependency_errors or run_errors:
            raise GenerationError(i18n_join('\n', dependency_errors + run_errors))
        files = [p.relative_to(staged).as_posix() for p in staged.rglob('*') if p.is_file()]
        if archive:
            zip_path = staged / '.bundle.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as handle:
                for name in sorted(files):
                    handle.write(staged / name, name)
            # Exclusive creation is portable to filesystems without hard links.
            # Remove an incomplete final copy if storage runs out during delivery.
            created = False
            try:
                with destination.open('xb') as target:
                    created = True
                    with zip_path.open('rb') as source:
                        shutil.copyfileobj(source, target)
            except BaseException:
                if created:
                    destination.unlink(missing_ok=True)
                raise
        else:
            staged.rename(destination)
    finally:
        if staged.exists():
            shutil.rmtree(staged)
    return destination if archive else destination / 'input.inp'
