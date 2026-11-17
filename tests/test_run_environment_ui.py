import json
import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QComboBox, QSpinBox, QInputDialog, QFileDialog, QLabel, QPlainTextEdit, QPushButton, QMessageBox
from core.models import Project
from core.run_config import RunEnvironment
from core.run_script_generator import run_command
from ui.main_window import MainWindow
from ui.widgets.section_card import SectionCard
from tests.test_layout_workflow import wait_for_worker, close_window


def test_navigation_live_resources_and_save_restore_without_command_preview(app, water, tmp_path):
    window = MainWindow(preset_directory=tmp_path / 'presets')
    window.load_into_ui(water)
    assert window.nav.item(6).text() == '07  运行环境'
    assert window.nav.item(7).text() == '08  导出与预设'
    assert window.stack.widget(6).widget() is window.run_panel
    assert window.stack.widget(7).widget() is window.export_panel
    panel = window.run_panel
    assert len(panel.findChildren(QSpinBox)) == 2 and len(panel.findChildren(QComboBox)) == 1
    assert [card.title_label.text() for card in panel.findChildren(SectionCard)] == [
        '目标操作系统', 'MPI / OpenMP 运行参数', '逻辑执行槽位']
    assert not panel.findChildren(QPlainTextEdit) and not panel.findChildren(QPushButton)
    assert [label.text() for label in panel.findChildren(QLabel)].count('目标操作系统') == 1
    assert panel.mpi_processes.minimum() == 1 and panel.omp_threads.minimum() == 1
    assert panel.cpu_slots.text() == '16' and panel.mode.text() == '纯 MPI'
    export = window.export_panel
    cards = {card.title_label.text(): card for card in export.findChildren(SectionCard)}
    status_card, export_card = cards['当前配置状态'], cards['导出 CP2K Input']
    assert status_card.content.itemAt(0).widget() is export.summary
    assert status_card.content.itemAt(1).widget() is export.run_summary
    assert status_card.content.itemAt(2).widget() is export.status
    assert export.run_note.parentWidget() is export_card
    assert export.run_summary.text().count('\n') == 2 and 'run.sh' not in export.run_summary.text()
    note = export.run_note.text()
    before = window.preview.toPlainText()
    window.nav.setCurrentRow(6)
    panel.mpi_processes.selectAll()
    QTest.keyClicks(panel.mpi_processes, '8')
    panel.omp_threads.setValue(4)
    panel.operating_system.setCurrentIndex(panel.operating_system.findData('wsl2'))
    assert panel.cpu_slots.text() == '32' and '混合' in panel.mode.text()
    command = run_command(window.project.run_environment)
    assert 'mpirun -np 8 cp2k.psmp -i input.inp -o output.out' in command
    assert 'OMP_NUM_THREADS=4' in command
    assert 'PowerShell' in panel.platform_note.text()
    assert window.project.run_environment == RunEnvironment(operating_system='wsl2', mpi_processes=8, omp_threads=4)
    assert '32' in window.export_panel.run_summary.text() and 'run.sh' in window.export_panel.run_note.text()
    assert export.run_note.text() == note
    assert 'MPI 进程数：8' in export.run_summary.text() and 'OpenMP 线程数：4' in export.run_summary.text()
    assert window.preview.toPlainText() == before and window.dirty
    path = tmp_path / 'roundtrip.json'
    window.project_path = path
    assert window.save()
    expected = window.project.model_dump()
    window.load_into_ui(Project())
    window._open_path(path)
    assert window.project.model_dump() == expected
    assert panel.mpi_processes.value() == 8 and panel.omp_threads.value() == 4
    assert panel.cpu_slots.text() == '32' and 'Windows / WSL2' in window.export_panel.run_summary.text()
    assert panel.operating_system.currentData() == 'wsl2'
    assert window.preview.toPlainText() == before
    close_window(window)


def test_legacy_warning_nonblocking_and_invalid_project_keeps_current(app, water, tmp_path, monkeypatch):
    window = MainWindow(preset_directory=tmp_path / 'presets')
    path = tmp_path / 'legacy.json'
    data = water.model_dump()
    data['run_environment'] = {'total_cpu_cores': 15, 'omp_threads': 4}
    path.write_text(json.dumps(data))
    window._open_path(path)
    assert window.project.structure == water.structure
    assert window.run_panel.mpi_processes.value() == 16
    assert '无法可靠换算' in window.report.toPlainText()
    window.refresh()
    assert '无法可靠换算' in window.report.toPlainText()
    before = window.project.model_dump()
    errors = []
    monkeypatch.setattr(window, '_error', lambda title, error: errors.append(str(error)))
    data['run_environment'] = {'mpi_processes': -1}
    path.write_text(json.dumps(data))
    window._open_path(path)
    assert errors and window.project.model_dump() == before
    close_window(window)


