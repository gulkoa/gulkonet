"""Render a unit-box path to a PNG for eyeballing."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

def render_many(paths, colors, size: int, out_path: str) -> None:
    """Draw several unit-box paths; a colour of None or "ink" draws black."""
    im = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(im)
    for path, color in zip(paths, colors):
        pts = [((x + 0.5) * size, (y + 0.5) * size) for x, y in path]
        fill = "black" if color in (None, "ink") else color
        if len(pts) > 1:
            draw.line(pts + pts[:1], fill=fill, width=2, joint="curve")
    im.save(out_path)
