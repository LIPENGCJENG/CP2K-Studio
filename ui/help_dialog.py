"""Compact application introduction, translated with the existing Qt bindings."""
from PySide6.QtCore import Qt
from i18n.messages import i18n_msg
from i18n.qt import QDialog, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton, QVBoxLayout
from ui.theme import COLORS


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        title = i18n_msg('CP2K Studio · Help', code='help.title')
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        heading = QLabel(title)
        heading.setObjectName('heading')
        layout.addWidget(heading)

        card = QFrame()
        card.setObjectName('sectionCard')
        content = QVBoxLayout(card)
        content.setContentsMargins(16, 16, 16, 16)
        content.setSpacing(18)
        self.purpose = self._section(content,
            i18n_msg('Purpose', code='help.purpose'),
            i18n_msg('CP2K Studio is a visual tool for generating CP2K input files. Configure calculation parameters through the graphical interface and quickly generate CP2K input files (.inp), simplifying the input-writing process.', code='help.purpose_text'))
        self.quick_start = self._section(content,
            i18n_msg('Quick Start', code='help.quick_start'),
            i18n_msg('Follow the numbered steps in the interface to enter or select calculation parameters. After checking the parameters, click Export to generate the CP2K input file.', code='help.quick_start_text'))
        self._section(content,
            i18n_msg('Developer', code='help.developer'),
            'Tao Zeng, PhD student\nUniversity of Padua')
        self.email = QLabel(
            f'<a href="mailto:tao.zeng@studenti.unipd.it" style="color:{COLORS["accent"]}">'
            'Email: tao.zeng@studenti.unipd.it</a>')
        self.email.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.email.setOpenExternalLinks(True)
        content.addWidget(self.email)
        layout.addWidget(card)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.ok_button = QPushButton(i18n_msg('OK', code='studio.fac2a67ad87807c4'))
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        buttons.addWidget(self.ok_button)
        layout.addLayout(buttons)

    @staticmethod
    def _section(layout, title, text):
        section = QVBoxLayout()
        section.setSpacing(6)
        heading = QLabel(title)
        heading.setObjectName('cardTitle')
        section.addWidget(heading)
        body = QLabel(text)
        body.setTextFormat(Qt.TextFormat.PlainText)
        body.setWordWrap(True)
        body.setMinimumWidth(460)
        body.setMaximumWidth(500)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        section.addWidget(body)
        layout.addLayout(section)
        return body
