"""Deterministic platform fixtures plus real bounded, shell-free processes."""
from pathlib import Path
from types import SimpleNamespace
import os
import sys
import threading
import time
import pytest
from core import environment_check as env
from core.run_config import RunEnvironment


def executable(folder, name):
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/name;path.write_text('#!/bin/sh\nexit 0\n');path.chmod(0o755)
    return path


class FakeRunner:
    def __init__(self, outputs=None):self.outputs=outputs or {};self.calls=[]
    def __call__(self, args, **kwargs):
        self.calls.append(tuple(map(str,args)))
        name=Path(args[0]).name
        if name in self.outputs:return self.outputs[name]
        return env.CommandResult('ok','CP2K version 2026.1\nSource code revision git:abcdef0\ncp2kflags: mpi omp fftw3 libxc',0)


def detector(tmp_path, runner, *, system='Linux', environ=None, mpi=16):
    environ={'PATH':str(tmp_path)} if environ is None else environ
    return env.EnvironmentDetector(RunEnvironment(mpi_processes=mpi),environ=environ,runner=runner,
        system=system,root=tmp_path,directories=[])


def test_path_order_aliases_explicit_user_installation_and_finder_fallback(tmp_path):
    paths=[executable(tmp_path,name) for name in ['cp2k','cp2k.sopt','cp2k.psmp','cp2k.popt']]
    selected=env.find_cp2k({'PATH':str(tmp_path)},'Linux',directories=[])
    assert [p.name for p in selected]==['cp2k.psmp','cp2k.popt','cp2k.sopt','cp2k']
    brew=tmp_path/'homebrew/bin';custom=executable(brew,'cp2k.psmp')
    assert env.find_cp2k({'PATH':''},'Darwin',directories=[brew])==[custom]
    renamed=executable(tmp_path,'custom binary; no shell')
    assert env.find_cp2k({'PATH':'','CP2K_EXE':str(renamed)},'Darwin',directories=[])==[renamed]
    roots=env.candidate_directories({'CONDA_PREFIX':str(tmp_path/'conda')},'Darwin',prefix=tmp_path/'venv',home=tmp_path/'home')
    assert Path('/opt/homebrew/bin') in roots and tmp_path/'conda/bin' in roots and tmp_path/'venv/bin' in roots


@pytest.mark.parametrize('text,version', [('CP2K version 2026.1','2026.1'),('CP2K version 2025.2 (git:abcdef0)','2025.2'),
    ('CP2K version 7.1','7.1'),('CP2K version 2026.2 (Development Version)','2026.2'),('Unrelated 2026.1',None)])
def test_version_is_observed_not_hardcoded(text,version):
    assert env.cp2k_version(text)[0]==version


@pytest.mark.parametrize('name,expected',[('cp2k.psmp',(True,True)),('cp2k.popt',(True,False)),
    ('cp2k.ssmp',(False,True)),('cp2k.sopt',(False,False)),('cp2k',(None,None)),('cp2k.psmp.exe',(True,True))])
def test_build_suffix_is_explicitly_an_inference(name,expected):
    assert env.build_support(name)[0]==expected


def test_generic_cp2k_recognizes_actual_parallel_mpi_f08_build_flags():
    _,_,flags=env.cp2k_version('CP2K version 2026.2\ncp2kflags: omp libint fftw3 libxc parallel scalapack mpi_f08 no_statm_access')
    assert env.build_support('cp2k',flags)[0]==(True,True)


def test_multiple_versions_alias_cache_mismatch_and_serial_warning(tmp_path):
    selected=executable(tmp_path,'cp2k.psmp')
    alias=tmp_path/'cp2k';alias.symlink_to(selected)
    serial=executable(tmp_path,'cp2k.sopt')
    runner=FakeRunner({'cp2k.psmp':env.CommandResult('ok','CP2K version 2025.2',0)})
    d=detector(tmp_path,runner);r=env.EnvironmentReport();d._cp2k(r)
    assert d.selected==selected and r.cp2k_found
    assert len([item for item in r.items if item.key.startswith('cp2k.version')])==3
    assert len(runner.calls)==2
    assert next(item for item in r.items if item.key=='cp2k.version.0').status=='warning'
    d.support=(False,False);d._mpi(r)
    assert next(item for item in r.items if item.key=='mpi.build').status=='warning'
    assert all('--version' in args for args in runner.calls)


