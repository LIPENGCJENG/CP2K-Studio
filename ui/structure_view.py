"""Qt QPainter atom/cell view with presentation-only camera state."""
from i18n.messages import i18n_msg, i18n_render
from i18n.language_manager import language_manager
import math
import numpy as np
from ase.data import atomic_numbers, covalent_radii
from ase.data.colors import jmol_colors
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QFont, QTransform
from i18n.qt import QWidget, QFrame, QHBoxLayout, QToolButton, QApplication
from ui.theme import COLORS


class StructureView(QWidget):
    atom_clicked = Signal(object, object)  # stable atom ID, keyboard modifiers

    def __init__(self):
        super().__init__()
        language_manager().callback(self, 'canvas', lambda view: view.update())
        self.structure = None
        self.selected_atom_ids = set()
        self.fixed_atom_ids = set()
        self._geometry_key = None
        self.last_pos = None
        self._drag_button = Qt.MouseButton.NoButton
        self._press_pos = None
        self._dragging = False
        self._pressed_atom = None
        self.show_labels = False
        self.perspective = False
        self.zoom = 1.0
        self.rotation = self.default_rotation()
        # World-space displacement of both the implicit camera and its target.
        # This is presentation state, separate from the structure's positions.
        self.pan_offset = np.zeros(3)
        self._points = np.empty((0, 3))
        self._center = np.zeros(3)
        self._radius = 1.0
        self._positions_count = 0
        self.setMinimumHeight(160)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.tools = QFrame(self)
        self.tools.setObjectName('viewTools')
        box = QHBoxLayout(self.tools)
        box.setContentsMargins(4, 4, 4, 4)
        box.setSpacing(4)
        def button(text, tooltip, callback, checkable=False):
            control = QToolButton()
            control.setObjectName('viewControl')
            control.setText(text)
            control.setAccessibleName(tooltip)
            control.setFixedSize(28, 28)
            control.setCheckable(checkable)
            control.clicked.connect(callback)
            box.addWidget(control)
            return control
        self.labels_button = button('Aa', i18n_msg('Show / hide all element labels', code='studio.e808c1fd40c65985'), self.set_labels_visible, True)
        self.axis_buttons = {}
        for axis in 'ABC':
            self.axis_buttons[axis] = button(axis, i18n_msg('View along the actual cell {p0} vector', code='studio.da5ba79f2319a28d', p0=axis), lambda checked=False, a=axis: self.align_cell_axis(a))
        self.reset_button = button('↺', i18n_msg('Reset camera and fit structure', code='studio.9595b75cbb077bfe'), lambda *_: self.reset_view())
        self.tools.adjustSize()
        self._update_axis_buttons()

    @staticmethod
    def default_rotation():
        yaw, pitch = .45, -.35
        cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        return np.array([[cy, 0, sy], [sp*sy, cp, -sp*cy], [-cp*sy, sp, cp*cy]])

    def set_structure(self, structure):
        key = (len(structure.symbols),tuple(structure.symbols[:3000]),tuple(structure.positions[:3000]),
               tuple(structure.cell),structure.periodic) if structure else None
        self.structure = structure
        self.fixed_atom_ids = {atom.atom_id for atom in structure.fixed_atoms} if structure else set()
        self.selected_atom_ids.intersection_update(structure.atom_ids if structure else [])
        if key == self._geometry_key:
            self.update()  # Constraints/selection may change without geometry.
            return
        self._geometry_key = key
        if structure and structure.symbols:
            positions = np.asarray(structure.positions[:3000], dtype=float)
            cell = np.asarray(structure.cell, dtype=float)
            corners = np.array([np.array([i, j, k]) @ cell for i in (0, 1) for j in (0, 1) for k in (0, 1)])
            self._points = np.vstack([positions, corners])
            self._positions_count = len(positions)
            self._center = (self._points.min(axis=0) + self._points.max(axis=0)) / 2
            self._radius = max(float(np.linalg.norm(self._points-self._center, axis=1).max()), .5)
        else:
            self._points = np.empty((0, 3))
            self._positions_count = 0
        self.zoom = 1.0
        self.pan_offset = np.zeros(3)
        self._end_gesture()
        self._update_axis_buttons()
        self.update()

    def set_selected_atoms(self, atom_ids):
        self.selected_atom_ids = set(atom_ids) & set(self.structure.atom_ids if self.structure else [])
        self.update()

    def _update_axis_buttons(self):
        for index, axis in enumerate('ABC'):
            valid = self.structure is not None and np.linalg.norm(self.structure.cell[index]) > 1e-10
            self.axis_buttons[axis].setEnabled(bool(valid))
            self.axis_buttons[axis].setAccessibleName(i18n_msg('View along the actual cell {p0} vector', code='studio.da5ba79f2319a28d', p0=axis) if valid else i18n_msg('No valid cell {p0} vector was provided', code='studio.8b611d6013de8616', p0=axis))

    def set_labels_visible(self, visible):
        self.show_labels = bool(visible)
        self.labels_button.setChecked(self.show_labels)
        self.update()

    def set_perspective(self, enabled):
        self.perspective = bool(enabled)
        self.update()

    def align_cell_axis(self, axis):
        if axis not in self.axis_buttons or not self.axis_buttons[axis].isEnabled():
            return
        direction = np.array(self.structure.cell['ABC'.index(axis)], dtype=float)
        direction /= np.linalg.norm(direction)
        up = np.array([0., 0., 1.]) if abs(direction[2]) < .95 else np.array([0., 1., 0.])
        right = np.cross(up, direction)
        right /= np.linalg.norm(right)
        self.rotation = np.vstack([right, np.cross(direction, right), direction])
        self.update()

    def reset_view(self):
        self.rotation = self.default_rotation()
        self.zoom = 1.0
        self.pan_offset = np.zeros(3)
        self._end_gesture()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.tools.move(max(8, self.width()-self.tools.width()-8), 8)
        self.tools.raise_()

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            if self._drag_button == Qt.MouseButton.NoButton:
                self._drag_button = event.button()
                self.last_pos = QPointF(event.position())
                self._press_pos = QPointF(event.position())
                self._dragging = False
                self._pressed_atom = self.atom_at(event.position()) if event.button() == Qt.MouseButton.LeftButton else None
                if event.button() == Qt.MouseButton.RightButton:
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == self._drag_button:
            atom_id = self._pressed_atom if not self._dragging else None
            left_click = self._drag_button == Qt.MouseButton.LeftButton
            self._end_gesture()
            if left_click and atom_id is not None and self.atom_at(event.position()) == atom_id:
                self.atom_clicked.emit(atom_id, event.modifiers())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.last_pos is None:
            super().mouseMoveEvent(event)
            return
        if not event.buttons() & self._drag_button:
            self._end_gesture()
            return
        delta = event.position()-self.last_pos
        self.last_pos = QPointF(event.position())
        if self._drag_button == Qt.MouseButton.RightButton:
            # Convert logical screen pixels into the current camera plane.
            # Inverse scale keeps sensitivity consistent after zoom/resizing;
            # R.T maps screen-right/up onto world-space camera directions.
            plane_delta = np.array([-delta.x(), delta.y(), 0.]) / self.projection_scale()
            self.pan_offset += self.rotation.T @ plane_delta
            self._dragging = True
            self.update()
        elif self._drag_button == Qt.MouseButton.LeftButton:
            if (event.position()-self._press_pos).manhattanLength() >= QApplication.startDragDistance():
                self._dragging = True
            if self._dragging and self._pressed_atom is None:
                self._rotate(delta)
        event.accept()

    def _rotate(self, delta):
        a, b = delta.x()*.01, delta.y()*.01
        ry = np.array([[math.cos(a),0,math.sin(a)], [0,1,0], [-math.sin(a),0,math.cos(a)]])
        rx = np.array([[1,0,0], [0,math.cos(b),-math.sin(b)], [0,math.sin(b),math.cos(b)]])
        self.rotation = rx @ ry @ self.rotation
        self.update()

    def _end_gesture(self):
        self.last_pos = None
        self._press_pos = None
        self._drag_button = Qt.MouseButton.NoButton
        self._pressed_atom = None
        self._dragging = False
        self.unsetCursor()

    def hideEvent(self, event):
        self._end_gesture()
        super().hideEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y() or event.pixelDelta().y()
        self.zoom = max(.15, min(8., self.zoom * 1.12**(delta/120)))
        self.update()
        event.accept()

    def projected_points(self):
        rotated = (self._points-self._center-self.pan_offset) @ self.rotation.T
        factor = np.ones(len(rotated))
        if self.perspective:
            distance = self._radius * 3.5
            depth = distance-rotated[:, 2]
            factor = np.divide(distance, depth, out=np.zeros_like(depth), where=depth > distance*.001)
        return rotated, rotated[:, :2]*factor[:, None], factor

    def projection_scale(self):
        return max(1, min(self.width()-70, self.height()-64)) / (2*self._radius) * .85 * self.zoom

    def screen_projection(self):
        """One projection shared by atom picking and all geometry/markers."""
        rotated, xy, factor = self.projected_points()
        scale = self.projection_scale()
        screen = np.column_stack((self.width()/2 + xy[:, 0]*scale, self.height()/2 - xy[:, 1]*scale))
        return rotated, screen, factor, scale

    def atom_radius(self, index, scale, factor):
        number = atomic_numbers[self.structure.symbols[index]]
        return max(3, min(24, covalent_radii[number]*scale*.5*factor))

    def atom_at(self, position):
        if not self.structure or not self._positions_count:
            return None
        if (not QRectF(self.rect()).contains(position)
                or QRectF(8, self.height()-94, 88, 84).contains(position)
                or self.tools.geometry().contains(position.toPoint())):
            return None
        rotated, screen, factor, scale = self.screen_projection()
        target = np.array([position.x(), position.y()])
        # Reverse paint order so overlapping atoms select the visible front one.
        for index in np.argsort(rotated[:self._positions_count, 2])[::-1]:
            if factor[index] <= 0:
                continue
            radius = self.atom_radius(index, scale, factor[index]) + 2
            if np.sum((screen[index] - target)**2) <= radius**2:
                return self.structure.atom_ids[index]
        return None

    def axis_directions(self):
        # Cartesian XYZ use the same rotation, with a constant overlay length.
        return self.rotation.T[:, :2].copy()

    def _paint_axes(self, painter):
        painter.setPen(Qt.PenStyle.NoPen)
        background = QColor(COLORS['card'])
        background.setAlpha(210)
        painter.setBrush(background)
        painter.drawRoundedRect(QRectF(8, self.height()-94, 88, 84), 6, 6)
        origin = QPointF(47, self.height()-48)
        for i, (label, color) in enumerate(zip('XYZ', ['#ef9d99', '#87dab7', '#8ebdec'])):
            direction = self.axis_directions()[i]
            endpoint = origin + QPointF(direction[0]*27, -direction[1]*27)
            painter.setPen(QPen(QColor(color), 2))
            painter.drawLine(origin, endpoint)
            painter.setBrush(QColor(color))
            painter.drawEllipse(endpoint, 2.5, 2.5)
            offset = QPointF(4, -4) if np.linalg.norm(direction)>.1 else QPointF(5, 12)
            painter.drawText(endpoint + offset, label)

    @staticmethod
    def _paint_atom_label(painter, center, radius, symbol, color):
        font = QFont(painter.font())
        font.setPixelSize(12)
        font.setBold(True)
        text = QPainterPath()
        text.addText(QPointF(), font, symbol)
        bounds = text.boundingRect()
        if bounds.isEmpty():
            return
        # Center visible glyphs, not their baseline; fit inside the sphere.
        text.translate(-bounds.center())
        fit = min(1., radius * 1.4 / max(bounds.width(), bounds.height()))
        text = QTransform.fromScale(fit, fit).map(text)
        text.translate(center)
        rgb = [color.redF(), color.greenF(), color.blueF()]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055)**2.4 for v in rgb]
        luminance = sum(v * weight for v, weight in zip(linear, [.2126, .7152, .0722]))
        clip = QPainterPath()
        clip.addEllipse(center, radius, radius)
        painter.save()
        painter.setClipPath(clip, Qt.ClipOperation.IntersectClip)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#000000' if luminance > .179 else '#ffffff'))
        painter.drawPath(text)
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(COLORS['input']))
        if not self.structure or not self.structure.symbols:
            painter.setPen(QColor(COLORS['muted']))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, i18n_render(i18n_msg('Import a structure to view it', code='studio.017f4634c538a9dc')))
            self._paint_axes(painter)
            return
        rotated, screen, factor, scale = self.screen_projection()
        def point(index):
            return QPointF(*screen[index])
        painter.setPen(QPen(QColor('#49657f'), 1))
        for i in range(8):
            for bit in (1,2,4):
                j = i ^ bit
                if i < j and factor[self._positions_count+i] > 0 and factor[self._positions_count+j] > 0:
                    painter.drawLine(point(self._positions_count+i), point(self._positions_count+j))
        for index in np.argsort(rotated[:self._positions_count,2]):
            if factor[index] <= 0:
                continue
            symbol = self.structure.symbols[index]
            z = atomic_numbers[symbol]
            radius = self.atom_radius(index, scale, factor[index])
            color = QColor.fromRgbF(*jmol_colors[z])
            painter.setBrush(color)
            painter.setPen(QPen(QColor('#c9dae8'), .6))
            p = point(index)
            painter.drawEllipse(p, radius, radius)
            atom_id = self.structure.atom_ids[index]
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if atom_id in self.fixed_atom_ids:
                painter.setPen(QPen(QColor(COLORS['warning']), 1.7))
                painter.drawRoundedRect(QRectF(p.x()-radius-3, p.y()-radius-3,
                                              2*radius+6, 2*radius+6), 3, 3)
            if atom_id in self.selected_atom_ids:
                painter.setPen(QPen(QColor(COLORS['accent']), 2.5))
                painter.drawEllipse(p, radius+7, radius+7)
            if self.show_labels:
                self._paint_atom_label(painter, p, radius, symbol, color)
        self._paint_axes(painter)
        painter.setPen(QColor(COLORS['muted']))
        caption = i18n_msg('{p0} atoms · {p1}', p0=len(self.structure.symbols), p1=self.structure.periodic)
        if self.fixed_atom_ids or self.selected_atom_ids:
            caption += i18n_msg(' · Selected (cyan): {p0} · Fixed (gold): {p1}', code='studio.a32c4d7e1419622a', p0=len(self.selected_atom_ids), p1=len(self.fixed_atom_ids))
        if len(self.structure.symbols)>3000:
            caption += i18n_msg(' · Previewing the first 3000 atoms', code='studio.2561994c2b497360')
        painter.drawText(108,self.height()-16,i18n_render(caption))
