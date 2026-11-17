"""Explicit developer smoke mode for the built app; no real CP2K calculation.

Run only with --packaging-smoke-test NEW_OUTPUT_FOLDER. All writable fixtures,
presets and results stay in that new folder; normal launches never import this.
"""
from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import time
import traceback


def run(destination):
    output = Path(destination).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'checks': [], 'errors': [], 'frozen': bool(getattr(sys, 'frozen', False)),
              'executable': sys.executable, 'cwd': os.getcwd()}
    window = None
    children = []
    try:
        from PySide6.QtWidgets import QApplication, QFileDialog
        from PySide6.QtCore import Qt
        from core.app_info import APP_NAME, APP_VERSION
        from core.resources import resource_path, external_environment
        from core.schema import CP2KSchema
        from core.models import Project, DFTConfig, Kind, FixedAtom
        from core.structure import load_structure
        from core.generator import generate_input
        from core.validator import InputValidator
        from core.project_io import save_project, load_project, export_bundle
        from core.input_export import export_input
        from core.presets import capture_preset, apply_preset, PresetStore
        from core.comprehensive_check import comprehensive_check
        from core.environment_check import EnvironmentDetector
        from core.local_run import LocalRunBackend
        from core import local_run_runtime as runtime
        from i18n.language_manager import language_manager
        from ui.main_window import MainWindow
        from ui.app_icon import set_application_icon
        from ui.preset_dialogs import default_preset_directory
        from ase import Atoms
        from ase.io import write

        app = QApplication.instance() or QApplication([])
        app.setApplicationName(APP_NAME)
        app.setOrganizationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        language_manager().attach(app)
        assert language_manager().language == 'en_US'
        assert not set_application_icon(app).isNull()
        assert '2026.1' in CP2KSchema().version
        assert not default_preset_directory().is_relative_to(resource_path())
        report['resource_root'] = str(resource_path())
        report['preset_directory'] = str(default_preset_directory())
        report['checks'].append('runtime, icon, schema, external user-preset path')

        fixtures = output / 'structures'
        fixtures.mkdir()
        atoms = Atoms('OH2', positions=[(2, 2, 2), (2, 2.75, 2.5), (2, 1.25, 2.5)],
                      cell=[12, 12, 12], pbc=True)
        imported = {}
        for extension in ['cif', 'xyz', 'extxyz']:
            path = fixtures / ('中文 water (test).' + extension)
            write(str(path), atoms, format='cif' if extension == 'cif' else 'extxyz')
            st = load_structure(path)
            assert st.symbols == ['O', 'H', 'H'] and len(st.positions) == 3
            imported[extension] = st
            report['checks'].append(extension + ' reader/writer')
        source = resource_path('resources', 'smoke-fixtures')
        if not source.is_dir():
            source = resource_path('tests', 'fixtures', 'xsd')
        for name, count, periodic in [('h2o_ms23.xsd', 3, 'NONE'), ('rutile_ms23.xsd', 6, 'XYZ'),
                                       ('slab_ms23.xsd', 18, 'XYZ')]:
            st = load_structure(source / name)
            # Slab count depends on the audited fixture; record the real count.
            assert len(st.symbols) > 0 and st.periodic == periodic
            if name == 'h2o_ms23.xsd':
                assert len(st.symbols) == count and st.periodicity_locked
            report['checks'].append('Materials Studio fixture: ' + name + f' ({len(st.symbols)} atoms)')

        project = Project(structure=imported['cif'],
            dft=DFTConfig(charge=0, multiplicity=1, xc_functional='PBE',
                basis_files=['BASIS_MOLOPT'], potential_file='GTH_POTENTIALS', poisson_solver='PERIODIC'),
            kinds={'H': Kind(basis_set='DZVP-MOLOPT-GTH', potential='GTH-PBE-q1'),
                   'O': Kind(basis_set='DZVP-MOLOPT-GTH', potential='GTH-PBE-q6')})
        project.dft.scf.eps_scf = 1e-7
        window = MainWindow(preset_directory=output / 'presets')
        window.load_into_ui(project)
        window.show()
        app.processEvents()
        assert window.nav.count() == window.stack.count() == 8 and window.tabs.count() == 2
        validator = InputValidator()
        for task in ['ENERGY', 'GEO_OPT', 'CELL_OPT', 'MD', 'VIBRATIONAL_ANALYSIS']:
            p = project.model_copy(deep=True)
            p.global_settings.run_type = task
            if task == 'VIBRATIONAL_ANALYSIS':
                p.vibrational.ir_enabled = p.vibrational.raman_enabled = True
            window.load_into_ui(p)
            window.nav.setCurrentRow(5)
            app.processEvents()
            text = generate_input(window.project, catalog=window.kind_panel.catalog)
            assert window.preview.toPlainText() == text
            checked = validator.parse(text)
            assert checked.ok, checked.errors
            assert checked.tree['+global']['run_type'] == task.lower()
            report['checks'].append(task + ' form, preview and XML')
        assert '&MOMENTS ON' in text and '&POLAR TRUE' in text
        view = window.structure_panel.view
        view.set_labels_visible(True)
        view.zoom = 1.4
        window.structure_panel.select_atom_ids([window.project.structure.atom_ids[0]])
        window.project.structure.fixed_atoms = [FixedAtom(atom_id=window.project.structure.atom_ids[0], components='Z')]
        window.structure_panel.set_structure(window.project.structure)
        view.set_labels_visible(True)
        view.zoom = 1.4
        app.processEvents()
        view.grab().save(str(output / 'viewer.png'))
        before = window.project.model_dump_json(), window.dirty, window._revision, window.preview.toPlainText()
        for language in ['zh_CN', 'en_US']:
            language_manager().set_language(language)
            app.processEvents()
            assert (window.project.model_dump_json(), window.dirty, window._revision, window.preview.toPlainText()) == before
            assert view.zoom == 1.4 and view.show_labels
            window.grab().save(str(output / ('window-' + language + '.png')))
        report['checks'].append('3D render, atom selection/fixed marker, Aa and language-state preservation')

        project = window.project.model_copy(deep=True)
        checked = comprehensive_check(project)
        assert not checked.validation.errors, checked.validation.errors
        assert all(stage.executed for stage in checked.stages)
        (output / 'validation.txt').write_text(checked.report().render('en_US'))
        path = output / 'project.cp2kstudio.json'
        save_project(project, path)
        restored = load_project(path)
        assert generate_input(restored) == generate_input(project)
        store = PresetStore(output / 'personal-presets')
        saved = store.save(capture_preset(project, 'Bundled smoke preset'))
        assert apply_preset(project, store.load(saved.id)).project.vibrational == project.vibrational
        export_input(project, output / 'standalone.inp')
        assert (output / 'standalone.inp').read_text() == generate_input(project)
        folder = export_bundle(project, output / 'package').parent
        assert {'input.inp', 'structure.xyz', 'run.sh', 'EXPORT_NOTES.txt', 'project.cp2kstudio.json'} <= {p.name for p in folder.iterdir()}
        assert validator.parse((folder / 'input.inp').read_text(), folder).ok
        report['checks'].append('comprehensive validation, project/preset roundtrip, INP and complete bundle')

        probe_environment = external_environment()
        probe_environment['PATH'] = '/usr/bin:/bin'
        environment = EnvironmentDetector(project.run_environment, environ=probe_environment).run()
        (output / 'environment.txt').write_text(environment.text('en_US'))
        assert environment.completed
        assert not [item for item in environment.items if item.group == 'python' and item.status in {'fail', 'unknown'}]
        report['checks'].append('environment detection with Finder-like minimal PATH')

        # This helper test intentionally substitutes the terminal emulator. A
        # separate explicit native-Terminal test handles macOS Automation.
        mock = output / "中文 mock package ' (safe)"
        mock.mkdir()
        (mock / 'input.inp').write_text('Harmless helper smoke test; no CP2K command.\n')
        (mock / 'run.sh').write_text('printf "%s" "$PWD" > observed-cwd\nprintf "mock stdout\\n"\nprintf "mock stderr\\n" >&2\nsleep 1\nprintf "mock log\\n" > output.out\nexit 7\n')
        backend = LocalRunBackend(cache=output / 'local-cache')
        def terminal(package, job, mode):
            if getattr(sys, 'frozen', False):
                command = [str(Path(sys.executable).with_name('cp2k-studio-runner')), mode, str(job / 'launch.json')]
            else:
                command = [sys.executable, str(job / 'runtime.py'), mode, str(job / 'launch.json')]
            with (job / (mode + '.log')).open('wb') as log:
                child = subprocess.Popen(command, cwd=package.directory, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=log, start_new_session=True, env=external_environment())
            children.append(child)
            return str(child.pid)
        backend._open_terminal = terminal
        result = backend.launch(backend.inspect(mock), confirmed=True)
        assert result.script_started and children[0].wait(timeout=10) == 7
        assert runtime.read_json(result.job / 'receipt.json')['exit_code'] == 7
        assert (mock / 'observed-cwd').read_text() == str(mock)
        assert 'mock stdout' in (result.job / 'run.log').read_text()
        assert 'mock stderr' in (result.job / 'run.log').read_text()
        children[1].send_signal(signal.SIGINT)
        children[1].wait(timeout=5)
        report['checks'].append('independent bundled console helper: safe script, cwd, stdout/stderr and exit 7')
        dialog = QFileDialog(window)
        assert not dialog.testOption(QFileDialog.Option.DontUseNativeDialog)
        assert not app.testAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)
        report['checks'].append('native-file-dialog options retained (visual verification separate)')
    except Exception:
        report['errors'].append(traceback.format_exc())
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=5)
        if window is not None:
            window.dirty = False
            window.close()
        report['passed'] = not report['errors']
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return 0 if report['passed'] else 1
