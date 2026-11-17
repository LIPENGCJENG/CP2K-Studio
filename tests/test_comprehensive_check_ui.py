"""One explicit UI entry point and session-only comprehensive check state."""
from threading import Event
import time
import pytest
from PySide6.QtWidgets import QToolBar, QDialog
from core.database_manager import BUNDLED_DATA
from core.schema import BUNDLED_XML
from ui import main_window
from ui.main_window import MainWindow
from ui.xml_dialog import XMLDialog
from tests.test_layout_workflow import wait_for_worker


@pytest.fixture
def window(app, water, tmp_path):
    window = MainWindow(preset_directory=tmp_path / 'presets')
    window.load_into_ui(water)
    yield window
    wait_for_worker(app, window)
    window.dirty = False
    window.close()


def check(app, window):
    window.export_panel.check_button.click()
    wait_for_worker(app, window)


def test_only_comprehensive_entry_uses_existing_xml_service(window, app, monkeypatch):
    actions = window.findChild(QToolBar).actions()
    assert not any(action.text() in ('XML 检查', 'XML 校验') for action in actions)
    assert not hasattr(window, 'validate_action') and not hasattr(window, 'validate_input')
    opened = []
    monkeypatch.setattr(XMLDialog, 'exec', lambda dialog: opened.append(dialog) or QDialog.DialogCode.Rejected)
    next(action for action in actions if action.text() == 'XML 规范').trigger()
    assert len(opened) == 1
    original = window.validation_service
    invoked = []
    def service(project):
        invoked.append(project.model_dump())
        return original(project)
    monkeypatch.setattr(window, 'validation_service', service)
    assert window.export_panel.check_button.text() == '综合检查'
    assert window._step_states[7].state == 'unchecked'
    check(app, window)
    assert len(invoked) == 1
    assert window._step_states[7].state == 'ready'
    assert window.tabs.currentIndex() == 1
    report = window.report.toPlainText()
    assert report.startswith('CP2K Studio · 综合检查')
    assert all(f'[{index}]' in report for index in range(1, 5))
    assert '错误：0' in report and '警告：0' in report


def test_known_failed_xml_blocks_export_and_skipped_stages_are_visible(window, app, tmp_path, monkeypatch):
    window.project.xml_spec = str(tmp_path / 'missing.xml')
    check(app, window)
    assert window._step_states[7].state == 'error'
    assert '未执行' in window.report.toPlainText()
    errors = []
    monkeypatch.setattr(window, '_error', lambda title, detail: errors.append((title, detail)))
    assert not window.ready_to_export()
    assert errors and errors[0][0] == '综合检查未通过'
    window.set_xml_spec(None)
    assert window._step_states[7].state == 'unchecked'
    check(app, window)
    assert window._step_states[7].state == 'ready'


def test_edit_during_background_check_discards_result_and_prevents_concurrency(window, app, monkeypatch):
    entered, release = Event(), Event()
    original = main_window.comprehensive_check
    calls = []
    def blocked(*args, **kwargs):
        calls.append(True)
        entered.set()
        assert release.wait(15)
        return original(*args, **kwargs)
    monkeypatch.setattr(main_window, 'comprehensive_check', blocked)
    window.check_current_configuration()
    try:
        assert entered.wait(5)
        assert not window.export_panel.check_button.isEnabled()
        window.check_current_configuration()
        window.global_panel.fields['global_settings.project_name'][0].setText('modified_during_check')
        window.refresh()
    finally:
        release.set()
    wait_for_worker(app, window)
    assert len(calls) == 1
    assert window._step_states[7].state == 'unchecked'
    assert window._comprehensive_result is None
    assert '重新' in window.statusBar().currentMessage()
    check(app, window)
    assert window._step_states[7].state == 'ready'


@pytest.mark.parametrize('source', ['xml', 'basis', 'potential'])
def test_dependency_change_automatically_invalidates_passed_check(window, app, tmp_path, source):
    if source == 'xml':
        path = tmp_path / 'custom.xml'
        path.write_bytes(BUNDLED_XML.read_bytes())
        window.set_xml_spec(str(path))
    else:
        basename = 'BASIS_MOLOPT' if source == 'basis' else 'GTH_POTENTIALS'
        path = tmp_path / basename
        path.write_bytes((BUNDLED_DATA / basename).read_bytes())
        project = window.project.model_copy(deep=True)
        # The panel pins source fingerprints, so update both the legacy source
        # list and explicit references through an actual project load.
        for kind in project.kinds.values():
            setattr(kind, source + '_ref', None)
        if source == 'basis':
            project.dft.basis_files = [str(path)]
        else:
            project.dft.potential_file = str(path)
            project.dft.potential_files = [str(path)]
        window.load_into_ui(project)
    check(app, window)
    assert window._step_states[7].state == 'ready', window.report.toPlainText()
    # Atomic replacement also exercises parent-directory monitoring; file-only
    # QFileSystemWatcher registrations disappear on some platforms after rename.
    replacement = tmp_path / 'replacement'
    replacement.write_bytes(path.read_bytes() + b'\n<!-- changed -->\n' if source == 'xml' else path.read_bytes() + b'\n# changed\n')
    replacement.replace(path)
    deadline = time.monotonic() + 5
    while window._step_states[7].state == 'ready' and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert window._step_states[7].state == 'unchecked'
    assert window._configuration_check_revision is None
    assert window._comprehensive_result is None


def test_ui_only_operations_and_save_preserve_report_but_open_invalidates(window, app, tmp_path):
    check(app, window)
    report = window.report.toPlainText()
    preview = window.preview.toPlainText()
    signature = window._configuration_check_snapshot
    for page in range(8):
        window.nav.setCurrentRow(page)
        window.tabs.setCurrentIndex(page % 2)
        window.preview.verticalScrollBar().setValue(10)
        app.processEvents()
    window.project_path = tmp_path / 'saved.json'
    assert window.save()
    assert window._step_states[7].state == 'ready'
    assert window._configuration_check_snapshot == signature
    assert window.report.toPlainText() == report
    assert window.preview.toPlainText() == preview
    window._open_path(window.project_path)
    assert window._step_states[7].state == 'unchecked'


def test_deletion_after_check_is_revalidated_by_core_export(window, app, tmp_path):
    from core.project_io import export_bundle
    from core.generator import GenerationError
    path = tmp_path / 'BASIS_MOLOPT'
    path.write_bytes((BUNDLED_DATA / 'BASIS_MOLOPT').read_bytes())
    project = window.project.model_copy(deep=True)
    project.dft.basis_files = [str(path)]
    for kind in project.kinds.values():
        kind.basis_ref = None
    window.load_into_ui(project)
    check(app, window)
    assert window._step_states[7].state == 'ready'
    path.unlink()
    with pytest.raises((GenerationError, FileNotFoundError)):
        export_bundle(window.project, tmp_path / 'must_not_export')
    assert not (tmp_path / 'must_not_export').exists()
