"""Harmless CI-only native executable; never included in Portable archives."""
import json
import os
from pathlib import Path
import sys
import time

if sys.argv[1:] == ['--version']:
    print('CP2K version 2026.2 (Studio harmless test fixture)')
    print('cp2kflags: omp')
    raise SystemExit(0)
if sys.argv[1:] != ['-i','input.inp','-o','output.out']:
    raise SystemExit(98)
Path('observed-native.json').write_text(json.dumps(dict(
    cwd=os.getcwd(), argv=sys.argv[1:], threads=os.environ.get('OMP_NUM_THREADS'),
    dll_path=os.environ.get('PATH'), pid=os.getpid())), encoding='utf-8')
print('mock CP2K stdout', flush=True)
print('mock CP2K stderr', file=sys.stderr, flush=True)
with Path('output.out').open('w', encoding='utf-8') as log:
    for index in range(30):
        log.write(f'MOCK log line {index}\n'); log.flush(); time.sleep(.2)
Path('mock-completed').write_text('mock, not a calculation', encoding='utf-8')
raise SystemExit(7)
