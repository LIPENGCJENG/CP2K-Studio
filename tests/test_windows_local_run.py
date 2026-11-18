"""Native Windows contracts; real execution uses only the CI mock EXE."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import base64
import json
import os
import subprocess
import sys
import time
import shutil
import pytest

from core import windows_local_run as native
from core import local_run_runtime as shared
from core.environment_check import CommandResult, EnvironmentDetector
from core.local_run import LocalRunError
from core.windows_run_config import (WindowsRunSettings, load_settings, save_settings,
    runtime_environment, guess_dll_directory)
from tests.test_windows_packaging import write_pe


@pytest.fixture
def folder(tmp_path):
    directory = tmp_path/"中文 package ' ; $() [literal]"
    directory.mkdir()
    (directory/'data').mkdir()
    for name in ['basis','potential']:
        (directory/'data'/name).write_text('test dependency', encoding='utf-8')
    (directory/'structure.xyz').write_text('1\nmock\nH 0 0 0\n', encoding='utf-8')
    (directory/'input.inp').write_text('''&FORCE_EVAL
 &DFT
  BASIS_SET_FILE_NAME data/basis
  POTENTIAL_FILE_NAME data/potential
 &END DFT
 &SUBSYS
  &TOPOLOGY
   COORD_FILE_NAME structure.xyz
  &END TOPOLOGY
 &END SUBSYS
&END FORCE_EVAL
''', encoding='utf-8')
    # Project JSON must not be opened; a run.sh is not required.
    (directory/'project.cp2kstudio.json').write_text('{not project data')
    return directory


class Probe:
    def __init__(self, result=None):
        self.calls=[]
        self.result=result or CommandResult('ok','CP2K version 2026.2\ncp2kflags: omp',0)
    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        return self.result


@pytest.fixture
def setup(folder,tmp_path,monkeypatch):
    exe=tmp_path/'MSYS2 中文 {literal}/bin/cp2k.ssmp.exe'; exe.parent.mkdir(parents=True)
    write_pe(exe)
    (exe.parent/'libgfortran-5.dll').write_bytes(b'fixture, not a DLL')
    probe=Probe()
    backend=native.WindowsLocalRunBackend(cache=tmp_path/'cache',settings_file=tmp_path/'settings.json',
        environ={'PATH':''},runner=probe)
    monkeypatch.setattr(native,'find_cp2k',lambda *a,**k:[])
    backend.detected_paths=(str(exe),)
    return backend,exe,probe


def test_inspection_without_run_sh_uses_detected_executable_and_dll_dir(folder,setup):
    backend,exe,probe=setup
    package=backend.inspect(folder)
    assert package.checked.version=='2026.2' and package.checked.mode=='OpenMP'
    assert package.settings.executable==str(exe) and package.settings.dll_directory==str(exe.parent)
    assert probe.calls==[[str(exe),'--version']]
    assert not (folder/'run.sh').exists() and not backend.cache.exists()
    assert not Path(backend.settings_file).exists()


def test_empty_environment_still_opens_configuration_instead_of_unsupported(folder,setup):
    backend,_,_=setup
    backend.detected_paths=()
    package=backend.inspect(folder)
    assert package.native_windows and not package.settings.executable and not package.checked


@pytest.mark.parametrize('missing',['input.inp','data/basis','data/potential','structure.xyz'])
def test_missing_input_dependencies_never_launch(folder,setup,missing):
    backend,_,probe=setup
    (folder/missing).unlink()
    with pytest.raises(LocalRunError):
        backend.inspect(folder)
    assert probe.calls==[] and not backend.cache.exists()


def test_preprocessor_and_invalid_folder_are_not_silently_accepted(folder):
    with pytest.raises(LocalRunError):
        native.validate_native_directory(folder/'missing')
    (folder/'input.inp').write_text('@INCLUDE unknown\n')
    with pytest.raises(LocalRunError) as error:
        native.validate_native_directory(folder)
    assert error.value.args[0].code=='winrun.preprocessor'


def test_preferences_are_user_local_safe_on_corruption_and_not_project_fields(tmp_path):
    path=tmp_path/'user/local-run/windows.json'
    selected=WindowsRunSettings('C:/msys/cp2k.ssmp.exe','C:/msys/bin',8)
    save_settings(selected,path)
    assert load_settings(path)==selected
    assert set(json.loads(path.read_text()))=={'executable','dll_directory','omp_threads'}
    for value in ['{bad', '{"omp_threads":0}', '{"omp_threads":true}', '{"omp_threads":999999999999999}']:
        path.write_text(value)
        assert load_settings(path)==WindowsRunSettings()


@pytest.mark.parametrize('threads',[0,-1,True,1.5,'4'])
def test_invalid_threads_are_rejected_before_version_probe(setup,threads):
    _,exe,probe=setup
    with pytest.raises(LocalRunError):
        native.probe_executable(WindowsRunSettings(str(exe),'',threads),runner=probe)
    assert probe.calls==[]


@pytest.mark.parametrize('code,status,output',[
    (0,'ok','not a CP2K executable'),(0xc0000135,'ok',''),(7,'ok','libgfortran-5.dll unavailable'),
    (None,'timeout',''),(None,'unavailable','')])
def test_missing_runtime_dll_or_failed_version_is_a_clear_error(setup,code,status,output):
    _,exe,_=setup
    with pytest.raises(LocalRunError) as error:
        native.probe_executable(WindowsRunSettings(str(exe)),runner=Probe(CommandResult(status,output,code)))
    assert error.value.args[0].code=='winrun.probe_error'
    assert 'libgfortran-5.dll' in str(error.value)


def test_missing_exe_invalid_pe_and_missing_dll_directory(setup,tmp_path):
    _,exe,probe=setup
    for path,dll in [(str(exe)+'missing',''),(str(exe),str(tmp_path/'missing'))]:
        with pytest.raises(LocalRunError):
            native.probe_executable(WindowsRunSettings(path,dll),runner=probe)
    exe.write_bytes(b'\x7fELF not Windows')
    with pytest.raises(LocalRunError):
        native.probe_executable(WindowsRunSettings(str(exe)),runner=probe)
    assert probe.calls==[]


def test_serial_and_mpi_modes_do_not_silently_change_threads_or_launch_mpi(setup):
    _,exe,_=setup
    serial=exe.with_name('cp2k.sopt.exe'); write_pe(serial)
    probe=Probe(CommandResult('ok','CP2K version 2026.2',0))
    assert native.probe_executable(WindowsRunSettings(str(serial)),runner=probe).mode=='Serial'
    with pytest.raises(LocalRunError) as error:
        native.probe_executable(WindowsRunSettings(str(serial),'',8),runner=probe)
    assert error.value.args[0].code=='winrun.serial_threads'
    mpi=exe.with_name('cp2k.psmp.exe'); write_pe(mpi)
    with pytest.raises(LocalRunError) as error:
        native.probe_executable(WindowsRunSettings(str(mpi)),runner=probe)
    assert error.value.args[0].code=='winrun.mode_error'


def test_runtime_environment_is_a_copy_and_contains_only_local_settings(setup,monkeypatch):
    _,exe,_=setup
    before={'PATH':'original','OMP_NUM_THREADS':'99','USER_VALUE':'untouched'}
    env=runtime_environment(WindowsRunSettings(str(exe),str(exe.parent),8),before)
    assert env['OMP_NUM_THREADS']=='8' and env['PATH'].startswith(str(exe.parent))
    assert env['USER_VALUE']=='untouched' and before['OMP_NUM_THREADS']=='99' and before['PATH']=='original'
    assert guess_dll_directory(str(exe))==str(exe.parent)


def test_powershell_source_never_interpolates_untrusted_paths(tmp_path,monkeypatch):
    manifest=tmp_path/"中文 ' ; $() ` [a] %PATH%"/'launch.json'
    command=native.powershell_command(manifest,'run')
    source=base64.b64decode(command).decode('utf-16-le')
    assert str(manifest) not in source and 'Set-Location -LiteralPath' in source
    encoded=source.split("FromBase64String('",1)[1].split("')",1)[0]
    assert base64.b64decode(encoded).decode('utf-8')==str(manifest)
    monkeypatch.setattr(native.shutil,'which',lambda name,**kw:'C:/Windows/'+name)
    commands=native.terminal_commands(manifest,'monitor',{'PATH':''})
    assert commands[0][1:4]==['-w','new','new-tab']
    assert '-NoExit' in commands[-1] and '-EncodedCommand' in commands[-1]
    assert not any(word in source.lower() for word in ['mpirun','cmd.exe','bash','wsl'])


def test_terminal_falls_back_to_new_powershell_console_without_redirecting_its_streams(setup,folder,monkeypatch,tmp_path):
    backend,exe,_=setup
    package=backend.prepare(folder,WindowsRunSettings(str(exe)))
    calls=[]
    monkeypatch.setattr(native.shutil,'which',lambda name,**kw:'C:/Windows/'+name)
    monkeypatch.setattr(subprocess,'CREATE_NEW_CONSOLE',0x10,raising=False)
    monkeypatch.setattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0x200,raising=False)
    def popen(argv,**kw):
        calls.append((argv,kw));code=1 if len(calls)==1 else None
        return SimpleNamespace(pid=123,poll=lambda:code,returncode=code)
    monkeypatch.setattr(native.subprocess,'Popen',popen)
    monkeypatch.setattr(native.time,'sleep',lambda n:None)
    backend._open_terminal(package,tmp_path,'run')
    assert len(calls)==2 and calls[-1][0][0].endswith('pwsh.exe')
    assert calls[-1][1]['creationflags'] & 0x10
    assert calls[-1][1]['shell'] is False and calls[-1][1]['close_fds']
    assert not {'stdin','stdout','stderr'} & calls[-1][1].keys()


def test_confirmed_launch_preserves_package_and_saves_only_successful_preferences(setup,folder,monkeypatch):
    backend,exe,_=setup
    (folder/'output.out').write_text('old log')
    (folder/'run.sh').write_text('never execute this')
    before={p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()}
    package=backend.prepare(folder,WindowsRunSettings(str(exe),str(exe.parent),8))
    with pytest.raises(LocalRunError):
        backend.launch(package)
    assert not backend.cache.exists()
    calls=[]
    def terminal(info,job,mode):
        calls.append(mode)
        if mode=='run':
            shared.write_json(job/'receipt.json',{'stage':'running','script_pid':123})
        return mode
    monkeypatch.setattr(backend,'_open_terminal',terminal)
    result=backend.launch(package,confirmed=True)
    assert calls==['run','monitor'] and result.script_started
    assert load_settings(backend.settings_file)==package.settings
    assert all((folder/name).read_bytes()==content for name,content in before.items())
    manifest=shared.read_json(result.job/'launch.json')
    assert manifest['settings']['omp_threads']==8 and manifest['old_output']
    message=manifest['messages']['running'].format_map(dict(directory=str(folder),threads=8,executable=str(exe)))
    assert str(exe) in message  # User braces must remain literal, not format keys.
    assert not any(key in manifest for key in ['bash','mpirun','project'])
    # Source mode stages its own stdlib helpers rather than using the GUI as Python.
    assert Path(manifest['runner'][-1]).is_file()


def test_failed_terminal_cancels_reservation_without_saving_settings(setup,folder,monkeypatch):
    backend,exe,_=setup
    package=backend.prepare(folder,WindowsRunSettings(str(exe)))
    def failed(*a):
        raise LocalRunError('terminal unavailable')
    monkeypatch.setattr(backend,'_open_terminal',failed)
    with pytest.raises(LocalRunError):
        backend.launch(package,confirmed=True)
    assert shared.launch_risk(backend.cache,folder)==''
    assert not Path(backend.settings_file).exists() and not (folder/'output.out').exists()


def test_changed_exe_requires_revalidation(setup,folder):
    backend,exe,_=setup
    package=backend.prepare(folder,WindowsRunSettings(str(exe)))
    exe.write_bytes(exe.read_bytes()+b'changed')
    with pytest.raises(LocalRunError) as error:
        backend.launch(package,confirmed=True)
    assert error.value.args[0].code=='winrun.exe_changed' and not backend.cache.exists()


def test_failed_native_start_reports_actual_reason_without_saving_settings(setup,folder,monkeypatch):
    backend,exe,_=setup
    package=backend.prepare(folder,WindowsRunSettings(str(exe)))
    def terminal(info,job,mode):
        if mode=='run':
            shared.write_json(job/'receipt.json',{'stage':'failed','script_pid':None,'exit_code':127,'error':'missing runtime file'})
        return mode
    monkeypatch.setattr(backend,'_open_terminal',terminal)
    with pytest.raises(LocalRunError) as error:
        backend.launch(package,confirmed=True)
    assert error.value.args[0].code=='winrun.failed_start'
    assert 'missing runtime file' in str(error.value) and not Path(backend.settings_file).exists()


def test_custom_relative_cache_and_preferences_are_resolved_before_entering_package(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    backend=native.WindowsLocalRunBackend(cache='cache',settings_file='settings.json')
    assert backend.cache==tmp_path/'cache' and backend.settings_file==tmp_path/'settings.json'


def test_native_log_follower_tail_creation_truncation_and_replacement(tmp_path):
    file=tmp_path/'output.out'
    follower=shared.LogFollower(file)
    assert follower.poll()==''
    file.write_text(''.join(f'{n}\n' for n in range(35)))
    assert follower.poll()==''.join(f'{n}\n' for n in range(5,35))
    file.write_text('new run\n')
    assert follower.poll()=='new run\n'
    replacement=tmp_path/'replacement'; replacement.write_text('replacement\n')
    replacement.replace(file)
    assert follower.poll()=='replacement\n'


def test_new_log_after_confirmation_is_not_overwritten_silently(folder,setup):
    backend,exe,_=setup
    package=backend.prepare(folder,WindowsRunSettings(str(exe)))
    (folder/'output.out').write_text('a new result')
    with pytest.raises(LocalRunError) as error:
        backend.launch(package,confirmed=True)
    assert error.value.args[0].code=='winrun.log_appeared'
    assert not backend.cache.exists() and (folder/'output.out').read_text()=='a new result'


def test_environment_check_reuses_native_preferences_without_writing_them(setup,monkeypatch):
    from core.run_config import RunEnvironment
    backend,exe,probe=setup
    settings=WindowsRunSettings(str(exe),str(exe.parent),4)
    monkeypatch.setattr('core.windows_run_config.load_settings',lambda:settings)
    config=RunEnvironment()
    before=config.model_dump_json()
    detector=EnvironmentDetector(config,system='Windows',runner=probe,environ={'PATH':''},directories=[exe.parent])
    report=detector.run()
    assert report.completed and report.cp2k_found
    assert detector.environ['OMP_NUM_THREADS']=='4' and str(exe.parent) in detector.environ['PATH']
    assert str(exe) in detector.known_paths and config.model_dump_json()==before
    assert not Path(backend.settings_file).exists()


def test_frozen_windows_dll_search_is_temporarily_cleared_and_restored(monkeypatch):
    import ctypes
    from core.resources import external_dll_search
    state={'directory':'C:/Studio/_internal','mode':2}
    def get_dll(size,buffer):
        if size:
            buffer.value=state['directory'] or ''
        return len(state['directory'] or '')
    def set_dll(value):
        state['directory']=value
        return 1
    def set_mode(value):
        old=state['mode'];state['mode']=value;return old
    api=SimpleNamespace(GetDllDirectoryW=get_dll,SetDllDirectoryW=set_dll,
        GetErrorMode=lambda:state['mode'],SetErrorMode=set_mode)
    monkeypatch.setattr(sys,'platform','win32')
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(ctypes,'WinDLL',lambda *a,**k:api,raising=False)
    with pytest.raises(RuntimeError):
        with external_dll_search():
            assert state['directory'] is None and state['mode'] & 0x8003
            raise RuntimeError('simulated Popen failure')
    assert state=={'directory':'C:/Studio/_internal','mode':2}


@pytest.mark.parametrize('shell_name',['pwsh.exe','powershell.exe'])
def test_encoded_powershell_passes_literal_paths_and_runner_arguments(folder,tmp_path,shell_name):
    shell=shutil.which(shell_name)
    if shell_name=='pwsh.exe' and not shell:
        shell=os.environ.get('CP2K_STUDIO_TEST_POWERSHELL') or shutil.which('pwsh')
    if not shell:
        pytest.skip('This PowerShell host is not installed on the test platform')
    from core.resources import external_dll_search
    runner=tmp_path/'mock helper.py'
    runner.write_text('import json,os,sys\nfrom pathlib import Path\nPath("ps-observed.json").write_text(json.dumps([os.getcwd(),sys.argv[1:]]),encoding="utf-8")\n',encoding='utf-8')
    manifest=folder/'launch manifest.json'
    manifest.write_text(json.dumps(dict(directory=str(folder),runner=[sys.executable,str(runner)],titles=native.TITLES)),encoding='utf-8')
    with external_dll_search():
        result=subprocess.run([shell,'-NoLogo','-NoProfile','-EncodedCommand',native.powershell_command(manifest,'run')],
            capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
    observed=json.loads((folder/'ps-observed.json').read_text(encoding='utf-8'))
    assert Path(observed[0])==folder and observed[1]==['run',str(manifest)]


@pytest.mark.skipif(sys.platform!='win32' or not os.environ.get('CP2K_STUDIO_TEST_CP2K'), reason='Requires the CI-only native Windows mock executable')
def test_real_native_mock_process_omp_exit_and_monitor_independence(folder,tmp_path):
    from scripts.windows_native_smoke import run
    assert 'exit 7' in run(os.environ['CP2K_STUDIO_TEST_CP2K'],folder,tmp_path)


@pytest.mark.skipif(sys.platform!='win32' or not os.environ.get('CP2K_STUDIO_TEST_CP2K'), reason='Requires the CI-only native Windows mock executable')
def test_native_helper_survives_its_launcher_exit(folder,tmp_path,monkeypatch):
    from scripts.windows_native_smoke import wait_for
    from core.resources import external_dll_search
    executable=os.environ['CP2K_STUDIO_TEST_CP2K']
    backend=native.WindowsLocalRunBackend(cache=tmp_path/'cache',settings_file=tmp_path/'settings.json')
    package=backend.prepare(folder,WindowsRunSettings(executable,'',2))
    children=[]
    def terminal(info,job,mode):
        if mode=='monitor':
            raise LocalRunError('No monitor needed for this independence test')
        manifest=shared.read_json(job/'launch.json')
        command=[*manifest['runner'],'run',str(job/'launch.json')]
        code='''import subprocess,sys,json
with open(sys.argv[2],'wb') as output:
    child=subprocess.Popen(json.loads(sys.argv[1]),stdin=subprocess.DEVNULL,stdout=output,stderr=output,
        close_fds=True,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW)
print(child.pid)
'''
        with external_dll_search():
            parent=subprocess.run([sys.executable,'-c',code,json.dumps(command),str(job/'run.log')],
                capture_output=True,text=True,timeout=15,env=runtime_environment(info.settings))
        assert parent.returncode==0,parent.stderr
        children.append(int(parent.stdout.strip()))
        return parent.stdout.strip()
    monkeypatch.setattr(backend,'_open_terminal',terminal)
    result=backend.launch(package,confirmed=True)
    try:
        assert result.script_started
        assert shared.read_json(result.job/'receipt.json')['stage']=='running'
        wait_for(lambda:shared.read_json(result.job/'receipt.json').get('stage')=='finished')
        assert shared.read_json(result.job/'receipt.json')['exit_code']==7
        assert (folder/'mock-completed').is_file()
    finally:
        import psutil
        for pid in children:
            try:
                process=psutil.Process(pid)
                if process.is_running():
                    process.terminate(); process.wait(timeout=10)
            except psutil.NoSuchProcess:
                pass
