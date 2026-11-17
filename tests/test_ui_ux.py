"""Presentation-only regressions: controls, camera math, state and model parity."""
from copy import deepcopy
import numpy as np
import pytest
from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QEvent
from PySide6.QtGui import QWheelEvent, QHelpEvent, QStatusTipEvent, QTextDocument
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QToolBar, QToolButton, QToolTip, QLabel, QLineEdit, QTableWidget, QStyleOptionSlider, QStyleOptionSpinBox, QStyle
from core.generator import generate_input
from core.models import Project
from core.presets import capture_preset
from core.validator import ValidationResult
from ui.main_window import MainWindow
from ui.theme import stylesheet
from ui.structure_view import StructureView
from ui.validation_state import step_states, show_step_states, StepState
from ui.widgets.section_card import SectionCard
from ui.widgets.help_icon import HelpIcon
from ui.widgets.numeric_field import NumericField
from ui.widgets.status_badge import STATUS_ROLE, StatusBadgeDelegate


def settle(app):
    for _ in range(4):
        app.processEvents()


def close(window):
    window.dirty=False
    window.close()


@pytest.fixture
def window(app, water, tmp_path):
    value=MainWindow(preset_directory=tmp_path/'presets')
    value.load_into_ui(water)
    value.show()
    settle(app)
    yield value
    close(value)


def test_theme_scrollbars_cards_and_menu_button(app, window):
    assert app.styleSheet()==stylesheet()
    assert '@background@' not in app.styleSheet()
    assert 'QScrollBar::handle:pressed' in app.styleSheet()
    assert window.preview.verticalScrollBar().width()==8
    assert window.preview.horizontalScrollBar().height()==8
    assert window.preset_button.objectName()=='presetMenuButton'
    toolbar=window.findChild(QToolBar)
    other=toolbar.widgetForAction(toolbar.actions()[0])
    assert abs(other.height()-window.preset_button.height())<=2
    assert all(window.stack.widget(i).widget().findChildren(SectionCard) for i in range(8))


def send_tooltip(app, widget, pos):
    QToolTip.hideText()
    app.sendEvent(widget, QHelpEvent(QEvent.Type.ToolTip, pos, widget.mapToGlobal(pos)))
    assert not QToolTip.isVisible()


def test_toolbar_blocks_automatic_and_regenerated_hover_help(app, window):
    toolbar = window.findChild(QToolBar)
    buttons = toolbar.findChildren(QToolButton)
    assert {b.text() for b in buttons if b.isVisible()} == {
        '项目管理', '预设管理', 'XML 规范', '环境检测', '本地运行', '使用说明'}
    for button in buttons:
        # Even a later QAction refresh must not restore visible hover help.
        if button.defaultAction():
            button.defaultAction().setToolTip('动态提示')
        else:
            button.setToolTip('动态提示')
        send_tooltip(app, button, button.rect().center())
        message = window.statusBar().currentMessage()
        app.sendEvent(button, QStatusTipEvent('动态状态提示'))
        assert window.statusBar().currentMessage() == message


@pytest.mark.parametrize('state', ['ready', 'warning', 'error', 'na', 'unchecked'])
def test_navigation_refresh_has_no_hover_help_but_keeps_status(app, window, state):
    for index in range(8):
        window.nav.item(index).setToolTip('旧的状态提示')
        window.nav.item(index).setStatusTip('旧的状态说明')
    states = [StepState(state, errors=['检查详情']) for _ in range(8)]
    show_step_states(window.nav, states)
    for index in range(8):
        item = window.nav.item(index)
        assert not item.toolTip() and not item.statusTip()
        assert item.data(STATUS_ROLE) == state
        assert '检查详情' in item.data(Qt.ItemDataRole.AccessibleDescriptionRole)
        send_tooltip(app, window.nav.viewport(), window.nav.visualItemRect(item).center())
        QTest.mouseClick(window.nav.viewport(), Qt.MouseButton.LeftButton,
                         pos=window.nav.visualItemRect(item).center())
        assert window.stack.currentIndex() == index