@pytest.mark.parametrize('output,name,version', [('mpirun (Open MPI) 5.0.11','Open MPI','5.0.11'),
    ('HYDRA build details:\n Version: 4.3.1','HYDRA','4.3.1'),('MPICH Version: 4.2.0','MPICH','4.2.0'),
    ('Intel(R) MPI Library for Linux* OS, Version 2021.12.0','Intel(R) MPI','2021.12.0')])
def test_mpi_implementation_and_version_without_starting_ranks(tmp_path,output,name,version):
    executable(tmp_path,'mpirun')
    runner=FakeRunner({'mpirun':env.CommandResult('ok',output,0)})
    d=detector(tmp_path,runner);d.selected=None;d.support=(True,True)
    r=env.EnvironmentReport();d._mpi(r)
    item=next(i for i in r.items if i.key=='mpi.launcher')
    assert item.status=='pass' and name in str(item.value) and version in str(item.value)
    assert runner.calls==[(str(tmp_path/'mpirun'),'--version')]
    assert next(i for i in r.items if i.key=='mpi.compatibility').status=='unknown'


def test_failed_and_unknown_mpi_are_not_passes_and_invalid_omp_is_not_copied(tmp_path):
    executable(tmp_path,'mpiexec')
    for result,status in [(env.CommandResult('timeout'),'fail'),(env.CommandResult('ok','unrecognized',0),'unknown')]:
        runner=FakeRunner({'mpiexec':result})
        d=detector(tmp_path,runner,environ={'PATH':str(tmp_path),'OMP_NUM_THREADS':'secret-token','API_KEY':'other-secret'})
        d.selected=None;d.support=(None,None);r=env.EnvironmentReport()
        d._mpi(r)
        assert next(i for i in r.items if i.key=='mpi.launcher').status==status
        assert 'secret-token' not in r.text('en_US') and 'other-secret' not in r.text('en_US')


def test_linux_links_missing_libraries_and_static_are_distinct(tmp_path):
    executable(tmp_path,'ldd');lib=tmp_path/'libopenblas.so';lib.write_text('')
    output=f'libopenblas.so => {lib} (0x123)\nlibmpi.so => not found\nlinux-vdso.so.1 (0x789)'
    runner=FakeRunner({'ldd':env.CommandResult('ok',output,0)})
    links,note=env.inspect_libraries(tmp_path/'cp2k.psmp',runner,'Linux',{'PATH':str(tmp_path)})
    assert note is None and (str(lib),'pass') in links and ('libmpi.so','fail') in links
    assert env.library_category(str(lib))=='BLAS / LAPACK'
    runner.outputs['ldd']=env.CommandResult('ok',output,1)
    assert ('libmpi.so','fail') in env.inspect_libraries(tmp_path/'cp2k.psmp',runner,'Linux',{'PATH':str(tmp_path)})[0]
    runner.outputs['ldd']=env.CommandResult('ok','not a dynamic executable',1)
    links,note=env.inspect_libraries(tmp_path/'cp2k.psmp',runner,'Linux',{'PATH':str(tmp_path)})
    assert not links and note.code=='env.static_libraries'


