import threading
import numpy as np
import time
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QHelpEvent
from shiboken6 import isValid
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QToolBar, QToolTip, QLabel, QToolButton
from i18n.language_manager import language_manager
from core.local_run import Package, Terminal, LaunchResult, LocalRunError
from ui.main_window import MainWindow
from ui import local_run_dialog as local_ui


def settle(app, predicate=lambda:True, timeout=5):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        app.processEvents()
        if predicate():return
        QTest.qWait(10)
    raise AssertionError('UI operation did not finish')


@pytest.fixture
def window(app,tmp_path):
    value=MainWindow(preset_directory=tmp_path/'presets')
    value.show()
    settle(app)
    yield value
    if isValid(value):
        value.dirty=False
        value.close()
    app.processEvents()


class Backend:
    def __init__(self,directory):
        self.calls=[]
        self.directory=directory
        self.main_thread=threading.get_ident()
        self.error=None

    def inspect(self,directory):
        assert threading.get_ident()!=self.main_thread
        self.calls.append(('inspect',directory))
        if self.error:raise self.error
        return Package(Path(directory),'/bin/bash',Terminal('mock','mock'),True,True)

    def launch(self,package,*,confirmed=False):
        assert threading.get_ident()!=self.main_thread
        self.calls.append(('launch',package.directory,confirmed))
        return LaunchResult(self.directory/'cache','one','two',True)


@pytest.fixture
def controller(window,tmp_path,monkeypatch):
    backend=Backend(tmp_path/'selected')
    value=local_ui.LocalRunController(window,window.local_run_action,backend=backend)
    value.messages=[]
    monkeypatch.setattr(value,'_message',lambda *a:value.messages.append(a))
    window._local_run_controller=value
    return value


def test_toolbar_order_bilingual_and_hover_rules(window,app):
    manager=language_manager()
    toolbar=window.findChild(QToolBar)
    before=window.project.model_dump()
    for language,expected in [('en_US',['Project','Presets','XML Schema','Environment Check','Local Run','Help']),
        ('zh_CN',['项目管理','预设管理','XML 规范','环境检测','本地运行','使用说明'])]:
        manager.set_language(language)
        buttons=[toolbar.widgetForAction(a) for a in toolbar.actions() if isinstance(toolbar.widgetForAction(a), QToolButton)]
        assert [b.text() for b in buttons]==expected
        button=toolbar.widgetForAction(window.local_run_action)
        assert button.height()==toolbar.widgetForAction(window.environment_action).height()
        assert not window.local_run_action.statusTip()
        app.sendEvent(button,QEvent(QEvent.Type.Enter))
        event=QHelpEvent(QEvent.Type.ToolTip,QPoint(5,5),button.mapToGlobal(QPoint(5,5)))
        app.sendEvent(button,event)
        assert event.isAccepted() and not QToolTip.isVisible()
    assert window.project.model_dump()==before and not window.dirty


def test_native_folder_cancel_has_no_backend_side_effects(controller,monkeypatch):
    calls=[]
    def choose(*a,**kw):
        calls.append((a,kw))
        return ''
    monkeypatch.setattr(local_ui.QFileDialog,'getExistingDirectory',choose)
    controller.choose_folder()
    assert len(calls)==1 and len(calls[0][0])==2 and not calls[0][1]
    assert controller.backend.calls==[] and controller.messages==[]
    assert not controller.busy and controller.action.isEnabled()


