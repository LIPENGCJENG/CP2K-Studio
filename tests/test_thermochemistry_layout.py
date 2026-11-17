"""The compact thermochemistry card keeps bindings, output controls and precision."""
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QStyle, QStyleOptionButton
from core.generator import generate_input
from core.models import Project
from core.presets import capture_preset, apply_preset
from core.project_io import save_project, load_project, export_bundle
from core.run_script_generator import generate_run_script
from i18n.language_manager import language_manager
from tests.test_vibrational_ui import window


def controls(window):
    panel = window.vibrational_panel
    return [panel.fields['vibrational.' + key][0] for key in
            ['thermochemistry', 'tc_temperature', 'tc_pressure', 'molden_vib', 'hessian']]


@pytest.mark.parametrize('language', ['en_US', 'zh_CN'])
@pytest.mark.parametrize('width', [1050, 1480])
def test_three_rows_align_and_fit_both_languages(window, app, language, width):
    language_manager().set_language(language)
    window.resize(width, 900)
    for _ in range(8):
        app.processEvents()
    panel = window.vibrational_panel
    thermo, temperature, pressure, molden, hessian = controls(window)
    grid = panel.thermo_grid.grid
    assert [grid.getItemPosition(i) for i in range(grid.count())] == [
        (0, 0, 1, 2), (1, 0, 1, 1), (1, 1, 1, 1), (2, 0, 1, 1), (2, 1, 1, 1)]
    for checkbox in [thermo, molden, hessian]:
        assert checkbox.parentWidget().layout().count() == 1
        assert checkbox.text()
    positions = [widget.mapTo(panel, QPoint()) for widget in controls(window)]
    assert positions[0].y() < positions[1].y() < positions[3].y()
    assert positions[1].y() == positions[2].y()
    assert temperature.height() == pressure.height()
    assert abs(temperature.width() - pressure.width()) <= 1
    assert positions[1].x() == positions[3].x()
    assert positions[2].x() == positions[4].x()
    centers = []
    for checkbox in [molden, hessian]:
        option = QStyleOptionButton()
        checkbox.initStyleOption(option)
        indicator = checkbox.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, checkbox)
        centers.append(checkbox.mapTo(panel, indicator.center()).y())
        content = checkbox.style().subElementRect(QStyle.SubElement.SE_CheckBoxContents, option, checkbox)
        assert all(checkbox.fontMetrics().horizontalAdvance(line) <= content.width() + 1
                   for line in checkbox.text().splitlines())
    assert abs(centers[0] - centers[1]) <= 1
    assert window.stack.widget(5).horizontalScrollBar().maximum() == 0
    card = panel.cards[2]
    assert card.help_icon and card.help_icon.toolTip()
    assert thermo.text() == ('THERMOCHEMISTRY' if language == 'en_US' else '热化学计算')
    assert temperature.parentWidget().layout().itemAt(0).widget().text() == (
        'TC_TEMPERATURE' if language == 'en_US' else '热化学温度')
    assert pressure.parentWidget().layout().itemAt(0).widget().text() == (
        'TC_PRESSURE' if language == 'en_US' else '热化学压力')
    assert not window.dirty


def test_thermochemistry_only_enables_temperature_and_pressure(window):
    thermo, temperature, pressure, molden, hessian = controls(window)
    assert not thermo.isChecked()
    assert temperature.text() == '273.15' and pressure.text() == '101325.0'
    assert not temperature.isEnabled() and not pressure.isEnabled()
    assert molden.isChecked() and not hessian.isChecked()
    for active in [True, False, True, False]:
        thermo.setChecked(active)
        assert temperature.isEnabled() is active and pressure.isEnabled() is active
        assert molden.isEnabled() and hessian.isEnabled()
        assert molden.isChecked() and not hessian.isChecked()
    assert temperature.text() == '273.15' and pressure.text() == '101325.0'


def test_live_language_resize_keeps_controls_parameters_preview_and_state(window, app):
    thermo, temperature, pressure, molden, hessian = controls(window)
    thermo.setChecked(True)
    temperature.setText('301.25')
    pressure.setText('98765')
    molden.setChecked(False)
    hessian.setChecked(True)
    window.refresh()
    snapshot = window.project.model_dump_json(), window.dirty, window._revision, window.preview.toPlainText()
    for language, width in [('en_US', 1050), ('zh_CN', 1480), ('en_US', 1480), ('zh_CN', 1050)]:
        language_manager().set_language(language)
        window.resize(width, 900)
        for _ in range(8):
            app.processEvents()
        assert controls(window) == [thermo, temperature, pressure, molden, hessian]
        assert (window.project.model_dump_json(), window.dirty, window._revision,
                window.preview.toPlainText()) == snapshot
        assert window.nav.currentRow() == 5
        assert ('Write Molden' if language == 'en_US' else '输出 Molden') in molden.text().replace('\n', ' ')
        assert ('Write Binary' if language == 'en_US' else 'Hessian') in hessian.text().replace('\n', ' ')


def test_edits_preserve_input_project_preset_and_package(window, app, tmp_path):
    thermo, temperature, pressure, molden, hessian = controls(window)
    thermo.setChecked(True)
    temperature.setText('301.25')
    pressure.setText('98765')
    molden.setChecked(False)
    hessian.setChecked(True)
    window.refresh()
    text = window.preview.toPlainText()
    assert text == generate_input(window.project)
    for fragment in ['THERMOCHEMISTRY T', 'TC_TEMPERATURE 301.25', 'TC_PRESSURE 98765',
                     '&MOLDEN_VIB OFF', '&HESSIAN ON']:
        assert fragment in text
    path = tmp_path / 'thermochemistry.json'
    save_project(window.project, path)
    restored = load_project(path)
    assert restored.vibrational == window.project.vibrational
    window.load_into_ui(restored)
    assert controls(window) == [thermo, temperature, pressure, molden, hessian]
    assert thermo.isChecked() and not molden.isChecked() and hessian.isChecked()
    preset = capture_preset(restored, 'thermochemistry')
    assert apply_preset(Project(), preset).project.vibrational == restored.vibrational
    folder = export_bundle(restored, tmp_path / 'job').parent
    exported = (folder / 'input.inp').read_text()
    for fragment in ['THERMOCHEMISTRY T', '&MOLDEN_VIB OFF', '&HESSIAN ON']:
        assert fragment in exported
    assert (folder / 'run.sh').read_text() == generate_run_script(restored.run_environment)
    thermo.setChecked(False)
    window.refresh()
    assert not window.project.vibrational.thermochemistry
    assert window.project.vibrational.tc_temperature == 301.25
    assert window.project.vibrational.tc_pressure == 98765
    assert '&HESSIAN ON' in window.preview.toPlainText()
    assert '&MOLDEN_VIB OFF' in window.preview.toPlainText()
