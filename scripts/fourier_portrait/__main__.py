"""Photo -> one continuous path -> Fourier coefficients JSON.

Usage:
    python -m scripts.fourier_portrait <image> --mask mask.png --landmarks landmarks.json --out src/data/fourier-portrait.json
        [--k 700] [--m 20000] [--sigma 1.5] [--low 0.05] [--high 0.12] [--min-len 12] [--smooth 3] [--prune 6]
        [--max-strokes 320] [--focus FX,FY,R] [--face-shrink 0.9] [--neck-drop 0.35] [--face-cut 1.15]
        [--color #rrggbb] [--previews DIR]

The drawing is one closed tour of edge strokes plus the mask silhouette; the jumps
between strokes are recorded so the browser lifts the pen there. With --landmarks the
face oval is cleared of strokes and the photo supplies the face when it fades in.
"""
from __future__ import annotations

import argparse
import os

from .edges import edge_map, load_gray, load_mask, mask_outline, prune, thin
from .features import cut_polygon, load_features, outside_polygon
from .fourier import coefficients, normalize, reconstruct, write_paths_json
from .path import chain_strokes, focus_select, order_strokes, resample, smooth
from .preview import render_many


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--mask", help="subject mask PNG (white = keep); its outline becomes a stroke")
    ap.add_argument("--landmarks", help="JSON from landmarks.py; strokes inside its face oval are removed")
    ap.add_argument("--out", required=True)
    ap.add_argument("--k", type=int, default=700, help="number of circles")
    ap.add_argument("--m", type=int, default=20000, help="points along the path")
    ap.add_argument("--sigma", type=float, default=1.5)
    ap.add_argument("--low", type=float, default=0.05)
    ap.add_argument("--high", type=float, default=0.12)
    ap.add_argument("--min-len", type=int, default=12)
    ap.add_argument("--smooth", type=int, default=3)
    ap.add_argument("--prune", type=int, default=6, help="spur length to remove after thinning")
    ap.add_argument("--max-strokes", type=int, default=0, help="keep only the N best strokes (0 = all)")
    ap.add_argument("--focus", help="FX,FY,R: rank strokes by length weighted by distance from (FX, FY) "
                    "(image fractions) with Gaussian radius R, instead of raw length")
    ap.add_argument("--face-shrink", type=float, default=0.9, help="scale of the face oval whose inside is cleared")
    ap.add_argument("--neck-drop", type=float, default=0.0, help="also clear the oval shifted down by this fraction of its height")
    ap.add_argument("--face-cut", type=float, default=0.0, help="cut strokes where they enter the oval scaled by this factor (0 = keep)")
    ap.add_argument("--color", default="ink", help="line colour: 'ink' (page colour) or #rrggbb")
    ap.add_argument("--previews", help="directory for path.png and recon.png")
    a = ap.parse_args()

    gray = load_gray(a.image)
    h, w = gray.shape
    mask = load_mask(a.mask, (h, w)) if a.mask else None
    edges = prune(thin(edge_map(gray, a.sigma, a.low, a.high, mask)), a.prune)
    strokes = chain_strokes(edges, a.min_len)
    silhouette = chain_strokes(mask_outline(mask), a.min_len) if mask is not None else []

    oval = load_features(a.landmarks)["oval"] if a.landmarks else None
    if oval is not None:
        strokes = outside_polygon(strokes, oval, a.face_shrink, a.neck_drop)
    focus = tuple(float(v) for v in a.focus.split(",")) if a.focus else None
    strokes = focus_select(strokes, a.max_strokes, (w, h), focus)
    if oval is not None and a.face_cut > 0:
        strokes = cut_polygon(strokes, oval, a.face_cut, a.min_len)
        silhouette = cut_polygon(silhouette, oval, a.face_cut, a.min_len)

    path, lifts = order_strokes(strokes + silhouette)
    unit = normalize(smooth(resample(path, a.m), a.smooth), w, h)
    coeffs = coefficients(unit, a.k)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    write_paths_json([(a.color, coeffs, lifts)], a.m, a.out)
    print(f"edges={int(edges.sum())} strokes={len(strokes) + len(silhouette)} lifts={len(lifts)} k={a.k} -> {a.out}")

    if a.previews:
        os.makedirs(a.previews, exist_ok=True)
        render_many([unit], [a.color], 1000, os.path.join(a.previews, "path.png"))
        render_many([reconstruct(coeffs, a.m)], [a.color], 1000, os.path.join(a.previews, "recon.png"))
        print(f"previews -> {a.previews}")


if __name__ == "__main__":
    main()
