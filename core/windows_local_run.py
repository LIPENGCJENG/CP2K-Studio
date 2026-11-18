"""Windows Native Serial/OpenMP launch adapter, independent of Project."""
from dataclasses import dataclass, replace, asdict
from pathlib import Path
import base64
import os
import shutil
import subprocess
import sys
import time
import uuid

from core import local_run_runtime as runtime
from core.local_run import LocalRunError, LaunchResult, TITLES, runtime_messages
from core.environment_check import CommandRunner, cp2k_version, build_support, find_cp2k
from core.file_references import generated_file_references
from core.resources import user_data_directory, external_dll_search
from core.windows_executable import is_native_windows_program
from core.windows_run_config import (WindowsRunSettings, load_settings, save_settings,
    guess_dll_directory, runtime_environment, settings_path)
from i18n.messages import i18n_msg, i18n_str, i18n_render


@dataclass(frozen=True)
class ExecutableCheck:
    version: str
    mode: str
    signature: tuple[int, int]


@dataclass(frozen=True)
class WindowsPackage:
    directory: Path
    settings: WindowsRunSettings
    old_output: bool
    previous_uncertain: bool = False
    checked: ExecutableCheck | None = None
    error: object = ''
    native_windows: bool = True


def validate_native_directory(directory):
    path = Path(directory).expanduser().resolve()
    if not path.is_dir():
        raise LocalRunError(i18n_msg('Select an extracted calculation folder containing input.inp.', code='winrun.directory_error'))
    inp = path / 'input.inp'
    if not inp.is_file():
        raise LocalRunError(i18n_msg('Missing input.inp in the calculation folder.', code='winrun.input_missing'))
    try:
        if inp.stat().st_size > 100 * 1024 * 1024:
            raise ValueError('input.inp exceeds 100 MB')
        text = inp.read_text(encoding='utf-8-sig')
        if '\0' in text:
            raise ValueError('NUL in input.inp')
        # Complete Studio exports use literal filenames. Do not guess paths
        # produced by preprocessing or silently rewrite an external input.
        if any(line.lstrip().startswith('@') for line in text.splitlines()):
            raise LocalRunError(i18n_msg('Preprocessed INP files cannot be checked reliably here. Select a self-contained exported package; input.inp was not changed.', code='winrun.preprocessor'))
        for ref in generated_file_references(text):
            if '$' in ref.value or '@' in ref.value:
                raise LocalRunError(i18n_msg('Cannot resolve an input dependency: {path}', code='winrun.dependency_error', path=ref.value))
            dependency = Path(ref.value).expanduser()
            if not dependency.is_absolute():
                dependency = path / dependency
            with dependency.open('rb') as handle:
                handle.read(1)
    except (OSError, UnicodeError, ValueError) as exc:
        if isinstance(exc, LocalRunError):
            raise
        raise LocalRunError(i18n_msg('Cannot read input.inp or a referenced structure/database/restart file: {error}', code='winrun.input_error', error=str(exc))) from exc
    return path


