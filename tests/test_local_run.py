"""Package validation and real, harmless script helpers; never run CP2K."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from types import SimpleNamespace
import pytest
from core import local_run as local
from core import local_run_runtime as runtime


@pytest.fixture
def package(tmp_path):
    directory = tmp_path / "中文 计算 (test) ' ; $() `quote`"
    directory.mkdir()
    (directory / 'input.inp').write_text('mock input, not a CP2K calculation')
    (directory / 'run.sh').write_text('printf "mock stdout\\n"\nprintf "mock stderr\\n" >&2\nprintf "%s" "$PWD" > observed-cwd\nprintf "new log\\n" > output.out\nexit 7\n')
    return directory


@pytest.fixture
def backend(tmp_path, monkeypatch):
    monkeypatch.setattr(local, 'detect_terminal', lambda *a: local.Terminal('xterm', '/mock/xterm'))
    return local.LocalRunBackend(cache=tmp_path / 'cache')


def wait_for(predicate, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError('mock job did not reach expected state')


def helper_adapter(backend, monkeypatch, modes=None):
    """Replace only the visible terminal, execute the actual staged helper."""
    children = {}
    def launch(package, job, mode):
        if modes is not None and mode not in modes:
            raise local.LocalRunError('mock monitor unavailable')
        with (job / (mode + '.log')).open('wb') as output:
            child = subprocess.Popen([package.bash, str(job / 'terminal.sh'),
                str(package.directory), sys.executable, str(job / 'runtime.py'),
                mode, str(job / 'launch.json')], start_new_session=True,
                stdin=subprocess.DEVNULL, stdout=output, stderr=output)
        children[mode] = child
        return str(child.pid)
    monkeypatch.setattr(backend, '_open_terminal', launch)
    return children


def test_valid_package_needs_only_readable_script_and_input(package):
    (package / 'project.cp2kstudio.json').write_text('{broken JSON must not be read')
    assert local.validate_directory(package) == package.resolve()
    assert not (package / 'data').exists()
    assert not (package / 'output.out').exists()


@pytest.mark.parametrize('filename', ['run.sh', 'input.inp'])
def test_missing_file_is_reported(package, backend, filename):
    (package / filename).unlink()
    with pytest.raises(local.LocalRunError) as error:
        backend.inspect(package)
    assert filename in str(error.value)
    assert not backend.cache.exists()


def test_missing_directory_zip_and_unreadable_file(package, monkeypatch, tmp_path):
    with pytest.raises(local.LocalRunError):
        local.validate_directory(tmp_path / 'missing')
    archive = tmp_path / 'package.ZIP'
    archive.write_bytes(b'zip')
    with pytest.raises(local.LocalRunError) as error:
        local.validate_directory(archive)
    assert 'ZIP' in str(error.value)
    original = Path.open
    def unreadable(path, *a, **kw):
        if path.name == 'run.sh':
            raise PermissionError('mock permission denied')
        return original(path, *a, **kw)
    monkeypatch.setattr(Path, 'open', unreadable)
    with pytest.raises(local.LocalRunError) as error:
        local.validate_directory(package)
    assert 'run.sh' in str(error.value) and 'permission denied' in str(error.value)


def test_no_execution_without_explicit_confirmation(package, backend, monkeypatch):
    info = backend.inspect(package)
    monkeypatch.setattr(backend, '_open_terminal', lambda *a: pytest.fail('unconfirmed terminal'))
    with pytest.raises(local.LocalRunError):
        backend.launch(info)
    assert not backend.cache.exists()
    assert not (package / 'output.out').exists()


@pytest.mark.parametrize('exit_code', [0, 7, 127])
def test_actual_script_cwd_streams_exit_and_unmodified_package(package, backend, monkeypatch, exit_code):
    path = package / 'run.sh'
    path.write_text(path.read_text().replace('exit 7', f'exit {exit_code}'))
    original = {p.name: p.read_bytes() for p in package.iterdir()}
    children = helper_adapter(backend, monkeypatch)
    result = backend.launch(backend.inspect(package), confirmed=True)
    try:
        assert result.script_started and result.monitor_terminal
        assert children['run'].wait(timeout=5) == exit_code
        receipt = runtime.read_json(result.job / 'receipt.json')
        assert receipt['stage'] == 'finished' and receipt['exit_code'] == exit_code
        text = (result.job / 'run.log').read_text()
        assert 'mock stdout' in text and 'mock stderr' in text and str(exit_code) in text
        assert (package / 'observed-cwd').read_text() == str(package.resolve())
        assert all((package / name).read_bytes() == data for name, data in original.items())
        assert runtime.launch_risk(backend.cache, package) == ''
        wait_for(lambda: 'new log' in (result.job / 'monitor.log').read_text())
        assert runtime.read_json(result.job / 'monitor.json')['pid'] == children['monitor'].pid
        assert os.getpgid(children['monitor'].pid) != os.getpgrp()
    finally:
        children['monitor'].send_signal(signal.SIGINT)
        assert children['monitor'].wait(timeout=5) == 0


def test_duplicate_run_and_monitor_independence(package, backend, monkeypatch):
    (package / 'run.sh').write_text('sleep 1\nprintf "finished\\n" > output.out\nexit 0\n')
    children = helper_adapter(backend, monkeypatch)
    result = backend.launch(backend.inspect(package), confirmed=True)
    try:
        assert runtime.launch_risk(backend.cache, package) == 'active'
        with pytest.raises(local.LocalRunError):
            backend.inspect(package)
        children['monitor'].send_signal(signal.SIGINT)
        assert children['monitor'].wait(timeout=3) == 0
        assert children['run'].poll() is None
        assert children['run'].wait(timeout=5) == 0
        assert (package / 'output.out').read_text() == 'finished\n'
        assert runtime.launch_risk(backend.cache, package) == ''
    finally:
        for child in children.values():
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=5)


def test_monitor_failure_does_not_cancel_or_repeat_calculation(package, backend, monkeypatch):
    children = helper_adapter(backend, monkeypatch, {'run'})
    result = backend.launch(backend.inspect(package), confirmed=True)
    assert result.script_started and result.monitor_terminal is None
    assert 'mock monitor' in result.monitor_error
    assert list(children) == ['run']
    assert children['run'].wait(timeout=5) == 7


def test_launch_failure_cancels_pending_and_never_runs(package, backend, monkeypatch):
    def fail(*a):
        raise local.LocalRunError('mock terminal failure')
    monkeypatch.setattr(backend, '_open_terminal', fail)
    with pytest.raises(local.LocalRunError):
        backend.launch(backend.inspect(package), confirmed=True)
    assert not (package / 'output.out').exists()
    assert runtime.launch_risk(backend.cache, package) == ''


def test_reservations_stale_state_and_inherited_lock(package, tmp_path):
    root = tmp_path / 'locks'
    folder = runtime.registry_folder(root, package)
    assert runtime.reserve(root, package, 'one', tmp_path)
    assert not runtime.reserve(root, package, 'two', tmp_path)
    assert runtime.launch_risk(root, package) == 'active'
    state = runtime.read_json(folder / 'active.json')
    runtime.write_json(folder / 'active.json', dict(state, created=0))
    assert runtime.launch_risk(root, package) == 'uncertain'
    lock = runtime.run_lock(folder)
    child = subprocess.Popen(['/bin/bash', '-c', 'sleep .5'], pass_fds=(lock.fileno(),))
    lock.close()
    assert runtime.launch_risk(root, package) == 'active'
    assert not runtime.reserve(root, package, 'three', tmp_path)
    child.wait(timeout=5)
    runtime.cancel_pending(folder, 'wrong-token')
    assert runtime.launch_risk(root, package) == 'uncertain'
    runtime.cancel_pending(folder, 'one')
    assert runtime.launch_risk(root, package) == ''


def test_helper_survives_launching_process_exit(package, backend, monkeypatch):
    (package / 'run.sh').write_text('sleep .5\nprintf "survived\\n" > output.out\n')
    # A short-lived launcher exits immediately after creating a detached helper.
    def launch(info, job, mode):
        if mode == 'monitor':
            raise local.LocalRunError('monitor deliberately omitted')
        command = [info.bash, str(job / 'terminal.sh'), str(info.directory),
                   sys.executable, str(job / 'runtime.py'), mode, str(job / 'launch.json')]
        code = 'import subprocess,sys; subprocess.Popen(sys.argv[1:],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)'
        subprocess.run([sys.executable, '-c', code, *command], check=True)
        return 'detached'
    monkeypatch.setattr(backend, '_open_terminal', launch)
    result = backend.launch(backend.inspect(package), confirmed=True)
    wait_for(lambda: runtime.read_json(result.job / 'receipt.json').get('stage') == 'finished')
    assert (package / 'output.out').read_text() == 'survived\n'


def test_terminal_keeps_actual_exit_code_and_holds_tty(package, backend, monkeypatch, capsys):
    def stage(info, job, mode):
        return mode
    monkeypatch.setattr(backend, '_open_terminal', stage)
    monkeypatch.setattr(local.time, 'monotonic', iter([0, 10]).__next__)
    result = backend.launch(backend.inspect(package), confirmed=True)
    manifest = runtime.read_json(result.job / 'launch.json')
    cwd = Path.cwd()
    prompts = []
    monkeypatch.setattr(runtime.sys, 'stdin', SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr('builtins.input', lambda text: prompts.append(text))
    try:
        assert runtime.calculate(manifest) == 7
        assert prompts
        # A stale terminal command must not execute run.sh again or exit silently.
        assert runtime.calculate(manifest) == 125
        assert len(prompts) == 2
        assert runtime.read_json(result.job / 'receipt.json')['exit_code'] == 7
    finally:
        os.chdir(cwd)


def test_receipt_failure_after_start_does_not_replace_actual_exit_code(package, backend, monkeypatch):
    monkeypatch.setattr(backend, '_open_terminal', lambda *a: 'mock')
    # Stage without waiting for the mocked terminal to start.
    tick = iter([0, 10])
    monkeypatch.setattr(local.time, 'monotonic', lambda: next(tick))
    result = backend.launch(backend.inspect(package), confirmed=True)
    manifest = runtime.read_json(result.job / 'launch.json')
    receipt = runtime.receipt
    def fail_running(manifest, stage, **kw):
        if stage == 'running':
            raise PermissionError('mock receipt failure')
        return receipt(manifest, stage, **kw)
    monkeypatch.setattr(runtime, 'receipt', fail_running)
    cwd = Path.cwd()
    try:
        assert runtime.calculate(manifest) == 7
        assert runtime.read_json(result.job / 'receipt.json')['exit_code'] == 7
        assert (package / 'output.out').read_text() == 'new log\n'
    finally:
        os.chdir(cwd)


def test_script_environment_is_not_overridden(package, backend, monkeypatch):
    (package / 'run.sh').write_text('export OMP_NUM_THREADS=9\nprintf "%s|%s" "$OMP_NUM_THREADS" "$LOCAL_RUN_SENTINEL" > environment\n')
    monkeypatch.setenv('LOCAL_RUN_SENTINEL','unchanged')
    children = helper_adapter(backend, monkeypatch, {'run'})
    result = backend.launch(backend.inspect(package), confirmed=True)
    assert children['run'].wait(timeout=5) == 0
    assert (package / 'environment').read_text() == '9|unchanged'
    assert runtime.read_json(result.job / 'receipt.json')['exit_code'] == 0


def test_concurrent_reservations_only_one_can_win(package, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    root = tmp_path / 'concurrent'
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda number: runtime.reserve(root,package,str(number),tmp_path), range(8)))
    assert sum(results) == 1
