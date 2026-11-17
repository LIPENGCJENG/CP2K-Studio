"""Real-database regressions for persistent Apply and model-derived progress."""
from dataclasses import replace
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QHeaderView
from core.database_manager import scan_databases
from core.generator import generate_input
from core.kind_recommender import recommend
from core.kind_validator import element_configuration_progress, validate_kinds
from core.models import Kind, Structure, DatabaseReference, Project
from core.presets import capture_preset
from core.project_io import save_project, load_project
from ui.main_window import MainWindow
from ui.recommendation_dialog import RecommendationDialog


@pytest.fixture(scope='module')
def catalog():
    return scan_databases()


@pytest.fixture
def cho(water):
    project = water.model_copy(deep=True)
    project.structure = Structure(symbols=['C', 'H', 'O', 'H'],
        positions=[(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)], cell=water.structure.cell, periodic='XYZ')
    project.kinds = {element: Kind(element=element) for element in ['C', 'H', 'O']}
    return project


def configure(project, catalog, label):
    element = project.structure.kind_elements[label]
    option = recommend(catalog, element, project.dft.xc_functional)[0]
    project.kinds[label] = Kind(element=element, basis_set=option.basis.name,
        potential=option.potential.name, basis_ref=DatabaseReference(**option.basis.reference()),
        potential_ref=DatabaseReference(**option.potential.reference()))
    return option


@pytest.fixture
def window(app, cho, tmp_path):
    window = MainWindow(preset_directory=tmp_path / 'presets')
    window.load_into_ui(cho)
    window.nav.setCurrentRow(4)
    window.show()
    app.processEvents()
    yield window
    window.dirty = False
    window.close()


def open_dialog(window, app):
    dialog = RecommendationDialog(window.kind_panel)
    dialog.setModal(True)
    dialog.show()
    app.processEvents()
    return dialog


def select(dialog, element, label=None, offset=0):
    dialog.element_filter.setCurrentIndex(dialog.element_filter.findData(element))
    rows = [row for row in range(dialog.table.rowCount()) if not dialog.table.isRowHidden(row)]
    assert rows
    assert all(dialog.table.item(row, 0).data(Qt.ItemDataRole.UserRole)[1].basis.element == element for row in rows)
    if label:
        rows = [row for row in rows if dialog.table.item(row, 0).data(Qt.ItemDataRole.UserRole)[0] == label]
    dialog.table.selectRow(rows[offset])
    return dialog.selected_option()[1]


def apply(dialog):
    QTest.mouseClick(dialog.apply_button, Qt.MouseButton.LeftButton)


def chosen_bases(dialog):
    return {label: view.basis.text().removeprefix('基组：')
            for label, view in dialog.chosen_views.items()}


def chosen_potentials(dialog):
    return {label: view.potential.text().removeprefix('赝势：')
            for label, view in dialog.chosen_views.items()}