def test_parameter_hover_help_is_not_blocked(app, window):
    assert not window.dft_panel.fields['dft.cutoff'][0].toolTip()
    window.nav.setCurrentRow(0)
    settle(app)
    field = window.structure_panel.components
    assert field.toolTip()
    pos = field.rect().center()
    try:
        app.sendEvent(field, QHelpEvent(QEvent.Type.ToolTip, pos, field.mapToGlobal(pos)))
        assert QToolTip.isVisible()
        assert QToolTip.text() == field.toolTip()
    finally:
        QToolTip.hideText()
    window.nav.setCurrentRow(0)
    settle(app)
    card = next(card for card in window.structure_panel.findChildren(SectionCard)
                if card.title_label.text() == '晶胞与周期性')
    assert card.help_icon.accessibleDescription() == 'PERIODIC · CELL 与 POISSON 保持一致'
    assert card.content.itemAt(0).widget() is window.structure_panel.periodic
    assert not any(label.text() == card.help_icon.accessibleDescription() for label in card.findChildren(QLabel))
    try:
        icon = card.help_icon
        pos = icon.rect().center()
        app.sendEvent(icon, QHelpEvent(QEvent.Type.ToolTip, pos, icon.mapToGlobal(pos)))
        assert QToolTip.isVisible() and QToolTip.text() == icon.toolTip()
    finally:
        QToolTip.hideText()


@pytest.mark.parametrize('title,expected', [
    ('导出 CP2K Input',
     '生成可用于 CP2K 计算的输入文件。单独 INP 使用与预览相同的生成逻辑；转移到其他计算环境时，建议导出计算包。\n\n'
     '坐标内嵌于单独 INP；基组和赝势依赖文件须保持可访问。多个赝势来源会同时生成所需的合并文件。'),
    ('保存当前设置为预设',
     '保存当前 DFT、SCF、基组、优化等设置，以便后续快速调用。默认不包含晶胞和结构坐标；草稿会标为不完整。'),
])
def test_export_card_help_is_complete_local_and_disappears_on_leave(app, window, title, expected):
    window.nav.setCurrentRow(7)
    settle(app)
    cards = window.export_panel.findChildren(SectionCard)
    card = next(card for card in cards if card.title_label.text() == title)
    icon = card.help_icon
    assert isinstance(icon, HelpIcon) and icon.width() == icon.height() == 16
    assert icon.x() - (card.title_label.x() + card.title_label.width()) == 6
    assert abs(icon.geometry().center().y() - card.title_label.geometry().center().y()) <= 1
    assert not card.toolTip() and not card.title_label.toolTip()
    assert icon.accessibleDescription() == expected
    document = QTextDocument()
    document.setHtml(icon.toolTip())
    assert ' '.join(document.toPlainText().split()) == ' '.join(expected.split())
    assert not any(label.text() in expected for label in card.findChildren(QLabel)
                   if label is not icon and label is not card.title_label and label.text())
    try:
        QTest.mouseMove(icon, icon.rect().center())
        pos = icon.rect().center()
        app.sendEvent(icon, QHelpEvent(QEvent.Type.ToolTip, pos, icon.mapToGlobal(pos)))
        assert QToolTip.isVisible() and QToolTip.text() == icon.toolTip()
        tip = next(widget for widget in app.topLevelWidgets() if widget.objectName() == 'qtooltip_label')
        assert tip.width() <= 380
        QTest.mouseMove(card.title_label, card.title_label.rect().center())
        QTest.qWait(450)
        assert not QToolTip.isVisible()
        send_tooltip(app, card.title_label, card.title_label.rect().center())
        send_tooltip(app, card, card.rect().center())
    finally:
        QToolTip.hideText()
    assert card.content.itemAt(0).widget() in [window.export_panel.bundle_button, window.export_panel.preset_button]
    assert 'MPI 进程数' in window.export_panel.run_summary.text()
    assert 'OpenMP 线程数' in window.export_panel.run_summary.text()
    assert '逻辑核数' in window.export_panel.run_summary.text()
    assert 'run.sh' in window.export_panel.run_note.text()


