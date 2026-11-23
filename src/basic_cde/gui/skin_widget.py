"""Teclado visual: pulsa teclas sobre una foto, sin reinyectar eventos Qt.

Solo realiza presentación e identifica teclas. El MainWindow enruta el
resultado hacia READY, INPUT o INKEY$ como si viniera del teclado real.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer, QRect, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPixmap, QPainterPath, QPolygonF
from PySide6.QtWidgets import QLabel

from basic_cde.gui.skin import led_center_for_mode, photo_size_for_mode
from basic_cde.gui.skin_keys import key_at, key_zones
from basic_cde.gui.skin_modern import MODERN_SKINS, modern_key_at, modern_key_zones


class SkinKeyboard(QLabel):
    keyClicked = Signal(str)
    volumeChange = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaledContents(True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pressed: str | None = None
        self._skin_picture = QPixmap()
        self._press_serial = 0
        self._volume_pressed = None
        self._volume_press_serial = 0
        self._orientation = 'vertical'

    def set_orientation(self, orientation: str):
        self._orientation = orientation

    def set_picture(self, picture: QPixmap):
        self._skin_picture = picture
        self.setPixmap(picture)

    def _photo_size(self) -> tuple[int, int]:
        if self._orientation in MODERN_SKINS:
            return MODERN_SKINS[self._orientation][0]
        return photo_size_for_mode(self._orientation)

    def _zone(self, name: str):
        zones = (modern_key_zones(self._orientation) if self._orientation in MODERN_SKINS
                 else key_zones(self._orientation))
        return next((z for z in zones if z.name == name), None)

    def _rect(self, name: str) -> QRect | None:
        zone = self._zone(name)
        if zone is None:
            return None
        x, y, width, height = zone.bounds
        photo_w, photo_h = self._photo_size()
        sx = self.width() / photo_w
        sy = self.height() / photo_h
        return QRect(round(x * sx), round(y * sy),
                     max(1, round(width * sx)), max(1, round(height * sy)))

    def _path(self, name: str) -> QPainterPath | None:
        zone = self._zone(name)
        if zone is None:
            return None
        photo_w, photo_h = self._photo_size()
        sx = self.width() / photo_w
        sy = self.height() / photo_h
        path = QPainterPath()
        if zone.polygon:
            poly = QPolygonF([QPointF(px * sx, py * sy) for px, py in zone.polygon])
            path.addPolygon(poly)
        else:
            x, y, width, height = zone.bounds
            path.addRect(QRectF(x * sx, y * sy, max(1.0, width * sx), max(1.0, height * sy)))
        return path

    def flash_key(self, name: str, duration_ms: int = 110):
        if self._rect(name) is None:
            return
        self._press_serial += 1
        serial = self._press_serial
        self._pressed = name
        self.update()

        def release():
            if self._press_serial == serial:
                self._pressed = None
                self.update()
        QTimer.singleShot(duration_ms, release)

    def _volume_controls(self):
        """Dos botones pequenos sobre el bisel, junto a la ruedita real."""
        modern_positions = {
            'vertical': ((38, 202, +1), (38, 257, -1)),
            'horizontal': ((41, 186, +1), (41, 241, -1)),
            'compact': ((52, 256, +1), (52, 336, -1)),
            'large': ((26, 163, +1), (26, 211, -1)),
        }
        if self._orientation in modern_positions:
            return modern_positions[self._orientation]
        if self._orientation == 'horizontal':
            return ((32, 161, +1), (32, 201, -1))
        return ((77, 201, +1), (77, 241, -1))

    def _volume_scale(self):
        """Mantiene el tamaño visual de los controles en las skins modernas."""
        if self._orientation not in MODERN_SKINS:
            return 1.0
        photo_w, _ = self._photo_size()
        return 16.0 / (26.0 * self.width() / photo_w)

    def _volume_hit(self, x, y):
        factor = self._volume_scale()
        for cx, cy, step in self._volume_controls():
            if abs(x - cx) <= 17 * factor and abs(y - cy) <= 16 * factor:
                return step
        return None

    def _draw_volume_controls(self, painter):
        photo_w, photo_h = self._photo_size()
        sx, sy = self.width() / photo_w, self.height() / photo_h
        factor = self._volume_scale()
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for cx, cy, step in self._volume_controls():
            # Clic: iluminar el contorno y hundir la flecha brevemente.
            active = self._volume_pressed == step
            painter.setBrush(QColor(45, 94, 58, 245) if active
                             else QColor(18, 22, 22, 215))
            painter.setPen(QColor(154, 255, 160) if active
                           else QColor(120, 135, 135, 210))
            painter.drawRoundedRect(
                QRectF((cx-13*factor)*sx, (cy-12*factor)*sy,
                       26*factor*sx, 24*factor*sy),
                4*factor*sx, 4*factor*sy)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(225, 255, 225) if active
                             else QColor(170, 235, 175))
            cy += 2*factor if active else 0
            if step > 0:
                points = ((cx, cy-6*factor),
                          (cx-7*factor, cy+5*factor),
                          (cx+7*factor, cy+5*factor))
            else:
                points = ((cx-7*factor, cy-5*factor),
                          (cx+7*factor, cy-5*factor),
                          (cx, cy+6*factor))
            painter.drawPolygon(
                QPolygonF([QPointF(x*sx, y*sy) for x,y in points]))
        painter.restore()

    def _draw_led(self, painter: QPainter):
        if self._orientation in MODERN_SKINS:
            return  # LED presente en las fotos nuevas.
        photo_w, photo_h = self._photo_size()
        sx = self.width() / photo_w
        sy = self.height() / photo_h
        cx, cy = led_center_for_mode(self._orientation)
        center = QPointF(cx * sx, cy * sy)
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(130, 255, 150, 55))
        painter.drawEllipse(center, 10 * sx, 10 * sy)
        painter.setBrush(QColor(90, 255, 120, 110))
        painter.drawEllipse(center, 6 * sx, 6 * sy)
        painter.setBrush(QColor(170, 255, 180, 230))
        painter.drawEllipse(center, 3.2 * sx, 3.2 * sy)
        painter.restore()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._draw_led(painter)
        self._draw_volume_controls(painter)
        if self._pressed and not self._skin_picture.isNull():
            rect = self._rect(self._pressed)
            path = self._path(self._pressed)
            if rect is not None and path is not None:
                painter.save()
                # La cruceta de PicoCalc no es rectangular. En las cuatro
                # flechas solo oscurecemos el polígono sin desplazar una
                # textura cuadrada que se saldría de los bordes reales.
                if self._zone(self._pressed).polygon:
                    painter.fillPath(path, QColor(0, 0, 0, 95))
                    painter.restore()
                    painter.end()
                    return
                painter.setClipPath(path)
                painter.fillPath(path, QColor(0, 0, 0, 135))
                dest = QRect(rect.x() + 2, rect.y() + 2, rect.width(), rect.height())
                scale_x = self._skin_picture.width() / self.width()
                scale_y = self._skin_picture.height() / self.height()
                source = QRect(round(rect.x() * scale_x), round(rect.y() * scale_y),
                               round(rect.width() * scale_x), round(rect.height() * scale_y))
                painter.drawPixmap(dest, self._skin_picture, source)
                painter.fillRect(dest, QColor(0, 0, 0, 35))
                painter.restore()
        painter.end()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        photo_w, photo_h = self._photo_size()
        x = event.position().x() * photo_w / self.width()
        y = event.position().y() * photo_h / self.height()
        delta = self._volume_hit(x, y)
        if delta is not None:
            self._volume_press_serial += 1
            serial = self._volume_press_serial
            self._volume_pressed = delta
            self.update()
            def release_volume():
                if self._volume_press_serial == serial:
                    self._volume_pressed = None
                    self.update()
            QTimer.singleShot(140, release_volume)
            self.volumeChange.emit(delta)
            event.accept()
            return
        name = (modern_key_at(x,y,self._orientation)
                if self._orientation in MODERN_SKINS
                else key_at(x,y,self._orientation))
        if name:
            self.flash_key(name)
            self.keyClicked.emit(name)
            event.accept()
        else:
            super().mousePressEvent(event)
