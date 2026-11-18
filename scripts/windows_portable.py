"""Verify a Windows GUI bundle, smoke-test it, then publish a verified ZIP."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.windows_executable import pe_info

ZIP_NAME = 'CP2K_Studio_v1.0_Windows_x64_Portable.zip'
REQUIRED = ['resources/icons/cp2k_studio.png', 'resources/icons/cp2k_studio.ico',
            'i18n/cp2kstudio_en_US.qm', 'i18n/cp2kstudio_zh_CN.qm', 'i18n/cp2kstudio_zh_CN.ts',
            'schemas/cp2k_input_2026.1.xml', 'data/cp2k-2026.1/manifest.json',
            'data/cp2k-2026.1/BASIS_MOLOPT', 'data/cp2k-2026.1/GTH_POTENTIALS',
            'ui/styles.qss', 'ui/assets/chevron.svg', 'presets/single_point.yaml',
            'cp2k_input_tools/pint_units.txt', 'ase/spacegroup/spacegroup.dat',
            'requirements.txt', 'build-info.json', 'PySide6/plugins/platforms/qwindows.dll']


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def verify(directory):
    directory = Path(directory)
    exe = directory / 'CP2K Studio.exe'
    if pe_info(exe) != (0x8664, 0x20b, 2):
        raise ValueError('Expected an AMD64 PE32+ Windows GUI executable')
    if pe_info(directory / 'cp2k-studio-runner.exe') != (0x8664, 0x20b, 3):
        raise ValueError('Missing or invalid AMD64 console Local Run helper')
    internal = directory / '_internal'
    for name in REQUIRED:
        if not (internal / name).is_file() or not (internal / name).stat().st_size:
            raise ValueError('Missing resource: ' + name)
    if not list(internal.glob('python3*.dll')):
        raise ValueError('Missing bundled Python DLL')
    # Check all provenance fingerprints, not merely the existence of libraries.
    manifest = json.loads((internal / 'data/cp2k-2026.1/manifest.json').read_text(encoding='utf-8'))
    for name, entry in manifest['files'].items():
        if digest(internal / 'data/cp2k-2026.1' / name) != entry['sha256']:
            raise ValueError('Database fingerprint mismatch: ' + name)
    for path in directory.rglob('*'):
        if path.is_symlink():
            raise ValueError('Unexpected symlink: ' + str(path))
        if path.name.lower() in {'.git', '.venv', '.env', 'build', 'cp2k', 'cp2k.exe',
                'cp2k.psmp', 'cp2k.ssmp', 'cp2k.popt', 'cp2k.sopt', 'cp2k.psmp.exe',
                'cp2k.ssmp.exe', 'cp2k.popt.exe', 'cp2k.sopt.exe', 'mpiexec.exe', 'mpirun.exe'} or path.suffix in {'.app', '.dmg'}:
            raise ValueError('Unexpected private/build/engine content: ' + str(path))
    return exe


def smoke(exe, output):
    done = subprocess.run([str(exe.resolve()), '--windows-smoke-test', str(output)],
                          cwd=str(output.parent), env=dict(os.environ, QT_QPA_PLATFORM='offscreen'), timeout=150)
    report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
    if done.returncode or not report.get('passed') or not report.get('frozen'):
        raise ValueError('Frozen smoke test failed: ' + str(report))
    print('Frozen resource/import/project/export smoke test passed; desktop UI is not verified.')


def package(directory):
    directory = Path(directory).resolve()
    exe = verify(directory)
    with tempfile.TemporaryDirectory(prefix='CP2K 中文 smoke ') as temporary:
        smoke(exe, Path(temporary) / 'initial')
    final = directory.parent / ZIP_NAME
    checksum = directory.parent / 'SHA256SUMS.txt'
    partial = final.with_suffix('.zip.partial')
    try:
        files = [p for p in directory.rglob('*') if p.is_file()]
        inventory = {str(p.relative_to(directory)).replace('\\', '/'): digest(p) for p in files}
        with zipfile.ZipFile(partial, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, directory.name + '/' + path.relative_to(directory).as_posix())
        with tempfile.TemporaryDirectory(prefix='CP2K 中文 unzip ') as temporary:
            extracted = Path(temporary) / directory.name
            with zipfile.ZipFile(partial) as archive:
                if archive.testzip() is not None:
                    raise ValueError('ZIP CRC verification failed')
                archive.extractall(temporary)
            verify(extracted)
            actual = {p.relative_to(extracted).as_posix(): digest(p) for p in extracted.rglob('*') if p.is_file()}
            if inventory != actual:
                raise ValueError('Extracted files differ from bundle')
            smoke(extracted / 'CP2K Studio.exe', Path(temporary) / 'relocated-smoke')
        checksum_text = digest(partial) + '  ' + ZIP_NAME + '\n'
        partial.replace(final)
        checksum.write_text(checksum_text, encoding='ascii')
        if digest(final) != checksum_text.split()[0]:
            raise ValueError('Final ZIP SHA256 mismatch')
        print(final, final.stat().st_size, 'bytes')
    except BaseException:
        partial.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        checksum.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    if sys.platform != 'win32':
        raise SystemExit('Run on native Windows x64')
    package(sys.argv[1])
