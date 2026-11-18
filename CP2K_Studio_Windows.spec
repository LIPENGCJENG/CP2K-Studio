"""Windows x64 GUI and an independent console-only native Local Run helper."""
from pathlib import Path
import runpy
import sys
from PyInstaller.utils.hooks import copy_metadata, collect_data_files

if sys.platform != 'win32':
    raise SystemExit('Build this spec on native Windows x64, not macOS/Wine.')
root = Path(SPECPATH).resolve()
identity = runpy.run_path(str(root / 'core/app_info.py'))
assets = root / 'build/windows-assets'
datas = []
for directory in ['schemas', 'data/cp2k-2026.1', 'presets', 'resources/icons', 'ui/assets']:
    for path in (root / directory).rglob('*'):
        if path.is_file() and path.suffix.lower() != '.icns' and path.name != '.DS_Store':
            datas.append((str(path), str(path.parent.relative_to(root))))
datas += [(str(root / 'ui/styles.qss'), 'ui'), (str(root / 'README.md'), '.'),
          (str(assets / 'requirements.txt'), '.'), (str(assets / 'build-info.json'), '.'),
          (str(root / 'docs/WINDOWS_BUILD.md'), 'docs')]
datas += [(str(root / 'docs/WINDOWS_LOCAL_RUN.md'), 'docs')]
datas += [(str(p), 'resources/smoke-fixtures') for p in (root / 'tests/fixtures/xsd').glob('*.xsd')]
datas += collect_data_files('cp2k_input_tools', includes=['pint_units.txt'])
for name in ['PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'numpy',
             'scipy', 'ase', 'pydantic', 'cp2k-input-tools', 'PyYAML', 'psutil', 'packaging']:
    datas += copy_metadata(name)
a = Analysis([str(root / 'main.py')], pathex=[str(root)], datas=datas,
             hiddenimports=['ase.io.xsd', 'ase.io.cif', 'ase.io.extxyz', 'ase.io.xyz', 'PySide6.QtSvg'],
             hookspath=[str(root / 'scripts/hooks')],
             excludes=['matplotlib', 'pytest', 'IPython', 'tkinter', 'PyQt5', 'PyQt6', 'PySide2',
                       'PIL', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
                       'PySide6.QtWebEngineQuick', 'PySide6.QtQml', 'PySide6.QtQuick',
                       'PySide6.QtQuickWidgets', 'PySide6.QtPdf'])
exe = EXE(PYZ(a.pure), a.scripts, [], exclude_binaries=True, name=identity['APP_NAME'],
          console=False, uac_admin=False, contents_directory='_internal', upx=False,
          icon=str(root / 'resources/icons/cp2k_studio.ico'), version=str(assets / 'version.txt'))
h = Analysis([str(root / 'scripts/windows_run_entry.py')], pathex=[str(root)],
             excludes=['PySide6','numpy','scipy','ase','matplotlib','pytest','tkinter'])
helper = EXE(PYZ(h.pure), h.scripts, [], exclude_binaries=True,
             name='cp2k-studio-runner', console=True, contents_directory='_internal', upx=False)
collection = COLLECT(exe, helper, a.binaries, a.datas, h.binaries, h.datas,
                     strip=False, upx=False, name=identity['APP_NAME'])
