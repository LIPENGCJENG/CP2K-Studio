"""Single-line help cells, complete native tooltips and unchanged workflows."""
import numpy as np
import pytest
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QHelpEvent, QTextDocument
from PySide6.QtTest import QTest, QSignalSpy
from PySide6.QtWidgets import QToolTip, QHeaderView, QSplitter, QStyleOptionViewItem
from i18n.language_manager import language_manager
from ui.widgets.poisson_reference import PoissonReference, REFERENCE_ROWS
from core.generator import generate_input
from core.validator import validate_project
from core.project_io import save_project, load_project, export_bundle
from core.input_export import export_input
from core.presets import capture_preset, apply_preset
from tests.test_poisson_reference_ui import window
from tests.test_layout_workflow import wait_for_worker


def plain_tooltip(text):
    document = QTextDocument()
    document.setHtml(text)
    return document.toPlainText()


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
def test_summaries_and_full_tooltips_share_the_same_localized_data(app, language):
    language_manager().set_language(language)
    table = PoissonReference()
    try:
        table.resize(620,200)
        table.show()
        app.processEvents()
        for row, reference in enumerate(REFERENCE_ROWS):
            assert table.item(row,0).text() == reference.solver
            assert table.item(row,1).text() == reference.periodicity
            for column, entries in [(2,reference.applications),(3,reference.constraints)]:
                item = table.item(row,column)
                assert '<b>' in item.toolTip() and '<li>' in item.toolTip()
                for message in entries:
                    text = message.render(language)
                    assert text in item.text()
                    assert text in plain_tooltip(item.toolTip())
                assert '…' not in item.text()  # The stored value was never shortened.
                option = QStyleOptionViewItem()
                table.initViewItemOption(option)
                table.itemDelegate().initStyleOption(option,table.model().index(row,column))
                assert not (option.features & QStyleOptionViewItem.ViewItemFeature.WrapText)
                assert option.textElideMode == Qt.TextElideMode.ElideRight
        assert 'FFTSG' in table.item(1,3).text() and 'L > 2D' in table.item(2,3).text()
        assert ('Reference only' if language == 'en_US' else '仅供参考') in table.item(4,3).text()
        assert ('reference orientations' if language == 'en_US' else '参考取向') in table.item(3,3).text()
        assert all(table.horizontalHeader().sectionResizeMode(i) == QHeaderView.ResizeMode.Fixed for i in range(4))
        assert not table.horizontalHeader().sectionsMovable()
    finally:
        table.close()
        table.deleteLater()
        app.processEvents()
        language_manager().set_language('zh_CN')


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
@pytest.mark.parametrize('column', [2,3])
def test_native_tooltip_shows_complete_wavelet_details_and_hides(app, language, column):
    language_manager().set_language(language)
    table = PoissonReference()
    try:
        table.resize(620,200)
        table.show()
        app.processEvents()
        position = table.visualItemRect(table.item(1,column)).center()
        event = QHelpEvent(QEvent.Type.ToolTip,position,table.viewport().mapToGlobal(position))
        app.sendEvent(table.viewport(),event)
        assert QToolTip.isVisible()
        assert QToolTip.text() == table.item(1,column).toolTip()
        entries = REFERENCE_ROWS[1].applications if column == 2 else REFERENCE_ROWS[1].constraints
        for text in entries:
            assert text.render(language) in plain_tooltip(QToolTip.text())
        tips = [widget for widget in app.topLevelWidgets() if widget.inherits('QTipLabel') and widget.isVisible()]
        assert tips and 320 <= tips[0].width() <= 450
        assert tips[0].height() < app.primaryScreen().availableGeometry().height()
        app.sendEvent(table.viewport(),QEvent(QEvent.Type.Leave))
        QTest.qWait(450)
        assert not QToolTip.isVisible()
    finally:
        QToolTip.hideText()
        table.close()
        table.deleteLater()
        app.processEvents()
        language_manager().set_language('zh_CN')


