"""The face oval from precomputed landmarks (see landmarks.py), and the filters
that keep edge strokes out of the face."""
from __future__ import annotations

import json

import numpy as np


def chain_connections(connections: list[tuple[int, int]], points: dict[int, tuple[float, float]]) -> list[np.ndarray]:
    """Order an edge list (pairs of landmark indices) into polylines of (x, y).
    Each connected component becomes one polyline; closed loops repeat their first point."""
    adj: dict[int, list[int]] = {}
    for a, b in connections:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    seen: set[int] = set()
    polys = []
    # open chains start at a degree-1 node; what remains are loops
    starts = sorted(adj, key=lambda n: (len(adj[n]) != 1, n))
    for s in starts:
        if s in seen:
            continue
        chain = [s]
        seen.add(s)
        cur, prev = s, None
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                # close the loop if the start is adjacent to the last node
                if len(chain) > 2 and s in adj[cur] and prev != s:
                    chain.append(s)
                break
            prev, cur = cur, nxt[0]
            chain.append(cur)
            seen.add(cur)
        polys.append(np.array([points[i] for i in chain], dtype=float))
    return polys


def _inside(poly: np.ndarray, p: np.ndarray) -> bool:
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xi:
                inside = not inside
    return inside


def outside_polygon(strokes: list[np.ndarray], polygon: np.ndarray, shrink: float = 1.0,
                    drop: float = 0.0) -> list[np.ndarray]:
    """Drop strokes whose centroid lies inside the polygon scaled by `shrink` about its
    centre, or inside that polygon shifted down by `drop` times its height (the neck,
    where the chin shadow would otherwise draw a second jaw)."""
    centre = polygon.mean(axis=0)
    poly = centre + (polygon - centre) * shrink
    polys = [poly]
    if drop > 0:
        height = poly[:, 1].max() - poly[:, 1].min()
        polys.append(poly + np.array([0.0, drop * height]))
    return [s for s in strokes if not any(_inside(p, s.mean(axis=0)) for p in polys)]


def cut_polygon(strokes: list[np.ndarray], polygon: np.ndarray, scale: float = 1.0,
                min_len: int = 15) -> list[np.ndarray]:
    """Cut strokes where they enter the polygon (scaled about its centre) and keep the
    outside pieces that are at least min_len points long."""
    centre = polygon.mean(axis=0)
    poly = centre + (polygon - centre) * scale
    out = []
    for s in strokes:
        inside = np.array([_inside(poly, p) for p in s] + [True])
        start = None
        for i, v in enumerate(inside):
            if not v and start is None:
                start = i
            elif v and start is not None:
                if i - start >= min_len:
                    out.append(s[start:i])
                start = None
    return out


def load_features(path: str) -> dict[str, np.ndarray]:
    """Read the landmarks JSON written by landmarks.py: {name: [[x, y], ...]} in pixels.
    Only "oval" is used; older files carry more keys."""
    with open(path) as f:
        raw = json.load(f)
    return {k: np.array(v, dtype=float) for k, v in raw.items()}
