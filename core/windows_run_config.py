"""User-local Windows execution preferences, never part of Project/Presets."""
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
import sys
from core.resources import user_data_directory, external_environment, resource_path


@dataclass(frozen=True)
class WindowsRunSettings:
    executable: str = ''
    dll_directory: str = ''
    omp_threads: int = 1


def settings_path():
    return user_data_directory() / 'local-run' / 'windows.json'


def load_settings(path=None):
    try:
        data = json.loads(Path(path or settings_path()).read_text(encoding='utf-8'))
        settings = WindowsRunSettings(**{k: data[k] for k in ['executable','dll_directory','omp_threads'] if k in data})
        if (type(settings.omp_threads) is not int or not 1 <= settings.omp_threads <= 2147483647
                or not isinstance(settings.executable, str) or not isinstance(settings.dll_directory, str)):
            raise ValueError('Invalid local settings')
        return settings
    except (OSError, ValueError, TypeError):
        return WindowsRunSettings()


def save_settings(settings, path=None):
    target = Path(path or settings_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    from core.local_run_runtime import write_json
    write_json(target, asdict(settings))


def guess_dll_directory(executable='', saved=''):
    candidates = [Path(saved)] if saved else []
    if executable:
        candidates.append(Path(executable).parent)
    candidates += [Path('C:/msys64/ucrt64/bin')]
    return next((str(p.resolve()) for p in candidates if p.is_dir()
                 and (str(p) == saved or (p/'libgfortran-5.dll').is_file())), '')


def runtime_environment(settings, environ=None):
    env = external_environment(environ)
    separator = ';' if sys.platform == 'win32' else os.pathsep
    entries = env.get('PATH', '').split(separator)
    if getattr(sys, 'frozen', False) and sys.platform == 'win32':
        internal = resource_path().resolve()
        entries = [p for p in entries if p and not Path(p).resolve().is_relative_to(internal)]
    prefix = [settings.dll_directory, str(Path(settings.executable).parent) if settings.executable else '']
    env['PATH'] = separator.join(dict.fromkeys(p for p in prefix + entries if p))
    env['OMP_NUM_THREADS'] = str(settings.omp_threads)
    return env
