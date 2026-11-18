"""Windows contracts are inspectable on macOS; these are not real EXE runs."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import zipfile
import pytest
import yaml
from core import environment_check as env
from core import resources
from core.local_run import LocalRunBackend, LocalRunError
from core.windows_executable import pe_info, is_native_windows_program
from scripts import windows_portable as portable

ROOT = Path(__file__).resolve().parents[1]


def write_pe(path, machine=0x8664, subsystem=2):
    content = bytearray(512)
    content[:2] = b'MZ'
    struct.pack_into('<I', content, 60, 128)
    content[128:132] = b'PE\0\0'
    struct.pack_into('<H', content, 132, machine)
    struct.pack_into('<H', content, 152, 0x20b)
    struct.pack_into('<H', content, 220, subsystem)
    path.write_bytes(content)
    path.chmod(0o755)


def test_workflow_only_dispatch_read_permissions_and_verified_artifacts():
    # BaseLoader preserves YAML's GitHub-specific 'on' key, rather than YAML 1.1 booleans.
    workflow = yaml.load((ROOT / '.github/workflows/build-windows-portable.yml').read_text(), Loader=yaml.BaseLoader)
    assert set(workflow['on']) == {'workflow_dispatch'}
    assert workflow['permissions'] == {'contents': 'read'}
    job = workflow['jobs']['portable']
    assert job['runs-on'] == 'windows-2025'
    assert 'continue-on-error' not in str(job)
    steps = job['steps']
    actions = [s for s in steps if 'uses' in s]
    assert len(actions) == 3 and all(len(s['uses'].split('@')[1]) == 40 for s in actions)
    upload = actions[-1]['with']
    assert upload['retention-days'] == '14' and upload['if-no-files-found'] == 'error'
    assert 'SHA256SUMS.txt' in upload['path'] and portable.ZIP_NAME in upload['path']
    assert actions[1]['with']['python-version'] == '3.12' and actions[1]['with']['architecture'] == 'x64'


def test_icon_preserves_source_and_contains_multiple_resolutions():
    # Read the ICO directory directly; Pillow is build-only, not a runtime test dependency.
    png = ROOT / 'resources/icons/cp2k_studio.png'
    assert hashlib.sha256(png.read_bytes()).hexdigest() == 'abf05e661c75f382f998ea5dab3567a4481570f4224ece695dcd00fe33472cc0'
    ico = (ROOT / 'resources/icons/cp2k_studio.ico').read_bytes()
    reserved, kind, count = struct.unpack_from('<HHH', ico)
    assert (reserved, kind) == (0, 1) and count == 7
    assert {(ico[6+i*16] or 256) for i in range(count)} == {16,24,32,48,64,128,256}


def test_windows_pe_guard_does_not_detect_or_execute_wsl_linux_binary(tmp_path):
    native = tmp_path / 'cp2k.psmp.exe'
    write_pe(native)
    elf = tmp_path / 'cp2k.ssmp.exe'
    elf.write_bytes(b'\x7fELF' + bytes(512)); elf.chmod(0o755)
    truncated = tmp_path / 'cp2k.exe'; truncated.write_bytes(b'MZ')
    assert pe_info(native) == (0x8664,0x20b,2)
    assert not is_native_windows_program(elf) and not is_native_windows_program(truncated)
    assert env.find_cp2k({'PATH':''}, 'Windows', directories=[tmp_path], known_paths=[elf]) == [native]
    def forbidden(*a, **k):
        pytest.fail('Invoked a POSIX linker on Windows')
    assert env.inspect_libraries(native, forbidden, 'Windows', {})[0] == []


def test_posix_adapter_does_not_dispatch_windows_to_bash_cmd_or_applescript(tmp_path, monkeypatch):
    for name in ['run.sh','input.inp']:
        (tmp_path / name).write_text('test')
    monkeypatch.setattr('core.local_run.detect_bash', lambda *a: pytest.fail('Bash detection must not run'))
    monkeypatch.setattr('core.local_run.subprocess.Popen', lambda *a, **k: pytest.fail('No command may start'))
    with pytest.raises(LocalRunError) as caught:
        LocalRunBackend(system='Windows', cache=tmp_path/'cache').inspect(tmp_path)
    assert caught.value.args[0].code == 'local.windows_unsupported'


def test_windows_paths_are_not_cwd_relative_and_user_data_stays_external(tmp_path, monkeypatch):
    internal = tmp_path / 'OneDrive 中文/CP2K Studio/_internal'
    monkeypatch.setattr(sys,'frozen', True, raising=False)
    monkeypatch.setattr(sys,'_MEIPASS',str(internal),raising=False)
    monkeypatch.setattr(sys,'platform','win32')
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'User/AppData/Local'))
    monkeypatch.chdir(tmp_path)
    assert resources.resource_path('schemas') == internal/'schemas'
    assert resources.user_data_directory() == tmp_path/'User/AppData/Local/CP2K Studio'


def test_windows_unicode_resource_paths_keep_metacharacter_restrictions(monkeypatch):
    from core.file_references import serialize_file_reference, FileReferenceError
    from pathlib import PureWindowsPath
    monkeypatch.setattr(sys, 'platform', 'win32')
    value = PureWindowsPath('C:/Users/用户/OneDrive/CP2K Studio/_internal/data/BASIS_MOLOPT').as_posix()
    assert serialize_file_reference(value, 'BASIS_SET_FILE_NAME') == value
    for invalid in [value+'\nKEYWORD T', value+';command', value+'$name', value+'  extra']:
        with pytest.raises(FileReferenceError):
            serialize_file_reference(invalid, 'BASIS_SET_FILE_NAME')


def test_relocated_portable_database_requires_matching_saved_fingerprint(tmp_path):
    old = tmp_path/'moved/CP2K Studio/_internal/data/cp2k-2026.1/BASIS_MOLOPT'
    current = ROOT/'data/cp2k-2026.1/BASIS_MOLOPT'
    assert resources.relocated_database(old, portable.digest(current)) == str(current.resolve())
    assert resources.relocated_database(old, '0'*64) is None


@pytest.fixture
def fake_bundle(tmp_path):
    app = tmp_path / 'CP2K Studio'
    internal = app / '_internal'; internal.mkdir(parents=True)
    write_pe(app / 'CP2K Studio.exe')
    write_pe(app / 'cp2k-studio-runner.exe', subsystem=3)
    for name in portable.REQUIRED:
        path = internal / name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b'test')
    (internal / 'data/cp2k-2026.1/manifest.json').write_text('{"files":{}}')
    (internal / 'python312.dll').write_bytes(b'dll fixture')
    return app


@pytest.mark.parametrize('machine,subsystem',[(0x14c,2),(0x8664,3)])
def test_verifier_rejects_x86_or_console_exe(fake_bundle,machine,subsystem):
    write_pe(fake_bundle / 'CP2K Studio.exe', machine, subsystem)
    with pytest.raises(ValueError,match='AMD64'):
        portable.verify(fake_bundle)


def test_verifier_rejects_missing_qt_and_changed_database(fake_bundle):
    plugin = fake_bundle/'_internal/PySide6/plugins/platforms/qwindows.dll'
    plugin.unlink()
    with pytest.raises(ValueError,match='qwindows'):
        portable.verify(fake_bundle)
    plugin.write_bytes(b'dll')
    (fake_bundle/'_internal/data/cp2k-2026.1/manifest.json').write_text('{"files":{"BASIS_MOLOPT":{"sha256":"invalid"}}}')
    with pytest.raises(ValueError,match='fingerprint'):
        portable.verify(fake_bundle)


def test_zip_structure_crc_file_hashes_and_relocation(fake_bundle,monkeypatch):
    calls=[]
    monkeypatch.setattr(portable,'smoke',lambda exe,output:calls.append(exe))
    portable.package(fake_bundle)
    archive = fake_bundle.parent / portable.ZIP_NAME
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert 'CP2K Studio/CP2K Studio.exe' in zipped.namelist()
        assert 'CP2K Studio/_internal/python312.dll' in zipped.namelist()
    assert len(calls)==2 and calls[0].parent != calls[1].parent
    assert (archive.parent/'SHA256SUMS.txt').read_text().split()[0] == portable.digest(archive)


def test_smoke_failure_does_not_produce_a_distributable(fake_bundle,monkeypatch):
    def fail(*a):
        raise ValueError('simulated startup failure')
    monkeypatch.setattr(portable,'smoke',fail)
    with pytest.raises(ValueError,match='startup'):
        portable.package(fake_bundle)
    assert not (fake_bundle.parent/portable.ZIP_NAME).exists()


def test_database_resources_are_all_tracked_and_match_manifest():
    manifest=json.loads((ROOT/'data/cp2k-2026.1/manifest.json').read_text())
    for name, entry in manifest['files'].items():
        assert portable.digest(ROOT/'data/cp2k-2026.1'/name)==entry['sha256']
    assert 'data/** -text' in (ROOT/'.gitattributes').read_text()
