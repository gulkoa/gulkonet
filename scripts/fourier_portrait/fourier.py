"""Fourier coefficients of a closed path, and the JSON the component consumes."""
from __future__ import annotations

import json

import numpy as np


def normalize(path: np.ndarray, width: int, height: int) -> np.ndarray:
    """Image-frame pixels -> unit box: x/width - 0.5, y/height - 0.5."""
    out = np.empty_like(path, dtype=float)
    out[:, 0] = path[:, 0] / width - 0.5
    out[:, 1] = path[:, 1] / height - 0.5
    return out


def _freqs(k: int) -> range:
    return range(-(k // 2), k - k // 2)


def coefficients(path: np.ndarray, k: int) -> list[tuple[int, float, float]]:
    """(freq, re, im) for freqs -k//2..k//2, sorted by amplitude descending."""
    z = path[:, 0] + 1j * path[:, 1]
    m = len(z)
    spectrum = np.fft.fft(z) / m
    coeffs = []
    for f in _freqs(k):
        c = spectrum[f % m]
        coeffs.append((int(f), float(c.real), float(c.imag)))
    coeffs.sort(key=lambda c: -np.hypot(c[1], c[2]))
    return coeffs


def reconstruct(coeffs, m: int) -> np.ndarray:
    """Evaluate the truncated series at m evenly spaced phases."""
    t = np.linspace(0.0, 1.0, m, endpoint=False)
    z = np.zeros(m, dtype=complex)
    for f, re, im in coeffs:
        z += (re + 1j * im) * np.exp(2j * np.pi * f * t)
    return np.stack([z.real, z.imag], axis=1)

def write_paths_json(paths, m: int, out_path: str) -> None:
    """paths: list of (color, coeffs[, lifts]); color is "#rrggbb" or "ink", lifts are
    (t0, t1) phase intervals where the pen is up. Writes {m, k, paths:[{color, coeffs[, lifts]}]}"""
    entries = []
    for p in paths:
        color, coeffs = p[0], p[1]
        e = {"color": color, "coeffs": [[int(f), round(re, 6), round(im, 6)] for f, re, im in coeffs]}
        if len(p) > 2 and p[2]:
            e["lifts"] = [[round(t0, 6), round(t1, 6)] for t0, t1 in p[2]]
        entries.append(e)
    data = {"m": int(m), "k": int(sum(len(e["coeffs"]) for e in entries)), "paths": entries}
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, separators=(",", ":"))
