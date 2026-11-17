"""Check actual generated files; never launch a shell, MPI or CP2K."""
from i18n.messages import i18n_msg, i18n_join
from pathlib import Path
from hashlib import sha256
import shlex
from core.file_references import check_generated_dependencies, generated_file_references
from core.basis_database import parse_basis_file
from core.potential_database import parse_potential_file
from core.kind_validator import active_kinds, validate_kinds
from core.run_config import RunEnvironment
from core.run_script_generator import run_command, INPUT_FILENAME


def check_input_dependencies(project, text, directory, catalog, *, require_relative=False):
    errors = check_generated_dependencies(text, directory, require_relative=require_relative)
    if errors:
        return errors
    if project.global_settings.run_type == 'MD' and project.md.continue_from_restart:
        from core.md import inspect_restart
        restart_refs = [ref for ref in generated_file_references(text) if ref.keyword == 'RESTART_FILE_NAME']
        if len(restart_refs) != 1:
            errors.append(i18n_msg('MD: continuation requires exactly one final EXT_RESTART/RESTART_FILE_NAME reference.', code='md.package_restart_reference'))
        for ref in restart_refs:
            path = Path(directory) / ref.value
            try:
                inspect_restart(project, path)
                def digest(file):
                    checksum = sha256()
                    with Path(file).open('rb') as stream:
                        for block in iter(lambda: stream.read(1024 * 1024), b''):
                            checksum.update(block)
                    return checksum.digest()
                if digest(path) != digest(Path(project.md.restart_file).expanduser()):
                    raise ValueError(i18n_msg('MD: the copied restart differs from its source. The file may have changed during export; regenerate the package.', code='md.restart_copy_changed'))
            except (OSError, ValueError, TypeError, KeyError) as exc:
                errors.append(i18n_msg('MD: final packaged restart is invalid: {detail}', code='md.package_restart_error', detail=exc))
    selected = validate_kinds(project, catalog).selected
    libraries = {'basis': [], 'potential': []}
    for ref in generated_file_references(text):
        category = {'BASIS_SET_FILE_NAME': 'basis', 'POTENTIAL_FILE_NAME': 'potential'}.get(ref.keyword)
        if not category:
            continue
        path = Path(ref.value)
        path = path if path.is_absolute() else Path(directory) / path
        try:
            entries = (parse_basis_file if category == 'basis' else parse_potential_file)(path)
            libraries[category].extend(entries)
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append(i18n_msg('{p0}: cannot read the final referenced database {p1}: {p2}. Reload the data file.', code='studio.26b75527fa69b987', p0=ref.keyword, p1=ref.value, p2=exc))
    for label, element in active_kinds(project).items():
        kind = project.kinds.get(label)
        for category, name in [('basis', kind.basis_set if kind else ''),
                               ('potential', kind.potential if kind else '')]:
            matches = [entry for entry in libraries[category] if entry.element == element and name in entry.names]
            expected = selected.get(label, {}).get(category)
            if not matches or not expected or matches[0].content_sha256 != expected.content_sha256:
                errors.append(i18n_msg("KIND {p0}: the final INP's {p1} file does not contain the required {p2} / {p3} entry. Check data sources and file order, then reselect the entry.", code='studio.c3197cd5d0c68893', p0=label, p1=category, p2=element, p3=name))
    return list(dict.fromkeys(errors))


def check_run_files(project, directory):
    errors = []
    directory = Path(directory).resolve()
    try:
        config = RunEnvironment.model_validate(project.run_environment.model_dump())
        script = (directory / 'run.sh').read_text(encoding='utf-8')
        notes = (directory / 'EXPORT_NOTES.txt').read_text(encoding='utf-8')
        expected = run_command(config).splitlines()
        commands = [line.strip() for line in script.splitlines()
                    if line.strip().startswith(('export OMP_NUM_THREADS=', 'mpirun '))]
        if commands != expected:
            errors.append(i18n_msg('RUN_ENVIRONMENT: MPI/OpenMP settings or input.inp/output.out commands in run.sh differ from this configuration. Regenerate the package.', code='studio.cb047e962f3bc670'))
        if i18n_join('\n', expected) not in notes:
            errors.append(i18n_msg('RUN_ENVIRONMENT: the command in EXPORT_NOTES.txt differs from run.sh or the current configuration. Regenerate the package.', code='studio.7da13f14652b3504'))
        for line in [f'MPI Processes: {config.mpi_processes}', f'OpenMP Threads per Process: {config.omp_threads}',
                     f'Required Logical CPU Slots: {config.required_cpu_slots}', f'Entry Input: {INPUT_FILENAME}']:
            if line not in notes.splitlines():
                errors.append(i18n_msg('RUN_ENVIRONMENT: EXPORT_NOTES.txt has a missing or incorrect {p0} value. Regenerate the notes.', code='studio.9c398b954cb84e4c', p0=line))
        assignments = [line.partition('=')[2] for line in script.splitlines() if line.startswith('input_file=')]
        if len(assignments) != 1 or shlex.split(assignments[0]) != [INPUT_FILENAME]:
            errors.append(i18n_msg('RUN_ENVIRONMENT: run.sh does not use input.inp as its input filename. Regenerate the script.', code='studio.de517a7757ed9d74'))
        if not (directory / INPUT_FILENAME).is_file():
            errors.append(i18n_msg('RUN_ENVIRONMENT: the package is missing input.inp, which run.sh requires. Export again.', code='studio.6ae9a6ba2db87959'))
        if 'cd "$(dirname "${BASH_SOURCE[0]}")"' not in script:
            errors.append(i18n_msg('RUN_ENVIRONMENT: run.sh does not switch to the package directory; relative dependency paths cannot be guaranteed.', code='studio.6dcd8a964ebedc04'))
        if config.required_cpu_slots != config.mpi_processes * config.omp_threads:
            errors.append(i18n_msg('RUN_ENVIRONMENT: required logical cores do not equal MPI × OpenMP.', code='studio.7f70374bc3179a09'))
    except (OSError, ValueError, UnicodeError) as exc:
        errors.append(i18n_msg('RUN_ENVIRONMENT: runtime settings or script files are unavailable: {p0}. Check step 07 and export again.', code='studio.aa50f82ce236fac6', p0=exc))
    return errors
