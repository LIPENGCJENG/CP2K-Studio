"""Read-only local environment inspection, independent of project validation.

Only bounded version/linker/OS probes run; never a shell, MPI job, or calculation.
Raw command output and arbitrary environment variables never enter the report.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from core.resources import resource_path, external_environment, external_dll_search
from core.windows_executable import is_native_windows_program
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from i18n.messages import i18n_msg, i18n_render

ROOT = resource_path()
EXECUTABLES = ('cp2k.psmp', 'cp2k.popt', 'cp2k.ssmp', 'cp2k.sopt', 'cp2k')
SYMBOLS = {'pass': '✓', 'warning': '!', 'fail': '×', 'unknown': '?'}
GROUPS = {
    'cp2k': i18n_msg('CP2K Installation', code='env.group_cp2k'),
    'mpi': i18n_msg('MPI Environment', code='env.group_mpi'),
    'libraries': i18n_msg('Runtime & Scientific Libraries', code='env.group_libraries'),
    'python': i18n_msg('Python Dependencies', code='env.group_python'),
    'system': i18n_msg('System Information', code='env.group_system'),
}
SUMMARY = {
    'ready': i18n_msg('Environment Ready', code='env.ready'),
    'issues': i18n_msg('Issues Detected', code='env.issues'),
    'missing': i18n_msg('CP2K Not Installed', code='env.not_installed'),
    'partial': i18n_msg('Partially Verified', code='env.partial'),
}


@dataclass(frozen=True)
class CheckItem:
    group: str
    key: str
    label: object
    status: str
    value: object
    detail: object = ''
    important: bool = True


@dataclass
class EnvironmentReport:
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    items: list[CheckItem] = field(default_factory=list)
    cp2k_found: bool | None = None
    completed: bool = False

    @property
    def summary(self):
        if not self.completed:
            return 'partial'
        if self.cp2k_found is False:
            return 'missing'
        relevant = [item.status for item in self.items if item.important]
        if any(s in {'warning', 'fail'} for s in relevant):
            return 'issues'
        return 'partial' if self.cp2k_found is None or 'unknown' in relevant else 'ready'

    def text(self, language=None):
        render = lambda value: i18n_render(value, language)
        lines = [render(i18n_msg('CP2K Studio · Environment Check', code='env.title')),
            render(i18n_msg('Checked at: {time}', code='env.checked_at', time=self.checked_at.isoformat(timespec='seconds'))),
            render(SUMMARY[self.summary]), '']
        for group, title in GROUPS.items():
            lines.append(render(title))
            for item in self.items:
                if item.group != group:
                    continue
                value = render(item.value).replace('\r', '\\r').replace('\n', ' / ')
                lines.append(f'{SYMBOLS[item.status]} {render(item.label)}: {value}')
                if item.detail:
                    lines.append('    ' + render(item.detail).replace('\r', '\\r').replace('\n', ' / '))
            lines.append('')
        lines.append(render(i18n_msg('Local inspection only. No DFT, SCF, or MD calculation was run. Installation checks do not verify all CP2K functions or numerical correctness. Results do not change the project, XML schema, or exported run settings.', code='env.scope')))
        return '\n'.join(lines)


@dataclass(frozen=True)
class CommandResult:
    status: str
    output: str = ''
    returncode: int | None = None


class CommandRunner:
    """Bound wall time/output, cancel promptly, and isolate incidental files."""
    def __init__(self, cancel=None, environ=None, timeout=4.0):
        self.cancel = cancel or threading.Event()
        self.environ = external_environment(environ)
        if 'PATH' in self.environ:
            # Preserve relative PATH semantics when probes use an isolated cwd.
            self.environ['PATH']=os.pathsep.join(str(Path(p or '.').absolute()) for p in self.environ['PATH'].split(os.pathsep))
        self.timeout = timeout

    def __call__(self, argv, *, timeout=None):
        if self.cancel.is_set():
            return CommandResult('cancelled')
        proc = None
        try:
            with tempfile.TemporaryDirectory(prefix='cp2k-env-probe-') as directory, tempfile.TemporaryFile() as output:
                options = {'start_new_session': True} if os.name == 'posix' else {'creationflags': subprocess.CREATE_NO_WINDOW}
                with external_dll_search():
                    proc = subprocess.Popen(list(map(str, argv)), stdin=subprocess.DEVNULL, stdout=output,
                        stderr=subprocess.STDOUT, shell=False, cwd=directory, env=self.environ, **options)
                deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
                status = 'ok'
                while proc.poll() is None:
                    if self.cancel.is_set():
                        status = 'cancelled'; break
                    if time.monotonic() >= deadline:
                        status = 'timeout'; break
                    if os.fstat(output.fileno()).st_size > 1024 * 1024:
                        status = 'output_limit'; break
                    self.cancel.wait(.04)
                if status != 'ok':
                    if os.name == 'posix':
                        try: os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                    else:
                        proc.kill()
                proc.wait(timeout=1)
                output.seek(0)
                text = output.read(1024 * 1024).decode('utf-8', errors='replace')
                return CommandResult(status, text, proc.returncode)
        except (OSError, subprocess.SubprocessError):
            if proc and proc.poll() is None:
                proc.kill()
            return CommandResult('unavailable')


def candidate_directories(environ, system, prefix=None, home=None):
    prefix, home = Path(prefix or sys.prefix), Path(home or Path.home())
    folders = ([] if getattr(sys, 'frozen', False) else
               [prefix / ('Scripts' if system == 'Windows' else 'bin'), Path(sys.executable).parent])
    folders += [home / '.local/bin', home / 'bin']
    for key in ['CONDA_PREFIX', 'VIRTUAL_ENV', 'CP2K_HOME', 'CP2K_ROOT', 'CP2K_BIN']:
        if environ.get(key):
            folder = Path(environ[key]).expanduser()
            folders.extend([folder, folder / 'bin'])
    if system == 'Darwin':
        folders.extend(map(Path, ['/opt/homebrew/bin', '/opt/homebrew/opt/cp2k/bin',
            '/usr/local/bin', '/usr/local/opt/cp2k/bin', '/usr/bin']))
    elif system == 'Linux':
        folders.extend(map(Path, ['/usr/local/bin','/usr/bin','/bin','/opt/cp2k/bin','/usr/local/cp2k/bin']))
    elif system == 'Windows':
        folders.append(Path('C:/msys64/ucrt64/bin'))
    if getattr(sys, 'frozen', False):
        internal = Path(sys.executable).resolve().parent
        if system == 'Darwin':
            internal = internal.parent  # The entire Contents, not only Frameworks.
        folders = [p for p in folders if not p.resolve().is_relative_to(internal)]
    return list(dict.fromkeys(folders))


def find_cp2k(environ=None, system=None, *, directories=None, known_paths=()):
    environ = os.environ if environ is None else environ
    system = system or platform.system()
    directories = candidate_directories(environ, system) if directories is None else directories
    found, real_paths = [], set()
    for name in EXECUTABLES:
        paths = []
        location = shutil.which(name, path=environ.get('PATH', ''))
        if location: paths.append(Path(location))
        paths.extend(Path(folder) / (name + '.exe' if system == 'Windows' else name) for folder in directories)
        paths.extend(Path(p).expanduser() for p in known_paths if Path(p).name.lower() in {name, name+'.exe'})
        for path in paths:
            try:
                if path.is_file() and os.access(path, os.X_OK) and (system != 'Windows' or is_native_windows_program(path)):
                    path = path.absolute()
                    # Keep symlink aliases visible, but avoid repeated identical paths.
                    if str(path) not in real_paths:
                        real_paths.add(str(path)); found.append(path)
            except OSError:
                continue
    explicit=[*known_paths,*(environ[key] for key in ['CP2K_EXECUTABLE','CP2K_EXE'] if environ.get(key))]
    for value in explicit:
        try:
            path=Path(value).expanduser().absolute()
            if (path.is_file() and os.access(path,os.X_OK) and str(path) not in real_paths
                    and (system != 'Windows' or is_native_windows_program(path))):
                real_paths.add(str(path));found.append(path)
        except (OSError,ValueError):pass
    return found


def cp2k_version(text):
    match = re.search(r'\bCP2K\s+(?:version\s*[:=]?\s*)?(\d{4}\.\d+(?:\.\d+)?|\d+\.\d+(?:\.\d+)?)\b', text, re.I)
    revision = re.search(r'\bgit[:\s]+([0-9a-f]{6,40})\b', text, re.I)
    flags = re.search(r'^\s*(?:cp2kflags|cp2k\s+flags|build\s+features)\s*[:=]\s*(.+)$', text, re.I | re.M)
    allowed = {'mpi','mpi_f08','parallel','omp','openmp','fftw','fftw3','libxc','libint','libint2','libxsmm','scalapack','dbcsr','elpa','mkl','cuda','hip','dlaf','sirius','cosma'}
    features = tuple(sorted({s.lower().lstrip('_') for s in re.findall(r'[A-Za-z0-9_]+', flags.group(1))} & allowed)) if flags else ()
    return match.group(1) if match else None, revision.group(1) if revision else None, features


def build_support(path, features=()):
    suffix = Path(path).name.lower().removesuffix('.exe').rsplit('.', 1)[-1]
    known = {'psmp': (True,True), 'popt': (True,False), 'ssmp': (False,True), 'sopt': (False,False)}
    if suffix not in known:
        suffix=Path(path).resolve().name.lower().removesuffix('.exe').rsplit('.',1)[-1]
    if suffix in known:
        return known[suffix], i18n_msg('Inferred from executable suffix; not a numerical test.', code='env.suffix_note')
    if {'mpi','mpi_f08','parallel','omp','openmp'} & set(features):
        return (bool({'mpi','mpi_f08','parallel'} & set(features)), bool({'omp','openmp'} & set(features))), i18n_msg('Reported build flags', code='env.reported_flags')
    return (None,None), i18n_msg('Build capabilities are not reported.', code='env.build_unknown')


def _read(path, size=262144):
    try:
        with Path(path).open(encoding='utf-8', errors='replace') as handle:
            return handle.read(size)
    except (OSError, ValueError):
        return ''


def cgroup_limits(proc_root=Path('/proc'), cgroup_root=Path('/sys/fs/cgroup')):
    """Inspect known cgroup membership and ancestors, never scan directories."""
    cpu, memory = [], []
    memberships = _read(proc_root / 'self/cgroup').splitlines()
    for line in memberships:
        parts = line.split(':', 2)
        if len(parts) != 3: continue
        _, controllers, relative = parts
        roots = [cgroup_root] if not controllers else [cgroup_root / c for c in controllers.split(',')]
        # Common combined v1 controller mount.
        if 'cpu' in controllers: roots.append(cgroup_root / 'cpu,cpuacct')
        for root in roots:
            current = root / relative.lstrip('/')
            for _ in range(32):
                cpu_max = _read(current / 'cpu.max').split()
                quota, period = _read(current / 'cpu.cfs_quota_us').strip(), _read(current / 'cpu.cfs_period_us').strip()
                try:
                    q, p = map(float, cpu_max) if len(cpu_max)==2 and cpu_max[0]!='max' else (float(quota),float(period))
                    if q>0 and p>0: cpu.append(q/p)
                except ValueError: pass
                limit = _read(current / 'memory.max').strip() or _read(current / 'memory.limit_in_bytes').strip()
                used = _read(current / 'memory.current').strip() or _read(current / 'memory.usage_in_bytes').strip()
                try:
                    limit_value=int(limit)
                    if limit_value>0:
                        try: used_value=int(used)
                        except ValueError: used_value=None
                        memory.append((limit_value,used_value))
                except ValueError: pass
                if current == root or root not in current.parents: break
                current = current.parent
    return (min(cpu) if cpu else None), memory


def inspect_system(runner, system=None, *, proc_root=Path('/proc'), cgroup_root=Path('/sys/fs/cgroup')):
    system = system or platform.system()
    info = dict(os=platform.platform(), architecture=platform.machine(), cpu=platform.processor(),
                physical=None, logical=os.cpu_count(), available_cores=None, cpu_capacity=None,
                total_memory=None, available_memory=None, memory_percent=None, memory_limit=None, memory_headroom=None)
    if system == 'Darwin':
        info['os'] = 'macOS ' + platform.mac_ver()[0]
        command = str(Path(shutil.which('sysctl') or '/usr/sbin/sysctl').absolute())
        result = runner([command,'-n','machdep.cpu.brand_string'])
        if result.status=='ok' and result.returncode==0:
            info['cpu'] = result.output.strip()[:200]
    elif system == 'Linux':
        try:
            info['os'] = platform.freedesktop_os_release().get('PRETTY_NAME', info['os'])
        except OSError: pass
        match = re.search(r'^(?:model name|Hardware)\s*:\s*(.+)$', _read(proc_root/'cpuinfo'), re.M)
        if match: info['cpu'] = match.group(1).strip()[:200]
    try:
        import psutil
        try:info['physical']=psutil.cpu_count(logical=False)
        except (psutil.Error,OSError,NotImplementedError):pass
        try:info['logical']=psutil.cpu_count(logical=True) or info['logical']
        except (psutil.Error,OSError,NotImplementedError):pass
        try:
            mem = psutil.virtual_memory()
            info.update(total_memory=mem.total,available_memory=mem.available,memory_percent=mem.percent)
        except (psutil.Error,OSError,NotImplementedError):pass
        try: info['available_cores'] = len(psutil.Process().cpu_affinity())
        except (AttributeError, psutil.Error, OSError): pass
    except (ImportError, OSError, RuntimeError): pass
    if info['available_cores'] is None:
        try: info['available_cores'] = len(os.sched_getaffinity(0))
        except (AttributeError,OSError): info['available_cores'] = info['logical']
    info['cpu_capacity'] = info['available_cores']
    if system == 'Linux':
        quota, memory = cgroup_limits(proc_root,cgroup_root)
        if quota is not None:
            info['cpu_capacity'] = min(info['available_cores'],quota) if info['available_cores'] else quota
        if memory and info['total_memory']:
            relevant = [(limit,used) for limit,used in memory if limit<info['total_memory']]
            if relevant:
                info['memory_limit'] = min(limit for limit,_ in relevant)
                known=[max(0,limit-used) for limit,used in relevant if used is not None]
                info['memory_headroom'] = min(known) if known else None
    return info


def python_dependencies(root=ROOT):
    """Read declared requirements; return name, specifier, optional, status, version."""
    try:
        from packaging.requirements import Requirement
    except ImportError:
        return [], i18n_msg('The packaging library is unavailable; requirements cannot be evaluated.', code='env.packaging_missing')
    declarations, seen = [], set()
    def read_requirements(file, depth=0):
        if depth>8 or file.resolve() in seen: return
        seen.add(file.resolve())
        for number,line in enumerate(_read(file).splitlines(),1):
            line=line.strip()
            if not line or line.startswith('#'):continue
            if line.startswith(('-r ', '--requirement ')):
                read_requirements(file.parent/line.split(maxsplit=1)[1],depth+1)
            elif line.startswith('-'):
                declarations.append((None,str(number),False))
            else:
                declarations.append((line.split(' #',1)[0].strip(),None,False))
    source = root/'requirements.txt'
    if source.is_file(): read_requirements(source)
    project = root/'pyproject.toml'
    python_spec = None
    if project.is_file():
        try:
            import tomllib
            config=tomllib.loads(project.read_text(encoding='utf-8')).get('project',{})
            declarations.extend((value,None,False) for value in config.get('dependencies',[]))
            declarations.extend((value,None,True) for group in config.get('optional-dependencies',{}).values() for value in group)
            python_spec=config.get('requires-python')
        except (ImportError,OSError,ValueError):
            return [],i18n_msg('pyproject.toml could not be evaluated; dependency metadata is incomplete.', code='env.pyproject_unknown')
    if not declarations:
        return [],i18n_msg('Dependency declarations are unavailable; include requirements.txt and distribution metadata when packaging.', code='env.requirements_missing')
    results=[]
    for source,number,optional in declarations:
        try:
            if source is None: raise ValueError()
            requirement=Requirement(source)
            if requirement.marker and not requirement.marker.evaluate():continue
            try:
                installed=metadata.version(requirement.name)
                valid=not requirement.specifier or requirement.specifier.contains(installed,prereleases=True)
                status='installed' if valid else 'mismatch'
                if requirement.url:status='unknown'  # Provenance cannot be inferred from a version.
            except metadata.PackageNotFoundError:
                installed='';status='unknown' if getattr(sys,'frozen',False) else 'missing'
            results.append((requirement.name,str(requirement.specifier),optional,status,installed))
        except (ValueError,TypeError):
            results.append(('?',number or '',optional,'unknown',''))
    if python_spec:
        from packaging.specifiers import SpecifierSet
        try:
            results.append(('Python',python_spec,False,'installed' if SpecifierSet(python_spec).contains(platform.python_version()) else 'mismatch',platform.python_version()))
        except ValueError: results.append(('Python','',False,'unknown',platform.python_version()))
    return list(dict.fromkeys(results)),None


def library_category(name):
    value=name.lower()
    if re.search(r'lib(?:mpi|mpich)',value): return 'MPI'
    if 'dbcsr' in value:return 'DBCSR'
    if 'scalapack' in value:return 'ScaLAPACK'
    if any(s in value for s in ['openblas','mkl','accelerate.framework']):return 'BLAS / LAPACK'
    if 'lapack' in value:return 'LAPACK'
    if 'blas' in value:return 'BLAS'
    if 'fftw' in value:return 'FFTW'
    if re.search(r'libxc(?:[.\-/]|$)',value):return 'LibXC'
    if re.search(r'libint(?:2|[.\-/]|$)',value):return 'Libint'
    return None


def inspect_libraries(executable, runner, system, environ):
    """Return actual dynamic link observations; absence never proves static loss."""
    if system not in {'Linux','Darwin'}:
        return [],i18n_msg('Native Windows DLL resolution is not verified. WSL2 is inspected as Linux.', code='env.windows_libraries')
    tool=shutil.which('ldd' if system=='Linux' else 'otool',path=environ.get('PATH',''))
    if not tool and system=='Darwin' and Path('/usr/bin/otool').is_file():tool='/usr/bin/otool'
    if not tool:return [],i18n_msg('The platform dependency inspection tool is unavailable.', code='env.linker_missing')
    tool=str(Path(tool).absolute())
    result=runner([tool,str(executable)] if system=='Linux' else [tool,'-L',str(executable)])
    if any(s in result.output.lower() for s in ['statically linked','not a dynamic executable']):
        return [],i18n_msg('Static or unlisted libraries cannot be verified from dynamic-link output; they are not marked missing.', code='env.static_libraries')
    if result.status!='ok' or (system=='Darwin' and result.returncode!=0):
        return [],i18n_msg('Dependency inspection did not complete successfully ({status}).', code='env.linker_failed',status=command_status(result))
    rpaths=[];weak=[]
    if system=='Darwin':
        load=runner([tool,'-l',str(executable)])
        rpaths=re.findall(r'cmd LC_RPATH\s+cmdsize \d+\s+path (.+?) \(offset',load.output)
        weak=re.findall(r'cmd LC_LOAD_WEAK_DYLIB\s+cmdsize \d+\s+name (.+?) \(offset',load.output)
    dependencies=[]
    base=Path(executable).resolve().parent
    for line in result.output.splitlines():
        if system=='Linux':
            missing=re.match(r'\s*(\S+)\s+=>\s+not found',line)
            if missing:
                dependencies.append((missing.group(1),'fail'));continue
            match=re.match(r'\s*\S+\s+=>\s+(/.+?)\s+\(0x',line) or re.match(r'\s*(/.+?)\s+\(0x',line)
            if match:
                path=match.group(1);dependencies.append((path,'pass' if Path(path).is_file() else 'unknown'))
        else:
            match=re.match(r'\s+(.+?)\s+\(compatibility version',line)
            if not match:continue
            original=match.group(1)
            def expand(value):return value.replace('@loader_path',str(base)).replace('@executable_path',str(base))
            paths=[Path(expand(original))]
            if original.startswith('@rpath/'):
                paths=[Path(expand(p))/original[len('@rpath/'):] for p in rpaths]
            paths.extend(Path(p)/Path(original).name for p in environ.get('DYLD_LIBRARY_PATH','').split(os.pathsep) if p)
            if any(p.is_file() for p in paths):
                dependencies.append((original,'pass'))
            elif original in weak or original.startswith(('/usr/lib/','/System/Library/')) or original.startswith('@'):
                dependencies.append((original,'unknown'))
            else:dependencies.append((original,'fail'))
    note=None
    if result.returncode!=0 and not any(status=='fail' for _,status in dependencies):
        note=i18n_msg('Dependency inspection did not complete successfully ({status}).',code='env.linker_failed',status=command_status(result))
    return dependencies,note


def command_status(result):
    return {'ok':i18n_msg('Exit code {exitcode}',code='env.exit_code',exitcode=result.returncode),
        'timeout':i18n_msg('Timed out',code='env.timeout'),
        'cancelled':i18n_msg('Cancelled',code='env.cancelled'),
        'not_probed':i18n_msg('Not probed within the time budget',code='env.not_probed'),
        'unavailable':i18n_msg('Unavailable or permission denied',code='env.unavailable'),
        'output_limit':i18n_msg('Output limit exceeded',code='env.output_limit')}[result.status]


class EnvironmentDetector:
    def __init__(self, run_environment, *, environ=None, runner=None, system=None, root=ROOT,
                 cancel=None, directories=None, known_paths=()):
        self.config=run_environment.model_copy(deep=True)
        self.environ=dict(os.environ if environ is None else environ)
        self.system=system or platform.system()
        if self.system == 'Windows':
            from core.windows_run_config import load_settings, guess_dll_directory, runtime_environment, WindowsRunSettings
            saved = load_settings()
            self.environ = runtime_environment(WindowsRunSettings(saved.executable,
                guess_dll_directory(saved.executable, saved.dll_directory), saved.omp_threads), self.environ)
            known_paths = (*known_paths, *([saved.executable] if saved.executable else []))
        self.cancel=cancel or threading.Event()
        self.runner=runner or CommandRunner(self.cancel,self.environ)
        self.root=Path(root);self.directories=directories;self.known_paths=known_paths

    def run(self, progress=lambda value:None):
        report=EnvironmentReport()
        stages=[('cp2k',self._cp2k),('mpi',self._mpi),('libraries',self._libraries),('python',self._python),('system',self._system)]
        self.selected=None;self.support=(None,None);self.selected_ok=False
        for group,check in stages:
            if self.cancel.is_set():break
            progress(i18n_msg('Checking: {section}',code='env.progress',section=GROUPS[group]))
            try:check(report)
            except Exception:
                report.items.append(CheckItem(group,group+'.unknown',GROUPS[group],'unknown',
                    i18n_msg('This check could not be completed; other checks continue.',code='env.check_failed')))
        report.completed=not self.cancel.is_set()
        return report

    def _cp2k(self, report):
        paths=find_cp2k(self.environ,self.system,directories=self.directories,known_paths=self.known_paths)
        report.cp2k_found=bool(paths)
        if not paths:
            report.items.append(CheckItem('cp2k','cp2k.path',i18n_msg('Executable',code='env.executable'),'fail',
                i18n_msg('CP2K Not Found',code='env.cp2k_missing'),i18n_msg('Check installation and the GUI process PATH. Common platform installation and current Python/Conda locations were also checked. Input generation remains available.',code='env.missing_note')))
            return
        self.selected=paths[0]
        report.items.append(CheckItem('cp2k','cp2k.selected',i18n_msg('Current Detection Target',code='env.selected'),'pass',str(self.selected)))
        if self.system == 'Darwin' and not any(shutil.which(name, path=self.environ.get('PATH', '')) for name in EXECUTABLES):
            report.items.append(CheckItem('cp2k', 'cp2k.off_path',
                i18n_msg('GUI PATH', code='env.gui_path'), 'warning',
                i18n_msg('CP2K was found outside the GUI PATH. Finder and Terminal may have different environments. Configure the target terminal before Local Run; Studio did not modify PATH.', code='env.off_path')))
        cache={};deadline=time.monotonic()+15
        for index,path in enumerate(paths):
            if self.cancel.is_set():return
            real=path.resolve()
            if real in cache:result=cache[real]
            elif time.monotonic()<deadline and len(cache)<12:
                result=self.runner([str(path),'--version'],timeout=min(4,max(.1,deadline-time.monotonic())))
                cache[real]=result
            else:result=CommandResult('not_probed')
            version,revision,features=cp2k_version(result.output)
            success=result.status=='ok' and result.returncode==0 and version is not None
            status='pass' if success else 'fail' if result.returncode not in {0,None} or result.status in {'unavailable','timeout'} else 'unknown'
            if success and version!='2026.1':status='warning'
            value=version or i18n_msg('Unknown',code='env.unknown')
            detail=i18n_msg('{path}; revision: {revision}',code='env.version_detail',path=str(path),revision=revision or i18n_msg('Unknown',code='env.unknown'))
            if not success:detail=i18n_msg('{path}; {status}',code='env.probe_detail',path=str(path),status=command_status(result))
            elif status=='warning':detail=i18n_msg('{detail}. Studio targets CP2K 2026.1; input specifications may differ. XML and calculation settings were not changed.',code='env.version_mismatch',detail=detail)
            report.items.append(CheckItem('cp2k',f'cp2k.version.{index}',i18n_msg('CP2K Version',code='env.cp2k_version'),status,value,detail,important=index==0))
            if index==0:
                self.selected_ok=success
                self.support,note=build_support(path,features)
                mpi,omp=self.support
                build=(i18n_msg('MPI + OpenMP',code='env.build_mpi_omp') if mpi and omp else
                    i18n_msg('MPI',code='env.build_mpi') if mpi else
                    i18n_msg('Serial + OpenMP',code='env.build_serial_omp') if mpi is False and omp else
                    i18n_msg('Serial',code='env.build_serial') if mpi is False else i18n_msg('Unknown',code='env.unknown'))
                report.items.append(CheckItem('cp2k','cp2k.build',i18n_msg('Build Type',code='env.build'),'pass' if mpi is not None else 'unknown',build,note))
                report.items.append(CheckItem('cp2k','cp2k.features',i18n_msg('Reported Features',code='env.features'),'pass' if features else 'unknown',', '.join(features) if features else i18n_msg('Not reported; no features were assumed.',code='env.features_unknown'),important=False))

    def _mpi(self, report):
        launcher=shutil.which('mpirun',path=self.environ.get('PATH','')) or shutil.which('mpiexec',path=self.environ.get('PATH',''))
        if launcher and self.system == 'Windows' and not is_native_windows_program(launcher):
            launcher = None
        if not launcher:
            folders=candidate_directories(self.environ,self.system) if self.directories is None else self.directories
            for folder in folders:
                names = ['mpirun.exe', 'mpiexec.exe'] if self.system == 'Windows' else ['mpirun','mpiexec']
                launcher=next((str(folder/name) for name in names if (folder/name).is_file() and os.access(folder/name,os.X_OK)
                               and (self.system != 'Windows' or is_native_windows_program(folder/name))),None)
                if launcher:break
        if not launcher:
            report.items.append(CheckItem('mpi','mpi.launcher',i18n_msg('MPI Runtime',code='env.mpi'),'warning',i18n_msg('mpirun / mpiexec not found.',code='env.mpi_missing')))
        else:
            launcher=str(Path(launcher).absolute())
            result=self.runner([launcher,'--version'])
            found=re.search(r'(?:Open\s*MPI|OpenRTE|MPICH|HYDRA|Intel\(R\) MPI|Microsoft MPI|MS-MPI)[^\r\n]*',result.output,re.I)
            # Keep only known implementation names and numeric versions, never raw diagnostics.
            name=re.search(r'Open\s*MPI|OpenRTE|MPICH|HYDRA|Intel\(R\) MPI|Microsoft MPI|MS-MPI',found.group(0),re.I).group(0) if found else ''
            version=re.search(r'\b\d+(?:\.\d+){1,3}\b',found.group(0)) if found else None
            version_text=version.group(0) if version else ''
            if not version_text:
                fallback=re.search(r'(?:Version|HYDRA build details)[\s:]*([0-9]+(?:\.[0-9]+){1,3})',result.output,re.I)
                if fallback:version_text=fallback.group(1)
            value=name + (' '+version_text if version_text else '')
            success=result.status=='ok' and result.returncode==0
            status='pass' if name and version_text and success else 'unknown' if success else 'fail'
            report.items.append(CheckItem('mpi','mpi.launcher',i18n_msg('MPI Runtime',code='env.mpi'),status,value or i18n_msg('Unknown implementation/version',code='env.mpi_unknown'),
                str(launcher) if success else i18n_msg('{path}; {status}',code='env.probe_detail',path=str(launcher),status=command_status(result))))
        mpi,_=self.support
        if mpi is False and self.config.mpi_processes>1:
            report.items.append(CheckItem('mpi','mpi.build',i18n_msg('Configured MPI Compatibility',code='env.mpi_compatibility'),'warning',i18n_msg('Multiple MPI ranks are configured, but the selected CP2K build is serial.',code='env.serial_warning')))
        else:
            report.items.append(CheckItem('mpi','mpi.compatibility',i18n_msg('Configured MPI Compatibility',code='env.mpi_compatibility'),'unknown',i18n_msg('Launcher presence does not verify ABI compatibility with CP2K. No MPI job was launched.',code='env.mpi_abi')))
        if self.selected and not shutil.which('cp2k.psmp',path=self.environ.get('PATH','')):
            report.items.append(CheckItem('mpi','mpi.script',i18n_msg('Exported run.sh',code='env.script'),'warning',i18n_msg('The existing script expects cp2k.psmp on PATH. This inspection does not change the script or choose another executable for it.',code='env.script_note')))
        raw=self.environ.get('OMP_NUM_THREADS','')
        valid=bool(re.fullmatch(r'[1-9][0-9]{0,9}(?:,[1-9][0-9]{0,9})*',raw)) and all(int(v)<=2147483647 for v in raw.split(','))
        report.items.append(CheckItem('mpi','mpi.omp','OMP_NUM_THREADS','pass' if valid else 'unknown' if not raw else 'warning',raw if valid else i18n_msg('Not set',code='env.not_set') if not raw else i18n_msg('Invalid OpenMP thread-count value (not copied).',code='env.omp_invalid'),important=False))

    def _libraries(self, report):
        if not self.selected:
            report.items.append(CheckItem('libraries','libraries.unavailable',GROUPS['libraries'],'unknown',i18n_msg('No CP2K executable is available to inspect.',code='env.no_library_target')));return
        libraries,note=inspect_libraries(self.selected,self.runner,self.system,self.environ)
        if note:report.items.append(CheckItem('libraries','libraries.check',GROUPS['libraries'],'unknown',note))
        elif not libraries:report.items.append(CheckItem('libraries','libraries.empty',GROUPS['libraries'],'unknown',i18n_msg('No resolvable dynamic links were reported.',code='env.no_links')))
        for index,(path,status) in enumerate(libraries):
            report.items.append(CheckItem('libraries',f'library.{index}',library_category(path) or i18n_msg('Runtime Library',code='env.library'),status,path))
        report.items.append(CheckItem('libraries','libraries.optional',i18n_msg('Optional / Static Scientific Libraries',code='env.optional_libraries'),'unknown',i18n_msg('Only observed dynamic links are listed. Missing names do not prove absent static libraries or disabled optional features. macOS shared-cache, transitive and late-loaded libraries may remain unverified.',code='env.library_scope'),important=False))

    def _python(self, report):
        report.items.append(CheckItem('python','python.interpreter',i18n_msg('Current Python',code='env.python'),'pass',platform.python_version(),sys.executable))
        requirements,note=python_dependencies(self.root)
        if note:report.items.append(CheckItem('python','python.metadata',GROUPS['python'],'unknown',note))
        for index,(name,spec,optional,state,version) in enumerate(requirements):
            label=i18n_msg('Optional',code='env.optional') if optional else i18n_msg('Required (declared)',code='env.required')
            status={'installed':'pass','missing':'unknown' if optional else 'fail','mismatch':'warning','unknown':'unknown'}[state]
            state_text={'installed':i18n_msg('Installed',code='env.installed'),'missing':i18n_msg('Missing',code='env.missing'),'mismatch':i18n_msg('Version Mismatch',code='env.mismatch'),'unknown':i18n_msg('Unknown',code='env.unknown')}[state]
            report.items.append(CheckItem('python',f'python.{index}',i18n_msg('{name} · {kind}',code='env.package_label',name=name,kind=label),status,i18n_msg('{state}; installed: {version}; required: {specifier}',code='env.package_value',state=state_text,version=version or '—',specifier=spec or '—'),important=not optional))

    def _system(self, report):
        info=inspect_system(self.runner,self.system)
        fields=[('os',i18n_msg('Operating System',code='env.os')),('architecture',i18n_msg('Architecture',code='env.architecture')),
            ('cpu',i18n_msg('CPU',code='env.cpu')),('physical',i18n_msg('Physical Cores',code='env.physical')),
            ('logical',i18n_msg('Logical Cores',code='env.logical')),('available_cores',i18n_msg('Available Logical Cores (OS / affinity)',code='env.available_cores')),
            ('cpu_capacity',i18n_msg('Known CPU Capacity (OS / affinity / quota)',code='env.cpu_capacity')),
            ('total_memory',i18n_msg('Total Memory',code='env.memory')),('available_memory',i18n_msg('Available Memory',code='env.available_memory')),
            ('memory_percent',i18n_msg('Memory Usage',code='env.memory_percent'))]
        if info['memory_limit'] is not None:
            fields=[(key,i18n_msg('Host / VM Total Memory',code='env.host_memory') if key=='total_memory' else
                i18n_msg('Host / VM Available Memory',code='env.host_available_memory') if key=='available_memory' else
                i18n_msg('Host / VM Memory Usage',code='env.host_memory_percent') if key=='memory_percent' else label) for key,label in fields]
            fields.extend([('memory_limit',i18n_msg('Container Memory Limit',code='env.memory_limit')),('memory_headroom',i18n_msg('Container Memory Headroom (conservative estimate)',code='env.memory_headroom'))])
        for key,label in fields:
            value=info.get(key)
            if value is not None and 'memory' in key and key!='memory_percent':value=f'{value/1024**3:.2f} GiB'
            elif key=='memory_percent' and value is not None:value=f'{value:.1f}%'
            report.items.append(CheckItem('system','system.'+key,label,'pass' if value is not None and value!='' else 'unknown',str(value) if value is not None and value!='' else i18n_msg('Unknown',code='env.unknown'),important=key not in {'physical','cpu'}))
        demand=self.config.required_cpu_slots;capacity=info['cpu_capacity']
        report.items.append(CheckItem('system','system.resources',i18n_msg('Configured Resources (read-only)',code='env.resources'),'warning' if capacity is not None and demand>capacity else 'pass' if capacity else 'unknown',i18n_msg('MPI: {mpi}; OpenMP: {omp}; required logical slots: {slots}',code='env.resource_values',mpi=self.config.mpi_processes,omp=self.config.omp_threads,slots=demand),i18n_msg('Comparison is local; the exported configuration may target another machine. CPU and memory alone cannot predict DFT completion.',code='env.resource_note')))
