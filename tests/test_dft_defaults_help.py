"""Initial electronic state is a real default, never a validation shortcut."""
import json
import pytest
from pydantic import ValidationError
from PySide6.QtWidgets import QLabel
from core.models import Project, DFTConfig
from core.project_io import save_project, load_project, export_bundle
from core.presets import capture_preset, apply_preset
from core.generator import generate_input
from core.validator import validate_project
from i18n.language_manager import language_manager
from ui.forms import FormPanel
from tests.test_xsd_ui import window
from tests.test_layout_workflow import wait_for_worker


def test_old_projects_missing_electronic_fields_get_defaults_without_overwriting_saved_values(water, tmp_path):
    data = water.model_dump()
    data['dft'].pop('charge')
    data['dft'].pop('multiplicity')
    data['dft']['uks'] = True
    path = tmp_path / 'legacy.json'
    path.write_text(json.dumps(data))
    restored = load_project(path)
    assert (restored.dft.charge, restored.dft.multiplicity, restored.dft.uks) == (0, 1, True)
    data['dft'].update(charge=-1, multiplicity=2, uks=True)
    path.write_text(json.dumps(data))
    restored = load_project(path)
    assert (restored.dft.charge, restored.dft.multiplicity, restored.dft.uks) == (-1, 2, True)
    data['dft'].update(charge=None, multiplicity=None)
    path.write_text(json.dumps(data))
    restored = load_project(path)
    assert restored.dft.charge is None and restored.dft.multiplicity is None
    assert any('CHARGE' in str(error) for error in validate_project(restored).errors)


@pytest.mark.parametrize('charge', [-2, 0, 3])
def test_positive_negative_and_zero_charge_are_editable_in_model(charge):
    config = DFTConfig()
    config.charge = charge
    assert config.charge == charge and config.multiplicity == 1 and not config.uks


@pytest.mark.parametrize('value', [0, -1, 1.5])
def test_multiplicity_still_requires_a_positive_integer(value):
    with pytest.raises(ValidationError):
        DFTConfig(multiplicity=value)


def test_defaults_do_not_bypass_electron_parity_or_uks_checks(water):
    water.dft = DFTConfig.model_validate(water.dft.model_dump(exclude={'charge','multiplicity','uks'}))
    assert validate_project(water).ok
    water.dft.charge = 1
    assert any(getattr(error, 'code', '') == 'studio.69cda7083d3901ba'
               for error in validate_project(water).errors)
    water.dft.multiplicity = 2
    assert not water.dft.uks
    assert any('UKS' in str(error) for error in validate_project(water).errors)
    water.dft.uks = True
    assert validate_project(water).ok