def test_preset_dropdown_opens_and_applies_without_losing_structure(app, window, monkeypatch):
    before=window.project.structure.model_dump()
    monkeypatch.setattr(window,'confirm_preset_application',lambda *args:True)
    opened=[]
    def choose():
        opened.append(window.preset_menu.isVisible())
        next(a for a in window.preset_menu.actions() if a.text()=='几何优化预设').trigger()
        window.preset_menu.close()
    QTimer.singleShot(40,choose)
    QTest.mouseClick(window.preset_button,Qt.MouseButton.LeftButton)
    QTest.qWait(80)
    settle(app)
    assert opened==[True]
    assert window.project.global_settings.run_type=='GEO_OPT'
    assert window.project.structure.model_dump()==before
    assert window._step_states[5].state=='ready'


@pytest.mark.parametrize('path,text,value,unit', [
    ('dft.cutoff','5.123456789123E2',512.3456789123,'Ry'),
    ('dft.rel_cutoff','6.0e1',60.,'Ry'),
    ('dft.eps_default','1.23456789123e-12',1.23456789123e-12,''),
])
def test_numeric_precision_units_and_pair_signal(window,path,text,value,unit):
    field=window.dft_panel.fields[path][0]
    assert isinstance(field,NumericField) and isinstance(field,QLineEdit)
    assert field.unit_label.text()==unit
    assert field.unit_label.focusPolicy()==Qt.FocusPolicy.NoFocus
    old=window._revision
    field.setText(text)
    assert window.dirty and window._revision>old
    window.refresh()
    assert getattr(window.project.dft,path.split('.')[-1])==value
    assert field.text()==text
    assert unit not in field.text() if unit else True
    assert not field.property('invalid')


def test_force_units_and_roundtrip_do_not_change_generator(window, app, tmp_path):
    window.global_panel.fields['global_settings.run_type'][0].setCurrentIndex(1)
    window.refresh()
    for key,unit in [('max_force','Ha/Bohr'),('rms_force','Ha/Bohr'),('max_dr','Bohr'),('rms_dr','Bohr')]:
        assert window.motion_panel.fields['motion.'+key][0].unit_label.text()==unit
    window.motion_panel.fields['motion.max_force'][0].setText('4.512345678901e-4')
    window.refresh()
    expected=generate_input(window.project)
    data=window.project.model_dump()
    window.project_path=tmp_path/'saved.json'
    assert window.save()
    window.load_into_ui(Project())
    window._open_path(tmp_path/'saved.json')
    assert window.project.model_dump()==data
    assert window.preview.toPlainText()==expected
    assert 'Ha/Bohr' not in expected
    assert window.scf_panel.fields['dft.scf.eps_scf'][0].unit_label.text()=='Ha'


def test_grid_reflows_and_units_never_overlap(app,window):
    window.nav.setCurrentRow(2)
    card=window.dft_panel.cards[2]
    grid=card.content.itemAt(0).widget()
    window.resize(1920,1080)
    settle(app)
    assert grid.columns==2
    electronic = window.dft_panel.cards[0].content.itemAt(0).widget()
    assert electronic.columns == 3
    window.centralWidget().setSizes([190,370,window.width()-566])
    settle(app)
    assert grid.columns==1
    assert electronic.columns == 3
    assert electronic.items[0].y() == electronic.items[1].y()
    controls = [window.dft_panel.fields[path][0] for path in ['dft.charge', 'dft.multiplicity', 'dft.uks']]
    assert controls[0].mapTo(electronic, QPoint()).y() == controls[1].mapTo(electronic, QPoint()).y()
    assert len({control.mapTo(electronic, control.rect().center()).y() for control in controls}) == 1
    assert controls[2].text() == '自旋极化 UKS'
    assert len({control.height() for control in controls}) == 1
    for left, right in zip(electronic.items, electronic.items[1:]):
        assert left.geometry().right() < right.x()
    assert window.stack.widget(2).horizontalScrollBar().maximum()==0
    for path in ['dft.cutoff','dft.rel_cutoff']:
        field=window.dft_panel.fields[path][0]
        assert field.maximumWidth()==240
        assert field.unit_label.geometry().right()<field.width()
        assert field.textMargins().right()>=field.unit_label.width()+8


