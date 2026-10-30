import json

import numpy as np

from scripts.fourier_portrait.fourier import coefficients, normalize, reconstruct, write_paths_json


def unit_circle(m=256):
    t = np.linspace(0, 2 * np.pi, m, endpoint=False)
    return np.stack([np.cos(t), np.sin(t)], 1) * 0.4


def test_normalize_maps_image_frame_to_unit_box():
    p = normalize(np.array([[0, 0], [100, 50]], float), 100, 50)
    assert p.tolist() == [[-0.5, -0.5], [0.5, 0.5]]


def test_circle_has_single_dominant_coefficient_at_freq_1():
    c = coefficients(unit_circle(), k=21)
    assert len(c) == 21
    f, re, im = c[0]
    assert f == 1 and abs(re - 0.4) < 1e-6 and abs(im) < 1e-6
    assert abs(c[1][1]) < 1e-6 and abs(c[1][2]) < 1e-6


def test_reconstruct_round_trips_circle():
    p = unit_circle()
    r = reconstruct(coefficients(p, k=21), 256)
    assert np.allclose(r, p, atol=1e-6)

def test_write_paths_json_shape(tmp_path):
    out = tmp_path / "p.json"
    paths = [("#112233", coefficients(unit_circle(), k=5)), ("#445566", coefficients(unit_circle(), k=3))]
    write_paths_json(paths, 256, str(out))
    d = json.loads(out.read_text())
    assert d["m"] == 256 and d["k"] == 8
    assert [p["color"] for p in d["paths"]] == ["#112233", "#445566"]
    assert [len(p["coeffs"]) for p in d["paths"]] == [5, 3]
    assert all(len(c) == 3 and isinstance(c[0], int) for p in d["paths"] for c in p["coeffs"])

def test_write_paths_json_carries_lifts(tmp_path):
    import json
    out = tmp_path / "p.json"
    write_paths_json([("#123456", [(1, 0.5, 0.0)], [(0.1, 0.2)])], 100, str(out))
    d = json.loads(out.read_text())
    assert d["paths"][0]["lifts"] == [[0.1, 0.2]]
    write_paths_json([("ink", [(1, 0.5, 0.0)])], 100, str(out))
    assert "lifts" not in json.loads(out.read_text())["paths"][0]
