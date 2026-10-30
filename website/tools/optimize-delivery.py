"""Create versioned delivery assets without changing the approved artwork."""

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "static/img/catalog-v7"
HERO = ROOT / "static/img/editorial/fast-v7"


def save_family(source, destination, sizes):
    with Image.open(source) as image:
        image = image.convert("RGBA")
        for width, quality in sizes:
            path = destination / f"{source.stem.rsplit('-960', 1)[0]}-{width}.webp"
            if not path.exists():
                height = round(image.height * width / image.width)
                image.resize((width, height), Image.Resampling.LANCZOS).save(
                    path, "WEBP", quality=quality, method=4
                )


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    HERO.mkdir(parents=True, exist_ok=True)
    sources = sorted((ROOT / "static/img/catalog").glob("*-960.webp"))
    for source in sources:
        save_family(source, DEST, [(160, 68), (320, 70), (480, 72), (640, 74), (960, 77)])
    save_family(
        ROOT / "static/img/editorial/chicken-burger-hero.webp",
        HERO,
        [(480, 76), (768, 78), (1024, 80)],
    )
    sizes = {
        str(p.relative_to(ROOT)): p.stat().st_size
        for p in [*DEST.glob("*.webp"), *HERO.glob("*.webp")]
    }
    report = ROOT.parent / "artifacts/performance/asset-sizes.json"
    report.write_text(json.dumps(sizes, indent=2))
    print(f"{len(sources)} products, {len(sizes)} optimized assets")
    for width in (160, 320, 480, 640, 960):
        print(
            width, round(sum(p.stat().st_size for p in DEST.glob(f"*-{width}.webp")) / 1024), "KiB"
        )
    for p in HERO.glob("*.webp"):
        print(p.name, round(p.stat().st_size / 1024), "KiB")


if __name__ == "__main__":
    main()