@pytest.mark.parametrize('task', ['ENERGY','GEO_OPT','CELL_OPT','VIBRATIONAL_ANALYSIS'])
def test_reference_interaction_language_and_splitter_keep_all_tasks_unchanged(window, app, tmp_path, task):
    w = window
    combo = w.global_panel.fields['global_settings.run_type'][0]
    combo.setCurrentIndex(combo.findData(task))
    w.refresh()
    w.nav.setCurrentRow(2)
    table = w.dft_panel.poisson_reference
    w.check_current_configuration()
    wait_for_worker(app,w)
    checked = w._comprehensive_result
    assert checked.validation.ok, checked.report()
    view = w.structure_panel.view
    view.zoom = 1.6
    view.set_labels_visible(True)
    view.pan_offset = np.array([.2,.3,.4])
    rotation = view.rotation.copy()
    snapshot = w.project.model_dump_json(), w.dirty, w._revision, w.preview.toPlainText()
    statuses = [status.state for status in w._step_states]
    spy = QSignalSpy(w.dft_panel.changed)
    splitter = next(split for split in w.findChildren(QSplitter) if split.orientation() == Qt.Orientation.Horizontal)
    sizes = []
    for language, width, requested_sizes in [('en_US',1050,[190,400,450]),('zh_CN',1480,[190,700,500]),('en_US',1480,[190,440,800])]:
        language_manager().set_language(language)
        w.resize(width,900)
        splitter.setSizes(requested_sizes)
        for _ in range(4): app.processEvents()
        w.stack.widget(2).ensureWidgetVisible(table)
        app.processEvents()
        sizes.append([table.columnWidth(i) for i in range(4)])
        assert sum(sizes[-1]) == table.viewport().width()
        assert table.horizontalScrollBar().maximum() == table.verticalScrollBar().maximum() == 0
        assert w.stack.widget(2).horizontalScrollBar().maximum() == 0
        for row in range(6):
            QTest.mouseClick(table.viewport(),Qt.MouseButton.LeftButton,pos=table.visualItemRect(table.item(row,2)).center())
        assert (w.project.model_dump_json(),w.dirty,w._revision,w.preview.toPlainText()) == snapshot
        assert w._comprehensive_result is checked and [status.state for status in w._step_states] == statuses
        assert view.zoom == 1.6 and view.show_labels
        assert np.array_equal(view.rotation,rotation) and np.array_equal(view.pan_offset,[.2,.3,.4])
        assert w.dft_panel.fields['dft.poisson_solver'][0].currentData() == 'PERIODIC'
    assert sizes[0] != sizes[1] != sizes[2]
    assert spy.count() == 0
    assert generate_input(w.project) == snapshot[3]
    saved = tmp_path / 'project.json'
    save_project(w.project,saved)
    assert load_project(saved) == w.project
    preset = capture_preset(w.project,'unchanged by reference')
    assert apply_preset(w.project,preset).project == w.project
    standalone = export_input(w.project,tmp_path/'reference.inp')
    assert standalone.path.read_text() == snapshot[3]
    bundle = export_bundle(w.project,tmp_path/'job').parent
    text = (bundle/'input.inp').read_text()
    assert 'POISSON_SOLVER PERIODIC' in text and 'RUN_TYPE '+task in text


def test_solver_dropdown_and_existing_validation_remain_independent(window):
    w = window
    w.structure_panel.periodic.setCurrentText('NONE')
    solver = w.dft_panel.fields['dft.poisson_solver'][0]
    solver.setCurrentIndex(solver.findData('MT'))
    w.refresh()
    assert w.project.dft.poisson_solver == 'MT' and 'POISSON_SOLVER MT' in w.preview.toPlainText()
    solver.setCurrentIndex(solver.findData('WAVELET'))
    w.refresh()
    assert w.project.dft.poisson_solver == 'WAVELET'
    assert 'PREFERRED_FFT_LIBRARY FFTSG' in w.preview.toPlainText()
    assert 'POISSON_SOLVER WAVELET' in w.preview.toPlainText()
    # Preserve/report the known reference-versus-check difference. The current
    # validator is dimension-based; this UI task must not change its policy.
    p = w.project.model_copy(deep=True)
    p.dft.poisson_solver = 'ANALYTIC'
    for periodic in ['NONE','X','Y','Z','XY','XZ','YZ']:
        p.structure.periodic = periodic
        assert validate_project(p).ok
    p.structure.periodic = 'XYZ'
    assert not validate_project(p).ok