def test_scf_active_cards_and_scientific_values(window,app):
    window.nav.setCurrentRow(3)
    settle(app)
    panel=window.scf_panel
    assert panel.stack.currentWidget() is panel.ot
    assert not panel.outer_max.isEnabled()
    panel.method.setCurrentIndex(1)
    window.refresh();settle(app)
    assert panel.stack.currentWidget() is panel.diag and panel.diag.isVisible()
    assert len(panel.diag.cards) == 1
    assert panel.diag.cards[0].title_label.text() == 'DIAGONALIZATION 设置'
    assert {'对角化参数', '混合与电子展宽'} <= {label.text() for label in panel.diag.cards[0].findChildren(QLabel)}
    assert not panel.ot.isVisible()
    assert panel.stack.height()==panel.diag.sizeHint().height()
    panel.diag.fields['dft.scf.smearing'][0].setChecked(True)
    panel.diag.fields['dft.scf.added_mos'][0].setText('12')
    panel.temperature.setText('3.01e2')
    panel.diag.fields['dft.scf.mixing_alpha'][0].setText('0.37')
    window.refresh()
    assert panel.temperature.isEnabled()
    assert window.project.dft.scf.electronic_temperature==301.
    assert '&DIAGONALIZATION' in window.preview.toPlainText()
    panel.method.setCurrentIndex(0)
    window.refresh();settle(app)
    assert panel.stack.currentWidget() is panel.ot
    assert panel.stack.height()==panel.ot.sizeHint().height()
    assert '&DIAGONALIZATION' not in window.preview.toPlainText()
    panel.method.setCurrentIndex(1)
    window.refresh();settle(app)
    assert panel.diag.fields['dft.scf.added_mos'][0].text() == '12'
    assert panel.diag.fields['dft.scf.smearing'][0].isChecked()
    assert window.project.dft.scf.added_mos == 12
    assert window.project.dft.scf.mixing_alpha == .37
    assert window.project.dft.scf.electronic_temperature == 301.


