"""Create responsive WebP derivatives; keep original food images intact.

Optional authoring utility, requires Pillow. Generated assets are served directly.
"""
from pathlib import Path

from PIL import Image

root = Path(__file__).resolve().parents[1] / "static" / "img"
output = root / "optimized"
output.mkdir(exist_ok=True)
source_bytes = result_bytes = 0
for source in sorted((root / "items").glob("*.png")):
    source_bytes += source.stat().st_size
    with Image.open(source) as image:
        for width in (320, 640):
            copy = image.convert("RGB")
            copy.thumbnail((width, width), Image.Resampling.LANCZOS)
            destination = output / f"{source.stem}-{width}.webp"
            copy.save(destination, format="WEBP", quality=86, method=6)
            result_bytes += destination.stat().st_size
print(f"Originals: {source_bytes:,} bytes; responsive derivatives: {result_bytes:,} bytes")
