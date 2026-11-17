"""One QTranslator owner and weak, signal-blocked display bindings."""
from pathlib import Path
from core.resources import resource_path
import weakref
from contextlib import contextmanager
from PySide6.QtCore import QObject, Signal, QLocale, QTranslator, QLibraryInfo, QTimer, QSignalBlocker
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid
from i18n.messages import Message, i18n_render

ROOT = resource_path('i18n')
LANGUAGES = {'en_US': 'English', 'zh_CN': '简体中文'}


class LanguageManager(QObject):
    language_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.language = 'en_US'
        self._translators = {}
        self._installed = []
        self._bindings = {}
        self._callbacks = {}
        self._windows = {}
        self._native_wrappers = {}
        self._app = None
        self._applying = False

    def attach(self, app=None):
        app = app or QApplication.instance()
        if app is not None and self._app is not app:
            self._app = app
            self.set_language(self.language, force=True)
        return self

    def translator(self, language):
        if language not in self._translators:
            translator = QTranslator(self)
            translator.load(str(ROOT / f'cp2kstudio_{language}.qm'))
            self._translators[language] = translator
        return self._translators[language]

    def translate(self, source, code, language=None):
        language = language or self.language
        if QApplication.instance() is None:
            from i18n.messages import _canonical_catalog
            return _canonical_catalog().get((code, source), source) if language == 'zh_CN' else source
        # Calling the requested QTranslator also permits deterministic report
        # rendering outside a GUI callback; missing entries fall back to English.
        return self.translator(language).translate('CP2KStudio', source, code) or source

    def set_language(self, language, *, force=False):
        if language not in LANGUAGES:
            raise ValueError(f'Unsupported interface language: {language}')
        if language == self.language and not force:
            return
        app = QApplication.instance()
        self.language = language
        QLocale.setDefault(QLocale(language))
        if app is not None:
            for translator in self._installed:
                app.removeTranslator(translator)
            self._installed.clear()
            qt = QTranslator(self)
            if qt.load(QLocale(language), 'qtbase', '_', QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
                app.installTranslator(qt)
                self._installed.append(qt)
            translator = self.translator(language)
            app.installTranslator(translator)
            self._installed.append(translator)
        self._applying = True
        try:
            for key, (ref, setter, message, owner_ref) in list(self._bindings.items()):
                obj = ref()
                owner = owner_ref() if owner_ref else obj
                if obj is not None and not isinstance(owner, QObject):
                    owner = obj.tableWidget() if hasattr(obj, 'tableWidget') else obj.listWidget() if hasattr(obj, 'listWidget') else obj
                if obj is None or not isValid(obj) or owner is None or not isValid(owner):
                    self._bindings.pop(key, None)
                    continue
                blocker = QSignalBlocker(owner) if isinstance(owner, QObject) else None
                try:
                    setter(obj, i18n_render(message))
                finally:
                    del blocker
            for key, (ref, method) in list(self._callbacks.items()):
                obj = ref()
                if obj is None or not isValid(obj):
                    self._callbacks.pop(key, None)
                else:
                    method(obj)
        finally:
            self._applying = False
        self.language_changed.emit(language)

    def bind(self, obj, name, setter, value, owner=None):
        key = (id(obj), name)
        if self._applying:
            return
        if isinstance(value, Message):
            self.retain_native_wrapper(obj)
            self._bindings[key] = (weakref.ref(obj), setter, value, weakref.ref(owner) if owner is not None else None)
        else:
            self._bindings.pop(key, None)

    def callback(self, obj, name, method):
        self.retain_native_wrapper(obj)
        self._callbacks[(id(obj), name)] = (weakref.ref(obj), method)

    def retain_native_wrapper(self, obj):
        # Native standard buttons/static dialogs have no Python subclass to
        # retain their wrapper. Keep that wrapper until its C++ parent deletes
        # it, so a later translation can still address the same Qt instance.
        key = id(obj)
        if isinstance(obj, QObject) and type(obj).__module__.startswith('PySide6.') and key not in self._native_wrappers:
            self._native_wrappers[key] = obj
            obj.destroyed.connect(lambda *_: self._native_wrappers.pop(key, None))

    def track_window(self, window):
        # Python GC may run in a validation worker. Keep each top-level window
        # alive until Qt's deferred GUI-thread destruction, including closed
        # windows waiting for their DeferredDelete event.
        key = id(window)
        self._windows[key] = window
        window.destroyed.connect(lambda *_: self._windows.pop(key, None))

    @contextmanager
    def dialog(self, kind, values):
        # Static Qt helpers enter a nested event loop. Bind their newly shown
        # dialog there, without a global event filter touching worker/timer
        # QObjects while Shiboken is destroying their wrappers.
        timer = QTimer(self)
        def shown():
            dialog = QApplication.activeModalWidget()
            if isinstance(dialog, kind):
                self._bind_dialog(dialog, values)
                timer.stop()
        timer.timeout.connect(shown)
        timer.start(1)
        try:
            yield
        finally:
            timer.stop()
            timer.deleteLater()

    def _bind_dialog(self, obj, values):
        for name, value in values.items():
            if name == '_items':
                from PySide6.QtWidgets import QComboBox
                combo = obj.findChild(QComboBox)
                if combo:
                    def update(target, items=tuple(value)):
                        blocker = QSignalBlocker(target)
                        for row, item in enumerate(items):
                            target.setItemText(row, i18n_render(item))
                        del blocker
                    self.callback(combo, 'dialog_items', update)
                continue
            setter = getattr(type(obj), name)
            self.bind(obj, name, lambda target, text, s=setter: s(target, text), value)

_manager = None


def language_manager():
    global _manager
    if _manager is None:
        _manager = LanguageManager()
    return _manager
