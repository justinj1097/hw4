"""White-background display copies of product photos.

73 of the 102 catalogue photos were flattened onto pure black. The originals in data/products/ are left untouched;
this makes data/products_web/ copies where the black region connected to the image border is flood-filled white,
so the grid matches the store's white product shots. Garments are never recoloured unless they touch the border
and are within a few levels of pure black.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

BLACK_CORNERS = 20  # average corner brightness below this means a black background
FILL_THRESHOLD = 24


def _whiten(src: Path, dest: Path) -> None:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    corners = [img.getpixel(p) for p in [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)]]
    if sum(sum(c) for c in corners) / 12 < BLACK_CORNERS:
        step = max(1, min(w, h) // 40)
        seeds = [(x, 0) for x in range(0, w, step)] + [(x, h - 1) for x in range(0, w, step)]
        seeds += [(0, y) for y in range(0, h, step)] + [(w - 1, y) for y in range(0, h, step)]
        for seed in seeds:
            if sum(img.getpixel(seed)) < FILL_THRESHOLD * 3:
                ImageDraw.floodfill(img, seed, (255, 255, 255), thresh=FILL_THRESHOLD)
    img.save(dest, "JPEG", quality=90)


def ensure_web_images(src_dir: Path, out_dir: Path) -> Path:
    """Build any missing or outdated display copies; returns the folder to serve."""
    out_dir.mkdir(exist_ok=True)
    for src in src_dir.glob("*.jpg"):
        dest = out_dir / src.name
        if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
            _whiten(src, dest)
    return out_dir
