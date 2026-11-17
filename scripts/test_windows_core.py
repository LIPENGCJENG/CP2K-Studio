"""Run platform-independent science/IO tests, not POSIX-terminal/desktop suites.

The excluded UI/terminal suites remain part of the macOS development tests;
tests/test_windows_packaging.py covers native Windows guards without a desktop.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    'models', 'generation', 'schema', 'databases', 'kind_workflow', 'recommendations',
    'project_io', 'presets', 'input_export', 'regression', 'structure', 'xsd_import',
    'atom_constraints', 'simulation_box', 'simulation_box_modes', 'molecular_periodicity',
    'ot_energy_gap', 'surface_dipole', 'cell_optimization', 'cell_opt_removed_type',
    'vibrational', 'vibrational_severity', 'independent_spectra', 'periodic_spectra',
    'linres_preconditioning', 'md', 'run_environment', 'windows_packaging',
]


def main():
    for start in range(0, len(MODULES), 7):
        batch = [str(ROOT / 'tests' / f'test_{name}.py') for name in MODULES[start:start+7]]
        print('Required core tests:', ', '.join(MODULES[start:start+7]), flush=True)
        code = subprocess.call([sys.executable, '-m', 'pytest', '-p', 'scripts.windows_core_plugin', '-q', *batch], cwd=ROOT)
        if code:
            return code
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
