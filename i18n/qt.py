"""Qt widgets with explicit Message bindings; user-entered strings are untouched.

Only Message instances are registered. A language change updates properties and
item captions in place with signals blocked; it never replaces widgets, invokes
business callbacks, changes itemData, or reads display text back into a project.
"""
from PySide6 import QtWidgets as W, QtGui as G
from PySide6.QtWidgets import *  # Re-export unchanged Qt layout/control APIs.
from PySide6.QtCore import Qt, QPersistentModelIndex, QSignalBlocker
from i18n.messages import Message, i18n_render
from i18n.language_manager import language_manager

PROPERTIES = {'setText': 'text', 'setWindowTitle': 'windowTitle', 'setToolTip': 'toolTip',
              'setStatusTip': 'statusTip', 'setPlaceholderText': 'placeholderText',
              'setAccessibleName': 'accessibleName', 'setAccessibleDescription': 'accessibleDescription',
              'setPlainText': 'toPlainText', 'setInformativeText': 'informativeText',
              'setDetailedText': 'detailedText', 'setLabelText': 'labelText', 'setTitle': 'title'}


def _setter(base, name):
    native = getattr(base, name)
    def set_value(self, value, *args):
        language_manager().bind(self, name, lambda target, text: native(target, text), value)
        return native(self, i18n_render(value) if isinstance(value, Message) else value, *args)
    return set_value


def _widget(base, initial=None):
    def init(self, *args, **kwargs):
        values = [a for a in args if isinstance(a, Message)]
        base.__init__(self, *(i18n_render(a) if isinstance(a, Message) else a for a in args), **kwargs)
        if values and initial:
            getattr(self, initial)(values[0])
    methods = {'__init__': init, '__module__': __name__}
    for name in PROPERTIES:
        if hasattr(base, name):
            methods[name] = _setter(base, name)
    return type(base.__name__, (base,), methods)


QLabel = _widget(W.QLabel, 'setText')
QPushButton = _widget(W.QPushButton, 'setText')
QToolButton = _widget(W.QToolButton)
QCheckBox = _widget(W.QCheckBox, 'setText')
QRadioButton = _widget(W.QRadioButton, 'setText')
QLineEdit = _widget(W.QLineEdit, 'setText')
QPlainTextEdit = _widget(W.QPlainTextEdit, 'setPlainText')
QTextEdit = _widget(W.QTextEdit, 'setText')
QAction = _widget(G.QAction, 'setText')
QListWidgetItem = _widget(W.QListWidgetItem, 'setText')
QTableWidgetItem = _widget(W.QTableWidgetItem, 'setText')
class QDialog(_widget(W.QDialog)):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        language_manager().track_window(self)


def set_button_text(button, text):
    """Bind captions of standard buttons that Qt constructs internally."""
    language_manager().bind(button, 'setText', lambda target, value: W.QAbstractButton.setText(target, value), text)
    W.QAbstractButton.setText(button, i18n_render(text))


class QTabWidget(W.QTabWidget):
    def addTab(self, widget, text):
        row = W.QTabWidget.addTab(self, widget, i18n_render(text))
        language_manager().bind(self, ('tab', row), lambda target, value: W.QTabWidget.setTabText(target, row, value), text)
        return row


def _append_plain_text(self, text):
    manager = language_manager()
    previous = manager._bindings.get((id(self), 'setPlainText'))
    source = previous[2] if previous else self.toPlainText()
    combined = source + '\n' + text
    manager.bind(self, 'setPlainText', lambda target, value: W.QPlainTextEdit.setPlainText(target, value), combined)
    return W.QPlainTextEdit.appendPlainText(self, i18n_render(text))


QPlainTextEdit.appendPlainText = _append_plain_text


def _item_set_data(base):
    def set_data(self, role, value):
        language_manager().bind(self, ('role', int(role)), lambda target, text: base.setData(target, role, text), value)
        return base.setData(self, role, i18n_render(value) if isinstance(value, Message) else value)
    return set_data


