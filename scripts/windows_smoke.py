"""Bounded, file-reporting frozen smoke mode; no desktop or CP2K claims."""
from pathlib import Path
import json
import traceback
import sys


def run(destination):
    output = Path(destination).resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'passed': False, 'frozen': bool(getattr(sys, 'frozen', False)), 'checks': []}
    try:
        from PySide6.QtWidgets import QApplication
        from core.resources import resource_path, user_data_directory
        from core.schema import CP2KSchema
        from core.models import Project, DFTConfig, Kind
        from core.structure import load_structure
        from core.generator import generate_input
        from core.validator import InputValidator
        from core.project_io import save_project, load_project, export_bundle
        from core.input_export import export_input
        from core.presets import PresetStore, capture_preset, apply_preset
        from core.environment_check import python_dependencies, inspect_libraries
        from core.windows_local_run import WindowsLocalRunBackend
        from ui.main_window import MainWindow
        from ui.app_icon import set_application_icon
        from ui.preset_dialogs import default_preset_directory
        from i18n.language_manager import language_manager
        from ase import Atoms
        from ase.io import write

        app = QApplication.instance() or QApplication([])
        app.setApplicationName('CP2K Studio')
        app.setOrganizationName('CP2K Studio')
        language_manager().attach(app)
        assert language_manager().language == 'en_US'
        assert not set_application_icon(app).isNull()
        assert '2026.1' in CP2KSchema().version
        assert not user_data_directory().is_relative_to(resource_path())
        assert not default_preset_directory().is_relative_to(resource_path())
        deps, error = python_dependencies()
        assert not error and deps and all(row[3] == 'installed' for row in deps)
        report['checks'].append('schema, icon, dependencies, external user data')
        atoms = Atoms('OH2', positions=[(2,2,2), (2,2.75,2.5), (2,1.25,2.5)], cell=[12,12,12], pbc=True)
        for extension in ['cif', 'xyz', 'extxyz']:
            path = output / ('中文 water (test).' + extension)
            write(str(path), atoms, format='cif' if extension == 'cif' else 'extxyz')
            structure = load_structure(path)
            assert structure.symbols == ['O','H','H']
        fixtures = resource_path('resources/smoke-fixtures')
        if not fixtures.exists():
            fixtures = resource_path('tests/fixtures/xsd')
        for name, count in [('h2o_ms23.xsd',3), ('rutile_ms23.xsd',6), ('slab_ms23.xsd',22)]:
            assert len(load_structure(fixtures / name).symbols) == count
        report['checks'].append('CIF/XYZ/EXTXYZ and real XSD imports')
        project = Project(structure=structure, dft=DFTConfig(charge=0, multiplicity=1,
            xc_functional='PBE', basis_files=['BASIS_MOLOPT'], potential_file='GTH_POTENTIALS', poisson_solver='PERIODIC'),
            kinds={'H':Kind(basis_set='DZVP-MOLOPT-GTH',potential='GTH-PBE-q1'),
                   'O':Kind(basis_set='DZVP-MOLOPT-GTH',potential='GTH-PBE-q6')})
        window = MainWindow(preset_directory=output / 'presets')
        validator = InputValidator()
        for task in ['ENERGY','GEO_OPT','CELL_OPT','MD','VIBRATIONAL_ANALYSIS']:
            project.global_settings.run_type = task
            project.vibrational.ir_enabled = project.vibrational.raman_enabled = True
            window.load_into_ui(project.model_copy(deep=True))
            app.processEvents()
            before = generate_input(window.project)
            assert validator.parse(before).ok
            snapshot = window.project.model_dump_json(), window.dirty, window._revision
            for language in ['zh_CN','en_US']:
                language_manager().set_language(language)
                app.processEvents()
                assert snapshot == (window.project.model_dump_json(), window.dirty, window._revision)
                assert generate_input(window.project) == before
        report['checks'].append('five task forms/XML, translation and state preservation')
        path = output / 'project.cp2kstudio.json'
        save_project(project, path)
        assert generate_input(load_project(path)) == generate_input(project)
        store = PresetStore(output / 'saved-presets')
        saved = store.save(capture_preset(project, 'Windows smoke'))
        assert apply_preset(project, store.load(saved.id)).project.vibrational == project.vibrational
        export_input(project, output / 'standalone.inp')
        package = export_bundle(project, output / 'package')
        assert validator.parse(package.read_text(encoding='utf-8'), package.parent).ok
        assert (package.parent / 'run.sh').is_file() and (package.parent / 'EXPORT_NOTES.txt').is_file()
        report['checks'].append('project/preset roundtrip, INP and complete package')
        def unexpected(*args, **kwargs):
            raise AssertionError('Windows must not invoke POSIX tools')
        assert inspect_libraries('unused.exe', unexpected, 'Windows', {})[0] == []
        backend = WindowsLocalRunBackend(cache=output/'local-jobs',settings_file=output/'local-settings.json')
        native_package = backend.inspect(package.parent)
        assert native_package.directory == package.parent and native_package.native_windows
        from ui.windows_local_run_dialog import WindowsLocalRunDialog
        dialog = WindowsLocalRunDialog(native_package, backend, window)
        before = window.project.model_dump_json(), window.dirty, window._revision, window.preview.toPlainText()
        dialog.executable.setText('C:/CP2K/cp2k.ssmp.exe'); dialog.threads.setValue(3)
        for language in ['zh_CN','en_US']:
            language_manager().set_language(language); app.processEvents()
            assert dialog.threads.value() == 3 and dialog.executable.text() == 'C:/CP2K/cp2k.ssmp.exe'
            assert before == (window.project.model_dump_json(),window.dirty,window._revision,window.preview.toPlainText())
        dialog.reject()
        import os
        if sys.platform == 'win32' and os.environ.get('CP2K_STUDIO_TEST_CP2K'):
            from scripts.windows_native_smoke import run as run_native_smoke
            report['checks'].append(run_native_smoke(os.environ['CP2K_STUDIO_TEST_CP2K'], package.parent, output))
        window.close()
        report['checks'].append('Windows native configuration/translation without project edits; no real calculation')
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['passed'] else 1
