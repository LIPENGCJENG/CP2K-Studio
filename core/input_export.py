"""Standalone INP delivery, using the existing generator and XML validator."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from dataclasses import dataclass
from pathlib import Path
from core.generator import generate_input, GenerationError
from core.validator import validate_project, InputValidator
from core.kind_validator import project_catalog
from core.database_resources import selected_resources, required_artifacts
from core.project_io import _atomic_text


@dataclass
class InputExportResult:
    path: Path
    dependencies: list[str]
    generated_files: list[Path]
    warnings: list[str]


def export_input(project, destination, *, overwrite=False):
    """Inline coordinates match the preview; only required sidecars are added."""
    catalog = project_catalog(project, force_reload=True)
    checked = validate_project(project, catalog)
    if not checked.ok:
        raise GenerationError(i18n_join('\n', checked.errors))
    text = generate_input(project, catalog=catalog)
    path = Path(destination).expanduser().resolve()
    if path.exists() and not overwrite:
        raise FileExistsError(i18n_msg('Input file already exists: {p0}', code='studio.dd30262c49175ad0', p0=path))
    artifacts = required_artifacts(project, catalog)
    if path.name in artifacts:
        raise ValueError(i18n_msg('INP filename conflicts with an automatically generated dependency', code='studio.238b96c601e33fdc'))
    for name, content in artifacts.items():
        sidecar = path.parent / name
        if sidecar.exists() and sidecar.read_text(encoding='utf-8') != content:
            raise FileExistsError(i18n_msg('Dependency already exists with different contents: {p0}. Choose a new folder or export a calculation package.', code='studio.c677e14a74bd0495', p0=sidecar))
    parsed = InputValidator(project.xml_spec).parse(text, path.parent)
    if parsed.ok:
        from core.vibrational import validate_spectroscopy_input
        parsed.errors.extend(validate_spectroscopy_input(project, parsed.tree))
    if not parsed.ok:
        raise GenerationError(i18n_join('\n', parsed.errors))
    created = []
    try:
        for name, content in artifacts.items():
            sidecar = path.parent / name
            if not sidecar.exists():
                _atomic_text(sidecar, content)
                created.append(sidecar)
        from core.bundle_checks import check_input_dependencies
        errors = check_input_dependencies(project, text, path.parent, catalog)
        if errors:
            raise GenerationError(i18n_join('\n', errors))
        _atomic_text(path, text)
    except Exception:
        for sidecar in created:
            sidecar.unlink(missing_ok=True)
        raise
    basis, potential = selected_resources(project, catalog)
    dependencies = basis + (potential if len(potential) == 1 else [i18n_str(path.parent / name) for name in artifacts])
    if project.global_settings.run_type == 'MD' and project.md.continue_from_restart:
        dependencies.append(project.md.restart_file)
    return InputExportResult(path, dependencies, [path.parent / name for name in artifacts], checked.warnings)
