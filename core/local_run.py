"""Independent, confirmed launch of an existing package in two system terminals."""
from dataclasses import dataclass
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import time
import uuid

from i18n.messages import i18n_msg, i18n_render, i18n_str
from core import local_run_runtime as runtime
from core.resources import external_environment

TITLES = {'run': 'CP2K Studio · Calculation', 'monitor': 'CP2K Studio · Output Monitor'}
APPLESCRIPT = '''on run argv
    tell application id "com.apple.Terminal"
        launch
        set createdTab to do script (item 1 of argv)
        set custom title of createdTab to (item 2 of argv)
        activate
        return id of front window
    end tell
end run'''


class LocalRunError(ValueError):
    pass


@dataclass(frozen=True)
class Terminal:
    kind: str
    executable: str


@dataclass(frozen=True)
class Package:
    directory: Path
    bash: str
    terminal: Terminal
    previous_uncertain: bool = False
    old_output: bool = False


@dataclass(frozen=True)
class LaunchResult:
    job: Path
    calculation_terminal: str
    monitor_terminal: str | None
    script_started: bool
    monitor_error: str = ''


def default_cache():
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Caches' / 'CP2K-Studio' / 'local-run'
    return Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'CP2K-Studio' / 'local-run'


def validate_directory(directory):
    path = Path(directory).expanduser().resolve()
    if path.suffix.lower() == '.zip' and path.is_file():
        raise LocalRunError(i18n_msg('Extract the ZIP package first, then select its calculation folder.', code='local.extract_zip'))
    if not path.is_dir():
        raise LocalRunError(i18n_msg('Calculation directory does not exist: {path}', code='local.missing_directory', path=str(path)))
    for filename in ['run.sh', 'input.inp']:
        file = path / filename
        if not file.is_file():
            raise LocalRunError(i18n_msg('Missing {filename} in the calculation folder.', code='local.missing_file', filename=filename))
        try:
            with file.open('rb') as handle:
                handle.read(1)
        except OSError as exc:
            raise LocalRunError(i18n_msg('Cannot read {filename}: {error}', code='local.unreadable', filename=filename, error=str(exc))) from exc
    return path


def detect_terminal(system=None, environ=None):
    system = system or platform.system()
    environ = os.environ if environ is None else environ
    if system == 'Darwin':
        executable = '/usr/bin/osascript'
        app = Path('/System/Applications/Utilities/Terminal.app')
        if not app.is_dir():
            app = Path('/Applications/Utilities/Terminal.app')
        if app.is_dir() and os.access(executable, os.X_OK):
            return Terminal('macos', executable)
    elif system == 'Linux':
        if not (environ.get('DISPLAY') or environ.get('WAYLAND_DISPLAY')):
            raise LocalRunError(i18n_msg('No graphical desktop session was detected. Local Run requires a visible system terminal; no background calculation was started.', code='local.no_display'))
        desktop = (environ.get('XDG_CURRENT_DESKTOP', '') + ':' + environ.get('DESKTOP_SESSION', '')).lower()
        preferred = ('konsole' if any(name in desktop for name in ['kde','plasma']) else
                     'xfce4-terminal' if 'xfce' in desktop else 'gnome-terminal')
        candidates = list(dict.fromkeys([preferred, 'gnome-terminal', 'konsole', 'xfce4-terminal', 'xterm']))
        for name in candidates:
            if name == 'xterm' and not environ.get('DISPLAY'):
                continue
            found = shutil.which(name, path=environ.get('PATH', ''))
            if found:
                return Terminal(name, str(Path(found).absolute()))
    elif system == 'Windows':
        raise LocalRunError(i18n_msg('Local Run currently supports macOS and Linux graphical terminals. Windows/WSL launching is not configured; CMD will not be used.', code='local.windows_unsupported'))
    raise LocalRunError(i18n_msg('No supported graphical terminal is available. macOS requires Terminal.app; Linux supports gnome-terminal, konsole, xfce4-terminal or xterm.', code='local.no_terminal'))


