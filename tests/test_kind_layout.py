"""Dynamic database help and the combined filter/KIND card."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import pytest
from PySide6.QtCore import QEvent
from PySide6.QtGui import QHelpEvent, QTextDocument
from PySide6.QtWidgets import QLabel, QToolTip
from ui.main_window import MainWindow
from ui.widgets.help_icon import HelpIcon
from ui.widgets.section_card import SectionCard


@pytest.fixture
def window(app, water, tmp_path):
    value = MainWindow(preset_directory=tmp_path / 'presets')
    value.load_into_ui(water)
    value.nav.setCurrentRow(4)
    value.show()
    app.processEvents()
    yield value
    value.dirty = False
    value.close()


def test_database_tooltip_is_complete_and_tracks_live_catalog(window, app, tmp_path):
    panel = window.kind_panel
    icon = panel.database_card.help_icon
    assert isinstance(icon, HelpIcon)
    loaded = [status for status in panel.catalog.statuses if status.entries]
    text = icon.accessibleDescription()
    assert all(Path(status.path).name in text for status in loaded)
    assert f'{sum(status.entries for status in loaded)} 条记录' in text
    assert '2026.1' in text
    assert not any(label.text().startswith('已加载：') for label in panel.findChildren(QLabel))
    assert not panel.database_card.toolTip()
    try:
        pos = icon.rect().center()
        app.sendEvent(icon, QHelpEvent(QEvent.Type.ToolTip, pos, icon.mapToGlobal(pos)))
        assert QToolTip.isVisible() and QToolTip.text() == icon.toolTip()
    finally:
        QToolTip.hideText()
    model = window.project.model_dump()
    new_status = replace(loaded[0], path=str(tmp_path / 'new-library'), version='2026.1-custom', entries=17)
    panel.catalog = replace(panel.catalog, statuses=[new_status])
    panel.update_summary()
    assert icon is panel.database_card.help_icon
    assert 'new-library' in icon.accessibleDescription()
    assert 'CP2K 2026.1-custom · 17 条记录' in icon.accessibleDescription()
    document = QTextDocument()
    document.setHtml(icon.toolTip())
    assert 'new-library' in document.toPlainText() and '17 条记录' in document.toPlainText()
    assert window.project.model_dump() == model


def test_combined_card_filters_keep_selected_records_and_input(window, app):
    panel = window.kind_panel
    cards = panel.findChildren(SectionCard)
    assert [card.title_label.text() for card in cards] == ['数据库文件管理', '基组与赝势配置']
    card = panel.configuration_card
    labels = [label.text() for label in card.findChildren(QLabel)]
    assert '数据库候选筛选' not in labels and '各 KIND 的基组与赝势' in labels
    assert not card.findChildren(SectionCard)
    assert not hasattr(panel, 'search') and panel.table.parentWidget() is card
    expected = window.preview.toPlainText()
    records = deepcopy(panel._records)
    for widget, value in [(panel.q_filter, '999')]:
        widget.setText(value)
        assert panel.table.rowCount() == len(panel._elements)
        assert panel._records == records
        widget.clear()
    panel.quality.setCurrentText('TZV2P')
    panel.source_filter.setCurrentIndex(1)
    panel.xc_filter.setCurrentText('BLYP')
    window.refresh()
    assert panel._records == records and window.preview.toPlainText() == expected
    assert panel.table.horizontalScrollBar().maximum() == 0


@pytest.mark.parametrize('width', [650, 410, 280])
def test_candidate_filters_stay_on_one_row_without_mutating_model(window, app, width):
    panel = window.kind_panel
    before = window.project.model_dump()
    panel.filters.setFixedWidth(width)
    app.processEvents()
    assert panel.filters.row.columns == 4
    assert len(panel.filters.row.items) == 4
    assert len({item.y() for item in panel.filters.row.items}) == 1
    if width < panel.filters.row.minimumWidth():
        assert panel.filters.horizontalScrollBar().maximum() > 0
    else:
        assert panel.filters.horizontalScrollBar().maximum() == 0
    assert window.project.model_dump() == before


@pytest.fixture(params=['en_US', 'zh_CN'])
def localized_window(window, request):
    from i18n.language_manager import language_manager
    manager = language_manager()
    manager.set_language(request.param)
    yield window
    manager.set_language('zh_CN')


def settle_geometry(app):
    for _ in range(6):
        app.processEvents()


def assert_kind_header_fits(table):
    from PySide6.QtWidgets import QHeaderView
    header = table.horizontalHeader()
    assert not header.sectionsMovable() and not header.stretchLastSection()
    assert [header.sectionResizeMode(c) for c in range(4)] == [
        QHeaderView.ResizeMode.Fixed, QHeaderView.ResizeMode.Stretch,
        QHeaderView.ResizeMode.Stretch, QHeaderView.ResizeMode.Fixed]
    assert table.columnWidth(0) == 70
    assert table.columnWidth(3) == 160
    assert abs(table.columnWidth(1) - table.columnWidth(2)) <= 1
    width = table.viewport().width()
    total = sum(table.columnWidth(c) for c in range(4))
    # If narrower than the fixed columns + two 40px minima, Qt may scroll.
    # Otherwise both stretch columns must fill the viewport exactly.
    assert abs(total - max(width, 70 + 160 + 2 * header.minimumSectionSize())) <= 1
    assert header.length() == total
    assert [header.visualIndex(c) for c in range(4)] == list(range(4))


def test_kind_columns_fill_viewport_and_status_is_complete(localized_window, app):
    from PySide6.QtCore import Qt
    from ui.widgets.status_badge import STATUS_ROLE
    window = localized_window
    table = window.kind_panel.table
    settle_geometry(app)
    assert_kind_header_fits(table)
    oxygen = next(row for row in range(table.rowCount()) if table.item(row, 0).text() == 'O')
    status = table.item(oxygen, 3)
    assert status.text() in ['✓ q=6 matched', '✓ q=6 匹配']
    assert status.data(STATUS_ROLE) == 'ready'
    assert table.columnWidth(3) >= table.fontMetrics().horizontalAdvance(status.text()) + 10
    header_text = table.horizontalHeaderItem(3).text()
    assert header_text in ['Status', '状态']
    assert table.columnWidth(3) >= table.horizontalHeader().fontMetrics().horizontalAdvance(header_text) + 8
    for column in [1, 2]:
        assert table.cellWidget(oxygen, column).width() <= table.columnWidth(column)


def test_kind_columns_follow_window_and_splitter_without_mutating_project(localized_window, app):
    window = localized_window
    before = window.project.model_dump_json()
    inp = window.preview.toPlainText()
    splitter = window.centralWidget()
    for width in [1250, 1050, 1680, 1480]:
        window.resize(width, 900)
        for middle in [360, 520, 760]:
            splitter.setSizes([190, middle, max(340, width-190-middle)])
            settle_geometry(app)
            assert_kind_header_fits(window.kind_panel.table)
            table = window.kind_panel.table
            for row in range(table.rowCount()):
                for column in [1, 2]:
                    assert table.cellWidget(row, column).width() <= table.columnWidth(column)
            assert window.project.model_dump_json() == before
            assert window.preview.toPlainText() == inp


def test_kind_header_mouse_drags_cannot_resize_or_reorder(localized_window, app):
    from PySide6.QtCore import Qt, QPoint
    from PySide6.QtTest import QTest
    table = localized_window.kind_panel.table
    header = table.horizontalHeader()
    settle_geometry(app)
    widths = [table.columnWidth(c) for c in range(4)]
    for column in range(4):
        boundary = header.sectionViewportPosition(column) + header.sectionSize(column) - 1
        start = QPoint(boundary, header.height() // 2)
        QTest.mousePress(header.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(header.viewport(), start+QPoint(-30, 0))
        QTest.mouseRelease(header.viewport(), Qt.MouseButton.LeftButton, pos=start+QPoint(-30, 0))
    start = QPoint(header.sectionViewportPosition(0)+20, header.height()//2)
    end = QPoint(header.sectionViewportPosition(2)+20, header.height()//2)
    QTest.mousePress(header.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(header.viewport(), end)
    QTest.mouseRelease(header.viewport(), Qt.MouseButton.LeftButton, pos=end)
    settle_geometry(app)
    assert [table.columnWidth(c) for c in range(4)] == widths
    assert_kind_header_fits(table)


def test_kind_language_switch_preserves_choices_and_geometry(localized_window, app):
    from i18n.language_manager import language_manager
    window = localized_window
    table = window.kind_panel.table
    choices = [table.cellWidget(row, col) for row in range(table.rowCount()) for col in [1, 2]]
    entries = [combo.currentData() for combo in choices]
    before = window.project.model_dump_json()
    inp = window.preview.toPlainText()
    revision, dirty = window._revision, window.dirty
    for language in ['en_US', 'zh_CN', 'en_US', 'zh_CN']:
        language_manager().set_language(language)
        settle_geometry(app)
        assert_kind_header_fits(table)
        assert [table.cellWidget(row, col) for row in range(table.rowCount()) for col in [1, 2]] == choices
        assert [combo.currentData() for combo in choices] == entries
        assert window.project.model_dump_json() == before
        assert window.preview.toPlainText() == inp
        assert (window._revision, window.dirty) == (revision, dirty)


def test_kind_filter_rebuild_does_not_reset_header_or_choices(localized_window, app):
    panel = localized_window.kind_panel
    records = deepcopy(panel._records)
    for text in ['999', '', '6', '']:
        panel.q_filter.setText(text)
        settle_geometry(app)
        assert_kind_header_fits(panel.table)
        assert panel._records == records


def test_kind_scrollbar_changes_keep_stretch_columns_filled(localized_window, app):
    from core.models import Structure
    window = localized_window
    original = window.project.model_copy(deep=True)
    many = original.model_copy(deep=True)
    labels = [f'O{i}' for i in range(9)]
    many.structure = Structure(symbols=['O']*9, positions=[(i*.1, 0, 0) for i in range(9)],
        cell=original.structure.cell, periodic=original.structure.periodic, kind_labels=labels)
    many.kinds = {label: original.kinds['O'].model_copy(deep=True) for label in labels}
    for project, scrolling in [(many, True), (original, False), (many, True)]:
        window.load_into_ui(project)
        settle_geometry(app)
        table = window.kind_panel.table
        assert (table.verticalScrollBar().maximum() > 0) == scrolling
        assert_kind_header_fits(table)