def test_project_and_preset_restore_explicit_electronic_state(water, tmp_path):
    water.dft.charge, water.dft.multiplicity, water.dft.uks = -1, 2, True
    path = tmp_path / 'saved.json'
    save_project(water, path)
    restored = load_project(path)
    assert restored.dft == water.dft
    preset = capture_preset(restored, 'charged doublet')
    target = Project(structure=water.structure, kinds=water.kinds)
    applied = apply_preset(target, preset).project
    assert (applied.dft.charge, applied.dft.multiplicity, applied.dft.uks) == (-1, 2, True)
    assert (target.dft.charge, target.dft.multiplicity, target.dft.uks) == (0, 1, False)


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
def test_new_project_has_real_default_fields_and_no_dirty_initialization(window, app, language):
    language_manager().set_language(language)
    window.new_project()
    app.processEvents()
    charge = window.dft_panel.fields['dft.charge'][0]
    multiplicity = window.dft_panel.fields['dft.multiplicity'][0]
    assert charge.text() == '0' and multiplicity.text() == '1'
    assert not charge.placeholderText() and not multiplicity.placeholderText()
    assert window.project.dft.charge == 0 and window.project.dft.multiplicity == 1
    assert not window.project.dft.uks and not window.dirty
    assert window._validation.errors  # Structure, functional and KINDs still needed.
    assert not any('CHARGE' in str(error) or 'MULTIPLICITY' in str(error) for error in window._validation.errors)
    assert not window.export_action.isEnabled()
    charge.setText('-1')
    multiplicity.setText('2')
    window.refresh()
    assert (window.project.dft.charge, window.project.dft.multiplicity) == (-1, 2)
    assert not window.project.dft.uks and window.dirty
    charge.clear()
    multiplicity.clear()
    window.refresh()
    assert window.project.dft.charge is None and window.project.dft.multiplicity is None
    assert any('CHARGE' in str(error) for error in window._validation.errors)
    assert any('MULTIPLICITY' in str(error) for error in window._validation.errors)


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
def test_internal_tooltips_and_removed_notes_stay_absent_while_help_and_state_remain(window, app, language):
    window.nav.setCurrentRow(2)
    view = window.structure_panel.view
    view.set_labels_visible(True)
    view.zoom = 1.6
    rotation = view.rotation.copy()
    window.check_current_configuration()
    wait_for_worker(app, window)
    checked = window._comprehensive_result
    snapshot = window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()
    for selected in [language, 'zh_CN' if language == 'en_US' else 'en_US', language]:
        language_manager().set_language(selected)
        app.processEvents()
        for panel in window.findChildren(FormPanel):
            for widget, _ in panel.fields.values():
                assert not widget.toolTip() and not widget.statusTip(), widget.objectName()
        assert window.structure_panel.components.toolTip()
        assert window.structure_view_card.help_icon.toolTip()
        assert window.dft_panel.cards[1].help_icon.toolTip()
        assert window.vibrational_panel.cards[0].help_icon.toolTip()
        card = window.dft_panel.poisson_card
        assert card.content.count() == 2
        assert card.content.itemAt(1).widget() is window.dft_panel.poisson_reference
        assert window.dft_panel.poisson_reference.rowCount() == 6
        assert not any('1D =' in label.text() or '本表为规范参考' in label.text()
                       for label in card.findChildren(QLabel))
        assert window.nav.currentRow() == 2 and view.show_labels and view.zoom == 1.6
        assert (view.rotation == rotation).all()
        assert window._comprehensive_result is checked
        assert (window.project.model_dump_json(), window._revision, window.dirty, window.preview.toPlainText()) == snapshot


@pytest.mark.parametrize('run_type', ['ENERGY','GEO_OPT','VIBRATIONAL_ANALYSIS'])
def test_export_note_keeps_script_text_and_delivers_real_notes_for_all_tasks(window, app, tmp_path, run_type):
    combo = window.global_panel.fields['global_settings.run_type'][0]
    if run_type == 'VIBRATIONAL_ANALYSIS':
        window.structure_panel.periodic.setCurrentText('NONE')
        solver = window.dft_panel.fields['dft.poisson_solver'][0]
        solver.setCurrentIndex(solver.findData('WAVELET'))
    combo.setCurrentIndex(combo.findData(run_type))
    window.refresh()
    for language in ['en_US','zh_CN']:
        language_manager().set_language(language)
        app.processEvents()
        text = window.export_panel.run_note.text()
        assert '"bash run.sh"' in text and '\n' not in text
        assert 'EXPORT_NOTES.txt' not in text and 'Hessian' not in text
        assert not any('vib.export_ui' == getattr(label.text(), 'code', '')
                       or 'EXPORT_NOTES.txt' in label.text() for label in window.export_panel.findChildren(QLabel))
        assert window.preview.toPlainText() == generate_input(window.project)
    bundle = export_bundle(window.project, tmp_path / run_type).parent
    notes = (bundle / 'EXPORT_NOTES.txt').read_text()
    assert 'bash run.sh' in notes and (bundle / 'run.sh').is_file()
    if run_type == 'VIBRATIONAL_ANALYSIS':
        assert 'VIBRATIONAL ANALYSIS' in notes and 'MOLDEN_VIB' in notes and 'HESSIAN' in notes
        assert '&MOLDEN_VIB ON' in (bundle / 'input.inp').read_text()