def test_camera_labels_projection_and_reload_are_presentation_only(app,water):
    view=StructureView();view.resize(540,300);view.show();view.set_structure(water.structure)
    before=water.model_dump()
    assert not view.show_labels
    initial=view.rotation.copy()
    QTest.mousePress(view,Qt.MouseButton.LeftButton,pos=QPoint(160,140))
    QTest.mouseMove(view,QPoint(205,170),delay=10)
    QTest.mouseRelease(view,Qt.MouseButton.LeftButton,pos=QPoint(205,170))
    assert not np.allclose(view.rotation,initial)
    view.labels_button.click()
    assert view.show_labels
    orth=view.projected_points()[1]
    assert [button.text() for button in view.tools.findChildren(QToolButton)] == ['Aa', 'A', 'B', 'C', '↺']
    assert view.tools.layout().count() == 5
    view.set_perspective(True)
    assert view.perspective
    assert not np.allclose(view.projected_points()[1],orth)
    view.set_structure(water.structure.model_copy(deep=True))
    assert view.show_labels and view.perspective
    wheel=QWheelEvent(QPointF(220,150),QPointF(220,150),QPoint(),QPoint(0,120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
    app.sendEvent(view,wheel)
    assert view.zoom>1
    assert np.allclose(view.axis_directions(),view.rotation.T[:,:2])
    assert water.model_dump()==before
    view.reset_button.click()
    assert view.zoom==1 and np.allclose(view.rotation,view.default_rotation())
    view.close()


@pytest.mark.parametrize('axis,index',[('A',0),('B',1),('C',2)])
def test_actual_triclinic_axis_alignment_not_cartesian(app,water,axis,index):
    structure=water.structure.model_copy(deep=True)
    structure.cell=((5,1,.5),(2,4,1),(.7,1.3,6))
    before=structure.model_dump()
    view=StructureView();view.set_structure(structure)
    view.axis_buttons[axis].click()
    transformed=view.rotation@np.asarray(structure.cell[index])
    assert np.allclose(transformed[:2],0,atol=1e-12)
    assert transformed[2]==pytest.approx(np.linalg.norm(structure.cell[index]))
    assert np.linalg.det(view.rotation)==pytest.approx(1)
    assert np.allclose(view.rotation@view.rotation.T,np.eye(3))
    assert structure.model_dump()==before
    view.close()


def test_camera_axis_disabled_without_cell_and_overlay_stays_in_corner(app,water):
    st=water.structure.model_copy(deep=True);st.cell=((0,0,0),)*3
    view=StructureView();view.set_structure(st);view.resize(530,300);view.show();settle(app)
    assert all(not b.isEnabled() for b in view.axis_buttons.values())
    assert view.tools.geometry().right()<=view.width()-5
    assert view.tools.y()==8
    view.resize(340,300);settle(app)
    assert view.tools.geometry().right()<=view.width()-5
    view.close()


def test_filter_selection_retention_visible_pin_and_badge_tooltips(window,app):
    panel=window.kind_panel
    before=deepcopy(panel._records)
    assert '不满足' not in panel.filter_note.text()
    panel.q_filter.setText('999')
    settle(app)
    assert panel._records==before and panel.table.rowCount()==len(panel._elements)
    assert '保持选中' in panel.filter_note.text()
    for row in range(panel.table.rowCount()):
        assert panel.table.cellWidget(row,1).property('pinned')
        assert '已保留' in panel.table.cellWidget(row,1).toolTip()
        badge=panel.table.item(row,3)
        assert len(badge.text())<18
        assert '不保证物理适用性' in badge.toolTip()
        assert panel.table.cellWidget(row,3) is None
    assert isinstance(panel.table.itemDelegateForColumn(3),StatusBadgeDelegate)
    panel.q_filter.clear();settle(app)
    assert panel._records==before
    window.nav.setCurrentRow(4)
    settle(app)
    assert panel.table.horizontalScrollBar().maximum()==0
    assert panel.table.height()<260  # only the actual two element rows, no large blank area


def test_nav_states_follow_local_report_and_not_page_visits(window,app):
    assert window._step_states[5].state=='na'
    assert window._step_states[7].state=='unchecked'
    before=[s.state for s in window._step_states]
    for index in range(8):window.nav.setCurrentRow(index)
    assert [s.state for s in window._step_states]==before
    field=window.dft_panel.fields['dft.cutoff'][0]
    field.setText('invalid')
    assert window.nav.item(2).data(STATUS_ROLE)=='unchecked'
    window.refresh()
    assert window.nav.item(2).data(STATUS_ROLE)=='error'
    assert window.nav.item(7).data(STATUS_ROLE)=='unchecked'
    assert not window.nav.item(2).toolTip()
    assert '有效数字' in window.nav.item(2).data(Qt.ItemDataRole.AccessibleDescriptionRole)
    assert window.export_panel.errors.count()==len(window._validation.errors)
    field.setText('400')
    window.refresh()
    window.global_panel.fields['global_settings.run_type'][0].setCurrentIndex(1)
    window.refresh()
    assert window._step_states[5].state=='ready' and window.motion_panel.isEnabled()
    window.motion_panel.fields['motion.max_force'][0].setText('NaN')
    window.refresh()
    assert window._step_states[5].state=='error'
    window.motion_panel.fields['motion.max_force'][0].setText('4.5e-4')
    window.refresh()
    assert window._step_states[5].state=='ready'


def test_initial_incomplete_modules_stay_incomplete_with_bad_numeric_draft(app,tmp_path):
    window=MainWindow(preset_directory=tmp_path)
    window.dft_panel.fields['dft.cutoff'][0].setText('bad')
    window.refresh()
    assert window._step_states[0].state=='error'
    assert window._step_states[2].state=='error'
    assert window._step_states[4].state=='error'
    assert window._step_states[7].state=='unchecked'
    close(window)


def test_warning_xml_error_and_unchecked_status_classification(water):
    warnings=ValidationResult(warnings=['KIND O：q 信息不完整'])
    states=step_states(water,warnings,checked=True)
    assert states[4].state=='warning' and states[7].state=='warning'
    states=step_states(water,ValidationResult(errors=['XML 规范/校验失败']),checked=True)
    assert states[7].state=='error'
    assert states[5].state=='na'


def test_camera_controls_filtering_navigation_do_not_change_input(window,app):
    expected=window.preview.toPlainText()
    model=window.project.model_dump()
    view=window.structure_panel.view
    view.set_labels_visible(True);view.set_perspective(True);view.align_cell_axis('B')
    window.kind_panel.quality.setCurrentText('TZV2P')
    for index in range(8):window.nav.setCurrentRow(index)
    window.refresh();settle(app)
    assert window.project.model_dump()==model
    assert window.preview.toPlainText()==expected==generate_input(window.project)


def test_parameter_and_scf_units_do_not_enter_preset(window,tmp_path):
    preset=capture_preset(window.project,'unit-free')
    assert preset.parameters['dft']['cutoff']==400
    assert preset.parameters['dft']['scf']['eps_scf']==1e-6
    assert 'Ha/Bohr' not in preset.model_dump_json()


def test_code_and_table_wheel_scroll_and_scrollbar_drag(app,window):
    code=window.preview
    before=code.verticalScrollBar().value()
    wheel=QWheelEvent(QPointF(100,100),QPointF(100,100),QPoint(),QPoint(0,-120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
    app.sendEvent(code.viewport(),wheel)
    assert code.verticalScrollBar().value()>before
    table=QTableWidget(100,2);table.resize(400,180);table.show();settle(app)
    bar=table.verticalScrollBar()
    assert bar.width()==8 and bar.maximum()>0
    opt=QStyleOptionSlider();opt.initFrom(bar);opt.orientation=Qt.Orientation.Vertical
    opt.minimum=bar.minimum();opt.maximum=bar.maximum();opt.pageStep=bar.pageStep()
    opt.sliderPosition=bar.value();opt.sliderValue=bar.value()
    handle=bar.style().subControlRect(QStyle.ComplexControl.CC_ScrollBar,opt,QStyle.SubControl.SC_ScrollBarSlider,bar)
    QTest.mousePress(bar,Qt.MouseButton.LeftButton,pos=handle.center())
    QTest.mouseMove(bar,QPoint(handle.center().x(),bar.height()-20),delay=10)
    QTest.mouseRelease(bar,Qt.MouseButton.LeftButton,pos=QPoint(handle.center().x(),bar.height()-20))
    assert bar.value()>0
    table.close()


def test_keyboard_scientific_input_and_tab_skip_unit_labels(app,window):
    window.nav.setCurrentRow(2);settle(app)
    charge=window.dft_panel.fields['dft.charge'][0]
    charge.setFocus();QTest.keyClick(charge,Qt.Key.Key_Tab)
    assert app.focusWidget() is window.dft_panel.fields['dft.multiplicity'][0]
    eps=window.dft_panel.fields['dft.eps_default'][0]
    eps.setFocus();eps.selectAll();QTest.keyClicks(eps,'1.23456789E-11')
    window.refresh()
    assert window.project.dft.eps_default==1.23456789e-11
    assert eps.unit_label.focusPolicy()==Qt.FocusPolicy.NoFocus


def test_styled_spinbox_arrow_buttons_remain_clickable(window,app):
    window.nav.setCurrentRow(6);settle(app)
    spin=window.run_panel.mpi_processes
    option=QStyleOptionSpinBox();option.initFrom(spin);option.rect=spin.rect()
    up=spin.style().subControlRect(QStyle.ComplexControl.CC_SpinBox,option,QStyle.SubControl.SC_SpinBoxUp,spin)
    down=spin.style().subControlRect(QStyle.ComplexControl.CC_SpinBox,option,QStyle.SubControl.SC_SpinBoxDown,spin)
    assert up.width()>=20 and down.width()>=20
    old=spin.value()
    QTest.mouseClick(spin,Qt.MouseButton.LeftButton,pos=up.center())
    assert spin.value()==old+1 and window.project.run_environment.mpi_processes==old+1
    QTest.mouseClick(spin,Qt.MouseButton.LeftButton,pos=down.center())
    assert spin.value()==old


def test_reopen_valid_project_clears_old_errors_in_inactive_fields(window,water):
    window.global_panel.fields['global_settings.run_type'][0].setCurrentIndex(1)
    window.refresh()
    force=window.motion_panel.fields['motion.max_force'][0]
    force.setText('NaN');window.refresh()
    assert force.property('invalid')
    window.load_into_ui(water)
    assert not force.property('invalid') and not window.motion_panel.isEnabled()
    outer=window.scf_panel.fields['dft.scf.outer_scf'][0]
    outer.setChecked(True)
    window.scf_panel.outer_max.setText('-1');window.refresh()
    assert window.scf_panel.outer_max.property('invalid')
    window.load_into_ui(water)
    assert not window.scf_panel.outer_max.property('invalid')
    assert not window.scf_panel.outer_max.isEnabled()