def detect_bash(environ=None):
    environ = os.environ if environ is None else environ
    bash = shutil.which('bash', path=environ.get('PATH', ''))
    if not bash:
        bash = next((p for p in ['/bin/bash','/usr/bin/bash'] if os.access(p, os.X_OK)), None)
    if not bash:
        raise LocalRunError(i18n_msg('Bash is not available. Configure Bash before running this package; no installation or PATH changes were made.', code='local.no_bash'))
    return str(Path(bash).absolute())


def terminal_argv(terminal, title, directory, command):
    """Each adapter requests a new window; user paths are literal argv values."""
    executable, kind = terminal.executable, terminal.kind
    if kind == 'macos':
        # User strings are arguments to a fixed AppleScript, never its source.
        shell_command = 'cd -- ' + shlex.quote(str(directory)) + ' && ' + shlex.join(command)
        return [executable, '-e', APPLESCRIPT, shell_command, title]
    if kind == 'gnome-terminal':
        return [executable, '--window', '--title=' + title, '--working-directory=' + str(directory), '--', *command]
    if kind == 'konsole':
        return [executable, '--separate', '--workdir', str(directory), '-p', 'LocalTabTitleFormat=' + title, '-e', *command]
    if kind == 'xfce4-terminal':
        return [executable, '--disable-server', '--window', '--title=' + title, '--working-directory=' + str(directory), '--execute', *command]
    if kind == 'xterm':
        return [executable, '-T', title, '-e', *command]
    raise LocalRunError(i18n_msg('Unsupported terminal adapter: {name}', code='local.unsupported_terminal', name=kind))


def runtime_messages():
    # Translations are frozen for this independent launch. Runtime has no Qt.
    messages = {
        'running': i18n_msg('Calculation directory: {directory}\nRunning: bash run.sh', code='local.console_running', directory='{directory}'),
        'monitor': i18n_msg('Output monitor: {directory}/output.out\nFollowing file changes (tail -n 30 -F behavior). Ctrl+C stops only this monitor.', code='local.console_monitor', directory='{directory}'),
        'old_log': i18n_msg('An existing output.out was found. Unchanged pre-launch content is excluded; waiting for new output. No success is inferred from log contents.', code='local.console_old_log'),
        'waiting': i18n_msg('Waiting for output.out to be created…', code='local.console_waiting'),
        'exit': i18n_msg('\nrun.sh exit code: {exit_code}. This is the script status, not proof of CP2K convergence; inspect the calculation terminal and log.', code='local.console_exit', exit_code='{exit_code}'),
        'hold': i18n_msg('Press Enter to close this terminal command…', code='local.console_hold'),
        'failed': i18n_msg('Could not run the selected script: {error}', code='local.console_failed', error='{error}'),
        'cancelled': i18n_msg('This launch was cancelled or superseded before execution. run.sh was not started.', code='local.console_cancelled'),
        'duplicate': i18n_msg('A calculation already owns this directory. This second script was not started.', code='local.console_duplicate'),
        'interrupted': i18n_msg('Ctrl+C received; waiting for the foreground run.sh to exit.', code='local.console_interrupted'),
        'read_error': i18n_msg('Cannot read output.out yet: {error}. Retrying…', code='local.console_read_error', error='{error}'),
        'monitor_stopped': i18n_msg('Output monitoring stopped. No stop signal was sent to the calculation.', code='local.console_monitor_stopped'),
    }
    return {key: i18n_render(value) for key, value in messages.items()}


