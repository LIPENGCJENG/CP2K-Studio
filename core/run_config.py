"""Execution settings, independent of scientific CP2K input parameters."""
from i18n.messages import i18n_msg
from copy import deepcopy
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


OS_LABELS = {'linux': 'Linux / Rocky Linux', 'macos': 'macOS', 'wsl2': 'Windows / WSL2'}
# QSpinBox uses signed 32-bit integers. Keep persistence and editable UI consistent.
MAX_PARALLEL = 2_147_483_647


class RunEnvironment(BaseModel):
    model_config = ConfigDict(extra='forbid', validate_assignment=True)
    operating_system: Literal['linux', 'macos', 'wsl2'] = 'linux'
    mpi_processes: int = Field(default=1, strict=True, ge=1, le=MAX_PARALLEL)
    omp_threads: int = Field(default=1, strict=True, ge=1, le=MAX_PARALLEL)

    @property
    def required_cpu_slots(self):
        return self.mpi_processes * self.omp_threads

    @property
    def execution_mode(self):
        return 'Pure MPI' if self.omp_threads == 1 else 'MPI + OpenMP'

    @property
    def mode_label(self):
        return i18n_msg('Pure MPI', code='studio.6076939a7e3a7b0d') if self.omp_threads == 1 else i18n_msg('Hybrid MPI + OpenMP', code='studio.592b04c989251f53')

    @property
    def os_label(self):
        return OS_LABELS[self.operating_system]


def migrate_run_environment(data):
    """Return a copy and nonblocking notices for the legacy total-core format.

    Modern malformed settings are intentionally left for model validation.
    Support both an early top-level format and the nested execution settings.
    """
    value = deepcopy(data)
    notices = []
    if not isinstance(value, dict):
        return value, notices
    nested = value.get('run_environment')
    if isinstance(nested, dict) and 'total_cpu_cores' in nested:
        legacy = nested.copy()
    elif 'total_cpu_cores' in value:
        legacy = {key: value.pop(key) for key in ('total_cpu_cores', 'omp_threads') if key in value}
        # An explicit modern configuration takes precedence over obsolete duplicates.
        if nested is not None:
            return value, [i18n_msg('Ignored legacy total_cpu_cores; current runtime settings were retained.', code='studio.c8545f203bfc44e3')]
    else:
        return value, notices
    total, omp = legacy.pop('total_cpu_cores'), legacy.get('omp_threads')
    valid = (type(total) is int and type(omp) is int and total > 0 and omp > 0
             and total % omp == 0)
    legacy.pop('mpi_processes', None)
    if valid:
        legacy['mpi_processes'] = total // omp
        try:
            converted = RunEnvironment.model_validate(legacy)
        except ValueError:
            valid = False
    if valid:
        value['run_environment'] = converted.model_dump()
        notices.append(i18n_msg('Converted legacy total_cpu_cores / omp_threads to MPI processes; verify runtime settings.', code='studio.dda2f26a5f277437'))
    else:
        value['run_environment'] = RunEnvironment().model_dump()
        notices.append(i18n_msg('Legacy runtime resources could not be converted reliably. Using Linux, MPI=1, OpenMP=1; review step 07.', code='studio.b08cfdf9dc4df1ce'))
    return value, notices
