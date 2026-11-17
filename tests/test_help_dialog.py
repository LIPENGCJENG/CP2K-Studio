"""Help is compact, bilingual, and independent of project configuration."""
import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel, QPushButton, QToolBar
from shiboken6 import isValid
from core.generator import generate_input
from i18n.language_manager import language_manager
from ui.help_dialog import HelpDialog
from ui.main_window import MainWindow
from ui.theme import apply_theme
from tests.test_layout_workflow import wait_for_worker


@pytest.fixture
def manager(app):
    value = language_manager().attach(app)
    apply_theme()
    yield value
    value.set_language('zh_CN')


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_help_content_link_compact_layout_and_only_confirmation_button(app, manager, language):
    manager.set_language(language)
    dialog = HelpDialog()
    try:
        dialog.show()
        app.processEvents()
        texts = [label.text() for label in dialog.findChildren(QLabel)]
        if language == 'zh_CN':
            assert dialog.windowTitle() == 'CP2K Studio · 使用说明'
            assert {'软件用途', '快速开始', '开发者信息'} <= set(texts)
            assert dialog.purpose.text() == 'CP2K Studio 是一款可视化 CP2K 输入文件生成工具，支持通过图形界面配置计算参数，快速生成 CP2K 输入文件（.inp），简化输入文件的编写过程。'
            assert dialog.quick_start.text() == '按照界面中的数字顺序依次填写或选择计算参数，完成参数检查后，点击导出即可生成 CP2K 输入文件。'
            assert dialog.ok_button.text() == '确定'
        else:
            assert dialog.windowTitle() == 'CP2K Studio · Help'
            assert {'Purpose', 'Quick Start', 'Developer'} <= set(texts)
            assert 'CP2K input files (.inp)' in dialog.purpose.text()
            assert 'numbered steps' in dialog.quick_start.text()
            assert dialog.ok_button.text() == 'OK'
            assert not any('\u4e00' <= char <= '\u9fff' for char in ''.join(texts))
        assert 'Tao Zeng, PhD student\nUniversity of Padua' in texts
        assert 'href="mailto:tao.zeng@studenti.unipd.it"' in dialog.email.text()
        assert dialog.email.openExternalLinks()
        assert dialog.findChildren(QPushButton) == [dialog.ok_button]
        assert dialog.ok_button.geometry().right() == dialog.width() - 21
        assert dialog.width() < 650 and dialog.height() < 550
        assert not any(old in '\n'.join(texts) for old in
                       ['README.md', '01–06', 'XML validation', 'XML 校验', 'Save Project:'])
        for label in dialog.findChildren(QLabel):
            assert label.isVisibleTo(dialog)
            assert label.geometry().bottom() < label.parentWidget().height()
            if label.wordWrap():
                assert label.height() >= label.heightForWidth(label.width())
    finally:
        dialog.close()
        app.processEvents()


@pytest.mark.parametrize('action', ['button', 'enter', 'escape'])
def test_help_closes_with_ok_or_keyboard(app, manager, action):
    dialog = HelpDialog()
    dialog.show()
    app.processEvents()
    finished = []
    dialog.finished.connect(finished.append)
    if action == 'button':
        dialog.ok_button.click()
    else:
        QTest.keyClick(dialog, Qt.Key.Key_Return if action == 'enter' else Qt.Key.Key_Escape)
    app.processEvents()
    assert finished == [0 if action == 'escape' else 1]
    assert not isValid(dialog) or not dialog.isVisible()


def test_open_help_switches_language_in_place(app, manager):
    manager.set_language('en_US')
    dialog = HelpDialog()
    try:
        dialog.show()
        app.processEvents()
        purpose = dialog.purpose
        english = purpose.text()
        manager.set_language('zh_CN')
        app.processEvents()
        assert dialog.windowTitle() == 'CP2K Studio · 使用说明'
        assert '可视化' in purpose.text() and dialog.ok_button.text() == '确定'
        manager.set_language('en_US')
        app.processEvents()
        assert dialog.purpose is purpose and purpose.text() == english
        assert dialog.ok_button.text() == 'OK'
    finally:
        dialog.close()
        app.processEvents()


def test_toolbar_opens_current_language_help_without_changing_project(app, manager, water, tmp_path):
    manager.set_language('en_US')
    window = MainWindow(preset_directory=tmp_path / 'presets')
    try:
        window.load_into_ui(water)
        window.show()
        wait_for_worker(app, window)
        before = window.project.model_dump_json(), generate_input(window.project), window.preview.toPlainText()
        status = window.dirty, window._revision, window._configuration_check_snapshot
        toolbar = window.findChild(QToolBar)
        action = next(action for action in toolbar.actions() if action.text() == 'Help')
        inspected, errors = [], []

        def inspect():
            dialog = app.activeModalWidget()
            try:
                assert isinstance(dialog, HelpDialog)
                expected = 'CP2K Studio · Help' if manager.language == 'en_US' else 'CP2K Studio · 使用说明'
                assert dialog.windowTitle() == expected
                inspected.append(expected)
            except Exception as exc:
                errors.append(exc)
            finally:
                if dialog is not None:
                    dialog.close()

        for language in ['en_US', 'zh_CN']:
            manager.set_language(language)
            QTimer.singleShot(0, inspect)
            action.trigger()
            app.processEvents()
        assert not errors, errors
        assert inspected == ['CP2K Studio · Help', 'CP2K Studio · 使用说明']
        assert (window.project.model_dump_json(), generate_input(window.project), window.preview.toPlainText()) == before
        assert (window.dirty, window._revision, window._configuration_check_snapshot) == status
    finally:
        wait_for_worker(app, window)
        window.dirty = False
        window.close()
        app.processEvents()
