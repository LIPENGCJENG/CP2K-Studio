"""One staged, non-executing configuration/XML/dependency/run check."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from core.models import Project
from core.schema import BUNDLED_XML
from core.validator import ValidationResult, InputValidator, validate_project
from core.kind_validator import project_catalog, resource_paths
from core.generator import generate_input
from core.file_references import FileReferenceError
from core.project_io import _resolved_resources, _write_bundle_files
from core.bundle_checks import check_input_dependencies, check_run_files


@dataclass
class CheckStage:
    name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)
    executed: bool = False
    reason: str = ''

    @property
    def state(self):
        return ('not_run' if not self.executed else 'error' if self.errors
                else 'warning' if self.warnings else 'ready')


@dataclass
class ComprehensiveResult:
    stages: list[CheckStage] = field(default_factory=lambda: [CheckStage(name) for name in
        [i18n_msg('Configuration Completeness', code='stage.configuration'), i18n_msg('XML Syntax Validation', code='stage.xml'), i18n_msg('External Dependencies', code='stage.dependencies'), i18n_msg('Runtime & Calculation Package', code='stage.runtime')]])
    signatures: dict = field(default_factory=dict)

    @property
    def validation(self):
        result = ValidationResult()
        for stage in self.stages:
            result.errors.extend(i18n_msg('[{p0}] {p1}', p0=stage.name, p1=text) for text in stage.errors)
            result.warnings.extend(i18n_msg('[{p0}] {p1}', p0=stage.name, p1=text) for text in stage.warnings)
            result.infos.extend(stage.infos)
        if not result.errors and any(not stage.executed for stage in self.stages):
            result.errors.append(i18n_msg('Required validation stages have not run. Correct the preceding issues and validate again.', code='studio.cff3cde96485c690'))
        return result

    def report(self):
        lines = [i18n_msg('CP2K Studio · Comprehensive Validation', code='studio.a313548c904ec74e'), 'CP2K Target: 2026.1', '']
        for index, stage in enumerate(self.stages, 1):
            lines.append(i18n_msg('[{p0}] {p1}', p0=index, p1=stage.name))
            if not stage.executed:
                lines.append(i18n_msg('○ Not run: ', code='studio.9912ba5b51b69dde') + stage.reason)
            else:
                lines.append({'ready': i18n_msg('✓ Passed', code='studio.d6c446460683f728'), 'warning': i18n_msg('! Warnings present', code='studio.a0245c0ceba51295'), 'error': i18n_msg('× Failed', code='studio.c7f4ebbc24b92c26')}[stage.state])
                lines.extend(i18n_msg('Error · ', code='studio.52d4395a320bcf3c') + text for text in stage.errors)
                lines.extend(i18n_msg('Warning · ', code='studio.45f51b987466bddc') + text for text in stage.warnings)
                lines.extend(i18n_msg('Info · ', code='validation.info_prefix') + text for text in stage.infos)
            lines.append('')
        result = self.validation
        summary = i18n_msg('Validation Failed', code='studio.cea8aae4ccdfeba2') if result.errors else i18n_msg('Validation Completed with Warnings', code='studio.c4fb32fba754cd3f') if result.warnings else i18n_msg('Validation Passed', code='studio.36f0f2f7ec0f4a31')
        lines += ['--------------------------------', summary,
                  i18n_msg('Errors: {p0}', code='studio.063abdaa463dea33', p0=len(result.errors)), i18n_msg('Warnings: {p0}', code='studio.a4924e37614f278b', p0=len(result.warnings)),
                  i18n_msg('No CP2K calculation was run. Static checks and XML syntax validation do not guarantee physical applicability or SCF convergence.', code='studio.712969f113692e34')]
        return i18n_join('\n', lines)


def file_signatures(paths):
    result = {}
    for value in paths:
        path = i18n_str(value)
        try:
            path = i18n_str(Path(value).expanduser().resolve())
            stat = Path(path).stat()
            result[path] = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino)
        except (OSError, ValueError, RuntimeError):
            result[path] = None
    return result


def source_signatures(project, catalog):
    basis, potential = resource_paths(project, catalog)
    paths = [*basis, *potential, project.xml_spec or BUNDLED_XML]
    paths.extend(item.path for item in project.databases.custom_files)
    if project.global_settings.run_type == 'MD' and project.md.continue_from_restart:
        paths.append(project.md.restart_file)
    return file_signatures(paths)


def comprehensive_check(project, *, draft_errors=(), validator_factory=None):
    result = ComprehensiveResult()
    configuration, xml, dependencies, run = result.stages
    configuration.executed = True
    try:
        project = _resolved_resources(Project.model_validate(project.model_dump()), Path.cwd())
        catalog = project_catalog(project, force_reload=True)
        result.signatures = source_signatures(project, catalog)
        local = validate_project(project, catalog)
        configuration.errors = list(dict.fromkeys([*draft_errors, *local.errors]))
        configuration.warnings = list(dict.fromkeys(local.warnings))
        configuration.infos = list(dict.fromkeys(local.infos))
    except Exception as exc:
        configuration.errors.append(i18n_msg('Invalid configuration: {p0}. Correct the fields, data sources, or runtime settings.', code='studio.043ec2473d76cc4a', p0=exc))
    if configuration.errors:
        for stage in result.stages[1:]:
            stage.reason = i18n_msg('Configuration completeness has blocking errors; a complete INP cannot be generated. Correct the first-stage issues first.', code='studio.b0d1609276358f00')
        return result
    try:
        validator = validator_factory(project) if validator_factory else InputValidator(project.xml_spec)
    except Exception as exc:
        xml.executed = True
        xml.errors.append(i18n_msg('XML schema unavailable: {p0}: {p1}. Select a valid 2026.1 file in XML Schema and retry.', code='studio.fc79ea0f09f3df0b', p0=project.xml_spec or BUNDLED_XML, p1=exc))
        dependencies.reason = run.reason = i18n_msg('XML schema is unavailable; no temporary calculation package was prepared.', code='studio.868e9f33b470b4b5')
        return result
    with TemporaryDirectory(prefix='cp2k-studio-check-') as temporary:
        directory = Path(temporary)
        try:
            bundle_text = _write_bundle_files(project, directory, catalog, local)
        except Exception as exc:
            dependencies.executed = True
            dependencies.errors.append(i18n_msg('Temporary package preparation failed: {p0}. Check source files and path permissions.', code='studio.ce74b6892260325e', p0=exc))
            xml.reason = run.reason = i18n_msg('Cannot prepare a complete package and final INP.', code='studio.ff2bb8484d57f177')
            return result
        xml.executed = True
        def parse(text, mode):
            try:
                parsed = validator.parse(text, directory)
                if parsed.ok:
                    from core.vibrational import validate_spectroscopy_input
                    parsed.errors.extend(validate_spectroscopy_input(project, parsed.tree))
                xml.errors.extend(i18n_msg('{p0}: {p1}', p0=mode, p1=error) for error in parsed.errors)
                xml.warnings.extend(parsed.warnings)
            except Exception as exc:
                xml.errors.append(i18n_msg('{p0}: XML validation service failed: {p1}. Check the schema and retry.', code='studio.16ee3017a83c1b3d', p0=mode, p1=exc))
        parse(bundle_text, i18n_msg('Package INP', code='studio.b0366e982a01c040'))
        inline_text = None
        try:
            inline_text = generate_input(project, catalog=catalog)
        except FileReferenceError as exc:
            dependencies.warnings.append(i18n_msg('Standalone INP cannot safely represent the source path: {p0}. Use the package with normalized paths.', code='studio.8c66fadfa9f5f384', p0=exc))
        except Exception as exc:
            xml.errors.append(i18n_msg('Standalone INP generation failed: {p0}. Correct the parameters and retry.', code='studio.c651d210d7125b83', p0=exc))
        if inline_text is not None:
            parse(inline_text, i18n_msg('Standalone INP', code='studio.5328fbb43263806e'))
        if not xml.errors:
            xml.infos.append(i18n_msg('CP2K 2026.1 XML validation passed; the final INP generated from this configuration was checked.', code='studio.47d98214973e699a'))
        dependencies.executed = True
        # Read the disk artifact again: preparation and parsing do not prove that
        # its final references still resolve from run.sh's working directory.
        try:
            final_text = (directory / 'input.inp').read_text(encoding='utf-8')
            dependencies.errors.extend(check_input_dependencies(project, final_text, directory, catalog, require_relative=True))
            if inline_text is not None:
                dependencies.errors.extend(check_input_dependencies(project, inline_text, directory, catalog))
        except (OSError, ValueError, UnicodeError) as exc:
            dependencies.errors.append(i18n_msg('Final input.inp or a dependency cannot be read: {p0}. Check the files and export again.', code='studio.864d370fa15ec908', p0=exc))
        if not dependencies.errors:
            dependencies.infos += [i18n_msg('Package: structure.xyz, basis and pseudopotential references are accessible and contain matching entries; INP paths are relative to the package.', code='studio.3664d2a34c19f65d'),
                                   i18n_msg('Standalone INP: coordinates are embedded; external basis/pseudopotential sources must remain accessible in the target environment. Merged files are generated alongside the INP.', code='studio.5f2292b560c08716')
                                   if inline_text is not None else i18n_msg('Standalone INP: path checks were skipped because source paths cannot be serialized safely; package paths were normalized.', code='studio.a84d03414247ea86')]
        run.executed = True
        run.errors.extend(check_run_files(project, directory))
        if not run.errors:
            config = project.run_environment
            run.infos += [i18n_msg('MPI: {p0} · OpenMP: {p1} · Required logical cores: {p2}', code='studio.ecaf21917207b4ae', p0=config.mpi_processes, p1=config.omp_threads, p2=config.required_cpu_slots),
                          i18n_msg('Commands, input/output filenames, and runtime settings agree in run.sh and EXPORT_NOTES.txt. Local CP2K/MPI installation was not checked.', code='studio.13bf4fcd8a5f60cf')]
    return result