def test_continuous_apply_filter_progress_preview_and_reopen(window, app, monkeypatch):
    dialog = open_dialog(window, app)
    panel = window.kind_panel
    assert dialog.progress.text() == '已配置 0/3 种元素'
    assert chosen_bases(dialog) == {'C': '未选择', 'H': '未选择', 'O': '未选择'}
    assert chosen_potentials(dialog) == {'C': '未选择', 'H': '未选择', 'O': '未选择'}
    assert [dialog.element_filter.itemText(i) for i in range(4)] == ['全部元素', 'C', 'H', 'O']
    # Filtering and Apply reuse parsed catalog and populated recommendation rows.
    monkeypatch.setattr('ui.recommendation_dialog.recommend', lambda *args: pytest.fail('recommendations rebuilt'))
    monkeypatch.setattr('core.database_manager.scan_databases', lambda *args: pytest.fail('database reparsed'))
    pointers = [dialog.table.item(row, 0) for row in range(dialog.table.rowCount())]
    changes = []
    panel.changed.connect(lambda: changes.append(True))
    for completed, element in enumerate(['C', 'H', 'O'], 1):
        previous_chosen = chosen_bases(dialog)
        option = select(dialog, element)
        assert chosen_bases(dialog) == previous_chosen
        selected = dialog.selected_option()
        dialog.table.horizontalScrollBar().setValue(dialog.table.horizontalScrollBar().maximum())
        dialog.table.verticalScrollBar().setValue(dialog.table.verticalScrollBar().maximum() // 2)
        position = (dialog.table.horizontalScrollBar().value(), dialog.table.verticalScrollBar().value())
        apply(dialog)
        assert dialog.isVisible() and dialog.selected_option() == selected
        assert dialog.element_filter.currentData() == element
        assert position == (dialog.table.horizontalScrollBar().value(), dialog.table.verticalScrollBar().value())
        assert dialog.progress.text() == f'已配置 {completed}/3 种元素'
        assert dialog.status.text() == f'已应用到 KIND {element}'
        assert window.project.kinds[element].basis_set == option.basis.name
        assert window.project.kinds[element].potential == option.potential.name
        assert chosen_bases(dialog)[element] == option.basis.name
        assert chosen_potentials(dialog)[element] == option.potential.name
        assert len(chosen_bases(dialog)) == 3  # element filtering leaves this full-project list intact
        row = next(row for row in range(panel.table.rowCount()) if panel.table.item(row, 0).text() == element)
        assert panel.table.cellWidget(row, 1).currentData().key == option.basis.key
        assert panel.table.cellWidget(row, 2).currentData().key == option.potential.key
        assert len(changes) == completed  # one complete model update per Apply
        if completed < 3:
            assert not any(f'KIND {element}：必须明确指定' in error for error in window._validation.errors)
    assert [dialog.table.item(row, 0) for row in range(dialog.table.rowCount())] == pointers
    assert window._step_states[4].state in {'ready', 'warning'}
    assert window.preview.toPlainText() == generate_input(window.project, catalog=panel.catalog)
    select(dialog, 'C', offset=1)
    apply(dialog)
    assert dialog.progress.text() == '已配置 3/3 种元素'
    panel.choose('O', 'potential', None)
    assert dialog.progress.text() == '已配置 2/3 种元素'
    count = len(changes)
    before = window.project.model_dump()
    QTest.mouseClick(dialog.close_button, Qt.MouseButton.LeftButton)
    assert not dialog.isVisible() and len(changes) == count
    assert window.project.model_dump() == before
    # A new chooser restores its count from persisted selections, not click history.
    monkeypatch.undo()
    reopened = open_dialog(window, app)
    assert reopened.progress.text() == '已配置 2/3 种元素'
    assert chosen_bases(reopened) == {label: kind.basis_set for label, kind in window.project.kinds.items()}
    assert chosen_potentials(reopened)['O'] == '未选择'
    QTest.keyClick(reopened, Qt.Key.Key_Escape)
    assert not reopened.isVisible() and window.project.model_dump() == before


def test_multiple_kinds_filter_targets_and_all_kinds_count(window, app):
    project = window.project.model_copy(deep=True)
    project.structure = Structure(symbols=['O', 'O', 'H', 'H'],
        positions=[(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)],
        cell=project.structure.cell, periodic='XYZ', kind_labels=['O1', 'O2', 'H', 'H'])
    project.kinds = {label: Kind(element=element) for label, element in project.structure.kind_elements.items()}
    window.load_into_ui(project)
    dialog = open_dialog(window, app)
    assert dialog.progress.text() == '已配置 0/2 种元素'
    select(dialog, 'O', label='O1')
    assert dialog.table.item(dialog.table.currentRow(), 0).text() == 'O1 / O'
    apply(dialog)
    assert window.project.kinds['O1'].basis_set and not window.project.kinds['O2'].basis_set
    assert chosen_bases(dialog)['O1'] == window.project.kinds['O1'].basis_set
    assert chosen_bases(dialog)['O2'] == '未选择'
    assert chosen_potentials(dialog)['O1'] == window.project.kinds['O1'].potential
    assert chosen_potentials(dialog)['O2'] == '未选择'
    assert dialog.progress.text() == '已配置 0/2 种元素'
    select(dialog, 'O', label='O2')
    apply(dialog)
    assert dialog.progress.text() == '已配置 1/2 种元素'
    dialog.element_filter.setCurrentIndex(dialog.element_filter.findData('H'))
    assert dialog.selected_option() is None
    before = window.project.model_dump()
    apply(dialog)
    assert dialog.status.text() == '请先选择基组与赝势组合'
    assert window.project.model_dump() == before
    assert chosen_bases(dialog) == {label: kind.basis_set or '未选择'
                                    for label, kind in window.project.kinds.items()}
    select(dialog, 'H')
    apply(dialog)
    assert dialog.progress.text() == '已配置 2/2 种元素'
    assert window.project.structure.kind_labels == ['O1', 'O2', 'H', 'H']
    assert '&KIND O1' in window.preview.toPlainText() and '&KIND O2' in window.preview.toPlainText()
    dialog.reject()


def test_failures_keep_selection_filters_and_model(window, app, monkeypatch):
    dialog = open_dialog(window, app)
    before = window.project.model_dump()
    apply(dialog)
    assert dialog.status.text() == '请先选择基组与赝势组合'
    option = select(dialog, 'C')
    selected = dialog.selected_option()
    with monkeypatch.context() as patch:
        def fail(*args):
            raise ValueError('测试应用错误')
        patch.setattr(window.kind_panel, 'apply_recommendation', fail)
        apply(dialog)
        assert '测试应用错误' in dialog.status.text()
    assert dialog.isVisible() and dialog.selected_option() == selected
    assert dialog.element_filter.currentData() == 'C'
    assert dialog.progress.text() == '已配置 0/3 种元素'
    assert window.project.model_dump() == before
    assert window.kind_panel._records == before['kinds']
    assert chosen_bases(dialog) == {'C': '未选择', 'H': '未选择', 'O': '未选择'}
    assert chosen_potentials(dialog) == {'C': '未选择', 'H': '未选择', 'O': '未选择'}
    # Stale candidate rows cannot apply after their catalog entry disappears.
    catalog = window.kind_panel.catalog
    monkeypatch.setattr(window.kind_panel, 'catalog', replace(catalog,
        entries=[entry for entry in catalog.entries if entry.key != option.basis.key]))
    apply(dialog)
    assert '应用失败' in dialog.status.text() and dialog.selected_option() == selected
    assert window.project.model_dump() == before
    assert dialog.progress.text() == '已配置 0/3 种元素'
    dialog.reject()


def test_invalid_numeric_draft_does_not_report_success_or_retain_changes(window, app):
    dialog = open_dialog(window, app)
    select(dialog, 'C')
    before = window.project.model_dump()
    window.dft_panel.fields['dft.cutoff'][0].setText('invalid')
    window.refresh()
    selected = dialog.selected_option()
    apply(dialog)
    assert '无效参数草稿' in dialog.status.text()
    assert dialog.isVisible() and dialog.selected_option() == selected
    assert dialog.progress.text() == '已配置 0/3 种元素'
    assert window.project.model_dump() == before
    assert window.kind_panel._records == before['kinds']
    assert chosen_bases(dialog) == {'C': '未选择', 'H': '未选择', 'O': '未选择'}
    dialog.reject()


def test_real_modal_entry_applies_before_close_without_recreating(window, app, monkeypatch):
    observed, errors = [], []

    class ObservedDialog(RecommendationDialog):
        def __init__(self, panel):
            super().__init__(panel)
            observed.append(self)
            QTimer.singleShot(0, self.interact)

        def interact(self):
            try:
                assert app.activeModalWidget() is self
                select(self, 'C')
                apply(self)
                assert self.isVisible() and app.activeModalWidget() is self
                assert self.progress.text() == '已配置 1/3 种元素'
                assert window.project.kinds['C'].basis_set
                self.close_button.click()
            except BaseException as exc:
                errors.append(exc)
                self.reject()

    monkeypatch.setattr('ui.recommendation_dialog.RecommendationDialog', ObservedDialog)
    window.kind_panel.show_recommendations()
    assert not errors and len(observed) == 1
    assert window.project.kinds['C'].basis_set and not window.project.kinds['O'].basis_set


def test_live_manual_load_preset_and_structure_updates(window, app, tmp_path, monkeypatch):
    dialog = open_dialog(window, app)
    panel = window.kind_panel
    option = recommend(panel.catalog, 'C', 'PBE')[0]
    panel.choose('C', 'basis', option.basis)
    assert dialog.progress.text() == '已配置 0/3 种元素'
    panel.choose('C', 'potential', option.potential)
    assert dialog.progress.text() == '已配置 1/3 种元素'
    complete = window.project.model_copy(deep=True)
    for label in complete.structure.kind_elements:
        configure(complete, panel.catalog, label)
    saved = tmp_path / 'configured.json'
    save_project(complete, saved)
    window.load_into_ui(load_project(saved))
    assert dialog.progress.text() == '已配置 3/3 种元素'
    assert chosen_bases(dialog) == {label: kind.basis_set for label, kind in window.project.kinds.items()}
    assert chosen_potentials(dialog) == {label: kind.potential for label, kind in window.project.kinds.items()}
    empty = complete.model_copy(deep=True)
    empty.kinds = {label: Kind(element=element) for label, element in empty.structure.kind_elements.items()}
    preset = window.preset_store.save(capture_preset(empty, '空白参数草稿'))
    monkeypatch.setattr(window, 'confirm_preset_application', lambda *args: True)
    window.apply_preset('user:' + preset.id)
    assert dialog.progress.text() == '已配置 0/3 种元素'
    assert chosen_bases(dialog) == {'C': '未选择', 'H': '未选择', 'O': '未选择'}
    window.structure_panel.set_structure(Structure(symbols=['H'], positions=[(0, 0, 0)], cell=complete.structure.cell))
    window.refresh()
    assert dialog.progress.text() == '已配置 0/1 种元素'
    assert chosen_bases(dialog) == {'H': '未选择'}
    assert [dialog.element_filter.itemText(i) for i in range(dialog.element_filter.count())] == ['全部元素', 'H']
    assert all(dialog.table.item(row, 0).data(Qt.ItemDataRole.UserRole)[0] == 'H' for row in range(dialog.table.rowCount()))
    window.load_into_ui(Project())
    assert dialog.progress.text() == '已配置 0/0 种元素'
    assert dialog.table.rowCount() == 0
    assert chosen_bases(dialog) == {}
    dialog.reject()


def test_chosen_basis_replacement_tooltips_and_adjustable_panel(window, app):
    dialog = open_dialog(window, app)
    assert dialog.size().width() == 1000 and dialog.size().height() == 500
    assert 180 <= dialog.splitter.sizes()[1] <= 360
    first = select(dialog, 'C')
    apply(dialog)
    replacement = next(row for row in range(dialog.table.rowCount())
                       if not dialog.table.isRowHidden(row)
                       and dialog.table.item(row, 0).data(Qt.ItemDataRole.UserRole)[1].basis.name != first.basis.name)
    dialog.table.selectRow(replacement)
    option = dialog.selected_option()[1]
    apply(dialog)
    assert dialog.isVisible() and chosen_bases(dialog)['C'] == option.basis.name
    view = dialog.chosen_views['C']
    assert option.basis.name in view.basis.toolTip()
    assert option.potential.name in view.potential.toolTip()
    assert view.basis.wordWrap() and view.potential.wordWrap()
    assert chosen_potentials(dialog)['C'] == option.potential.name
    position = dialog.table.currentRow()
    dialog.splitter.setSizes([650, 320])
    app.processEvents()
    assert dialog.splitter.sizes()[1] > 230 and dialog.table.currentRow() == position
    assert dialog.progress.text() == '已配置 1/3 种元素'
    dialog.reject()


@pytest.mark.parametrize('width,height', [(800, 480), (1000, 500), (1440, 760)])
def test_recommendation_columns_align_fill_width_and_keep_selection(window, app, width, height):
    dialog = open_dialog(window, app)
    select(dialog, 'H')
    selected = dialog.selected_option()
    dialog.resize(width, height)
    for _ in range(4):
        app.processEvents()
    left, right = dialog.table.geometry(), dialog.chosen_card.geometry()
    assert right.x() - (left.x() + left.width()) == 16
    assert left.y() == right.y() and left.height() == right.height()
    assert dialog.chosen_card.title_label.text() == '当前已选配置'
    header = dialog.table.horizontalHeader()
    assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.ResizeToContents
    assert header.sectionResizeMode(1) == header.sectionResizeMode(2) == QHeaderView.ResizeMode.Interactive
    assert header.sectionResizeMode(3) == QHeaderView.ResizeMode.Stretch
    assert header.length() >= dialog.table.viewport().width()
    if not dialog.table.horizontalScrollBar().maximum():
        assert abs(header.sectionViewportPosition(3) + header.sectionSize(3) - dialog.table.viewport().width()) <= 1
    assert header.sectionSize(1) >= 150 and header.sectionSize(2) >= 150
    assert dialog.selected_option() == selected
    for column, value in [(1, selected[1].basis.name), (2, selected[1].potential.name)]:
        assert dialog.table.item(dialog.table.currentRow(), column).toolTip() == value
    apply(dialog)
    assert dialog.isVisible() and chosen_potentials(dialog)['H'] == selected[1].potential.name
    dialog.reject()


def test_chosen_configuration_tracks_each_field_independently(window, app):
    dialog = open_dialog(window, app)
    panel = window.kind_panel
    option = recommend(panel.catalog, 'C', 'PBE')[0]
    panel.choose('C', 'basis', option.basis)
    assert chosen_bases(dialog)['C'] == option.basis.name
    assert chosen_potentials(dialog)['C'] == '未选择'
    assert dialog.progress.text() == '已配置 0/3 种元素'
    panel.choose('C', 'potential', option.potential)
    assert chosen_potentials(dialog)['C'] == option.potential.name
    assert dialog.progress.text() == '已配置 1/3 种元素'
    original_view = dialog.chosen_views['C']
    panel.choose('C', 'basis', None)
    assert dialog.chosen_views['C'] is original_view
    assert chosen_bases(dialog)['C'] == '未选择'
    assert chosen_potentials(dialog)['C'] == option.potential.name
    assert dialog.progress.text() == '已配置 0/3 种元素'
    dialog.reject()


def test_long_configuration_names_wrap_and_scroll_independently(window, app):
    project = window.project.model_copy(deep=True)
    labels = [f'C{index}' for index in range(12)]
    project.structure = Structure(symbols=['C'] * len(labels),
        positions=[(index, 0, 0) for index in range(len(labels))],
        cell=project.structure.cell, periodic='XYZ', kind_labels=labels)
    option = max(recommend(window.kind_panel.catalog, 'C', 'PBE'),
                 key=lambda item: len(item.basis.name) + len(item.potential.name))
    project.kinds = {label: Kind(element='C', basis_set=option.basis.name, potential=option.potential.name,
        basis_ref=DatabaseReference(**option.basis.reference()),
        potential_ref=DatabaseReference(**option.potential.reference())) for label in labels}
    window.load_into_ui(project)
    before = window.project.model_dump()
    dialog = open_dialog(window, app)
    dialog.splitter.setSizes([800, 180])
    for _ in range(6):
        app.processEvents()
    assert len(dialog.chosen_views) == len(labels)
    assert dialog.progress.text() == '已配置 1/1 种元素'
    assert dialog.chosen_scroll.verticalScrollBar().maximum() > 0
    assert dialog.chosen_scroll.horizontalScrollBar().maximum() == 0
    view = dialog.chosen_views['C0']
    assert option.basis.name in view.basis.toolTip()
    assert option.potential.name in view.potential.toolTip()
    for field in [view.basis, view.potential]:
        assert field.wordWrap() and field.height() >= field.heightForWidth(field.width())
        assert not field.textInteractionFlags() & Qt.TextInteractionFlag.TextEditable
    left_scroll = dialog.table.verticalScrollBar().value()
    dialog.chosen_scroll.verticalScrollBar().setValue(dialog.chosen_scroll.verticalScrollBar().maximum())
    assert dialog.table.verticalScrollBar().value() == left_scroll
    assert window.project.model_dump() == before
    assert window.preview.toPlainText() == generate_input(window.project, catalog=window.kind_panel.catalog)
    dialog.reject()


@pytest.mark.parametrize('problem', ['basis_missing', 'potential_missing', 'unknown_name', 'version', 'file_hash', 'entry_hash'])
def test_progress_rejects_incomplete_or_invalid_records(cho, catalog, problem):
    for label in cho.structure.kind_elements:
        configure(cho, catalog, label)
    assert element_configuration_progress(cho, catalog) == (3, 3)
    kind = cho.kinds['O']
    if problem == 'basis_missing': kind.basis_set = ''
    elif problem == 'potential_missing': kind.potential = ''
    elif problem == 'unknown_name': kind.basis_set = 'MISSING-BASIS'
    elif problem == 'version': kind.basis_ref.version = '2025.2'
    elif problem == 'file_hash': kind.basis_ref.sha256 = 'invalid'
    elif problem == 'entry_hash': kind.basis_ref.entry_sha256 = 'invalid'
    assert element_configuration_progress(cho, catalog) == (2, 3)


def test_progress_checks_actual_files_without_reparsing(cho, catalog, tmp_path):
    option = configure(cho, catalog, 'O')
    path = tmp_path / 'basis'
    original = Path(option.basis.path).read_bytes()
    path.write_bytes(original)
    copied = replace(option.basis, path=str(path))
    local = replace(catalog, entries=[copied, *catalog.entries])
    cho.kinds['O'].basis_ref = DatabaseReference(**copied.reference())
    assert element_configuration_progress(cho, local) == (1, 3)
    path.unlink()
    assert element_configuration_progress(cho, local) == (0, 3)
    path.write_bytes(original + b'\n# changed\n')
    assert element_configuration_progress(cho, local) == (0, 3)


def test_warnings_and_shorter_notes_keep_original_recommendations(cho, catalog):
    for label in cho.structure.kind_elements:
        configure(cho, catalog, label)
    cho.dft.xc_functional = 'BLYP'
    assert any('XC' in issue.message and issue.severity == 'Warning' for issue in validate_kinds(cho, catalog).issues)
    assert element_configuration_progress(cho, catalog) == (3, 3)
    for element in ['C', 'H', 'O']:
        options = recommend(catalog, element, 'PBE')
        assert options
        for option in options:
            assert '仍需收敛性和物理适用性检查' not in option.note
            assert 'q 与 XC 名称一致' in option.note
            assert option.basis.q == option.potential.q and option.potential.xc == 'PBE'
            if 'SR' in option.basis.tags:
                assert '短程形式 SR' in option.note
