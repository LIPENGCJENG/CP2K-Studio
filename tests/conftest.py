import os
import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture
def water():
    """Explicit test chemistry, never application defaults."""
    from core.models import Project, Structure, DFTConfig, Kind
    return Project(
        structure=Structure(symbols=['O', 'H', 'H'],
            positions=[(0, 0, -0.065587), (0, -0.757136, 0.520545), (0, 0.757136, 0.520545)],
            cell=((6, 0, 0), (0, 6, 0), (0, 0, 6)), periodic='XYZ'),
        dft=DFTConfig(charge=0, multiplicity=1, xc_functional='PBE',
            basis_files=['BASIS_MOLOPT'], potential_file='GTH_POTENTIALS', poisson_solver='PERIODIC'),
        kinds={'H': Kind(basis_set='DZVP-MOLOPT-GTH', potential='GTH-PBE-q1'),
               'O': Kind(basis_set='DZVP-MOLOPT-GTH', potential='GTH-PBE-q6')})


@pytest.fixture(scope='session')
def validator():
    from core.validator import InputValidator
    return InputValidator()


@pytest.fixture
def vib_project(water):
    """Explicit molecular test chemistry; no new application chemistry defaults."""
    water.global_settings.run_type = 'VIBRATIONAL_ANALYSIS'
    water.structure.periodic = 'NONE'
    water.dft.poisson_solver = 'WAVELET'
    water.dft.scf.eps_scf = 1e-9
    return water


@pytest.fixture(scope='session')
def app():
    from PySide6.QtWidgets import QApplication
    application = QApplication.instance() or QApplication([])
    from i18n.language_manager import language_manager
    language_manager().attach(application).set_language("zh_CN")
    return application
