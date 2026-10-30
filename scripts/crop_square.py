"""Crop a square region out of a photo and resize it.

Usage:
    python scripts/crop_square.py <in> <out> --left L --top T --size S [--resize N]
"""
import argparse

from PIL import Image


def crop_square(src: str, dst: str, left: int, top: int, size: int, resize: int) -> None:
    im = Image.open(src).convert("RGB")
    box = (left, top, left + size, top + size)
    if box[2] > im.width or box[3] > im.height or left < 0 or top < 0:
        raise SystemExit(f"crop box {box} exceeds image size {im.size}")
    out = im.crop(box).resize((resize, resize), Image.LANCZOS)
    out.save(dst, quality=90)
    print(f"wrote {dst} ({resize}x{resize}) from box {box}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--left", type=int, required=True)
    ap.add_argument("--top", type=int, required=True)
    ap.add_argument("--size", type=int, required=True)
    ap.add_argument("--resize", type=int, default=1000)
    a = ap.parse_args()
    crop_square(a.src, a.dst, a.left, a.top, a.size, a.resize)


if __name__ == "__main__":
    main()
