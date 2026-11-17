"""Prepare derived icons and runtime metadata without changing source assets."""
from pathlib import Path
from importlib import metadata
import json
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'build' / 'macos-assets'


def prepare():
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = ROOT / 'resources' / 'icons' / 'cp2k_studio.icns'
    if not icon.is_file():
        source = ROOT / 'resources' / 'icons' / 'cp2k_studio.png'
        iconset = ASSETS / 'CP2K.iconset'
        iconset.mkdir(exist_ok=True)
        for size in [16, 32, 128, 256, 512]:
            for scale in [1, 2]:
                target = iconset / f'icon_{size}x{size}{"@2x" if scale == 2 else ""}.png'
                subprocess.run(['/usr/bin/sips', '-z', str(size * scale), str(size * scale),
                                str(source), '--out', str(target)], check=True,
                               stdout=subprocess.DEVNULL)
        subprocess.run(['/usr/bin/iconutil', '-c', 'icns', str(iconset), '-o', str(icon)], check=True)
    # pytest is development-only; packaged Environment Check inspects exactly
    # the runtime declarations and shipped distribution metadata.
    from packaging.requirements import Requirement
    declarations = []
    versions = {}
    for line in (ROOT / 'requirements.txt').read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        req = Requirement(line)
        if req.name.lower() == 'pytest':
            continue
        declarations.append(line)
        versions[req.name] = metadata.version(req.name)
    (ASSETS / 'requirements.txt').write_text('\n'.join(declarations) + '\n')
    (ASSETS / 'build-info.json').write_text(json.dumps(dict(
        python=platform.python_version(), architecture=platform.machine(),
        macos=platform.mac_ver()[0], pyinstaller=metadata.version('pyinstaller'),
        dependencies=versions, cp2k_engine_included=False, mpi_included=False), indent=2) + '\n')
    print('Icon:', icon)
    print('Runtime metadata:', ASSETS)


if __name__ == '__main__':
    prepare()
