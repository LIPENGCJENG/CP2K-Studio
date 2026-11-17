"""Reserved execution boundary. Version 1 only generates input files."""
from i18n.messages import i18n_msg


def run_calculation(*args, **kwargs):
    raise NotImplementedError(i18n_msg('This version does not execute CP2K; export the input and run it in the target environment', code='studio.84bf2369949d367f'))