@pytest.mark.parametrize('accepted',[False,True])
def test_confirm_cancel_or_run_is_independent_from_project(controller,window,app,monkeypatch,accepted,tmp_path,water):
    directory=tmp_path/'selected 中文'
    directory.mkdir()
    # This invalid project file must never be loaded by Local Run.
    (directory/'project.cp2kstudio.json').write_text('{broken')
    monkeypatch.setattr(local_ui.QFileDialog,'getExistingDirectory',lambda *a,**k:str(directory))
    if accepted:
        window.load_into_ui(water)
        window.dirty=True
        window.refresh()
        window.structure_panel.select_atom_ids([water.structure.atom_ids[0]])
    view=window.structure_panel.view
    view.set_labels_visible(True)
    view.zoom=1.6
    view.pan_offset=np.array([.1,.2,.3])
    rotation=view.rotation.copy()
    selection=window.structure_panel.selected_atom_ids().copy()
    confirmations=[]
    class Confirmation:
        def __init__(self,package,parent):confirmations.append(package)
        def exec(self):return local_ui.QDialog.DialogCode.Accepted if accepted else local_ui.QDialog.DialogCode.Rejected
    monkeypatch.setattr(local_ui,'LocalRunConfirmation',Confirmation)
    before=(window.project.model_dump(),window.dirty,window._revision,
            window.preview.toPlainText(),window.nav.currentRow(),window.windowTitle(),
            window._configuration_check_revision,window.structure_panel.view.structure)
    for name in ['refresh','check_configuration','open_project','collect_project']:
        if hasattr(window,name):
            monkeypatch.setattr(window,name,lambda:pytest.fail('Local Run touched project logic'))
    button=window.findChild(QToolBar).widgetForAction(window.local_run_action)
    QTest.mouseClick(button,Qt.MouseButton.LeftButton)
    settle(app,lambda:not controller.busy)
    assert len(confirmations)==1
    assert controller.backend.calls[0]==('inspect',str(directory))
    assert len(controller.backend.calls)==(2 if accepted else 1)
    if accepted:
        assert controller.backend.calls[1]==('launch',directory,True)
        assert controller.messages[0][1].code=='local.started'
    assert before==(window.project.model_dump(),window.dirty,window._revision,
            window.preview.toPlainText(),window.nav.currentRow(),window.windowTitle(),
            window._configuration_check_revision,window.structure_panel.view.structure)
    assert (directory/'project.cp2kstudio.json').read_text()=='{broken'
    assert view.show_labels and view.zoom==1.6
    assert np.array_equal(view.rotation,rotation) and np.array_equal(view.pan_offset,[.1,.2,.3])
    assert window.structure_panel.selected_atom_ids()==selection


def test_preflight_failure_never_confirms_or_launches(controller,app,monkeypatch):
    controller.backend.error=LocalRunError('missing input.inp')
    monkeypatch.setattr(local_ui.QFileDialog,'getExistingDirectory',lambda *a,**k:'selected')
    monkeypatch.setattr(local_ui,'LocalRunConfirmation',lambda *a:pytest.fail('invalid package confirmed'))
    controller.choose_folder()
    settle(app,lambda:not controller.busy)
    assert len(controller.backend.calls)==1
    assert 'input.inp' in controller.messages[0][1]
    assert controller.messages[0][2] is True


@pytest.mark.parametrize('language',['en_US','zh_CN'])
def test_confirmation_plain_path_translation_run_cancel_and_trust(app,tmp_path,language):
    manager=language_manager()
    manager.set_language(language)
    package=Package(tmp_path/'<b>中文 (test)</b>','bash',Terminal('mock','mock'),True,True)
    dialog=local_ui.LocalRunConfirmation(package)
    dialog.show()
    settle(app)
    assert dialog.run_button.text()==('Run' if language=='en_US' else '运行')
    assert dialog.cancel_button.isDefault() and not dialog.run_button.autoDefault()
    labels=dialog.findChildren(QLabel)
    path=next(label for label in labels if str(package.directory)==label.text())
    assert path.textFormat()==Qt.TextFormat.PlainText
    texts='\n'.join(label.text() for label in labels)
    assert 'bash run.sh' in texts and 'tail -n 30 -F' in texts
    assert ('trust' if language=='en_US' else '信任') in texts
    manager.set_language('zh_CN' if language=='en_US' else 'en_US')
    assert dialog.run_button.text()==('运行' if language=='en_US' else 'Run')
    assert path.text()==str(package.directory)
    dialog.close()
    app.processEvents()


@pytest.mark.parametrize('started,monitor_error,expected',[
    (True,'','local.started'),(False,'','local.unconfirmed'),(True,'monitor failed','local.partial')])
def test_startup_status_does_not_claim_calculation_success(controller,tmp_path,started,monitor_error,expected):
    result=LaunchResult(tmp_path,'one',None if monitor_error else 'two',started,monitor_error)
    controller._launched(result,None)
    assert controller.messages[0][1].code==expected
    assert controller.messages[0][2]==bool(monitor_error or not started)


def test_window_close_does_not_cancel_independent_launcher(controller,window,app):
    started=threading.Event()
    finished=threading.Event()
    def launch():
        started.set()
        time.sleep(.2)
        finished.set()
        return None
    controller._start(launch,controller._launched)
    settle(app,started.is_set)
    # QObject destruction disconnects UI callbacks; it does not terminate the worker.
    window.close()
    app.processEvents()
    settle(app,finished.is_set)
