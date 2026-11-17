# PyInstaller macOS ARM64 onedir/windowed bundle, with a console-only helper.
from pathlib import Path
import runpy
from PyInstaller.utils.hooks import copy_metadata, collect_data_files

root = Path(SPECPATH).resolve()
identity = runpy.run_path(str(root / 'core' / 'app_info.py'))
assets = root / 'build' / 'macos-assets'
datas = []
for directory in ['schemas', 'data/cp2k-2026.1', 'presets', 'examples', 'resources/icons', 'ui/assets']:
    for path in (root / directory).rglob('*'):
        if path.is_file() and path.name != '.DS_Store' and '__pycache__' not in path.parts:
            datas.append((str(path), str(path.parent.relative_to(root))))
datas += [(str(root / 'ui/styles.qss'), 'ui'), (str(root / 'README.md'), '.'),
          (str(assets / 'requirements.txt'), '.'), (str(assets / 'build-info.json'), '.')]
datas += [(str(p), 'docs') for p in (root / 'docs').glob('*.md')]
datas += [(str(p), 'resources/smoke-fixtures') for p in (root / 'tests/fixtures/xsd').glob('*.xsd')]
datas += collect_data_files('cp2k_input_tools', includes=['pint_units.txt'])
for name in ['PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6',
             'numpy', 'scipy', 'ase', 'pydantic', 'cp2k-input-tools', 'PyYAML',
             'psutil', 'packaging']:
    datas += copy_metadata(name)

excluded = ['matplotlib', 'pytest', 'IPython', 'tkinter', 'PyQt5', 'PyQt6', 'PySide2',
            'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
            'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtPdf']
a = Analysis([str(root / 'main.py')], pathex=[str(root)], datas=datas,
             hiddenimports=['ase.io.xsd', 'ase.io.cif', 'ase.io.extxyz', 'ase.io.xyz',
                            'PySide6.QtSvg'],
             hookspath=[str(root / 'scripts/hooks')], excludes=excluded)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=identity['APP_NAME'],
          console=False, argv_emulation=False, target_arch='arm64',
          codesign_identity=None, entitlements_file=None)

h = Analysis([str(root / 'scripts/local_run_entry.py')], pathex=[str(root)],
             excludes=['PySide6', 'numpy', 'scipy', 'ase', 'matplotlib', 'pytest', 'tkinter'])
helper = EXE(PYZ(h.pure), h.scripts, [], exclude_binaries=True,
             name='cp2k-studio-runner', console=True, target_arch='arm64', codesign_identity=None)
collection = COLLECT(exe, helper, a.binaries, a.datas, h.binaries, h.datas,
                     strip=False, upx=False, name=identity['APP_NAME'])
# COLLECT inherits its console flag from the last EXE. The bundle identity is
# the GUI executable, even though it also carries a separate console helper.
collection.console = exe.console
app = BUNDLE(collection, name=identity['APP_NAME'] + '.app',
             icon=str(root / 'resources/icons/cp2k_studio.icns'),
             bundle_identifier=identity['BUNDLE_IDENTIFIER'], version=identity['APP_VERSION'],
             info_plist={
                 'CFBundleName': identity['APP_NAME'],
                 'CFBundleDisplayName': identity['APP_NAME'],
                 'CFBundleShortVersionString': identity['APP_VERSION'],
                 'CFBundleVersion': identity['BUILD_NUMBER'],
                 'LSBackgroundOnly': False,
                 'LSUIElement': False,
                 'NSHighResolutionCapable': True,
                 'NSAppleEventsUsageDescription':
                     'CP2K Studio opens Terminal windows to run the calculation package you select and monitor its output.',
             })
