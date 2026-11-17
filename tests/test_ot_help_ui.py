"""Bilingual field help and optional gap drafts preserve existing controls."""
import numpy as np
import pytest
from PySide6.QtCore import QEvent
from PySide6.QtGui import QHelpEvent, QTextDocument
from PySide6.QtWidgets import QToolTip
from core.generator import generate_input
from core.project_io import save_project, load_project
from i18n.language_manager import language_manager
from i18n.messages import i18n_render
from tests.test_poisson_reference_ui import window


def plain(icon):
    document = QTextDocument()
    document.setHtml(icon.toolTip())
    return document.toPlainText()


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
@pytest.mark.parametrize('width', [1050, 1480])
def test_three_help_icons_align_with_labels_and_existing_inputs(window, app, language, width):
    w = window
    language_manager().set_language(language)
    w.resize(width, 900)
    for page, panel, field, label, icon in [
        (2, w.dft_panel, w.dft_panel.fields['dft.eps_default'][0], w.dft_panel.eps_default_label, w.dft_panel.eps_default_help),
        (3, w.scf_panel, w.scf_panel.ot.fields['dft.scf.minimizer'][0], w.scf_panel.minimizer_label, w.scf_panel.minimizer_help),
        (3, w.scf_panel, w.scf_panel.energy_gap, w.scf_panel.energy_gap_label, w.scf_panel.energy_gap_help)]:
        w.nav.setCurrentRow(page)
        w.stack.widget(page).ensureWidgetVisible(icon)
        for _ in range(6): app.processEvents()
        assert icon.width() == icon.height() == 16
        assert icon.x() - label.geometry().right() - 1 == 6
        assert abs(icon.geometry().center().y() - label.geometry().center().y()) <= 1
        assert not label.wordWrap() and label.buddy() is field
        assert field.y() - label.parentWidget().layout().itemAt(0).geometry().bottom() - 1 >= 0
        if field is w.scf_panel.ot.fields['dft.scf.minimizer'][0]:
            assert field.width() == w.scf_panel.ot.fields['dft.scf.preconditioner'][0].width()
        else:
            assert 144 <= field.width() <= 240
        assert not field.toolTip() and not field.statusTip()
        assert w.stack.widget(page).horizontalScrollBar().maximum() == 0
    grid = w.dft_panel.cards[2].content.itemAt(0).widget()
    if grid.columns == 2:
        assert w.dft_panel.fields['dft.eps_default'][0].y() == w.dft_panel.fields['dft.ngrids'][0].y()
    assert w.dft_panel.fields['dft.eps_default'][0].text() == '1e-10'
    assert w.scf_panel.ot.fields['dft.scf.minimizer'][0].currentData() == 'CG'
    assert not w.scf_panel.energy_gap.text() and w.scf_panel.energy_gap.placeholderText() == 'Auto (-1.0)'
    assert w.scf_panel.energy_gap.unit_label.text() == 'Ha'
    assert not w.dirty


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
def test_native_tooltips_have_complete_translated_help_without_changing_state(window, app, language):
    w = window
    camera = w.structure_panel.view
    camera.zoom = 1.5
    camera.pan_offset = np.array([.1, .2, .3])
    rotation = camera.rotation.copy()
    snapshot = w.project.model_dump_json(), w._revision, w.dirty, w.preview.toPlainText()
    language_manager().set_language(language)
    for page, icon, markers in [
        (3, w.scf_panel.energy_gap_help, ['FULL_ALL', '0.001–0.002', '0.2–0.5', 'Auto', 'Ha',
            'physical band gap' if language == 'en_US' else '真实带隙']),
        (3, w.scf_panel.minimizer_help, ['DIIS', 'CG', 'Usually more robust' if language == 'en_US' else '通常更稳健']),
        (2, w.dft_panel.eps_default_help, ['EPS_DEFAULT ≤ (EPS_SCF)² × 100', '1E-10', '1E-12', '1E-14',
            'not a mandatory CP2K rule' if language == 'en_US' else '不是 CP2K 的强制要求'])]:
        w.nav.setCurrentRow(page)
        w.stack.widget(page).ensureWidgetVisible(icon)
        for _ in range(5): app.processEvents()
        text = plain(icon)
        assert all(marker in text for marker in markers)
        p = icon.rect().center()
        try:
            app.sendEvent(icon, QHelpEvent(QEvent.Type.ToolTip, p, icon.mapToGlobal(p)))
            assert QToolTip.isVisible() and QToolTip.text() == icon.toolTip()
            tips = [widget for widget in app.topLevelWidgets() if widget.inherits('QTipLabel') and widget.isVisible()]
            assert tips and 320 <= tips[0].width() <= 420
            assert tips[0].height() <= app.primaryScreen().availableGeometry().height()
        finally:
            QToolTip.hideText()
    assert (w.project.model_dump_json(), w._revision, w.dirty, w.preview.toPlainText()) == snapshot
    assert camera.zoom == 1.5 and np.array_equal(camera.pan_offset, [.1, .2, .3])
    assert np.array_equal(camera.rotation, rotation)


@pytest.mark.parametrize('text,expected', [('', None), ('Auto', None), ('-1.0', -1.0), ('8e-2', .08), ('0.08123456789012345', .08123456789012345)])
def test_edit_auto_and_manual_values_update_preview_and_survive_solver_switch(window, app, tmp_path, text, expected):
    w = window
    panel = w.scf_panel
    panel.energy_gap.setText(text)
    w.refresh()
    assert w.project.dft.scf.energy_gap == expected and w.project.dft.scf.minimizer == 'CG'
    assert ('ENERGY_GAP' in w.preview.toPlainText()) is (expected is not None)
    assert w.preview.toPlainText() == generate_input(w.project)
    # Also exercise switching before the next debounced refresh.
    panel.energy_gap.setText('0.1234567890123456')
    panel.method.setCurrentText('DIAGONALIZATION')
    w.refresh()
    assert w.project.dft.scf.energy_gap == .1234567890123456
    assert 'ENERGY_GAP' not in w.preview.toPlainText() and '&OT' not in w.preview.toPlainText()
    path = tmp_path / 'settings.json'
    save_project(w.project, path)
    w.load_into_ui(load_project(path))
    panel.method.setCurrentText('OT')
    w.refresh()
    assert panel.energy_gap.text() == '0.1234567890123456'
    assert 'ENERGY_GAP 0.1234567890123456' in w.preview.toPlainText()
    assert w.project.dft.eps_default == 1e-10


@pytest.mark.parametrize('text', ['bad', 'NaN', 'inf', '-inf', '1e999'])
def test_invalid_gap_is_actionable_and_inactive_draft_does_not_block_diag(window, app, text):
    w = window
    panel = w.scf_panel
    panel.energy_gap.setText(text)
    w.refresh()
    assert not w._validation.ok and panel.energy_gap.property('invalid')
    assert any('ENERGY_GAP' in str(error) for error in w._draft_errors)
    assert w.project.dft.scf.energy_gap is None
    language_manager().set_language('en_US')
    w.refresh()
    assert any('finite real number' in i18n_render(error) for error in w._draft_errors)
    assert panel.energy_gap.text() == text
    panel.method.setCurrentText('DIAGONALIZATION')
    w.refresh()
    assert w._validation.ok and 'ENERGY_GAP' not in w.preview.toPlainText()
    panel.method.setCurrentText('OT')
    w.refresh()
    assert not w._validation.ok and panel.energy_gap.text() == text
