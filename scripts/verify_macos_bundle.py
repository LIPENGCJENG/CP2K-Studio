"""Static verification of a developer ARM64 app (not a notarization check)."""
from pathlib import Path
import hashlib
import json
import plistlib
import subprocess
import sys
import xml.etree.ElementTree as ET


def verify(app):
    app = Path(app).resolve()
    contents = app / 'Contents'
    metadata = plistlib.loads((contents / 'Info.plist').read_bytes())
    expected = {'CFBundleName': 'CP2K Studio', 'CFBundleDisplayName': 'CP2K Studio',
                'CFBundleExecutable': 'CP2K Studio', 'CFBundleShortVersionString': '1.0.0',
                'CFBundleVersion': '1', 'LSBackgroundOnly': False, 'LSUIElement': False}
    for key, value in expected.items():
        assert metadata.get(key) == value, (key, metadata.get(key))
    assert metadata.get('CFBundleIdentifier') and metadata.get('NSAppleEventsUsageDescription')
    assert (contents / 'Resources' / metadata['CFBundleIconFile']).read_bytes()[:4] == b'icns'
    architectures = {}
    for name in ['CP2K Studio', 'cp2k-studio-runner']:
        path = contents / 'MacOS' / name
        arch = subprocess.check_output(['/usr/bin/lipo', '-archs', str(path)], text=True).strip()
        assert arch == 'arm64', (name, arch)
        architectures[name] = arch
    root = contents / 'Frameworks'
    for name in ['ui/styles.qss', 'resources/icons/cp2k_studio.png', 'i18n/cp2kstudio_en_US.qm',
                 'i18n/cp2kstudio_zh_CN.qm', 'i18n/cp2kstudio_zh_CN.ts',
                 'cp2k_input_tools/pint_units.txt', 'ase/spacegroup/spacegroup.dat',
                 'data/cp2k-2026.1/BASIS_MOLOPT', 'data/cp2k-2026.1/GTH_POTENTIALS',
                 'presets/single_point.yaml', 'requirements.txt', 'build-info.json']:
        assert (root / name).is_file(), name
        assert (root / name).resolve().is_relative_to(app), name
    version = ET.parse(root / 'schemas/cp2k_input_2026.1.xml').getroot().findtext('CP2K_VERSION')
    assert '2026.1' in version
    assert not [p for p in app.rglob('*') if p.name in {'cp2k.psmp', 'mpirun', 'mpiexec'}]
    signed = subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)],
                            capture_output=True, text=True)
    assert signed.returncode == 0, signed.stderr
    return dict(app=str(app), version=metadata['CFBundleShortVersionString'],
                bundle_identifier=metadata['CFBundleIdentifier'], architectures=architectures,
                png_sha256=hashlib.sha256((root / 'resources/icons/cp2k_studio.png').read_bytes()).hexdigest(),
                code_signature='ad-hoc (not Developer ID / not notarized)', resources='passed')


if __name__ == '__main__':
    print(json.dumps(verify(sys.argv[1]), ensure_ascii=False, indent=2))
