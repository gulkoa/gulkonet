import numpy as np

from scripts.fourier_portrait.features import chain_connections, outside_polygon


def test_chain_connections_orders_an_open_chain():
    pts = {0: (0.0, 0.0), 1: (1.0, 0.0), 2: (2.0, 0.0), 3: (3.0, 0.0)}
    polys = chain_connections([(2, 3), (0, 1), (1, 2)], pts)
    assert len(polys) == 1
    assert polys[0].tolist() in ([[0, 0], [1, 0], [2, 0], [3, 0]], [[3, 0], [2, 0], [1, 0], [0, 0]])


def test_chain_connections_closes_a_loop():
    pts = {0: (0.0, 0.0), 1: (1.0, 0.0), 2: (1.0, 1.0), 3: (0.0, 1.0)}
    polys = chain_connections([(0, 1), (1, 2), (2, 3), (3, 0)], pts)
    assert len(polys) == 1 and len(polys[0]) == 5
    assert np.allclose(polys[0][0], polys[0][-1])


def test_chain_connections_splits_disjoint_pieces():
    pts = {i: (float(i), 0.0) for i in range(6)}
    polys = chain_connections([(0, 1), (1, 2), (4, 5)], pts)
    assert sorted(len(p) for p in polys) == [2, 3]


def test_outside_polygon_drops_strokes_whose_centroid_is_inside():
    square = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    inside = np.array([[4.0, 4.0], [6.0, 6.0]])
    outside = np.array([[20.0, 20.0], [22.0, 22.0]])
    kept = outside_polygon([inside, outside], square)
    assert len(kept) == 1 and kept[0] is outside


def test_outside_polygon_shrink_keeps_strokes_near_the_edge():
    square = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    rim = np.array([[0.5, 5.0], [1.0, 5.0]])
    assert outside_polygon([rim], square, shrink=1.0) == []
    assert outside_polygon([rim], square, shrink=0.8) == [rim]

def test_outside_polygon_drop_also_excludes_the_band_below_the_polygon():
    from scripts.fourier_portrait.features import outside_polygon
    square = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    below = np.array([[5.0, 12.0], [5.0, 13.0]])     # just under the chin
    far_below = np.array([[5.0, 30.0], [5.0, 31.0]])
    assert outside_polygon([below, far_below], square, shrink=1.0) == [below, far_below]
    assert outside_polygon([below, far_below], square, shrink=1.0, drop=0.5) == [far_below]


def test_cut_polygon_keeps_only_the_pieces_outside_the_polygon():
    from scripts.fourier_portrait.features import cut_polygon
    square = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    line = np.array([[float(x), 5.0] for x in range(-10, 21)])   # crosses the square
    pieces = cut_polygon([line], square, scale=1.0, min_len=3)
    assert len(pieces) == 2
    assert all((p[:, 0] <= 0).all() or (p[:, 0] >= 10).all() for p in pieces)   # boundary points count as outside
    assert cut_polygon([line], square, scale=1.0, min_len=20) == []
