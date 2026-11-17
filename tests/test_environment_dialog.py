"""Modeless, asynchronous checks never edit configuration or restart on locale."""
import threading
import time
import numpy as np
import pytest
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QToolBar
from shiboken6 import isValid
from core.environment_check import EnvironmentReport,CheckItem
from i18n.language_manager import language_manager
from i18n.messages import i18n_msg
from ui.environment_dialog import EnvironmentCheckDialog
from tests.test_poisson_reference_ui import window
from tests.test_layout_workflow import wait_for_worker


def settle(app,dialog,timeout=4):
    deadline=time.monotonic()+timeout
    while dialog.report is None or dialog._running:
        assert time.monotonic()<deadline
        app.processEvents();QTest.qWait(10)
    app.processEvents()


class FixtureDetector:
    calls=[]
    delay=.12
    def __init__(self,config,*,cancel):self.config=config;self.cancel=cancel
    def run(self,progress):
        self.calls.append((threading.get_ident(),self.config.model_dump()))
        progress(i18n_msg('Checking environment…',code='env.checking'))
        self.cancel.wait(self.delay)
        return EnvironmentReport(cp2k_found=True,completed=not self.cancel.is_set(),items=[
            CheckItem('cp2k','cp2k.version',i18n_msg('CP2K Version',code='env.cp2k_version'),'pass','2026.1'),
            CheckItem('system','resources',i18n_msg('Configured Resources (read-only)',code='env.resources'),'pass',str(self.config.required_cpu_slots)),
            CheckItem('system','cpu','CPU','unknown','Fixture CPU')])


@pytest.fixture
def factory():
    FixtureDetector.calls=[]
    return FixtureDetector


def test_toolbar_environment_local_run_help_order_and_existing_hover_rules(window,app,monkeypatch,factory):
    import ui.environment_dialog as module
    language_manager().set_language('en_US')
    original=module.EnvironmentCheckDialog
    monkeypatch.setattr(module,'EnvironmentCheckDialog',lambda *a,**kw:original(*a,**kw,detector_factory=factory))
    toolbar=window.findChild(QToolBar)
    actions=toolbar.actions()
    index=actions.index(window.environment_action)
    assert actions[index].text()=='Environment Check' and actions[index+1].text()=='Local Run' and actions[index+2].text()=='Help'
    button=toolbar.widgetForAction(window.environment_action)
    help_button=toolbar.widgetForAction(actions[index+2])
    assert button.height()==help_button.height() and not button.statusTip()
    window.environment_action.trigger();app.processEvents()
    dialog=window._environment_dialog
    assert dialog.isVisible() and not dialog.isModal()
    settle(app,dialog)
    window.environment_action.trigger()
    assert window._environment_dialog is dialog and len(factory.calls)==1
    dialog.close();app.processEvents()
    window.environment_action.trigger();app.processEvents()
    assert window._environment_dialog is not dialog
    settle(app,window._environment_dialog)
    window._environment_dialog.close();app.processEvents()


def test_worker_runs_off_gui_thread_and_keeps_event_loop_and_view_responsive(window,app,factory):
    ticks=[]
    timer=QTimer();timer.setInterval(10);timer.timeout.connect(lambda:ticks.append(1));timer.start()
    dialog=EnvironmentCheckDialog(window,config_provider=window.run_panel.config,detector_factory=factory)
    dialog.show();app.processEvents()
    assert dialog._running and not dialog.recheck.isEnabled() and dialog.close_button.isEnabled()
    view=window.structure_panel.view
    view.update();window.nav.setCurrentRow(2)
    settle(app,dialog);timer.stop()
    assert ticks and factory.calls[0][0]!=threading.get_ident()
    assert window.nav.currentRow()==2 and dialog.copy.isEnabled() and dialog.output.isReadOnly()
    dialog.close();app.processEvents()


