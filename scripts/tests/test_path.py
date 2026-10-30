import numpy as np

from scripts.fourier_portrait.path import chain_strokes, order_strokes, resample, smooth


def test_chain_strokes_walks_a_line_into_one_stroke():
    e = np.zeros((20, 20), bool)
    e[10, 2:18] = True
    strokes = chain_strokes(e, min_len=4)
    assert len(strokes) == 1 and len(strokes[0]) == 16
    assert strokes[0][0].tolist() in ([2, 10], [17, 10])


def test_chain_strokes_drops_short_strokes():
    e = np.zeros((20, 20), bool)
    e[10, 2:18] = True
    e[3, 3:5] = True
    assert len(chain_strokes(e, min_len=4)) == 1


def test_order_strokes_reverses_to_nearest_endpoint():
    a = np.array([[0, 0], [10, 0]], float)      # longest, starts chain
    b = np.array([[30, 0], [12, 0]], float)     # its far end is nearer to (10,0)
    p, lifts = order_strokes([a, b])
    assert p[:4].tolist() == [[0, 0], [10, 0], [12, 0], [30, 0]]
    assert p[-1].tolist() == [0, 0]            # closed
    assert len(lifts) == 2                     # the jump 10->12 and the closing jump 30->0


def test_resample_is_even_and_closed():
    sq = np.array([[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], float)
    r = resample(sq, 40)
    assert r.shape == (40, 2)
    seg = np.linalg.norm(np.diff(np.vstack([r, r[:1]]), axis=0), axis=1)
    assert np.allclose(seg, 1.0, atol=1e-6)


def test_smooth_preserves_shape_and_mean():
    p = np.random.default_rng(0).random((50, 2))
    s = smooth(p, 5)
    assert s.shape == p.shape and np.allclose(s.mean(0), p.mean(0))

def jump_length(path, breaks):
    return sum(np.linalg.norm(path[b] - path[b - 1]) for b in breaks)


def test_improve_order_never_increases_total_jump_length():
    from scripts.fourier_portrait.path import improve_order
    rng = np.random.default_rng(1)
    strokes = [rng.random((5, 2)) * 100 + rng.random(2) * 1000 for _ in range(12)]

    def total_jumps(seq):
        return sum(np.linalg.norm(seq[i + 1][0] - seq[i][-1]) for i in range(len(seq) - 1)) \
            + np.linalg.norm(seq[0][0] - seq[-1][-1])

    greedy = sorted(strokes, key=len)  # arbitrary order
    better = improve_order(greedy)
    assert len(better) == len(greedy)
    assert total_jumps(better) <= total_jumps(greedy)
    # every original stroke is present, possibly reversed
    for s in strokes:
        assert any(np.array_equal(s, b) or np.array_equal(s[::-1], b) for b in better)

def test_improve_order_leaves_an_optimal_tour_unchanged():
    from scripts.fourier_portrait.path import improve_order
    # short strokes laid head-to-tail around a circle: already the best tour
    strokes = []
    for i in range(8):
        a = 2 * np.pi * i / 8
        b = a + 0.3
        strokes.append(np.array([[np.cos(a), np.sin(a)], [np.cos(b), np.sin(b)]]) * 100)
    for rounds in (1, 2, 50):
        out = improve_order(strokes, max_rounds=rounds)
        assert all(np.array_equal(a, b) for a, b in zip(strokes, out)), rounds

def test_focus_select_prefers_strokes_near_the_focus():
    from scripts.fourier_portrait.path import focus_select
    near = np.array([[45.0, 33.0]] * 10)        # short, on the focus point
    far = np.array([[95.0, 95.0]] * 100)        # long, in the far corner
    picked = focus_select([far, near], 1, (100, 100), (0.45, 0.33, 0.2))
    assert len(picked) == 1 and picked[0] is near


def test_focus_select_with_no_limit_keeps_all():
    from scripts.fourier_portrait.path import focus_select
    strokes = [np.zeros((n, 2)) for n in (5, 50)]
    assert focus_select(strokes, 0, (100, 100), (0.5, 0.5, 0.3)) == strokes

def test_pen_up_intervals_marks_the_jumps_between_strokes_as_fractions_of_arc_length():
    from scripts.fourier_portrait.path import pen_up_intervals
    a = np.array([[0.0, 0.0], [10.0, 0.0]])          # 10 long
    b = np.array([[20.0, 0.0], [30.0, 0.0]])         # jump 10, 10 long, jump 30 back to start
    lifts = pen_up_intervals([a, b])
    assert [(round(t0, 3), round(t1, 3)) for t0, t1 in lifts] == [(0.167, 0.333), (0.5, 1.0)]


def test_focus_select_without_focus_keeps_the_longest():
    from scripts.fourier_portrait.path import focus_select
    strokes = [np.zeros((n, 2)) for n in (5, 50, 20)]
    assert [len(s) for s in focus_select(strokes, 2, (100, 100))] == [50, 20]
