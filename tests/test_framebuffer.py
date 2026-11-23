from basic_cde.devices.framebuffer import Framebuffer


def test_pixels_and_clipping():
    fb = Framebuffer()
    assert fb.get_pixel(0, 0) == (0, 0, 0, 255)
    fb.pixel(319, 319, 4, 5, 6)
    fb.pixel(320, 0, 1, 2, 3)
    assert fb.get_pixel(319, 319) == (4, 5, 6, 255)
    assert len(fb.snapshot()) == 320 * 320 * 4
