"""Read-only bundle resources and new writable application diagnostics."""
from pathlib import Path
import os
import sys
import hashlib


def resource_path(*parts):
    root = (Path(sys._MEIPASS) if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
            else Path(__file__).resolve().parents[1])
    return root.joinpath(*parts)


def user_data_directory():
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'CP2K Studio'
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'CP2K Studio'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'CP2K-Studio'


def relocated_database(path, sha256):
    """Recover a missing old App's database only with an identical fingerprint."""
    original = Path(path)
    if original.is_file() or not sha256:
        return None
    parts = original.parts
    candidates = []
    for index, part in enumerate(parts):
        tail = parts[index + 1:]
        if (part.endswith('.app') and len(tail) == 5 and tail[0] == 'Contents'
                and tail[1] in {'Resources', 'Frameworks'} and tail[2:4] == ('data', 'cp2k-2026.1')):
            candidates.append(tail[2:])
        elif part == '_internal' and len(tail) == 3 and tail[:2] == ('data', 'cp2k-2026.1'):
            candidates.append(tail)
    for tail in candidates:
        current = resource_path(*tail)
        try:
            if current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest() == sha256:
                return str(current.resolve())
        except OSError:
            pass
    return None


def external_environment(environ=None):
    """Do not pass PyInstaller's private loader/plugin paths to system tools.

    This returns a copy and never adds Homebrew or changes the system PATH.
    Development launches retain their existing environment exactly.
    """
    result = dict(os.environ if environ is None else environ)
    if not getattr(sys, 'frozen', False):
        return result
    root = resource_path().resolve()
    for key in list(result):
        if key.startswith('_PYI_') or key == '_MEIPASS2':
            result.pop(key)
    for key in ['QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH',
                'PYTHONHOME', 'PYTHONPATH', 'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH']:
        value = result.get(key)
        if not value:
            continue
        inside = any(Path(p).resolve().is_relative_to(root) for p in value.split(os.pathsep) if p)
        if inside:
            original = result.pop(key + '_ORIG', None)
            result.pop(key, None)
            if original:
                result[key] = original
    return result
