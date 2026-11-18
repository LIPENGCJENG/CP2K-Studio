"""Headless integration of the bundled helper with a harmless CI executable."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time


def wait_for(predicate, timeout=25):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if predicate():
            return
        time.sleep(.05)
    raise AssertionError('Native helper did not reach the expected state')


def run(executable, directory, output):
    from core.windows_local_run import WindowsLocalRunBackend
    from core.windows_run_config import WindowsRunSettings, load_settings, runtime_environment
    from core.resources import external_dll_search
    from core import local_run_runtime as runtime
    directory, output = Path(directory), Path(output)
    before = {p.name:p.read_bytes() for p in directory.iterdir() if p.is_file()}
    settings_file = output/'native-settings.json'
    backend=WindowsLocalRunBackend(cache=output/'native-jobs',settings_file=settings_file)
    settings=WindowsRunSettings(str(Path(executable).resolve()), str(Path(executable).parent.resolve()), 3)
    package=backend.prepare(directory,settings)
    children={}
    def terminal(info,job,mode):
        manifest=runtime.read_json(job/'launch.json')
        flags=(getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)|getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (job/(mode+'.log')).open('wb') as log, external_dll_search():
            child=subprocess.Popen([*manifest['runner'],mode,str(job/'launch.json')],
                cwd=info.directory,env=runtime_environment(info.settings),shell=False,
                stdin=subprocess.DEVNULL,stdout=log,stderr=log,close_fds=True,creationflags=flags)
        children[mode]=child
        return str(child.pid)
    # A hosted runner cannot prove interactive Terminal window behavior.
    # Substitute only its window host, execute the real independent helper.
    backend._open_terminal=terminal
    try:
        result=backend.launch(package,confirmed=True)
        wait_for(lambda:(directory/'observed-native.json').is_file())
        observed=json.loads((directory/'observed-native.json').read_text(encoding='utf-8'))
        assert observed['threads']=='3' and Path(observed['cwd'])==directory
        assert observed['argv']==['-i','input.inp','-o','output.out']
        wait_for(lambda:(result.job/'monitor.json').is_file())
        wait_for(lambda:'MOCK log line' in (result.job/'monitor.log').read_text(encoding='utf-8',errors='replace'))
        children['monitor'].terminate(); children['monitor'].wait(timeout=10)
        assert children['run'].poll() is None
        assert children['run'].wait(timeout=30)==7
        state=runtime.read_json(result.job/'receipt.json')
        assert state['exit_code']==7 and state['stage']=='finished'
        assert (directory/'mock-completed').is_file()
        assert load_settings(settings_file)==settings
        assert all((directory/name).read_bytes()==data for name,data in before.items())
        text=(result.job/'run.log').read_text(encoding='utf-8',errors='replace')
        assert 'mock CP2K stderr' in text and 'mock CP2K stdout' in text and '7' in text
        assert runtime.launch_risk(backend.cache,directory)==''
        return 'native helper: mock version, DLL PATH/OMP, cwd/argv, monitor independence, exit 7, preferences'
    finally:
        for child in children.values():
            if child.poll() is None:
                child.terminate(); child.wait(timeout=10)
