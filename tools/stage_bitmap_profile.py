#!/usr/bin/env python3
"""Stage a two-GIF Bitmap performance build from prepared desktop assets."""

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def stage(source, target, count=2, volume=None):
    source, target = Path(source), Path(target)
    manifest = json.loads((source / "manifest.json").read_text())
    assets = manifest.get("assets", [])[:count]
    if not assets:
        raise ValueError("No baked GIFs. Put GIFs in assets/images and run prepare_matrixportal_assets.py first.")
    payload = sum((source / "media" / Path(asset["file"]).name).stat().st_size for asset in assets)
    if volume:
        available = shutil.disk_usage(volume).free
        if payload + 8192 > available:
            raise ValueError("Selected GIFs need %d bytes, but CIRCUITPY has %d free. Use smaller GIFs." % (payload, available))
    if target.exists():
        shutil.rmtree(target)
    (target / "media").mkdir(parents=True)
    prepared = []
    for asset in assets:
        filename = Path(asset["file"]).name
        shutil.copy2(source / "media" / filename, target / "media" / filename)
        prepared.append({"name": asset["name"], "file": "/media/" + filename})
    (target / "manifest.json").write_text(json.dumps({"assets": prepared}))
    shutil.copy2(ROOT / "matrixportal_bitmap_profile.py", target / "code.py")
    shutil.copy2(ROOT / "matrixportal_backend.py", target / "matrixportal_backend.py")
    print("Profile build:", target)
    print("GIF payload bytes:", payload)
    for asset in prepared:
        print("  ", asset["name"])
    print("Copy these build contents to CIRCUITPY while it is stable; copy code.py last.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="matrixportal_build")
    parser.add_argument("--output", default="matrixportal_profile_build")
    parser.add_argument("--count", type=int, choices=(1, 2), default=2)
    parser.add_argument("--target-volume", default=None)
    args = parser.parse_args()
    stage(args.source, args.output, count=args.count, volume=args.target_volume)