def probe_executable(settings, *, environ=None, runner=None):
    if type(settings.omp_threads) is not int or settings.omp_threads < 1:
        raise LocalRunError(i18n_msg('OpenMP Threads must be a positive integer.', code='winrun.threads_error'))
    exe = Path(settings.executable).expanduser().resolve()
    if not exe.is_file() or exe.suffix.lower() != '.exe' or not is_native_windows_program(exe):
        raise LocalRunError(i18n_msg('Choose an existing native Windows CP2K .exe file.', code='winrun.exe_error'))
    if settings.dll_directory and not Path(settings.dll_directory).is_dir():
        raise LocalRunError(i18n_msg('Runtime DLL Directory does not exist: {path}', code='winrun.dll_error', path=settings.dll_directory))
    probe = runner or CommandRunner(environ=runtime_environment(settings, environ), timeout=8)
    result = probe([str(exe), '--version'])
    version, _, features = cp2k_version(result.output)
    if result.status != 'ok' or result.returncode != 0 or version is None:
        code = f'0x{(result.returncode & 0xffffffff):08X}' if isinstance(result.returncode, int) else result.status
        raise LocalRunError(i18n_msg('CP2K --version could not start successfully ({status}). Check Runtime DLL Directory, including libgfortran-5.dll for MSYS2 UCRT64. EXE existence alone does not verify its runtime.\n{detail}', code='winrun.probe_error', status=code, detail=result.output.strip()[-1800:]))
    (mpi, omp), _ = build_support(exe, features)
    if mpi or any(f in features for f in ['mpi','mpi_f08','parallel']) or mpi is None or omp is None:
        raise LocalRunError(i18n_msg('Windows Native currently requires a verified Serial/OpenMP build, normally cp2k.sopt.exe or cp2k.ssmp.exe. MPI/WSL launch is not configured.', code='winrun.mode_error'))
    if not omp and settings.omp_threads != 1:
        raise LocalRunError(i18n_msg('The selected CP2K build is Serial. Set OpenMP Threads to 1, or choose cp2k.ssmp.exe.', code='winrun.serial_threads'))
    stat = exe.stat()
    return ExecutableCheck(version, 'OpenMP' if omp else 'Serial', (stat.st_size, stat.st_mtime_ns))


def powershell_command(manifest, mode):
    """Only Base64 bytes and a fixed enum enter PowerShell source."""
    if mode not in {'run','monitor'}:
        raise ValueError('Unknown terminal mode')
    encoded_path = base64.b64encode(str(manifest).encode('utf-8')).decode('ascii')
    source = f'''$ErrorActionPreference = 'Stop'
$manifestPath = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_path}'))
$m = [IO.File]::ReadAllText($manifestPath, [Text.Encoding]::UTF8) | ConvertFrom-Json
$Host.UI.RawUI.WindowTitle = [string]$m.titles.{mode}
Set-Location -LiteralPath ([string]$m.directory)
$runner = @($m.runner)
$invokeArgs = @()
if ($runner.Count -gt 1) {{ $invokeArgs += $runner[1..($runner.Count - 1)] }}
$invokeArgs += @('{mode}', $manifestPath)
& ([string]$runner[0]) @invokeArgs
'''
    return base64.b64encode(source.encode('utf-16-le')).decode('ascii')


