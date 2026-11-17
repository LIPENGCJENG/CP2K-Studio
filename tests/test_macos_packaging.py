"""Frozen resource discovery and independent helper boundaries."""
from pathlib import Path
import os
import sys
from types import SimpleNamespace
import pytest
from core import resources
from core import local_run as local
from core import local_run_runtime as runtime
from core.environment_check import candidate_directories


def test_resource_root_ignores_cwd_and_supports_frozen_layout(tmp_path, monkeypatch):
    expected = Path(__file__).resolve().parents[1] / 'schemas' / 'cp2k_input_2026.1.xml'
    monkeypatch.chdir(tmp_path)
    assert resources.resource_path('schemas', 'cp2k_input_2026.1.xml') == expected
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path / 'App/Contents/Frameworks'), raising=False)
    assert resources.resource_path('schemas', 'cp2k_input_2026.1.xml') == Path(sys._MEIPASS) / 'schemas/cp2k_input_2026.1.xml'


def test_external_tools_keep_path_and_user_values_but_not_private_loader_paths(tmp_path, monkeypatch):
    root = tmp_path / 'CP2K Studio.app/Contents/Frameworks'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(root), raising=False)
    env = {'PATH': '/usr/bin:/bin', 'OMP_NUM_THREADS': '7', '_PYI_ARCHIVE_FILE': 'gui',
           'QT_PLUGIN_PATH': str(root / 'PySide6/plugins'), 'LD_LIBRARY_PATH': str(root),
           'LD_LIBRARY_PATH_ORIG': '/user/libraries', 'PYTHONPATH': '/user/modules'}
    original = dict(env)
    cleaned = resources.external_environment(env)
    assert env == original and cleaned['PATH'] == env['PATH'] and cleaned['OMP_NUM_THREADS'] == '7'
    assert cleaned['LD_LIBRARY_PATH'] == '/user/libraries' and cleaned['PYTHONPATH'] == '/user/modules'
    assert '_PYI_ARCHIVE_FILE' not in cleaned and 'QT_PLUGIN_PATH' not in cleaned
    monkeypatch.delattr(sys, 'frozen')
    assert resources.external_environment(env) == env


def test_environment_detection_does_not_search_inside_bundle(tmp_path, monkeypatch):
    contents = tmp_path / 'CP2K Studio.app/Contents'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(contents / 'MacOS/CP2K Studio'))
    folders = candidate_directories({'CP2K_HOME': str(contents / 'Resources')}, 'Darwin',
                                    prefix=contents / 'Frameworks', home=tmp_path / 'home')
    assert not any(p.is_relative_to(contents) for p in folders)
    assert Path('/opt/homebrew/bin') in folders


def test_saved_builtin_references_survive_an_app_move_without_scientific_changes(water, tmp_path):
    import json
    from core.database_manager import default_catalog
    from core.models import DatabaseReference
    from core.project_io import load_project, relocate_project_resources
    from core.presets import Preset, apply_preset
    data = water.model_dump()
    catalog = default_catalog()
    old_root = tmp_path / 'old location/CP2K Studio.app/Contents/Frameworks/data/cp2k-2026.1'
    for label in ['H', 'O']:
        for category, key, selected in [('basis','basis_ref','basis_set'), ('potential','potential_ref','potential')]:
            entry = catalog.find(category, label, data['kinds'][label][selected])[0]
            ref = entry.reference()
            ref['path'] = str(old_root / Path(entry.path).name)
            data['kinds'][label][key] = ref
    data['dft']['basis_files'] = [data['kinds']['O']['basis_ref']['path']]
    data['dft']['potential_file'] = data['kinds']['O']['potential_ref']['path']
    data['dft']['potential_files'] = [data['dft']['potential_file']]
    path = tmp_path / 'previous-project.json'
    text = json.dumps(data)
    path.write_text(text)
    restored = load_project(path)
    assert path.read_text() == text
    assert restored.structure == water.structure and restored.vibrational == water.vibrational
    assert restored.dft.scf == water.dft.scf and restored.global_settings == water.global_settings
    assert all(Path(k.basis_ref.path).is_file() and Path(k.potential_ref.path).is_file() for k in restored.kinds.values())
    preset = Preset(name='Old App preset', parameters={'kinds': data['kinds'], 'dft': data['dft']})
    applied = apply_preset(water, preset).project
    assert all(Path(k.basis_ref.path).is_file() for k in applied.kinds.values())
    invalid = water.model_copy(deep=True)
    invalid.kinds['O'].basis_ref = DatabaseReference(**dict(data['kinds']['O']['basis_ref'], sha256='0'*64))
    assert relocate_project_resources(invalid).kinds['O'].basis_ref.path == invalid.kinds['O'].basis_ref.path


@pytest.fixture
def frozen_package(tmp_path, monkeypatch):
    app = tmp_path / 'CP2K Studio.app/Contents'
    executable = app / 'MacOS/CP2K Studio'
    executable.parent.mkdir(parents=True)
    executable.touch()
    helper = executable.with_name('cp2k-studio-runner')
    helper.touch()
    helper.chmod(0o700)
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(app / 'Frameworks'), raising=False)
    monkeypatch.setattr(sys, 'executable', str(executable))
    monkeypatch.setattr(local, 'detect_terminal', lambda *a: local.Terminal('xterm', '/mock/xterm'))
    directory = tmp_path / "中文 package ' (safe)"
    directory.mkdir()
    (directory / 'run.sh').write_text('exit 0\n')
    (directory / 'input.inp').write_text('mock')
    return directory, helper


def test_frozen_launch_uses_console_helper_without_source_python(frozen_package, tmp_path, monkeypatch):
    directory, helper = frozen_package
    backend = local.LocalRunBackend(cache=tmp_path / 'cache')
    calls = []
    def terminal(package, job, mode):
        calls.append(mode)
        if mode == 'run':
            runtime.write_json(job / 'receipt.json', {'stage': 'running', 'script_pid': 123})
        return mode
    monkeypatch.setattr(backend, '_open_terminal', terminal)
    monkeypatch.setattr(local.shutil, 'copyfile', lambda *a: pytest.fail('frozen launch copied a source Python file'))
    result = backend.launch(backend.inspect(directory), confirmed=True)
    assert calls == ['run', 'monitor'] and result.script_started
    assert not (result.job / 'runtime.py').exists()
    assert 'exec "$2" "$3" "$4"' in (result.job / 'terminal.sh').read_text()
    assert ' -u ' not in (result.job / 'terminal.sh').read_text()
    helper.unlink()
    with pytest.raises(local.LocalRunError) as error:
        backend.inspect(directory)
    assert error.value.args[0].code == 'local.helper_missing'


def test_frozen_terminal_argv_uses_helper_and_sanitized_environment(frozen_package, tmp_path, monkeypatch):
    directory, helper = frozen_package
    backend = local.LocalRunBackend(cache=tmp_path / 'cache')
    package = backend.inspect(directory)
    calls = []
    def popen(argv, **kw):
        calls.append((argv, kw))
        return SimpleNamespace(pid=123, poll=lambda: None)
    monkeypatch.setattr(local.subprocess, 'Popen', popen)
    monkeypatch.setattr(local.time, 'sleep', lambda *a: None)
    monkeypatch.setenv('_PYI_ARCHIVE_FILE', 'gui')
    backend._open_terminal(package, tmp_path, 'run')
    argv, options = calls[0]
    assert str(helper) in argv and str(helper.with_name('CP2K Studio')) not in argv
    assert '_PYI_ARCHIVE_FILE' not in options['env']
    assert options['env']['PATH'] == os.environ['PATH']
