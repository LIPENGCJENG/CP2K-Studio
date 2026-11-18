"""Build an isolated, harmless --version/exit-code fixture on the CI runner."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    if sys.platform != 'win32':
        raise SystemExit('Build the test executable on Windows')
    folder = ROOT / 'build/windows-test-engine'
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--console',
        '--name','cp2k.ssmp','--distpath',str(folder/'dist'),'--workpath',str(folder/'work'),
        '--specpath',str(folder),str(ROOT/'tests/fixtures/windows_mock_cp2k.py')],check=True,cwd=ROOT)
    executable = folder/'dist/cp2k.ssmp.exe'
    assert executable.is_file()
    if os.environ.get('GITHUB_ENV'):
        with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as handle:
            handle.write('CP2K_STUDIO_TEST_CP2K=' + str(executable) + '\n')
    print('CI-only mock executable (not a CP2K engine):',executable)
