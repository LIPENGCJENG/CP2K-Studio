#!/bin/bash
set -euo pipefail
trap 'status=$?; printf "Build failed (exit %s). See the error above.\n" "$status" >&2; exit "$status"' ERR

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo 'This script builds macOS ARM64 applications and must run on macOS.' >&2
    exit 1
fi
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd -- "$project_dir"
build_python="${CP2K_BUILD_PYTHON:-$project_dir/.venv/bin/python}"
if [[ ! -x "$build_python" ]]; then
    echo 'Project Python was not found. Create .venv and install requirements.txt and requirements-build.txt.' >&2
    exit 1
fi
if [[ $# -eq 1 && "${1:-}" == '--clean' ]]; then
    # Only PyInstaller's explicitly named rebuildable cache is removed.
    [[ ! -L "$project_dir/build" && ! -L "$project_dir/build/CP2K_Studio" ]] || { echo 'Refusing to clean a symlinked build directory.' >&2; exit 1; }
    rm -rf -- "$project_dir/build/CP2K_Studio"
elif [[ $# -gt 0 ]]; then
    echo 'Usage: bash build_macos.sh [--clean]' >&2
    exit 1
fi
"$build_python" - <<'PY'
import platform, sys
from importlib import metadata
if platform.machine() != 'arm64':
    raise SystemExit('Use a native ARM64 Python, not Intel/Rosetta.')
if sys.prefix == sys.base_prefix:
    raise SystemExit('Use the project virtual environment; system Python is not a build target.')
try:
    import PyInstaller
except ImportError:
    raise SystemExit('Install build tools with this venv Python: -m pip install -r requirements-build.txt')
for name in ['PyInstaller','PySide6','numpy','ase','pydantic','cp2k-input-tools','PyYAML','psutil','packaging']:
    print(name, metadata.version(name))
print('Python',platform.python_version(),platform.machine(),sys.executable)
PY
"$build_python" scripts/macos_build_assets.py
"$build_python" -m PyInstaller --noconfirm --distpath "$project_dir/dist" \
    --workpath "$project_dir/build" "$project_dir/CP2K_Studio.spec"
[[ -x "$project_dir/dist/CP2K Studio.app/Contents/MacOS/CP2K Studio" ]]
"$build_python" scripts/verify_macos_bundle.py "$project_dir/dist/CP2K Studio.app"
echo "Built: $project_dir/dist/CP2K Studio.app"
du -sh -- "$project_dir/dist/CP2K Studio.app"
