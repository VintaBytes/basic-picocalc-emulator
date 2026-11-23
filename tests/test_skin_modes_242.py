from pathlib import Path

from basic_cde.gui.skin_keys import KEY_ZONES


def test_arrow_keys_use_polygons_not_plain_rectangles():
    lookup = {zone.name: zone for zone in KEY_ZONES}
    for name in ('Up', 'Down', 'Left', 'Right'):
        assert lookup[name].polygon


def test_window_starts_in_vertical_skin_and_supports_horizontal():
    source = (Path(__file__).parents[1] / 'src/basic_cde/gui/window.py').read_text(encoding='utf-8')
    assert "self.display_mode = 'skin-vertical'" in source
    assert 'def enable_skin_vertical(self):' in source
    assert 'def enable_skin_horizontal(self):' in source
    assert "self._enable_skin('horizontal')" in source
