import numpy as np

from scripts.fourier_portrait.edges import edge_map, thin


def ring_image(size=64, r_in=18, r_out=22):
    yy, xx = np.mgrid[:size, :size]
    d = np.hypot(xx - size / 2, yy - size / 2)
    return ((d > r_in) & (d < r_out)).astype(np.float32)


def test_edge_map_finds_ring_edges_only():
    e = edge_map(ring_image(), sigma=1.0, low=0.05, high=0.2, mask=None)
    yy, xx = np.nonzero(e)
    d = np.hypot(xx - 32, yy - 32)
    assert len(d) > 50
    assert np.all((d > 14) & (d < 26))


def test_edge_map_is_thin_at_intensity_transitions():
    # two rims at r=18 and r=22: about 2*pi*(18+22) ~ 250 pixels, not a filled band
    e = edge_map(ring_image(), sigma=1.0, low=0.05, high=0.2, mask=None)
    assert 150 < e.sum() < 400


def test_edge_map_respects_mask():
    mask = np.zeros((64, 64), bool)
    mask[:, :32] = True
    e = edge_map(ring_image(), sigma=1.0, low=0.05, high=0.2, mask=mask)
    assert e[:, 32:].sum() == 0 and e[:, :32].sum() > 0


def test_thin_makes_one_pixel_lines():
    from scipy import ndimage
    e = ndimage.binary_dilation(edge_map(ring_image(), sigma=1.0, low=0.05, high=0.2, mask=None))
    t = thin(e)
    assert 0 < t.sum() < e.sum()
    # no 2x2 fully-set block remains
    blocks = t[:-1, :-1] & t[1:, :-1] & t[:-1, 1:] & t[1:, 1:]
    assert blocks.sum() == 0


def test_prune_removes_short_spurs_but_keeps_loop():
    from scripts.fourier_portrait.edges import prune
    e = np.zeros((30, 30), bool)
    # a square loop
    e[5, 5:25] = True; e[24, 5:25] = True; e[5:25, 5] = True; e[5:25, 24] = True
    loop_count = e.sum()
    # a 3-pixel spur hanging off the top edge
    e[2:5, 15] = True
    p = prune(e, iterations=4)
    assert p.sum() == loop_count
    assert not p[2:5, 15].any()


def test_mask_outline_is_a_thin_ring_inside_the_mask():
    from scripts.fourier_portrait.edges import mask_outline
    mask = np.zeros((64, 64), bool)
    yy, xx = np.mgrid[:64, :64]
    mask[np.hypot(xx - 32, yy - 32) < 20] = True
    o = mask_outline(mask)
    assert o.sum() > 80
    assert (o & ~mask).sum() == 0
    d = np.hypot(xx - 32, yy - 32)[o]
    assert np.all(d > 17) and np.all(d < 20.5)


def test_mask_outline_ignores_the_image_border():
    from scripts.fourier_portrait.edges import mask_outline
    mask = np.zeros((40, 40), bool)
    mask[20:, 10:30] = True          # a block touching the bottom edge
    o = mask_outline(mask)
    assert o[39, 11:29].sum() == 0   # no line along the frame edge (side edges may reach the corners)
    assert o[20, 10:30].sum() > 10   # the real top edge is there
