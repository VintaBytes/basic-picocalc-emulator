"""Cruceta en fotografías actuales: cada dirección tiene región propia."""
import pytest
from basic_cde.gui.skin_modern import ARROW_POLYGONS, modern_key_at, modern_key_zones, KEY_TRANSFORMS

# Puntos centrales del interior de las teclas, medidos en píxeles de foto.
POINTS = {
    'vertical': {'Up': (173, 855), 'Left': (112, 922),
                 'Right': (236, 922), 'Down': (173, 978)},
    'horizontal': {'Up': (1017, 196), 'Left': (961, 254),
                   'Right': (1075, 253), 'Down': (1018, 313)},
}

@pytest.mark.parametrize('mode', ['vertical', 'horizontal'])
def test_each_arrow_region_matches_the_photo(mode):
    regions = {zone.name: zone for zone in modern_key_zones(mode)}
    for name, point in POINTS[mode].items():
        assert regions[name].polygon == ARROW_POLYGONS[mode][name]
        assert modern_key_at(*point, mode) == name


def test_horizontal_non_arrow_alignment_corrected_without_touching_vertical():
    assert KEY_TRANSFORMS['horizontal'] == (1.29, 1.23, 770, -681)
    assert KEY_TRANSFORMS['vertical'] == (1.253, 1.225, -54, -25)


def test_screen_only_skins_do_not_have_virtual_arrow_regions():
    assert modern_key_zones('large') == ()
    assert modern_key_zones('compact') == ()