QListWidgetItem.setData = _item_set_data(W.QListWidgetItem)
QTableWidgetItem.setData = _item_set_data(W.QTableWidgetItem)


class QListWidget(_widget(W.QListWidget)):
    def addItem(self, value):
        return W.QListWidget.addItem(self, QListWidgetItem(value) if isinstance(value, str) else value)

    def addItems(self, values):
        for value in values:
            self.addItem(value)


class QTableWidget(_widget(W.QTableWidget)):
    def setHorizontalHeaderLabels(self, labels):
        for column, label in enumerate(labels):
            self.setHorizontalHeaderItem(column, QTableWidgetItem(label))

    def setVerticalHeaderLabels(self, labels):
        for row, label in enumerate(labels):
            self.setVerticalHeaderItem(row, QTableWidgetItem(label))


class QComboBox(_widget(W.QComboBox)):
    def _bind_item(self, row, value):
        index = QPersistentModelIndex(self.model().index(row, self.modelColumn()))
        def update(combo, text):
            if not index.isValid():
                return
            old_text = combo.currentText()
            edited = combo.isEditable() and old_text != combo.itemText(combo.currentIndex())
            W.QComboBox.setItemText(combo, index.row(), text)
            if edited:
                blocker = QSignalBlocker(combo.lineEdit())
                combo.setEditText(old_text)
                del blocker
        language_manager().bind(self, ('item', index), update, value)

    def addItem(self, *args):
        row = self.count()
        text = next((arg for arg in args if isinstance(arg, (str, Message))), None)
        result = W.QComboBox.addItem(self, *(i18n_render(a) if isinstance(a, Message) else a for a in args))
        if text is not None:
            self._bind_item(row, text)
        return result

    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

    def clear(self):
        manager = language_manager()
        for key in list(manager._bindings):
            if key[0] == id(self) and isinstance(key[1], tuple) and key[1][0] == 'item':
                manager._bindings.pop(key, None)
        return W.QComboBox.clear(self)

    def setItemText(self, row, text):
        self._bind_item(row, text)
        return W.QComboBox.setItemText(self, row, i18n_render(text))

    def setCurrentText(self, text):
        return W.QComboBox.setCurrentText(self, i18n_render(text))

    def findText(self, text, *args):
        return W.QComboBox.findText(self, i18n_render(text), *args)


class QFormLayout(W.QFormLayout):
    def addRow(self, *args):
        if args and isinstance(args[0], Message):
            label = QLabel(args[0])
            if len(args) > 1 and isinstance(args[1], W.QWidget):
                label.setBuddy(args[1])
            args = (label, *args[1:])
        return W.QFormLayout.addRow(self, *args)


class QMenu(_widget(W.QMenu, 'setTitle')):
    def addAction(self, *args):
        if args and isinstance(args[0], Message):
            action = QAction(args[0], self)
            if len(args) > 1:
                action.triggered.connect(args[1])
            W.QMenu.addAction(self, action)
            return action
        return W.QMenu.addAction(self, *args)

    def addMenu(self, *args):
        if args and isinstance(args[0], Message):
            menu = QMenu(args[0], self)
            W.QMenu.addMenu(self, menu)
            return menu
        return W.QMenu.addMenu(self, *args)


class QMenuBar(_widget(W.QMenuBar)):
    def addMenu(self, title):
        if isinstance(title, Message):
            menu = QMenu(title, self)
            W.QMenuBar.addMenu(self, menu)
            return menu
        return W.QMenuBar.addMenu(self, title)


class QToolBar(_widget(W.QToolBar, 'setWindowTitle')):
    def addAction(self, *args):
        if args and isinstance(args[0], Message):
            action = QAction(args[0], self)
            if len(args) > 1:
                action.triggered.connect(args[1])
            W.QToolBar.addAction(self, action)
            return action
        return W.QToolBar.addAction(self, *args)


