"""The supplied bitmap is loaded once at startup without cwd or UI side effects."""
from hashlib import sha256
from pathlib import Path
import os
import subprocess
import sys

import pytest
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import QDialog
from i18n.language_manager import language_manager
from ui import app_icon
from ui.main_window import MainWindow

ROOT = Path(__file__).resolve().parents[1]
SUPPLIED_ICON_SHA256 = 'abf05e661c75f382f998ea5dab3567a4481570f4224ece695dcd00fe33472cc0'


@pytest.fixture
def icon_app(app):
    original = QIcon(app.windowIcon())
    yield app
    app.setWindowIcon(original)


def test_supplied_icon_bytes_dimensions_and_transparency_are_preserved():
    assert app_icon.ICON_PATH == ROOT/'resources'/'icons'/'cp2k_studio.png'
    assert app_icon.ICON_PATH.is_absolute()
    assert sha256(app_icon.ICON_PATH.read_bytes()).hexdigest() == SUPPLIED_ICON_SHA256
    image = QImage(str(app_icon.ICON_PATH))
    assert not image.isNull() and image.size().toTuple() == (1024, 1024)
    assert image.hasAlphaChannel() and image.pixelColor(0, 0).alpha() == 0


def test_icon_loads_from_another_working_directory(icon_app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    icon = app_icon.set_application_icon(icon_app)
    assert not icon.isNull() and not icon_app.windowIcon().isNull()
    assert icon_app.windowIcon().cacheKey() == icon.cacheKey()
    assert icon.availableSizes()[0].toTuple() == (1024, 1024)


@pytest.mark.parametrize('failure', ['missing', 'corrupt', 'directory'])
def test_missing_or_invalid_icon_logs_warning_and_keeps_existing_default(icon_app, tmp_path, monkeypatch, caplog, failure):
    existing = app_icon.set_application_icon(icon_app)
    path = tmp_path/'broken.png'
    if failure == 'corrupt':
        path.write_bytes(b'not an image')
    elif failure == 'directory':
        path.mkdir()
    monkeypatch.setattr(app_icon, 'ICON_PATH', path)
    with caplog.at_level('WARNING', logger='ui.app_icon'):
        result = app_icon.set_application_icon(icon_app)
    assert result.isNull()
    assert icon_app.windowIcon().cacheKey() == existing.cacheKey()
    assert str(path) in caplog.text and 'Application icon' in caplog.text


def test_icon_io_failure_is_nonfatal(icon_app, monkeypatch, caplog):
    class UnreadablePixmap:
        def load(self, filename):
            raise OSError('permission denied')
    monkeypatch.setattr(app_icon, 'QPixmap', UnreadablePixmap)
    with caplog.at_level('WARNING', logger='ui.app_icon'):
        assert app_icon.load_application_icon().isNull()
    assert 'permission denied' in caplog.text


def test_window_dialog_and_language_switch_share_icon_without_changing_project(icon_app, water, tmp_path):
    icon = app_icon.set_application_icon(icon_app)
    window = MainWindow(preset_directory=tmp_path/'presets')
    window.load_into_ui(water)
    dialog = QDialog(window)
    manager = language_manager()
    previous_language = manager.language
    before, preview = window.project.model_dump_json(), window.preview.toPlainText()
    revision, dirty = window._revision, window.dirty
    try:
        for language in ['en_US', 'zh_CN', 'en_US']:
            manager.set_language(language)
            assert not window.windowIcon().isNull()
            assert window.windowIcon().cacheKey() == icon.cacheKey()
            assert dialog.windowIcon().cacheKey() == icon.cacheKey()
            assert icon_app.windowIcon().cacheKey() == icon.cacheKey()
            assert window.project.model_dump_json() == before
            assert window.preview.toPlainText() == preview
            assert (window._revision, window.dirty) == (revision, dirty)
        window.edited()
        window.refresh()
        assert window.windowTitle().endswith('*')
        assert window.windowIcon().cacheKey() == icon.cacheKey()
    finally:
        window.timer.stop()
        window.dirty = False
        dialog.close()
        window.close()
        icon_app.processEvents()
        manager.set_language(previous_language)


@pytest.mark.parametrize('missing', [False, True])
def test_real_entry_point_starts_from_foreign_cwd_with_or_without_icon(tmp_path, missing):
    # Exercise main.main(), including its single QApplication and real event
    # loop, in a fresh process. Only schedule assertions and a clean shutdown.
    script = '''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from ui import app_icon
if sys.argv[2] == 'missing':
    app_icon.ICON_PATH = Path.cwd() / 'missing.png'
from ui.main_window import MainWindow
import main
failures = []
native_exec = QApplication.exec

def inspect():
    app = QApplication.instance()
    try:
        windows = [w for w in app.topLevelWidgets() if isinstance(w, MainWindow)]
        assert len(windows) == 1 and windows[0].isVisible()
        window = windows[0]
        if sys.argv[2] != 'missing':
            assert not app.windowIcon().isNull()
            assert window.windowIcon().cacheKey() == app.windowIcon().cacheKey()
        assert window.language_selector.currentData() == 'en_US'
        assert 'CP2K Studio' in window.windowTitle()
        window.dirty = False
        window.close()
    except BaseException as exc:
        failures.append(repr(exc))
    finally:
        app.quit()

def checked_exec(self):
    QTimer.singleShot(0, inspect)
    return native_exec()
QApplication.exec = checked_exec
result = main.main()
assert result == 0 and not failures, failures
print('entry point icon check passed')
'''
    environment = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    result = subprocess.run([sys.executable, '-c', script, str(ROOT), 'missing' if missing else 'present'],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stderr + result.stdout
    assert 'entry point icon check passed' in result.stdout
    if missing:
        assert 'Application icon is missing' in result.stderr
