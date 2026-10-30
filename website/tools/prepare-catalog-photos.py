"""Alpha-preserving framing and responsive WebP preparation for catalog artwork."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "website/static/img/catalog"


def main():
    rows = json.loads(
        (ROOT / "artifacts/lower-section/photo-manifest.json").read_text(encoding="utf-8-sig")
    )
    OUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (1000, ((len(rows) + 4) // 5) * 190), "#242b20")
    draw = ImageDraw.Draw(sheet)
    total = 0
    for i, row in enumerate(rows):
        source = Image.open(row["source"]).convert("RGBA")
        bounds = source.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        if not bounds:
            raise ValueError(row["id"])
        food = ImageOps.contain(source.crop(bounds), (1056, 804), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (1200, 934))
        canvas.alpha_composite(food, ((1200 - food.width) // 2, (934 - food.height) // 2))
        for width in (320, 640, 960):
            path = OUT / f"{row['id']}-{width}.webp"
            valid = False
            if path.exists():
                try:
                    with Image.open(path) as existing:
                        existing.verify()
                    valid = True
                except (OSError, ValueError):
                    pass
            if not valid:
                canvas.resize((width, round(width * 934 / 1200)), Image.Resampling.LANCZOS).save(
                    path, "WEBP", quality=86 if width > 320 else 82, method=4
                )
            total += path.stat().st_size
        thumb = ImageOps.contain(canvas, (196, 150), Image.Resampling.LANCZOS)
        x, y = (i % 5) * 200, (i // 5) * 190
        sheet.paste(thumb, (x + (200 - thumb.width) // 2, y + 8), thumb)
        draw.text((x + 6, y + 162), row["id"], fill="#e3e8d8")
    sheet.save(ROOT / "artifacts/lower-section/new-photos-contact.jpg", quality=93)
    print(f"{len(rows)} products; {len(rows) * 3} alpha WebPs; {total / 1024 / 1024:.2f} MiB")


if __name__ == "__main__":
    main()