class QStatusBar(_widget(W.QStatusBar)):
    def showMessage(self, text, timeout=0):
        language_manager().bind(self, 'status', lambda target, value: W.QStatusBar.showMessage(target, value), text)
        return W.QStatusBar.showMessage(self, i18n_render(text), timeout)


class QMainWindow(_widget(W.QMainWindow)):
    def menuBar(self):
        if not hasattr(self, '_translated_menu_bar'):
            self._translated_menu_bar = QMenuBar(self)
            self.setMenuBar(self._translated_menu_bar)
        return self._translated_menu_bar

    def statusBar(self):
        if not hasattr(self, '_translated_status_bar'):
            self._translated_status_bar = QStatusBar(self)
            self.setStatusBar(self._translated_status_bar)
        return self._translated_status_bar


class QDialogButtonBox(W.QDialogButtonBox):
    def addButton(self, *args):
        if args and isinstance(args[0], Message):
            button = QPushButton(args[0], self)
            W.QDialogButtonBox.addButton(self, button, args[1])
            return button
        return W.QDialogButtonBox.addButton(self, *args)


class QMessageBox(_widget(W.QMessageBox)):
    def addButton(self, *args):
        if args and isinstance(args[0], Message):
            button = QPushButton(args[0], self)
            W.QMessageBox.addButton(self, button, args[1])
            return button
        return W.QMessageBox.addButton(self, *args)


def _message_box_call(name):
    def call(parent, title, text, *args, **kwargs):
        with language_manager().dialog(W.QMessageBox, {'setWindowTitle': title, 'setText': text}):
            return getattr(W.QMessageBox, name)(parent, i18n_render(title), i18n_render(text), *args, **kwargs)
    return staticmethod(call)


for _name in ['information', 'warning', 'critical', 'question']:
    setattr(QMessageBox, _name, _message_box_call(_name))


class QFileDialog(W.QFileDialog):
    pass


def _file_call(name):
    def call(parent=None, caption='', *args, **kwargs):
        # Translate application-supplied captions/filters before opening. Let
        # Qt choose NSOpenPanel/NSSavePanel or the platform's native picker;
        # do not inspect, style, or retranslate its system-owned controls.
        return getattr(W.QFileDialog, name)(parent, i18n_render(caption),
            *(i18n_render(a) if isinstance(a, Message) else a for a in args),
            **{key: i18n_render(value) if isinstance(value, Message) else value
               for key, value in kwargs.items()})
    return staticmethod(call)


for _name in ['getOpenFileName', 'getOpenFileNames', 'getSaveFileName', 'getExistingDirectory']:
    setattr(QFileDialog, _name, _file_call(_name))


class QInputDialog(W.QInputDialog):
    @staticmethod
    def getDouble(parent, title, label, *args, **kwargs):
        with language_manager().dialog(W.QInputDialog, {'setWindowTitle': title, 'setLabelText': label}):
            return W.QInputDialog.getDouble(parent, i18n_render(title), i18n_render(label), *args, **kwargs)

    @staticmethod
    def getText(parent, title, label, *args, **kwargs):
        with language_manager().dialog(W.QInputDialog, {'setWindowTitle': title, 'setLabelText': label}):
            return W.QInputDialog.getText(parent, i18n_render(title), i18n_render(label), *args, **kwargs)

    @staticmethod
    def getItem(parent, title, label, items, *args, **kwargs):
        rendered = [i18n_render(item) for item in items]
        with language_manager().dialog(W.QInputDialog, {'setWindowTitle': title, 'setLabelText': label, '_items': items}):
            value, accepted = W.QInputDialog.getItem(parent, i18n_render(title), i18n_render(label), rendered, *args, **kwargs)
        current = [i18n_render(item) for item in items]
        return (items[current.index(value)] if value in current else items[rendered.index(value)] if value in rendered else value), accepted