def test_macos_rpath_system_shared_cache_and_unresolved_file(tmp_path):
    executable(tmp_path,'otool');program=executable(tmp_path/'bin','cp2k.psmp')
    lib=tmp_path/'lib';lib.mkdir();(lib/'libdbcsr.dylib').write_text('')
    class Otool:
        def __call__(self,args,**kwargs):
            if '-l' in args:return env.CommandResult('ok','cmd LC_RPATH\n cmdsize 48\n path @loader_path/../lib (offset 12)',0)
            return env.CommandResult('ok',f'{program}:\n @rpath/libdbcsr.dylib (compatibility version 1.0.0)\n /usr/lib/nonexistent-shared-cache.dylib (compatibility version 1.0.0)\n {tmp_path}/missing.dylib (compatibility version 1.0.0)',0)
    links,note=env.inspect_libraries(program,Otool(),'Darwin',{'PATH':str(tmp_path)})
    assert links==[('@rpath/libdbcsr.dylib','pass'),('/usr/lib/nonexistent-shared-cache.dylib','unknown'),(str(tmp_path/'missing.dylib'),'fail')]
    assert note is None


def test_native_windows_does_not_run_linux_or_macos_linker_commands(tmp_path):
    runner=FakeRunner()
    links,note=env.inspect_libraries(tmp_path/'cp2k.exe',runner,'Windows',{})
    assert not runner.calls and not links and note.code=='env.windows_libraries'


def test_python_reads_current_declarations_versions_markers_and_optional_groups(tmp_path,monkeypatch):
    (tmp_path/'requirements.txt').write_text('good>=2\nbad>=3\nmissing>=1\nignored; python_version<"2"\nprivate @ https://user:secret@private.invalid/pkg.whl\n')
    (tmp_path/'pyproject.toml').write_text('[project]\nrequires-python=">=3.10"\n[project.optional-dependencies]\nscience=["optional>=1"]\n')
    def version(name):
        if name in ['missing','optional']:raise env.metadata.PackageNotFoundError(name)
        return '2.1'
    monkeypatch.setattr(env.metadata,'version',version)
    rows,note=env.python_dependencies(tmp_path)
    values={name:(spec,optional,state,ver) for name,spec,optional,state,ver in rows}
    assert note is None and values['good'][2]=='installed' and values['bad'][2]=='mismatch'
    assert values['missing'][2]=='missing' and values['optional'][1:3]==(True,'missing')
    assert 'ignored' not in values and values['private'][2]=='unknown'
    d=detector(tmp_path,FakeRunner());r=env.EnvironmentReport();d._python(r)
    text=r.text('en_US')
    assert 'secret' not in text and 'private.invalid' not in text and sys.executable in text
    assert next(i for i in r.items if getattr(i.label,'params',{}).get('name')=='optional').status=='unknown'


def test_frozen_missing_metadata_and_missing_requirement_files_are_unknown(tmp_path,monkeypatch):
    assert env.python_dependencies(tmp_path)[1].code=='env.requirements_missing'
    (tmp_path/'requirements.txt').write_text('testpackage>=1\n')
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    def absent(name):raise env.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(env.metadata,'version',absent)
    assert env.python_dependencies(tmp_path)[0][0][3]=='unknown'


@pytest.mark.parametrize('version',[1,2])
def test_cgroup_limits_include_ancestors_and_effective_hardware_capacity(tmp_path,monkeypatch,version):
    proc=tmp_path/'proc';(proc/'self').mkdir(parents=True)
    root=tmp_path/'cgroup';root.mkdir()
    if version==2:
        (proc/'self/cgroup').write_text('0::/job/task\n')
        directory=root/'job';directory.mkdir();(directory/'task').mkdir()
        (directory/'cpu.max').write_text('150000 100000')
        (directory/'memory.max').write_text(str(8*1024**3));(directory/'memory.current').write_text(str(3*1024**3))
    else:
        (proc/'self/cgroup').write_text('2:cpu,cpuacct:/job\n3:memory:/job\n')
        directory=root/'cpu/job';directory.mkdir(parents=True)
        (directory/'cpu.cfs_quota_us').write_text('150000');(directory/'cpu.cfs_period_us').write_text('100000')
        directory=root/'memory/job';directory.mkdir(parents=True)
        (directory/'memory.limit_in_bytes').write_text(str(8*1024**3));(directory/'memory.usage_in_bytes').write_text(str(3*1024**3))
    import psutil
    monkeypatch.setattr(psutil,'cpu_count',lambda logical=True:16 if logical else None)
    monkeypatch.setattr(psutil,'virtual_memory',lambda:SimpleNamespace(total=32*1024**3,available=20*1024**3,percent=37.5))
    monkeypatch.setattr(psutil,'Process',lambda:SimpleNamespace(cpu_affinity=lambda:[0,1,2,3]))
    info=env.inspect_system(FakeRunner(),'Linux',proc_root=proc,cgroup_root=root)
    assert info['physical'] is None and info['logical']==16 and info['available_cores']==4
    assert info['cpu_capacity']==1.5 and info['memory_limit']==8*1024**3 and info['memory_headroom']==5*1024**3


