"""Regresion de controles de volumen en las cuatro skins modernas."""

import os

# Permite ejecutar pruebas Qt sin escritorio gráfico.
if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication
from basic_cde.gui.skin_widget import SkinKeyboard
from basic_cde.gui.skin_modern import MODERN_SKINS, modern_skin_layout


POSITIONS = {
    "vertical": ((38, 202, +1), (38, 257, -1)),
    "horizontal": ((41, 186, +1), (41, 241, -1)),
    "compact": ((52, 256, +1), (52, 336, -1)),
    "large": ((26, 163, +1), (26, 211, -1)),
}


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.mark.parametrize("mode", POSITIONS)
def test_volume_controls_present(qt_app, mode):
    widget = SkinKeyboard()
    widget.set_orientation(mode)

    assert mode in MODERN_SKINS
    assert widget._volume_controls() == POSITIONS[mode]
    assert len(widget._volume_controls()) == 2


@pytest.mark.parametrize("mode", POSITIONS)
def test_volume_hit_regions(qt_app, mode):
    widget = SkinKeyboard()
    widget.set_orientation(mode)

    layout = modern_skin_layout(mode)
    widget.resize(layout.host_width, layout.host_height)

    for x, y, direction in POSITIONS[mode]:
        assert widget._volume_hit(x, y) == direction


@pytest.mark.parametrize("mode", POSITIONS)
def test_volume_visual_size(qt_app, mode):
    widget = SkinKeyboard()
    widget.set_orientation(mode)

    layout = modern_skin_layout(mode)
    widget.resize(layout.host_width, layout.host_height)

    photo_width = MODERN_SKINS[mode][0][0]
    factor = widget._volume_scale()

    displayed_width = 26 * factor * widget.width() / photo_width

    assert 15 <= displayed_width <= 17
