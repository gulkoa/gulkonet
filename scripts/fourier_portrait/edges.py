"""Edge extraction with numpy/scipy/Pillow only."""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage


def load_gray(path: str) -> np.ndarray:
    """Load an image as float32 grayscale in 0..1 (H x W)."""
    im = Image.open(path).convert("L")
    return np.asarray(im, dtype=np.float32) / 255.0


def load_mask(path: str, shape: tuple[int, int]) -> np.ndarray:
    """Load a mask image (white = keep) as a bool array of the given (H, W)."""
    im = Image.open(path).convert("L")
    h, w = shape
    if im.size != (w, h):
        im = im.resize((w, h), Image.NEAREST)
    return np.asarray(im) > 127


def edge_map(
    gray: np.ndarray,
    sigma: float,
    low: float,
    high: float,
    mask: np.ndarray | None,
) -> np.ndarray:
    """Blur, Sobel gradient magnitude, hysteresis threshold, optional mask."""
    blurred = ndimage.gaussian_filter(gray, sigma)
    gx = ndimage.sobel(blurred, axis=1)
    gy = ndimage.sobel(blurred, axis=0)
    mag = np.hypot(gx, gy)
    mag = _non_max_suppress(mag, gx, gy)
    strong = mag > high
    weak = mag > low
    labels, _ = ndimage.label(weak, structure=np.ones((3, 3), int))
    keep_labels = np.unique(labels[strong])
    keep_labels = keep_labels[keep_labels != 0]
    edges = np.isin(labels, keep_labels)
    if mask is not None:
        edges &= mask
    return edges


def _non_max_suppress(mag: np.ndarray, gx: np.ndarray, gy: np.ndarray) -> np.ndarray:
    """Keep only pixels that are maximal along their gradient direction (Canny step)."""
    angle = np.mod(np.degrees(np.arctan2(gy, gx)), 180.0)
    p = np.pad(mag, 1)
    n = p[:-2, 1:-1]; s_ = p[2:, 1:-1]
    e = p[1:-1, 2:]; w = p[1:-1, :-2]
    ne = p[:-2, 2:]; sw = p[2:, :-2]
    nw = p[:-2, :-2]; se = p[2:, 2:]
    horiz = (angle < 22.5) | (angle >= 157.5)
    diag1 = (angle >= 22.5) & (angle < 67.5)
    vert = (angle >= 67.5) & (angle < 112.5)
    diag2 = (angle >= 112.5) & (angle < 157.5)
    a = np.where(horiz, e, np.where(diag1, se, np.where(vert, s_, sw)))
    b = np.where(horiz, w, np.where(diag1, nw, np.where(vert, n, ne)))
    keep = (mag >= a) & (mag >= b)
    return np.where(keep, mag, 0.0)


def _neighbours(img: np.ndarray):
    p = np.pad(img, 1).astype(np.uint8)
    p2 = p[:-2, 1:-1]
    p3 = p[:-2, 2:]
    p4 = p[1:-1, 2:]
    p5 = p[2:, 2:]
    p6 = p[2:, 1:-1]
    p7 = p[2:, :-2]
    p8 = p[1:-1, :-2]
    p9 = p[:-2, :-2]
    return p2, p3, p4, p5, p6, p7, p8, p9


def thin(edges: np.ndarray) -> np.ndarray:
    """Zhang-Suen thinning to one-pixel-wide lines (pure numpy)."""
    img = edges.astype(np.uint8).copy()
    while True:
        changed = False
        for step in (0, 1):
            p2, p3, p4, p5, p6, p7, p8, p9 = _neighbours(img)
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            b = sum(seq[:8]).astype(np.int32)
            a = np.zeros_like(b)
            for i in range(8):
                a += ((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.int32)
            if step == 0:
                c1 = (p2 * p4 * p6) == 0
                c2 = (p4 * p6 * p8) == 0
            else:
                c1 = (p2 * p4 * p8) == 0
                c2 = (p2 * p6 * p8) == 0
            remove = (img == 1) & (b >= 2) & (b <= 6) & (a == 1) & c1 & c2
            if remove.any():
                img[remove] = 0
                changed = True
        if not changed:
            break
    return img.astype(bool)


def prune(edges: np.ndarray, iterations: int) -> np.ndarray:
    """Remove endpoint pixels `iterations` times, deleting spurs up to that length."""
    img = edges.astype(np.uint8).copy()
    for _ in range(iterations):
        seq = list(_neighbours(img))
        seq.append(seq[0])
        b = sum(seq[:8]).astype(np.int32)
        a = np.zeros_like(b)
        for i in range(8):
            a += ((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.int32)
        # one contiguous run of at most three neighbours: a line tip or a bump on a line
        tips = (img == 1) & (a == 1) & (b >= 1) & (b <= 3)
        if not tips.any():
            break
        img[tips] = 0
    return img.astype(bool)


def mask_outline(mask: np.ndarray) -> np.ndarray:
    """One-pixel silhouette of the mask: mask pixels whose 4-neighbourhood leaves the mask."""
    # border_value=1 so a subject touching the frame edge gets no outline along that edge
    eroded = ndimage.binary_erosion(mask, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]), border_value=1)
    return thin(mask & ~eroded)