def terminal_commands(manifest, mode, environ):
    shell = next((p for name in ['pwsh.exe','powershell.exe']
                  if (p := shutil.which(name, path=environ.get('PATH','')))), None)
    if not shell:
        default = Path(environ.get('SystemRoot','C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        shell = str(default) if default.is_file() else None
    if not shell:
        raise LocalRunError(i18n_msg('PowerShell was not found. Install or enable PowerShell to open independent Windows consoles.', code='winrun.no_terminal'))
    command = [shell, '-NoLogo', '-NoProfile', '-NoExit', '-EncodedCommand', powershell_command(manifest, mode)]
    terminal = shutil.which('wt.exe', path=environ.get('PATH',''))
    return ([[terminal, '-w', 'new', 'new-tab', '--title', TITLES[mode], *command]] if terminal else []) + [command]


class WindowsLocalRunBackend:
    native_windows = True

    def __init__(self, *, cache=None, settings_file=None, environ=None, runner=None):
        self.cache = (Path(cache) if cache is not None else user_data_directory()/'local-run/windows-jobs').expanduser().resolve()
        self.settings_file = (Path(settings_file) if settings_file is not None else settings_path()).expanduser().resolve()
        self.environ = dict(os.environ if environ is None else environ)
        self.runner = runner
        self.detected_paths = ()

    def inspect(self, directory):
        directory = validate_native_directory(directory)
        risk = runtime.launch_risk(self.cache, directory)
        if risk == 'active':
            raise LocalRunError(i18n_msg('A calculation or pending terminal launch already exists for this folder. Check the existing terminals before starting another run.', code='local.active_directory'))
        saved = load_settings(self.settings_file)
        candidates = [*self.detected_paths, *([saved.executable] if saved.executable else []),
                      *find_cp2k(self.environ, 'Windows')]
        exe = next((str(Path(p).resolve()) for p in candidates if Path(p).is_file()
                    and Path(p).name.lower().endswith(('.ssmp.exe','.sopt.exe'))), '')
        if not exe:
            exe = next((str(Path(p).resolve()) for p in [*self.detected_paths, saved.executable]
                        if p and Path(p).is_file() and is_native_windows_program(p)), saved.executable)
        settings = replace(saved, executable=exe, dll_directory=guess_dll_directory(exe, saved.dll_directory))
        package = WindowsPackage(directory, settings, (directory/'output.out').exists(), risk == 'uncertain')
        if exe:
            try:
                package = replace(package, checked=probe_executable(settings, environ=self.environ, runner=self.runner))
            except LocalRunError as exc:
                package = replace(package, error=exc.args[0])
        return package

    def prepare(self, directory, settings):
        directory = validate_native_directory(directory)
        normalized = replace(settings, executable=str(Path(settings.executable).expanduser().resolve()),
            dll_directory=str(Path(settings.dll_directory).expanduser().resolve()) if settings.dll_directory else '')
        checked = probe_executable(normalized, environ=self.environ, runner=self.runner)
        return WindowsPackage(directory, normalized, (directory/'output.out').exists(), checked=checked)

    def _runner(self, job):
        if getattr(sys, 'frozen', False):
            helper = Path(sys.executable).with_name('cp2k-studio-runner.exe')
            if not helper.is_file():
                raise LocalRunError(i18n_msg('The Windows Local Run helper is missing. Restore the complete Portable folder.', code='winrun.helper_missing'))
            return [str(helper)]
        target = job / 'runtime/core'
        target.mkdir(parents=True)
        for name in ['__init__.py','local_run_runtime.py','windows_run_runtime.py','windows_run_config.py','resources.py']:
            shutil.copyfile(Path(__file__).with_name(name), target/name)
        entry = target.parent/'entry.py'
        entry.write_text('from core.windows_run_runtime import main\nraise SystemExit(main())\n', encoding='utf-8')
        interpreter = Path(sys.executable)
        if interpreter.name.lower() == 'pythonw.exe' and interpreter.with_name('python.exe').is_file():
            interpreter = interpreter.with_name('python.exe')
        return [str(interpreter), str(entry)]

    def _open_terminal(self, package, job, mode):
        env = runtime_environment(package.settings, self.environ)
        failures = []
        for command in terminal_commands(job/'launch.json', mode, env):
            flags = getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)
            if Path(command[0]).name.lower() != 'wt.exe':
                flags |= getattr(subprocess,'CREATE_NEW_CONSOLE',0)
            try:
                with external_dll_search():
                    child = subprocess.Popen(command, cwd=package.directory, env=env, shell=False,
                        creationflags=flags, close_fds=True)
                time.sleep(.25)
                if child.poll() not in {None, 0}:
                    failures.append(str(child.returncode)); continue
                return str(child.pid)
            except OSError as exc:
                failures.append(str(exc))
        raise LocalRunError(i18n_msg('Cannot open a Windows terminal: {error}', code='winrun.terminal_error', error='; '.join(failures)))

    def launch(self, package, *, confirmed=False):
        if not confirmed or not package.checked:
            raise LocalRunError(i18n_msg('Validate the executable and confirm Start Calculation first.', code='winrun.confirm_first'))
        validate_native_directory(package.directory)
        if not package.old_output and (package.directory/'output.out').exists():
            raise LocalRunError(i18n_msg('output.out appeared while configuring this run. CP2K may overwrite it. Click Start Calculation again to confirm, or Cancel.', code='winrun.log_appeared'))
        stat = Path(package.settings.executable).stat()
        if (stat.st_size, stat.st_mtime_ns) != package.checked.signature:
            raise LocalRunError(i18n_msg('CP2K EXE changed after validation. Reopen Local Run and check it again.', code='winrun.exe_changed'))
        token = uuid.uuid4().hex
        job = self.cache/'jobs'/token
        job.mkdir(parents=True, exist_ok=False)
        registry = runtime.registry_folder(self.cache, package.directory)
        if not runtime.reserve(self.cache, package.directory, token, job):
            raise LocalRunError(i18n_msg('A calculation or pending terminal launch already exists for this folder. Check the existing terminals before starting another run.', code='local.active_directory'))
        try:
            messages = runtime_messages()
            messages.update({
                'running': i18n_render(i18n_msg('Calculation directory: {directory}\nWindows Native: one CP2K process, OpenMP threads {threads}\n{executable} -i input.inp -o output.out', code='winrun.console_running', directory='{directory}',threads='{threads}',executable='{executable}')),
                'exit': i18n_render(i18n_msg('\nCP2K exit code: {exit_code}. Inspect output.out; exit status does not prove convergence.', code='winrun.console_exit', exit_code='{exit_code}')),
                'failed': i18n_render(i18n_msg('Could not start native CP2K: {error}', code='winrun.console_failed', error='{error}')),
                'old_log': i18n_render(i18n_msg('Existing output.out may contain a previous run. Showing its last lines is not a success indication; CP2K may overwrite this log.', code='winrun.console_old_log')),
                'version': i18n_render(i18n_msg('CP2K Version', code='env.cp2k_version')),
                'preferences_error': i18n_render(i18n_msg('CP2K started, but local preferences could not be saved: {error}', code='winrun.preferences_error', error='{error}')),
                'interrupted': i18n_render(i18n_msg('Ctrl+C received; waiting for the native CP2K process to exit.', code='winrun.console_interrupted')),
                'cancelled': i18n_render(i18n_msg('This native calculation launch was cancelled or superseded before execution. CP2K was not started.', code='winrun.console_cancelled')),
                'waiting': i18n_render(i18n_msg('Follow output.out (equivalent to tail -n 30 -F).', code='local.follow')),
            })
            manifest = dict(kind='windows-native-v1', token=token, job=str(job), registry=str(registry),
                directory=str(package.directory), settings=asdict(package.settings), runner=self._runner(job),
                settings_file=str(self.settings_file or settings_path()),
                titles=TITLES, messages=messages, baseline=None, old_output=package.old_output,
                version=package.checked.version, created=time.time())
            runtime.write_json(job/'launch.json', manifest)
            calculation = self._open_terminal(package, job, 'run')
        except Exception:
            runtime.cancel_pending(registry, token)
            raise
        monitor, error = None, ''
        try:
            monitor = self._open_terminal(package, job, 'monitor')
        except Exception as exc:
            error = i18n_str(exc)
        deadline = time.monotonic() + 3
        state = {}
        while time.monotonic() < deadline:
            state = runtime.read_json(job/'receipt.json')
            if state.get('stage') in {'running','finished','failed'}:
                break
            time.sleep(.05)
        if state.get('stage') == 'failed' and not state.get('script_pid'):
            raise LocalRunError(i18n_msg('Native CP2K failed to start (exit {exit_code}). Check the calculation terminal. {detail}',
                code='winrun.failed_start',exit_code=state.get('exit_code','?'),detail=state.get('error','')))
        if state.get('script_pid'):
            try:
                save_settings(package.settings, self.settings_file)
            except OSError:
                import logging
                logging.getLogger(__name__).warning('CP2K started, but local Windows settings could not be saved', exc_info=True)
        return LaunchResult(job, calculation, monitor, bool(state.get('script_pid')), error)