def test_export_page_bundle_uses_current_resources_for_zip(app, water, tmp_path, monkeypatch):
    import zipfile
    window = MainWindow(preset_directory=tmp_path / 'presets')
    window.load_into_ui(water)
    window.run_panel.mpi_processes.setValue(8)
    window.run_panel.omp_threads.setValue(2)
    window.nav.setCurrentRow(7)
    monkeypatch.setattr(QInputDialog, 'getItem', lambda *args, **kwargs: ('ZIP 压缩包', True))
    monkeypatch.setattr(QInputDialog, 'getText', lambda *args, **kwargs: ('job with spaces', True))
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', lambda *args, **kwargs: str(tmp_path))
    successes = []
    monkeypatch.setattr(window, 'show_bundle_export_success', lambda path: successes.append(path))
    window.export_panel.bundle_button.click()
    wait_for_worker(app, window)
    path = tmp_path / 'job with spaces.zip'
    assert successes == [path] and window.last_export_directory == tmp_path
    with zipfile.ZipFile(path) as archive:
        assert 'mpirun -np 8 cp2k.psmp' in archive.read('run.sh').decode()
        assert 'OMP_NUM_THREADS=2' in archive.read('EXPORT_NOTES.txt').decode()
    close_window(window)


@pytest.mark.parametrize('clicked', ['打开所在目录', '确定'])
def test_bundle_success_dialog_is_compact_and_path_is_selectable(app, tmp_path, monkeypatch, clicked):
    from ui import main_window
    window = MainWindow(preset_directory=tmp_path / 'presets')
    path = tmp_path / ('较长目录 with spaces/' * 6) / 'cp2k_project05.zip'
    opened = []
    snapshot = {}
    monkeypatch.setattr(main_window.QDesktopServices, 'openUrl',
                        lambda url: opened.append(url.toLocalFile()) or True)

    def inspect_and_close():
        box = app.activeModalWidget()
        try:
            snapshot.update(text=box.text(), details=box.detailedText(), info=box.informativeText(),
                            buttons=[button.text() for button in box.buttons()],
                            rows=[button.geometry().center().y() for button in box.buttons()],
                            flags=box.textInteractionFlags(), height=box.height())
            label = box.findChild(QLabel, 'qt_msgbox_label')
            label.setSelection(len('已导出：\n'), len(str(path)))
            snapshot['selected_path'] = label.selectedText()
            next(button for button in box.buttons() if button.text() == clicked).click()
        finally:
            if box.isVisible():
                box.reject()

    QTimer.singleShot(0, inspect_and_close)
    try:
        window.show_bundle_export_success(path)
        assert snapshot['text'] == f'已导出：\n{path}'
        assert not snapshot['details'] and not snapshot['info']
        assert set(snapshot['buttons']) == {'打开所在目录', '确定'}
        assert len(snapshot['buttons']) == 2 and len(set(snapshot['rows'])) == 1
        assert snapshot['flags'] & Qt.TextInteractionFlag.TextSelectableByMouse
        assert snapshot['flags'] & Qt.TextInteractionFlag.TextSelectableByKeyboard
        assert snapshot['selected_path'] == str(path)
        assert snapshot['height'] < 300
        assert opened == ([str(path.parent.resolve())] if clicked == '打开所在目录' else [])
    finally:
        close_window(window)


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_linux_runtime_notes_are_compact_and_stay_removed_after_language_switch(app, water, tmp_path, language):
    from i18n.language_manager import language_manager
    manager = language_manager()
    manager.set_language(language)
    window = MainWindow(preset_directory=tmp_path/'presets')
    window.load_into_ui(water)
    window.nav.setCurrentRow(6)
    window.show()
    panel = window.run_panel
    layout = panel.layout()
    hint = layout.itemAt(5).widget()
    try:
        # Switching back from other systems must remove their text binding too.
        for system in ['macos', 'wsl2', 'linux']:
            panel.operating_system.setCurrentIndex(panel.operating_system.findData(system))
            if system != 'linux':
                assert not panel.platform_note.isHidden()
                assert ('macOS' if system == 'macos' else 'PowerShell') in panel.platform_note.text()
        panel.mpi_processes.setValue(8)
        panel.omp_threads.setValue(2)
        window.check_current_configuration()
        wait_for_worker(app, window)
        assert window._step_states[7].state == 'ready'
        before, preview = window.project.model_dump_json(), window.preview.toPlainText()
        revision, dirty = window._revision, window.dirty
        result = window._comprehensive_result
        for selected_language in ['en_US', 'zh_CN', 'en_US', 'zh_CN']:
            manager.set_language(selected_language)
            for _ in range(6):
                app.processEvents()
            assert panel.platform_note.isHidden() and panel.platform_note.text() == ''
            expected = ('The target environment must provide mpirun and cp2k.psmp on PATH with compatible MPI implementations.'
                        if selected_language == 'en_US' else
                        '目标环境须能通过 PATH 找到 mpirun 和 cp2k.psmp，且两者使用兼容的 MPI。')
            assert hint.text() == expected
            assert 'input.inp' not in hint.text() and 'output.out' not in hint.text()
            assert 'bash run.sh' not in '\n'.join(label.text() for label in panel.findChildren(QLabel)
                                                 if not label.isHidden())
            last_card = layout.itemAt(3).widget()
            assert hint.y() - last_card.geometry().bottom() - 1 == layout.spacing()
            assert panel.mpi_processes.value() == 8 and panel.omp_threads.value() == 2
            assert panel.cpu_slots.text() == '16'
            assert window.project.model_dump_json() == before
            assert window.preview.toPlainText() == preview
            assert (window._revision, window.dirty) == (revision, dirty)
            assert window._comprehensive_result is result and window._step_states[7].state == 'ready'
    finally:
        close_window(window)
        app.processEvents()
        manager.set_language('zh_CN')
