"""One shell command shared by preview, scripts and export documentation."""
from pathlib import PurePosixPath
import shlex
from core.run_config import RunEnvironment

INPUT_FILENAME = 'input.inp'
OUTPUT_FILENAME = 'output.out'


def _input_name(value):
    # Bundle filenames are relative, portable and cannot escape the package.
    if (not isinstance(value, str) or not value or any(c in value for c in '\x00\n\r\\')
            or PurePosixPath(value).is_absolute() or '..' in PurePosixPath(value).parts):
        raise ValueError('输入文件名必须是计算包内的有效相对路径')
    return value


def run_command(config: RunEnvironment, input_filename=INPUT_FILENAME):
    config = RunEnvironment.model_validate(config.model_dump())
    args = ['mpirun', '-np', str(config.mpi_processes), 'cp2k.psmp',
            '-i', _input_name(input_filename), '-o', OUTPUT_FILENAME]
    return f'export OMP_NUM_THREADS={config.omp_threads}\n' + shlex.join(args)


def generate_run_script(config: RunEnvironment, input_filename=INPUT_FILENAME):
    command = run_command(config, input_filename)
    # The filename is assigned as a single quoted shell word, never evaluated.
    name = shlex.quote(_input_name(input_filename))
    return f'''#!/usr/bin/env bash
set -euo pipefail

# CP2K Studio - Run Script
cd "$(dirname "${{BASH_SOURCE[0]}}")"

input_file={name}
if [[ ! -f "$input_file" ]]; then
    printf 'Input file not found: %s\\n' "$input_file" >&2
    exit 2
fi
if ! command -v cp2k.psmp >/dev/null 2>&1; then
    printf 'cp2k.psmp: command not found; install CP2K and add it to PATH.\\n' >&2
    exit 127
fi
if ! command -v mpirun >/dev/null 2>&1; then
    printf 'mpirun: command not found; install a compatible MPI and add it to PATH.\\n' >&2
    exit 127
fi

# MPI / OpenMP settings and CP2K invocation
{command}
'''
