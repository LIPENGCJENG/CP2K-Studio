"""Independent native Windows console worker: stdlib only, no GUI/project."""
from pathlib import Path
import os
import subprocess
import sys
from core import local_run_runtime as shared
from core.resources import external_dll_search
from core.windows_run_config import WindowsRunSettings, runtime_environment, save_settings


def calculate(manifest):
    folder = Path(manifest['registry'])
    lock = process = None
    code = 127
    error_detail = ''
    try:
        with shared.coordination(folder):
            state = shared.read_json(folder/'active.json')
            if state.get('token') != manifest['token'] or state.get('stage') != 'pending':
                raise RuntimeError(manifest['messages']['cancelled'])
            lock = shared.run_lock(folder)
            if lock is None:
                raise RuntimeError(manifest['messages']['duplicate'])
            os.chdir(manifest['directory'])
            if not Path('input.inp').is_file():
                raise FileNotFoundError('input.inp')
            settings = WindowsRunSettings(**manifest['settings'])
            shared.say(manifest, 'running', directory=repr(os.getcwd()),
                       threads=settings.omp_threads, executable=settings.executable)
            print(manifest['messages']['version'] + ':', manifest['version'], flush=True)
            with external_dll_search():
                process = subprocess.Popen([settings.executable, '-i', 'input.inp', '-o', 'output.out'],
                    cwd=manifest['directory'], env=runtime_environment(settings), shell=False)
            started = shared.receipt(manifest, 'running', pid=os.getpid(), script_pid=process.pid)
            shared.write_json(folder/'active.json', dict(state, **started))
            try:
                save_settings(settings, manifest['settings_file'])
            except OSError as exc:
                shared.say(manifest,'preferences_error',error=str(exc))
    except Exception as exc:
        error_detail = str(exc)
        shared.say(manifest, 'failed', error=str(exc))
    if process is not None:
        while True:
            try:
                code = process.wait()
                break
            except KeyboardInterrupt:
                shared.say(manifest, 'interrupted')
    try:
        if lock is not None:
            final = shared.receipt(manifest, 'finished' if process else 'failed', exit_code=code,
                                   script_pid=process.pid if process else None,error=error_detail)
            with shared.coordination(folder):
                state = shared.read_json(folder/'active.json')
                if state.get('token') == manifest['token']:
                    shared.write_json(folder/'active.json', dict(state, **final))
        elif not (Path(manifest['job'])/'receipt.json').exists():
            shared.receipt(manifest, 'failed', exit_code=code, script_pid=None)
    except OSError as exc:
        shared.say(manifest, 'failed', error=str(exc))
    finally:
        if lock is not None:
            lock.close()
    if process is not None:
        shared.say(manifest, 'exit', exit_code=code)
    # PowerShell -NoExit also keeps the console available after this helper exits.
    return code


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in {'run','monitor'}:
        return 2
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    manifest = shared.read_json(sys.argv[2])
    if manifest.get('kind') != 'windows-native-v1':
        return 2
    if sys.argv[1] == 'run':
        return calculate(manifest)
    if manifest.get('old_output'):
        shared.say(manifest, 'old_log')
    # LogFollower handles creation, last 30 lines, truncation and replacement.
    # This monitor never acquires the calculation lock or sends process signals.
    return shared.monitor(manifest)