@pytest.mark.parametrize('language',['en_US','zh_CN'])
def test_language_copy_recheck_and_snapshots_do_not_change_project_or_camera(window,app,factory,language):
    view=window.structure_panel.view
    view.set_labels_visible(True);view.zoom=1.6;view.pan_offset=np.array([.1,.2,.3]);rotation=view.rotation.copy()
    snapshot=window.project.model_dump_json(),window._revision,window.dirty,window.preview.toPlainText()
    checked=window._comprehensive_result
    dialog=EnvironmentCheckDialog(window,config_provider=window.run_panel.config,detector_factory=factory)
    dialog.resize(520,360);dialog.show();settle(app,dialog)
    result=dialog.report
    language_manager().set_language(language);app.processEvents()
    assert dialog.report is result and len(factory.calls)==1
    assert dialog.windowTitle()==('Environment Check' if language=='en_US' else '环境检测')
    text=dialog.output.toPlainText()
    assert ('CP2K Version' if language=='en_US' else 'CP2K 版本') in text
    dialog.copy.click();assert QApplication.clipboard().text()==result.text()
    assert (window.project.model_dump_json(),window._revision,window.dirty,window.preview.toPlainText())==snapshot
    assert window._comprehensive_result is checked
    assert view.show_labels and view.zoom==1.6 and np.array_equal(view.rotation,rotation) and np.array_equal(view.pan_offset,[.1,.2,.3])
    dialog.recheck.click();app.processEvents();settle(app,dialog)
    assert len(factory.calls)==2 and dialog.report is not result
    assert dialog.output.horizontalScrollBar().maximum()==0
    dialog.close();app.processEvents()


def test_recheck_snapshots_latest_runtime_settings_without_collecting_project(window,app,factory):
    dialog=EnvironmentCheckDialog(window,config_provider=window.run_panel.config,detector_factory=factory)
    dialog.show();settle(app,dialog)
    window.run_panel.mpi_processes.setValue(2);window.run_panel.omp_threads.setValue(3)
    # Keep the normal debounced project update out of this read-only probe test.
    window.timer.stop()
    before=window.project.model_dump_json(),window._revision,window.dirty
    dialog.recheck.click();app.processEvents();settle(app,dialog)
    assert factory.calls[-1][1]['mpi_processes']==2 and factory.calls[-1][1]['omp_threads']==3
    assert (window.project.model_dump_json(),window._revision,window.dirty)==before
    dialog.close();app.processEvents()


def test_closing_cancels_worker_without_waiting_or_closing_main_window(window,app,factory,monkeypatch):
    monkeypatch.setattr(factory,'delay',2)
    dialog=EnvironmentCheckDialog(window,detector_factory=factory)
    dialog.show();app.processEvents()
    token=dialog._cancel
    start=time.monotonic();dialog.close();app.processEvents()
    assert token.is_set() and time.monotonic()-start<.5 and window.isVisible()
    QTest.qWait(100);app.processEvents()


def test_unexpected_worker_failure_is_unknown_not_ready_and_can_be_copied(window,app):
    class Broken(FixtureDetector):
        def run(self,progress):raise RuntimeError('SECRET-DO-NOT-COPY')
    dialog=EnvironmentCheckDialog(window,detector_factory=Broken)
    dialog.show();settle(app,dialog)
    assert dialog.report.summary=='partial' and 'SECRET-DO-NOT-COPY' not in dialog.output.toPlainText()
    assert dialog.copy.isEnabled() and dialog.recheck.isEnabled()
    dialog.close();app.processEvents()


def test_constructor_failure_is_reported_and_escape_cancels_without_crashing(window,app,factory):
    def broken(*a,**k):raise PermissionError('PRIVATE')
    dialog=EnvironmentCheckDialog(window,detector_factory=broken)
    dialog.show();settle(app,dialog)
    assert dialog.report.summary=='partial' and 'PRIVATE' not in dialog.output.toPlainText()
    dialog.reject();app.processEvents()
    assert window.isVisible()
    second=EnvironmentCheckDialog(window,detector_factory=factory)
    second.show();app.processEvents()
    token=second._cancel
    second.reject();app.processEvents()
    assert token.is_set()
    QTest.qWait(60)


def test_environment_issues_do_not_invalidate_successful_project_validation(window,app):
    class LocalIssue(FixtureDetector):
        def run(self,progress):
            report=super().run(progress)
            report.items.append(CheckItem('cp2k','failure','CP2K','fail','Fixture failure'))
            return report
    window.check_current_configuration();wait_for_worker(app,window)
    assert window._step_states[7].state=='ready'
    checked=window._comprehensive_result
    before=window.project.model_dump_json(),window._revision,window.dirty,window.preview.toPlainText()
    dialog=EnvironmentCheckDialog(window,detector_factory=LocalIssue)
    dialog.show();settle(app,dialog)
    assert dialog.report.summary=='issues'
    assert window._comprehensive_result is checked and window._step_states[7].state=='ready'
    assert window.export_action.isEnabled()
    assert (window.project.model_dump_json(),window._revision,window.dirty,window.preview.toPlainText())==before
    dialog.close();app.processEvents()
