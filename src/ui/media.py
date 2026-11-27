"""Images: logo, lovebird mascot and destination pictures.

A destination shows its uploaded photo (assets/destinations/<file>) when one is
set in the 'afbeelding' column, otherwise its generated illustration.
"""

import base64
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from src import config
from src.illustrations import destination_svg

LOGO = config.ASSETS_DIR / "orange_travel_logo_cropped.png"
LOVEBIRD = config.ASSETS_DIR / "lovebird.png"
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
ALLOWED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]


@lru_cache(maxsize=128)
def _file_uri(path: str, mtime: float) -> str:
    """Base64 data URI of an image file (mtime in the key refreshes the cache after an upload)."""
    file = Path(path)
    data = base64.b64encode(file.read_bytes()).decode("ascii")
    return f"data:{MIME.get(file.suffix.lower(), 'image/png')};base64,{data}"


def file_uri(path: Path) -> str:
    return _file_uri(str(path), path.stat().st_mtime) if path.exists() else ""


def svg_uri(svg: str) -> str:
    return "data:image/svg+xml;utf8," + quote(svg)


def uploaded_image_path(image_name: str | None) -> Path | None:
    """Path of an uploaded destination image, or None if not set / missing."""
    if not image_name:
        return None
    path = config.DESTINATION_IMAGES_DIR / Path(str(image_name)).name
    return path if path.exists() else None


def destination_image_uri(destination_id: str, category: str, image_name: str | None = None) -> str:
    path = uploaded_image_path(image_name)
    if path:
        return file_uri(path)
    return svg_uri(destination_svg(destination_id, category))


def category_image_uri(category: str) -> str:
    """Illustration for the category choice tiles (fixed, recognisable scenes)."""
    seeds = {"Strand": "tile-strand-2", "Natuur": "tile-natuur-1", "Stad": "tile-stad-4"}
    return svg_uri(destination_svg(seeds.get(category, category), category))