def test_command_timeout_cancellation_permissions_and_shell_metacharacters(tmp_path):
    runner=env.CommandRunner(timeout=.2)
    before=time.monotonic();result=runner([sys.executable,'-c','import time; time.sleep(5)'])
    assert result.status=='timeout' and time.monotonic()-before<2
    token=threading.Event();token.set()
    assert env.CommandRunner(token)([sys.executable,'--version']).status=='cancelled'
    file=tmp_path/'no-permission';file.write_text('text')
    assert runner([str(file)]).status=='unavailable'
    marker=tmp_path/'should-not-exist'
    result=runner([sys.executable,'-c','import sys; print(sys.argv[1])',f'; touch {marker}'])
    assert result.returncode==0 and not marker.exists()


def test_linux_x86_system_metadata_comes_from_the_inspected_platform(tmp_path,monkeypatch):
    proc=tmp_path/'proc';proc.mkdir();(proc/'cpuinfo').write_text('model name : Intel Fixture CPU\n')
    monkeypatch.setattr(env.platform,'machine',lambda:'x86_64')
    monkeypatch.setattr(env.platform,'freedesktop_os_release',lambda:{'PRETTY_NAME':'Rocky Linux Fixture'})
    runner=FakeRunner()
    result=env.inspect_system(runner,'Linux',proc_root=proc,cgroup_root=tmp_path/'cgroup')
    assert result['architecture']=='x86_64' and result['os']=='Rocky Linux Fixture' and result['cpu']=='Intel Fixture CPU'
    assert not runner.calls


def test_relative_path_entries_still_resolve_with_isolated_probe_working_directory(tmp_path,monkeypatch):
    folder=tmp_path/'relative-bin';executable(folder,'mpirun')
    monkeypatch.chdir(tmp_path)
    runner=env.CommandRunner(environ={'PATH':'relative-bin'})
    assert runner.environ['PATH']==str(folder)
    fake=FakeRunner({'mpirun':env.CommandResult('ok','Open MPI 5.0.11',0)})
    d=detector(tmp_path,fake,environ={'PATH':'relative-bin'});d.selected=None;d.support=(True,True)
    d._mpi(env.EnvironmentReport())
    assert fake.calls==[(str(folder/'mpirun'),'--version')]


@pytest.mark.parametrize('found,status,important,summary',[(False,'pass',True,'missing'),(True,'pass',True,'ready'),
    (True,'unknown',True,'partial'),(True,'unknown',False,'ready'),(True,'warning',True,'issues'),(True,'fail',True,'issues')])
def test_summary_is_based_on_actual_severity_and_unknown_is_not_pass(found,status,important,summary):
    r=env.EnvironmentReport(cp2k_found=found,completed=True,items=[env.CheckItem('system','test','CPU',status,'observed',important=important)])
    assert r.summary==summary and env.SYMBOLS[status] in r.text('en_US')


def test_missing_cp2k_and_one_failed_check_do_not_stop_other_sections(tmp_path):
    d=detector(tmp_path,FakeRunner(),environ={'PATH':''})
    def failure(report):raise PermissionError('secret text must not leak')
    d._python=failure
    report=d.run()
    assert report.summary=='missing' and report.completed
    assert {i.group for i in report.items}=={'cp2k','mpi','libraries','python','system'}
    assert 'secret text' not in report.text('en_US')
