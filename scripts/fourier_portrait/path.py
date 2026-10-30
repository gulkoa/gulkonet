"""Turn a thinned edge map into one continuous closed path."""
from __future__ import annotations

import numpy as np

_OFFSETS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]


def _walk(start: tuple[int, int], remaining: set[tuple[int, int]]) -> list[tuple[int, int]]:
    stroke = [start]
    remaining.discard(start)
    y, x = start
    while True:
        nxt = None
        for dy, dx in _OFFSETS:
            cand = (y + dy, x + dx)
            if cand in remaining:
                nxt = cand
                break
        if nxt is None:
            return stroke
        stroke.append(nxt)
        remaining.discard(nxt)
        y, x = nxt


def chain_strokes(edges: np.ndarray, min_len: int = 8) -> list[np.ndarray]:
    """Walk 8-connected edge pixels into strokes of (x, y) points."""
    remaining = set(zip(*np.nonzero(edges)))
    remaining = {(int(y), int(x)) for y, x in remaining}

    def degree(p):
        return sum((p[0] + dy, p[1] + dx) in remaining for dy, dx in _OFFSETS)

    strokes: list[np.ndarray] = []
    # endpoints first, so open lines are walked end to end
    for p in sorted(remaining):
        if p in remaining and degree(p) == 1:
            s = _walk(p, remaining)
            strokes.append(s)
    # whatever is left belongs to loops or was consumed
    while remaining:
        p = min(remaining)
        strokes.append(_walk(p, remaining))
    out = []
    for s in strokes:
        if len(s) >= min_len:
            out.append(np.array([(x, y) for y, x in s], dtype=float))
    return out

def order_strokes(strokes: list[np.ndarray]) -> tuple[np.ndarray, list[tuple[float, float]]]:
    """Greedy nearest-endpoint ordering (reversing strokes when their far end is nearer),
    improved with 2-opt. Returns the closed path and the pen-up intervals of its jumps."""
    if not strokes:
        return np.zeros((0, 2)), []
    pool = sorted(strokes, key=len, reverse=True)
    chain = [pool.pop(0)]
    cur = chain[-1][-1]
    while pool:
        best_i, best_d, best_rev = 0, np.inf, False
        for i, s in enumerate(pool):
            d0 = np.linalg.norm(s[0] - cur)
            d1 = np.linalg.norm(s[-1] - cur)
            if d0 < best_d:
                best_i, best_d, best_rev = i, d0, False
            if d1 < best_d:
                best_i, best_d, best_rev = i, d1, True
        s = pool.pop(best_i)
        if best_rev:
            s = s[::-1]
        chain.append(s)
        cur = s[-1]
    chain = improve_order(chain)
    path = np.vstack(chain)
    return np.vstack([path, path[:1]]), pen_up_intervals(chain)


def pen_up_intervals(seq: list[np.ndarray]) -> list[tuple[float, float]]:
    """For an ordered closed tour of strokes, the jumps between consecutive strokes
    (and from the last back to the first) as (t0, t1) fractions of total arc length."""
    lengths = [float(np.linalg.norm(np.diff(s, axis=0), axis=1).sum()) for s in seq]
    jumps = [float(np.linalg.norm(seq[(i + 1) % len(seq)][0] - seq[i][-1])) for i in range(len(seq))]
    total = sum(lengths) + sum(jumps)
    out = []
    t = 0.0
    for ln, jp in zip(lengths, jumps):
        t += ln
        if jp > 0:
            out.append((t / total, (t + jp) / total))
        t += jp
    return out


def improve_order(seq: list[np.ndarray], max_rounds: int = 50) -> list[np.ndarray]:
    """2-opt on the closed tour of strokes: reverse a sub-sequence (and each stroke
    inside it) whenever that shortens the two jumps it touches."""
    seq = list(seq)
    n = len(seq)
    if n < 3:
        return seq

    def jump(a, b):
        return float(np.linalg.norm(b[0] - a[-1]))

    for _ in range(max_rounds):
        improved = False
        # seq[0] stays pinned: i starts at 1, so the degenerate whole-tour reversal never occurs
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                a, b = seq[i - 1], seq[i]
                c, d = seq[j], seq[(j + 1) % n]
                if d is a:
                    continue
                before = jump(a, b) + jump(c, d)
                after = jump(a, c[::-1]) + jump(b[::-1], d)
                if after + 1e-9 < before:
                    seq[i:j + 1] = [s[::-1] for s in reversed(seq[i:j + 1])]
                    improved = True
        if not improved:
            break
    return seq


def resample(path: np.ndarray, m: int) -> np.ndarray:
    """Resample a closed path to m points evenly spaced by arc length."""
    if not np.allclose(path[0], path[-1]):
        path = np.vstack([path, path[:1]])
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    t = np.linspace(0.0, total, m, endpoint=False)
    x = np.interp(t, cum, path[:, 0])
    y = np.interp(t, cum, path[:, 1])
    return np.stack([x, y], axis=1)


def smooth(path: np.ndarray, window: int) -> np.ndarray:
    """Circular moving average over the path points."""
    if window <= 1:
        return path.copy()
    kernel = np.ones(window) / window
    out = np.empty_like(path, dtype=float)
    for c in range(path.shape[1]):
        padded = np.concatenate([path[-(window // 2):, c], path[:, c], path[: window - window // 2 - 1, c]])
        out[:, c] = np.convolve(padded, kernel, mode="valid")
    return out

def focus_select(strokes: list[np.ndarray], n: int, size: tuple[int, int],
                 focus: tuple[float, float, float] | None = None) -> list[np.ndarray]:
    """Keep the n highest-scoring strokes. Score is length, times exp(-(d/r)^2) when
    focus=(fx, fy, r) is given, d being the centroid's distance from (fx, fy) in
    image-fraction coordinates. size is (width, height) in pixels. n <= 0 keeps all."""
    if n <= 0:
        return strokes
    w, h = size

    def score(s: np.ndarray) -> float:
        if focus is None:
            return float(len(s))
        fx, fy, r = focus
        cx, cy = s.mean(axis=0)
        d = np.hypot(cx / w - fx, cy / h - fy)
        return len(s) * float(np.exp(-((d / r) ** 2)))

    return sorted(strokes, key=score, reverse=True)[:n]
