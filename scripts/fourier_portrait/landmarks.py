"""One-off: detect face landmarks with mediapipe and write the face oval (pixel
coordinates) to a JSON file that the main pipeline reads with --landmarks.

    python -m scripts.fourier_portrait.landmarks src/assets/alex-sunset.jpg --model PATH/face_landmarker.task         --out scripts/fourier_portrait/landmarks.json

mediapipe and the model file are offline tools only; nothing here ships to the browser.
Model: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
"""
from __future__ import annotations

import argparse
import json

import numpy as np
from PIL import Image

from .features import chain_connections


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    import mediapipe as mp
    from mediapipe.tasks.python.vision import face_landmarker as fl

    rgb = np.asarray(Image.open(a.image).convert("RGB"))
    h, w = rgb.shape[:2]
    det = fl.FaceLandmarker.create_from_model_path(a.model)
    res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
    if not res.face_landmarks:
        raise SystemExit("no face found")
    lms = res.face_landmarks[0]
    pts = {i: (l.x * w, l.y * h) for i, l in enumerate(lms)}
    table = fl.FaceLandmarksConnections.FACE_LANDMARKS_FACE_OVAL
    polys = chain_connections([(c.start, c.end) for c in table], pts)
    oval = max(polys, key=len)
    with open(a.out, "w") as f:
        json.dump({"oval": oval.tolist()}, f)
    print(f"{len(lms)} landmarks -> {a.out}: oval with {len(oval)} points")


if __name__ == "__main__":
    main()
