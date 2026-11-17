"""Offline-first, versioned CP2K data discovery, indexing and explicit downloads."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from dataclasses import dataclass, field, replace
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from core.resources import resource_path
import json
import os
import shutil
import sys
import tempfile
import urllib.request
from core.basis_database import parse_basis_file
from core.potential_database import parse_potential_file
from core.models import DatabaseSettings

VERSION = '2026.1'
REF = 'v2026.1'
BUNDLED_DATA = resource_path('data', f'cp2k-{VERSION}')
OFFICIAL_FILES = {'BASIS_MOLOPT': 'basis', 'BASIS_MOLOPT_UCL': 'basis', 'BASIS_MOLOPT_UZH': 'basis',
                  'POTENTIAL': 'potential', 'GTH_POTENTIALS': 'potential', 'POTENTIAL_UZH': 'potential',
                  'BASIS_SET':'basis','GTH_BASIS_SETS':'basis'}


def cache_directory():
    base = Path(os.environ.get('XDG_CACHE_HOME', Path.home()/'.cache'))
    if sys.platform == 'darwin' and 'XDG_CACHE_HOME' not in os.environ:
        base = Path.home()/'Library'/'Caches'
    return base/'CP2K-Studio'/VERSION


@dataclass
class DatabaseStatus:
    path: str
    category: str
    version: str
    source: str
    state: str
    detail: str = ''
    entries: int = 0
    sha256: str = ''


@dataclass
class DatabaseCatalog:
    entries: list = field(default_factory=list)
    statuses: list[DatabaseStatus] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def find(self, category, element, name, path=None):
        resolved = i18n_str(Path(path).expanduser().resolve()) if path else None
        return [e for e in self.entries if e.category == category and e.element == element
                and name in e.names and (resolved is None or e.path == resolved)]

    def query(self, category, element, *, search='', quality='', source='', xc='', q=None):
        text = search.casefold()
        entries = [e for e in self.entries if e.category == category and e.element == element
                   and (not quality or e.quality == quality) and (not source or Path(e.path).name == source)
                   and (not xc or e.xc == xc) and (q is None or e.q == q)
                   and (not text or text in (' '.join(e.names) + ' ' + Path(e.path).name).casefold())]
        # An alias is part of an entry, not an additional option. Identical copies
        # in lower-priority files do not create redundant UI choices.
        seen, result = set(), []
        for e in entries:
            key = (e.element, e.name, e.content_sha256)
            if key not in seen:
                seen.add(key)
                result.append(e)
        return result

    def path_for(self, value, category):
        p = Path(value).expanduser()
        if p.is_file():
            return i18n_str(p.resolve())
        if p.is_absolute() or '/' in value or '\\' in value:
            return None
        return next((e.path for e in self.entries if e.category == category and Path(e.path).name == value), None)

    def index_conflicts(self):
        grouped = {}
        for e in self.entries:
            for name in e.names:
                grouped.setdefault((e.category,e.element,name), []).append(e)
        self.conflicts = [i18n_msg('{p0} {p1}: same name, different contents (', code='studio.ba6572f598a3a639', p0=element, p1=name) + i18n_join(', ', dict.fromkeys(Path(e.path).name for e in entries)) + '）'
                          for (_,element,name), entries in grouped.items() if len({e.content_sha256 for e in entries})>1]


def _manifest(folder):
    try:
        return json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def local_directories():
    candidates = []
    if os.environ.get('CP2K_DATA_DIR'):
        candidates.append(Path(os.environ['CP2K_DATA_DIR']))
    executable = shutil.which('cp2k') or shutil.which('cp2k.psmp') or shutil.which('cp2k.ssmp')
    if executable:
        root=Path(executable).resolve().parent.parent/'share'/'cp2k'
        candidates += [root/'data',root]
    candidates += [Path(prefix)/'share'/'cp2k'/suffix for prefix in {sys.prefix,sys.base_prefix} for suffix in ['data','']]
    candidates += [Path('/opt/homebrew/share/cp2k/data'),Path('/opt/homebrew/share/cp2k'),
                   Path('/usr/local/share/cp2k/data'),Path('/usr/local/share/cp2k'),Path('/usr/share/cp2k/data'),Path('/usr/share/cp2k')]
    return list(dict.fromkeys(p.expanduser().resolve() for p in candidates if p.is_dir()))


def scan_databases(settings=None, references=()):
    settings = settings or DatabaseSettings()
    catalog = DatabaseCatalog()
    official = _manifest(BUNDLED_DATA)
    known_hashes = {item['sha256'] for item in official.get('files',{}).values()}
    visited = set()

    def load(path, category, source, version='', expected='', declared=False):
        path = Path(path).expanduser().resolve()
        key = (i18n_str(path),category)
        if key in visited:
            return
        visited.add(key)
        status = DatabaseStatus(i18n_str(path),category,version,source,'Error')
        catalog.statuses.append(status)
        try:
            content = path.read_bytes()
            status.sha256 = sha256(content).hexdigest()
            if expected and status.sha256 != expected:
                raise ValueError(i18n_msg('File fingerprint mismatch; loading refused', code='studio.ecf90746096e9e3b'))
            verified=status.sha256 in known_hashes
            if verified:
                status.version = version or VERSION
                version = VERSION if not version else version
            if version != VERSION:
                raise ValueError(i18n_msg('Version is {p0}; target is {p1}. Provide version information.', code='studio.f1909a23bc366d1c', p0=version or i18n_msg('Unknown', code='studio.4d8c1c5b42830791'), p1=VERSION))
            if not verified and not declared:
                raise ValueError(i18n_msg('Contents are absent from the pinned official manifest; explicitly add the custom file and declare its version', code='studio.9b07e34d190bf30d'))
            entries = (parse_basis_file if category == 'basis' else parse_potential_file)(path)
            uzh_fingerprint=any('UZH' in name and metadata['sha256']==status.sha256
                                for name,metadata in official.get('files',{}).items())
            catalog.entries.extend(replace(e,version=version,source=source,
                family='UZH' if uzh_fingerprint else e.family) for e in entries)
            status.version, status.state, status.entries = version, 'Warning' if declared else 'Info', len(entries)
            status.detail = i18n_msg('User-declared version; not certified as official data', code='studio.4f59e1eb8a7cbb90') if declared else i18n_msg('File and version verified', code='studio.0633042e6cedc935')
            if entries.issues:
                status.state = 'Warning'
                status.detail += '\n' + i18n_join('\n', entries.issues)
        except (OSError, ValueError, UnicodeError) as exc:
            status.detail = i18n_str(exc)

    def folder(path, source, declared=''):
        manifest = _manifest(path)
        version = manifest.get('cp2k_version','')
        for name, category in OFFICIAL_FILES.items():
            metadata = manifest.get('files',{}).get(name,{})
            # Missing optional names are reported, never fabricated.
            load(path/name, category, source, version or declared,
                 metadata.get('sha256',''), declared=bool(declared))

    if settings.data_directory:
        folder(Path(settings.data_directory).expanduser(), i18n_msg('User-Specified Folder', code='studio.73fc5c2ef0ef34eb'), settings.declared_version)
    for directory in local_directories():
        folder(directory, i18n_msg('Local Installation Discovery', code='studio.eb0c895aec1fe268'))
    if cache_directory().is_dir():
        folder(cache_directory(), i18n_msg('Official User Cache', code='studio.df517971e5841e83'))
    folder(BUNDLED_DATA, i18n_msg('Bundled Official Cache v2026.1', code='studio.01f0769d7b7f3af5'))
    for custom in settings.custom_files:
        load(custom.path, custom.category, i18n_msg('User Custom File', code='studio.3fc5ddfcb4133a7c'), custom.version, declared=True)
    for category, ref in references:
        if ref:
            # Changed references remain inspectable, but selection validation will
            # compare the saved fingerprint and prevent silent substitution.
            load(ref.path,category,ref.source or i18n_msg('Project Record', code='studio.9f3c96e2f7b3f072'),ref.version,
                 declared=not ref.source.startswith((i18n_msg('Bundled Official', code='studio.0be64517931d478f'),i18n_msg('Official User', code='studio.f5a0cfe232dd30b2'))))
    catalog.index_conflicts()
    return catalog


@lru_cache(maxsize=4)
def _default_catalog(stamps):
    return scan_databases()


def default_catalog():
    # Detect on-disk updates without parsing everything on each keystroke.
    paths = [p for d in [BUNDLED_DATA,cache_directory(),*local_directories()] for p in d.glob('*') if p.is_file()]
    return _default_catalog(tuple((i18n_str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in paths))


def download_official_data(destination=None):
    """Only called by an explicit GUI action; all-or-nothing pinned data update."""
    destination = Path(destination or cache_directory())
    destination.parent.mkdir(parents=True,exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix='.cp2k-download-',dir=destination.parent))
    try:
        # Match the audited release commit, not a moving branch or third party.
        manifest = _manifest(BUNDLED_DATA)
        if manifest.get('cp2k_version') != VERSION or not manifest.get('commit'):
            raise ValueError(i18n_msg('The bundled official version manifest is unavailable; download version cannot be verified', code='studio.4dda470a0496a2c3'))
        for name,metadata in manifest['files'].items():
            if name not in OFFICIAL_FILES:
                continue
            url = f'https://raw.githubusercontent.com/cp2k/cp2k/{manifest["commit"]}/data/{name}'
            with urllib.request.urlopen(url,timeout=30) as response:
                content = response.read(50*1024*1024+1)
            if sha256(content).hexdigest() != metadata['sha256']:
                raise ValueError(i18n_msg('{p0}: downloaded fingerprint does not match the pinned version', code='studio.bb307a5ca9f5e296', p0=name))
            path = staged/name
            path.write_bytes(content)
            (parse_basis_file if metadata['kind']=='basis' else parse_potential_file)(path)
        (staged/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        # Keep the previous cache recoverable until all files were verified.
        backup = destination.with_name(destination.name+'.previous')
        if backup.exists():
            shutil.rmtree(backup)
        if destination.exists():
            destination.rename(backup)
        try:
            staged.rename(destination)
        except OSError:
            if backup.exists():
                backup.rename(destination)
            raise
        if backup.exists():
            shutil.rmtree(backup)
        return destination
    finally:
        if staged.exists():
            shutil.rmtree(staged)
