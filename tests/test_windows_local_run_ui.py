"""Windows configuration remains independent from every Project/UI state."""
from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path
import threading
import time
import numpy as np
import pytest
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel
from core.local_run import LaunchResult, LocalRunError
from core.windows_local_run import WindowsPackage, ExecutableCheck
from core.windows_run_config import WindowsRunSettings
from ui.windows_local_run_dialog import WindowsLocalRunDialog
from ui import local_run_dialog as ui
from ui.main_window import MainWindow
from i18n.language_manager import language_manager
from i18n.messages import i18n_msg


def settle(app, predicate, timeout=5):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError('Native configuration worker did not finish')


class Backend:
    native_windows=True
    def __init__(self,folder):
        self.package=WindowsPackage(folder,WindowsRunSettings('C:/CP2K/cp2k.ssmp.exe','C:/msys64/ucrt64/bin',4),True,
            checked=ExecutableCheck('2026.2','OpenMP',(1,1)))
        self.calls=[];self.error=None;self.delay=0;self.completed=0;self.main_thread=threading.get_ident()
    def inspect(self,directory):
        assert threading.get_ident()!=self.main_thread
        self.calls.append(('inspect',directory))
        return self.package
    def prepare(self,directory,settings):
        assert threading.get_ident()!=self.main_thread
        self.calls.append(('prepare',settings));time.sleep(self.delay)
        self.completed+=1
        if self.error:
            raise self.error
        return replace(self.package,settings=settings)
    def launch(self,package,*,confirmed=False):
        assert threading.get_ident()!=self.main_thread
        self.calls.append(('launch',package.settings,confirmed))
        return LaunchResult(package.directory/'cache','one','two',True)


@pytest.mark.parametrize('language',['en_US','zh_CN'])
def test_configuration_translation_preserves_paths_threads_and_project(app,water,tmp_path,language):
    window=MainWindow(preset_directory=tmp_path/'presets');window.load_into_ui(water)
    backend=Backend(tmp_path)
    dialog=WindowsLocalRunDialog(backend.package,backend,window)
    dialog.show();app.processEvents()
    before=window.project.model_dump_json(),window.dirty,window._revision,window.preview.toPlainText()
    language_manager().set_language(language)
    app.processEvents()
    assert dialog.start_button.text()==('Start Calculation' if language=='en_US' else '开始计算')
    assert dialog.mode.text()==('Windows Native / OpenMP' if language=='en_US' else 'Windows 原生 / OpenMP')
    assert dialog.threads.value()==4 and dialog.dll_directory.text()=='C:/msys64/ucrt64/bin'
    assert dialog.cancel_button.isDefault() and not dialog.start_button.autoDefault()
    assert before==(window.project.model_dump_json(),window.dirty,window._revision,window.preview.toPlainText())
    dialog.reject();window.close();app.processEvents()


@pytest.mark.parametrize('accepted',[False,True])
def test_native_controller_launch_and_cancel_never_collect_or_modify_project(app,water,tmp_path,monkeypatch,accepted):
    window=MainWindow(preset_directory=tmp_path/'presets');window.load_into_ui(water)
    window.show();app.processEvents();window.dirty=True;window.refresh()
    window.structure_panel.select_atom_ids([water.structure.atom_ids[0]])
    selection=window.structure_panel.selected_atom_ids().copy()
    view=window.structure_panel.view
    view.set_labels_visible(True);view.zoom=1.6;view.pan_offset=np.array([.1,.2,.3])
    before=(window.project.model_dump_json(),window.dirty,window._revision,window.preview.toPlainText(),window._configuration_check_revision)
    backend=Backend(tmp_path)
    controller=ui.LocalRunController(window,window.local_run_action,backend=backend)
    messages=[];monkeypatch.setattr(controller,'_message',lambda *a:messages.append(a))
    monkeypatch.setattr(ui.QFileDialog,'getExistingDirectory',lambda *a,**k:str(tmp_path))
    for name in ['collect_project','refresh','check_configuration']:
        if hasattr(window,name):
            monkeypatch.setattr(window,name,lambda:pytest.fail('Native Local Run changed the project'))
    def operate():
        dialog=QApplication.activeModalWidget()
        if not isinstance(dialog,WindowsLocalRunDialog):
            QTimer.singleShot(10,operate);return
        if accepted:
            dialog.threads.setValue(8);dialog.start_button.click()
        else:
            dialog.reject()
    QTimer.singleShot(0,operate)
    controller.choose_folder()
    settle(app,lambda:not controller.busy)
    assert len(backend.calls)==(3 if accepted else 1)
    if accepted:
        assert backend.calls[-1][1].omp_threads==8 and backend.calls[-1][2]
        assert messages[-1][1].code=='winrun.started'
    assert before==(window.project.model_dump_json(),window.dirty,window._revision,window.preview.toPlainText(),window._configuration_check_revision)
    assert view.show_labels and view.zoom==1.6 and np.array_equal(view.pan_offset,[.1,.2,.3])
    assert window.structure_panel.selected_atom_ids()==selection
    window.dirty=False;window.close();app.processEvents()


def test_invalid_executable_keeps_configuration_open_and_cancel_during_probe_is_final(app,tmp_path):
    backend=Backend(tmp_path)
    backend.error=LocalRunError(i18n_msg('Choose an existing native Windows CP2K .exe file.',code='winrun.exe_error'))
    dialog=WindowsLocalRunDialog(backend.package,backend)
    dialog.show();dialog.start_button.click()
    settle(app,lambda:dialog._worker is None)
    assert dialog.isVisible() and dialog.launch_package is None and dialog.start_button.isEnabled()
    assert dialog.status.text()
    backend.error=None;backend.delay=.15
    dialog.start_button.click();dialog.reject()
    # i18n.QDialog uses WA_DeleteOnClose, so Qt correctly disconnects its
    # receiver instead of delivering a callback into a destroyed dialog.
    settle(app,lambda:backend.completed==2)
    assert dialog.launch_package is None


def test_new_output_while_configuring_requires_a_fresh_start_confirmation(app,tmp_path):
    backend=Backend(tmp_path)
    original=replace(backend.package,old_output=False)
    dialog=WindowsLocalRunDialog(original,backend)
    dialog.show();dialog.start_button.click()
    settle(app,lambda:dialog._worker is None)
    assert dialog.isVisible() and dialog.launch_package is None
    dialog.start_button.click()
    settle(app,lambda:dialog._worker is None)
    assert dialog.launch_package is not None


def test_browse_uses_native_exe_and_directory_dialogs(app,tmp_path,monkeypatch):
    backend=Backend(tmp_path);dialog=WindowsLocalRunDialog(backend.package,backend)
    import ui.windows_local_run_dialog as module
    calls=[]
    def choose(*args,**kwargs):
        calls.append((args,kwargs));return ('C:/中文 CP2K/cp2k.ssmp.exe','')
    monkeypatch.setattr(module.QFileDialog,'getOpenFileName',choose)
    monkeypatch.setattr(module.QFileDialog,'getExistingDirectory',lambda *a,**k:'C:/DLL 中文')
    dialog.choose_executable();settle(app,lambda:dialog._worker is None)
    dialog.choose_dll()
    assert calls[0][0][-1].source=='Windows Executable (*.exe)' and not calls[0][1]
    assert dialog.executable.text()=='C:/中文 CP2K/cp2k.ssmp.exe' and dialog.dll_directory.text()=='C:/DLL 中文'
    assert dialog.launch_package is None
    dialog.reject()