class LocalRunBackend:
    def __init__(self, *, cache=None, system=None, environ=None):
        self.cache = (Path(cache) if cache is not None else default_cache()).expanduser().resolve()
        self.system = system or platform.system()
        self.environ = dict(os.environ if environ is None else environ)

    def inspect(self, directory):
        directory = validate_directory(directory)
        terminal = detect_terminal(self.system, self.environ)
        bash = detect_bash(self.environ)
        if getattr(sys, 'frozen', False):
            helper = Path(sys.executable).with_name('cp2k-studio-runner')
            if not helper.is_file() or not os.access(helper, os.X_OK):
                raise LocalRunError(i18n_msg('The bundled Local Run helper is missing or cannot be executed. Rebuild or restore the complete CP2K Studio.app.', code='local.helper_missing'))
        risk = runtime.launch_risk(self.cache, directory)
        if risk == 'active':
            raise LocalRunError(i18n_msg('A calculation or pending terminal launch already exists for this folder. Check the existing terminals before starting another run.', code='local.active_directory'))
        return Package(directory, bash, terminal, risk == 'uncertain', (directory / 'output.out').exists())

    def _open_terminal(self, package, job, mode):
        if getattr(sys, 'frozen', False):
            command = [package.bash, str(job / 'terminal.sh'), str(package.directory),
                       str(Path(sys.executable).with_name('cp2k-studio-runner')),
                       mode, str(job / 'launch.json')]
        else:
            command = [package.bash, str(job / 'terminal.sh'), str(package.directory), sys.executable,
                       str(job / 'runtime.py'), mode, str(job / 'launch.json')]
        argv = terminal_argv(package.terminal, TITLES[mode], package.directory, command)
        if package.terminal.kind == 'macos':
            try:
                result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                                        text=True, timeout=20, check=False,
                                        **({'env': external_environment()} if getattr(sys, 'frozen', False) else {}))
            except subprocess.TimeoutExpired as exc:
                raise LocalRunError(i18n_msg('Terminal automation timed out. The terminal may have opened; inspect it before retrying.', code='local.automation_timeout')) from exc
            if result.returncode:
                if '-1743' in result.stderr:
                    raise LocalRunError(i18n_msg('macOS denied Terminal automation. Allow the application hosting Python/CP2K Studio to control Terminal in System Settings → Privacy & Security → Automation, then retry.', code='local.automation_denied'))
                raise LocalRunError(i18n_msg('Terminal could not be opened: {error}', code='local.terminal_failed', error=result.stderr.strip()[-2000:]))
            return result.stdout.strip()
        log = job / (mode + '-terminal.log')
        with log.open('wb') as output:
            child = subprocess.Popen(argv, cwd=package.directory, start_new_session=True,
                                     stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                     close_fds=True,
                                     **({'env': external_environment()} if getattr(sys, 'frozen', False) else {}))
        # A terminal server may exit 0 after handing off its visible window.
        # Never wait for the long-running terminal/calculation to finish.
        time.sleep(.25)
        if child.poll() not in {None, 0}:
            raise LocalRunError(i18n_msg('Terminal could not be opened: {error}', code='local.terminal_failed', error=log.read_text(errors='replace')[-2000:]))
        return str(child.pid)

    def launch(self, package, *, confirmed=False):
        if confirmed is not True:
            raise LocalRunError(i18n_msg('Confirm Run before executing the selected script.', code='local.confirm_required'))
        package = self.inspect(package.directory)  # Recheck races after the dialog.
        token = uuid.uuid4().hex
        job = self.cache / 'jobs' / token
        job.mkdir(parents=True, mode=0o700)
        os.chmod(job, 0o700)
        registry = runtime.registry_folder(self.cache, package.directory)
        if not runtime.reserve(self.cache, package.directory, token, job):
            raise LocalRunError(i18n_msg('A calculation or pending terminal launch already exists for this folder. Check the existing terminals before starting another run.', code='local.active_directory'))
        try:
            manifest = dict(token=token, job=str(job), registry=str(registry),
                            directory=str(package.directory), bash=package.bash, titles=TITLES,
                            baseline=runtime.file_snapshot(package.directory / 'output.out'),
                            messages=runtime_messages(), created=time.time())
            runtime.write_json(job / 'launch.json', manifest)
            # A frozen GUI executable is not a Python interpreter. The console
            # helper embeds its own runtime and remains independent of the GUI.
            if getattr(sys, 'frozen', False):
                bootstrap = '#!/bin/bash\ncd -- "$1" || exit 1\nexec "$2" "$3" "$4"\n'
            else:
                shutil.copyfile(Path(runtime.__file__), job / 'runtime.py')
                bootstrap = '#!/bin/bash\ncd -- "$1" || exit 1\nexec "$2" -u "$3" "$4" "$5"\n'
            (job / 'terminal.sh').write_text(bootstrap, encoding='utf-8')
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
        while time.monotonic() < deadline:
            state = runtime.read_json(job / 'receipt.json')
            if state.get('stage') in {'running', 'finished', 'failed'}:
                return LaunchResult(job, calculation, monitor, bool(state.get('script_pid')), error)
            time.sleep(.05)
        return LaunchResult(job, calculation, monitor, False, error)
