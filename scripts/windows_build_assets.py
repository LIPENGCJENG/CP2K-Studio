"""Prepare Windows icon/version metadata; never touch the original PNG."""
from pathlib import Path
from importlib import metadata
import json
import platform
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def prepare():
    from PIL import Image
    from core.app_info import APP_VERSION
    assets = ROOT / 'build/windows-assets'
    assets.mkdir(parents=True, exist_ok=True)
    icon = ROOT / 'resources/icons/cp2k_studio.ico'
    with Image.open(ROOT / 'resources/icons/cp2k_studio.png') as image:
        image.convert('RGBA').save(icon, format='ICO', sizes=[(s, s) for s in [16, 24, 32, 48, 64, 128, 256]])
    declarations, versions = [], {}
    for line in (ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        requirement = Requirement(line)
        if requirement.name.lower() == 'pytest':
            continue
        declarations.append(line)
        versions[requirement.name] = metadata.version(requirement.name)
    (assets / 'requirements.txt').write_text('\n'.join(declarations) + '\n', encoding='utf-8')
    (assets / 'build-info.json').write_text(json.dumps(dict(
        version=APP_VERSION, python=platform.python_version(), platform=platform.platform(),
        architecture=platform.machine(), pyinstaller=metadata.version('pyinstaller'),
        dependencies=versions, cp2k_engine_included=False, mpi_included=False), indent=2), encoding='utf-8')
    version = tuple(map(int, APP_VERSION.split('.'))) + (0,)
    (assets / 'version.txt').write_text(f'''VSVersionInfo(
  ffi=FixedFileInfo(filevers={version!r}, prodvers={version!r}, mask=0x3f,
    flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'CP2K Studio'),
    StringStruct('FileDescription', 'CP2K Studio'),
    StringStruct('FileVersion', '{APP_VERSION}'),
    StringStruct('ProductName', 'CP2K Studio'),
    StringStruct('ProductVersion', '{APP_VERSION}'),
    StringStruct('OriginalFilename', 'CP2K Studio.exe')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])])
''', encoding='utf-8')
    print('Prepared:', icon, assets)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    prepare()
