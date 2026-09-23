#!/usr/bin/env python3
"""Bake desktop media/settings into MatrixPortal-ready assets.

Run this on the Mac, not on CircuitPython. It applies the same crop, framing and
processing settings used by the simulator, writes every asset as a native-size
GIF for ``gifio.OnDiskGif``, pre-generates JPEG thumbnails, and compiles the
phone controller to static HTML for the S3 web server.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

# Running ``python tools/prepare_matrixportal_assets.py`` makes ``tools`` the
# first import directory. Add the project root explicitly so this script can use
# the simulator's canonical desktop adapters without requiring PYTHONPATH setup.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from image_assets import ImageLibrary
from tools.build_controller_asset import build as build_controller_asset


def safe_name(index, name):
    stem = Path(name).stem
    clean = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stem)
    clean = clean.strip("_") or "asset"
    return "%03d_%s.gif" % (index, clean[:48])


def prepare_asset(asset, output_path):
    frames = [asset.prepare_frame(frame, asset.settings) for frame in asset.frames]
    if not frames:
        return False
    durations = [max(10, int(round(value * 1000))) for value in asset.durations]
    while len(durations) < len(frames):
        durations.append(100)

    first = frames[0]
    first.save(
        output_path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
        disposal=2,
    )
    return True


def prepare_thumbnail(asset, output_path, width=256, height=128):
    frame = asset.prepare_frame(asset.frames[0], asset.settings)
    frame = frame.resize((width, height), Image.Resampling.NEAREST)
    frame.save(output_path, format="JPEG", quality=78, optimize=True)


def build(args):
    source = Path(args.source)
    output = Path(args.output)
    media_dir = output / "media"
    www_dir = output / "www"
    thumbs_dir = www_dir / "thumbs"

    if args.clean and output.exists():
        shutil.rmtree(output)
    media_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    library = ImageLibrary(
        source,
        width=args.width,
        height=args.height,
        metadata_file=Path(args.metadata),
    )

    manifest = {
        "version": 1,
        "width": args.width,
        "height": args.height,
        "assets": [],
    }

    for index, asset in enumerate(library.assets):
        filename = safe_name(index, asset.path.name)
        output_path = media_dir / filename
        if not prepare_asset(asset, output_path):
            continue
        prepare_thumbnail(asset, thumbs_dir / ("%d.jpg" % index))

        meta = library.metadata_entry(asset.path.name)
        manifest["assets"].append(
            {
                "index": index,
                "name": asset.path.name,
                "file": "/media/" + filename,
                "tags": list(meta.get("tags", [])),
                "favorite": bool(meta.get("favorite", False)),
                "settings": asset.settings.to_dict(),
            }
        )
        print("Prepared:", asset.path.name, "->", filename)

    with open(output / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    build_controller_asset(www_dir / "index.html")

    print()
    print("MatrixPortal build ready:", output)
    print("Assets:", len(manifest["assets"]))
    print("Controller: www/index.html")
    print("Copy the build contents to CIRCUITPY after the hardware runtime is installed.")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="assets/images")
    parser.add_argument("--metadata", default="assets/image_settings.json")
    parser.add_argument("--output", default="matrixportal_build")
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--clean", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
