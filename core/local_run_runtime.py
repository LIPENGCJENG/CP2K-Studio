"""Standalone terminal helper: stdlib only, with no project/Qt imports.

A private copy is staged per launch so an independent terminal does not rely
on the GUI process remaining alive. Only the user's confirmed run.sh is run.
"""
from contextlib import contextmanager
import base64
import codecs
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

PENDING_SECONDS = 300


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except PermissionError:
        if os.name != 'nt':
            raise
        return {}
    except (FileNotFoundError, ValueError):
        return {}


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        os.chmod(temporary, 0o600)
        json.dump(value, handle, ensure_ascii=False)
    for attempt in range(20):
        try:
            os.replace(temporary, path)
            break
        except PermissionError:
            if os.name != 'nt' or attempt == 19:
                raise
            time.sleep(.02)


def registry_folder(root, directory):
    digest = hashlib.sha256(os.fsencode(str(Path(directory).resolve()))).hexdigest()
    return Path(root) / 'directories' / digest


@contextmanager
def coordination(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (folder / 'state.lock').open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            if not handle.seek(0, 2):
                handle.write(b'\0'); handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            return
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run_lock(folder):
    """Return a held lock or None. The descriptor also survives in run.sh."""
    handle = (Path(folder) / 'running.lock').open('a+b')
    if os.name == 'nt':
        import msvcrt
        if not handle.seek(0, 2):
            handle.write(b'\0'); handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            handle.close()
            return None
        return handle
    import fcntl
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def launch_risk(root, directory):
    folder = registry_folder(root, directory)
    if not folder.exists():
        return ''
    with coordination(folder):
        lock = run_lock(folder)
        if lock is None:
            return 'active'
        lock.close()
        state = read_json(folder / 'active.json')
        if state.get('stage') == 'pending':
            return 'active' if time.time() - state.get('created', 0) < PENDING_SECONDS else 'uncertain'
        return 'uncertain' if state.get('stage') == 'running' else ''


def reserve(root, directory, token, job):
    folder = registry_folder(root, directory)
    with coordination(folder):
        lock = run_lock(folder)
        if lock is None:
            return False
        lock.close()
        previous = read_json(folder / 'active.json')
        if previous.get('stage') == 'pending' and time.time() - previous.get('created', 0) < PENDING_SECONDS:
            return False
        write_json(folder / 'active.json', {'token': token, 'job': str(job), 'stage': 'pending', 'created': time.time()})
    return True


def cancel_pending(folder, token):
    with coordination(folder):
        state = read_json(Path(folder) / 'active.json')
        lock = run_lock(folder)
        if lock is not None:
            lock.close()
            if state.get('token') == token and state.get('stage') == 'pending':
                write_json(Path(folder) / 'active.json', dict(state, stage='failed'))


def file_snapshot(path):
    try:
        with Path(path).open('rb') as handle:
            stat = os.fstat(handle.fileno())
            head = handle.read(128)
            handle.seek(max(0, stat.st_size - 128))
            tail = handle.read(128)
        return {'dev': stat.st_dev, 'ino': stat.st_ino, 'size': stat.st_size,
                'head': base64.b64encode(head).decode('ascii'),
                'tail': base64.b64encode(tail).decode('ascii')}
    except FileNotFoundError:
        return None


class LogFollower:
    """Follow a filename across creation/truncation/replacement, without old output.

    Unchanged pre-launch bytes are skipped. New/replaced files start at their
    last 30 lines, like tail -n 30 -F. Polling is presentation, not CP2K parsing.
    """
    def __init__(self, path, baseline=None):
        self.path = Path(path)
        self.identity = (baseline['dev'], baseline['ino']) if baseline else None
        self.offset = baseline['size'] if baseline else 0
        self.head = base64.b64decode(baseline['head']) if baseline else b''
        self.anchor = base64.b64decode(baseline['tail']) if baseline else b''
        self.missing = baseline is None
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')

    def poll(self):
        try:
            with self.path.open('rb') as handle:
                stat = os.fstat(handle.fileno())
                identity = (stat.st_dev, stat.st_ino)
                reset = self.missing or identity != self.identity or stat.st_size < self.offset
                if not reset:
                    # Detect rapid truncate-and-regrow even when size has caught up.
                    head = handle.read(len(self.head))
                    handle.seek(max(0, self.offset - len(self.anchor)))
                    reset = head != self.head or handle.read(len(self.anchor)) != self.anchor
                if reset:
                    handle.seek(max(0, stat.st_size - 1024 * 1024))
                    start = handle.tell()
                    end = handle.read()
                    lines = end.splitlines(keepends=True)
                    tail = b''.join(lines[-30:])
                    self.offset = start + len(end) - len(tail)
                    self.decoder.reset()
                handle.seek(self.offset)
                content = handle.read(1024 * 1024)
                self.offset += len(content)
                handle.seek(0)
                self.head = handle.read(min(128, self.offset))
                handle.seek(max(0, self.offset - 128))
                self.anchor = handle.read(min(128, self.offset))
                self.identity, self.missing = identity, False
                return self.decoder.decode(content)
        except FileNotFoundError:
            self.missing = True
            return ''


def say(manifest, key, **parameters):
    print(manifest['messages'][key].format_map(parameters), flush=True)


def receipt(manifest, stage, **extra):
    value = dict(stage=stage, token=manifest['token'], time=time.time(), **extra)
    write_json(Path(manifest['job']) / 'receipt.json', value)
    return value


def calculate(manifest):
    folder = Path(manifest['registry'])
    lock = None
    process = None
    code = 127
    try:
        with coordination(folder):
            state = read_json(folder / 'active.json')
            if state.get('token') != manifest['token'] or state.get('stage') != 'pending':
                code = 125
                raise RuntimeError(manifest['messages']['cancelled'])
            lock = run_lock(folder)
            if lock is None:
                code = 125
                raise RuntimeError(manifest['messages']['duplicate'])
            os.chdir(manifest['directory'])
            if not Path('input.inp').is_file():
                raise FileNotFoundError('input.inp')
            with Path('run.sh').open('rb') as handle:
                handle.read(1)
            say(manifest, 'running', directory=repr(os.getcwd()))
            # Resolve Bash in this terminal's environment. Never alter PATH,
            # MPI/OMP settings or the user's script, and inherit the real TTY.
            bash = shutil.which('bash') or manifest['bash']
            process = subprocess.Popen([bash, 'run.sh'], cwd=manifest['directory'],
                                       pass_fds=(lock.fileno(),))
            started = receipt(manifest, 'running', pid=os.getpid(), script_pid=process.pid)
            write_json(folder / 'active.json', dict(state, **started))
    except Exception as exc:
        say(manifest, 'failed', error=str(exc))
    # Once Bash starts, even a cache/receipt write failure must not release the
    # directory or replace the actual exit status with a launcher error code.
    if process is not None:
        while True:
            try:
                code = process.wait()
                break
            except KeyboardInterrupt:
                say(manifest, 'interrupted')
        code = 128 - code if code < 0 else code
    try:
        if lock is not None:
            final = receipt(manifest, 'finished' if process else 'failed', exit_code=code,
                            script_pid=process.pid if process else None)
            with coordination(folder):
                state = read_json(folder / 'active.json')
                if state.get('token') == manifest['token']:
                    write_json(folder / 'active.json', dict(state, **final))
        elif not (Path(manifest['job']) / 'receipt.json').exists():
            receipt(manifest, 'failed', exit_code=code, script_pid=None)
        # A repeated terminal command must not overwrite the original run's
        # startup/exit receipt when it never acquired the directory lock.
    except OSError as exc:
        say(manifest, 'failed', error=str(exc))
    finally:
        if lock is not None:
            lock.close()
    if process is not None:
        say(manifest, 'exit', exit_code=code)
    if sys.stdin.isatty():
        try:
            input(manifest['messages']['hold'])
        except (EOFError, KeyboardInterrupt):
            pass
    return code


def monitor(manifest):
    os.chdir(manifest['directory'])
    say(manifest, 'monitor', directory=repr(os.getcwd()))
    if manifest['baseline'] is not None:
        say(manifest, 'old_log')
    else:
        say(manifest, 'waiting')
    follower = LogFollower('output.out', manifest['baseline'])
    announced = False
    last_error = ''
    write_json(Path(manifest['job']) / 'monitor.json', {'pid': os.getpid()})
    try:
        while True:
            try:
                content = follower.poll()
                if content:
                    sys.stdout.write(content)
                    sys.stdout.flush()
                last_error = ''
            except OSError as exc:
                if str(exc) != last_error:
                    say(manifest, 'read_error', error=str(exc))
                    last_error = str(exc)
            state = read_json(Path(manifest['job']) / 'receipt.json')
            if not announced and state.get('stage') == 'finished':
                say(manifest, 'exit', exit_code=state['exit_code'])
                announced = True
            time.sleep(.2)
    except KeyboardInterrupt:
        say(manifest, 'monitor_stopped')
    return 0


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in {'run', 'monitor'}:
        return 2
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    manifest = read_json(sys.argv[2])
    title = manifest['titles'][sys.argv[1]]
    if sys.stdout.isatty():
        print('\033]0;' + title + '\007', end='', flush=True)
    return calculate(manifest) if sys.argv[1] == 'run' else monitor(manifest)


if __name__ == '__main__':
    sys.exit(main())
