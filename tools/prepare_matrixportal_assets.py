#!/usr/bin/env python3
"""Bake desktop media/settings into a MatrixPortal-ready deployment build.

Run this on the Mac, never on CircuitPython. All framing and image processing is
resolved here. The S3 receives native-size GIFs and only streams those prepared
frames at runtime.

The build also records exact storage usage so media size is known before copying
to CIRCUITPY. Runtime performance remains a device measurement and is reported by
the MatrixPortal smoke/performance tools instead of inferred from desktop speed.
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
from tools.build_large_icons import DESTINATION as LARGE_ICON_MODULE, build as build_large_icons
from tools.build_board_icons import build as build_board_icons
from tools.build_controller_asset import build as build_controller_asset


DEVICE_MODULES = (
    "code.py", "matrixportal_backend.py", "matrixportal_native_colors.py", "matrixportal_ulab_colors.py", "matrixportal_bitmap_buffer_probe.py", "matrixportal_effects.py", "runtime_random.py",
    "matrixportal_colorsys.py", "matrixportal_library.py", "matrixportal_media.py",
    "matrixportal_server.py", "matrixportal_diagnostics.py", "control_bus.py", "runtime_metrics.py",
    "runtime_io.py", "display.py", "totem_runtime.py", "controller.py",
    "chaos_engine.py", "info_scenes.py", "particles.py", "text_engine.py",
    "text.py", "transition_engine.py", "visual_engine.py", "overlay_engine.py",
    "embedded_icon_library.py",
)


def safe_name(index, name):
    stem = Path(name).stem
    clean = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stem)
    clean = clean.strip("_") or "asset"
    return "%03d_%s.gif" % (index, clean[:48])


def human_bytes(value):
    value = int(value or 0)
    units = ("B", "KiB", "MiB", "GiB")
    amount = float(value)
    for unit in units:
        if amount < 1024.0 or unit == units[-1]:
            return "%0.1f %s" % (amount, unit) if unit != "B" else "%d B" % value
        amount /= 1024.0


def directory_bytes(path):
    path = Path(path)
    if not path.exists():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def prepare_asset(asset, output_path):
    # This is intentionally the only place the hardware GIF is cropped,
    # positioned, scaled, sharpened, dithered, color-corrected, etc.
    frames = [asset.prepare_frame(frame, asset.settings) for frame in asset.frames]
    if not frames:
        return None
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
    return {
        "bytes": output_path.stat().st_size,
        "frames": len(frames),
        "duration_ms": sum(durations[: len(frames)]),
    }


def prepare_thumbnail(asset, output_path, width=256, height=128):
    frame = asset.prepare_frame(asset.frames[0], asset.settings)
    frame = frame.resize((width, height), Image.Resampling.NEAREST)
    frame.save(output_path, format="JPEG", quality=78, optimize=True)
    return output_path.stat().st_size


def storage_snapshot(path):
    if not path:
        return None
    target = Path(path).expanduser()
    if not target.exists():
        return {"path": str(target), "available": False}
    usage = shutil.disk_usage(target)
    return {
        "path": str(target),
        "available": True,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def write_build_report(output, manifest, target_storage=None):
    build = manifest["build"]
    assets = sorted(
        manifest["assets"], key=lambda item: int(item.get("bytes", 0)), reverse=True
    )
    lines = [
        "Festival Totem MatrixPortal Build",
        "=================================",
        "",
        "Prepared resolution: %dx%d" % (manifest["width"], manifest["height"]),
        "Assets: %d" % build["asset_count"],
        "GIF media: %s" % human_bytes(build["media_bytes"]),
        "Controller thumbnails: %s" % human_bytes(build["thumbnail_bytes"]),
        "Controller HTML: %s" % human_bytes(build["controller_bytes"]),
        "Large icon module: %s" % human_bytes(build["large_icon_bytes"]),
        "Manifest: %s" % human_bytes(build["manifest_bytes"]),
        "Total generated payload: %s" % human_bytes(build["payload_bytes"]),
        "",
        "Media is baked: YES",
        "The S3 does not crop, zoom, color-correct, sharpen, dither, or resize GIFs.",
        "",
        "Largest GIFs",
        "------------",
    ]
    for asset in assets[:12]:
        lines.append(
            "%8s  %4d frames  %7.2fs  %s"
            % (
                human_bytes(asset.get("bytes", 0)),
                int(asset.get("frame_count", 0)),
                float(asset.get("duration_ms", 0)) / 1000.0,
                asset.get("name", ""),
            )
        )

    if target_storage:
        lines.extend(["", "Target volume", "-------------"])
        if target_storage.get("available"):
            free = int(target_storage["free_bytes"])
            payload = int(build["payload_bytes"])
            lines.extend(
                [
                    "Path: %s" % target_storage["path"],
                    "Free before copy: %s" % human_bytes(free),
                    "Build / free space: %0.1f%%"
                    % ((payload / max(1, free)) * 100.0),
                    "Estimated free after copy: %s" % human_bytes(max(0, free - payload)),
                ]
            )
        else:
            lines.append("Target path not mounted: %s" % target_storage["path"])

    report_path = output / "BUILD_REPORT.txt"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def build(args):
    build_large_icons()
    source = Path(args.source)
    output = Path(args.output)
    media_dir = output / "media"
    www_dir = output / "www"
    thumbs_dir = www_dir / "thumbs"

    if args.clean and output.exists():
        shutil.rmtree(output)
    media_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LARGE_ICON_MODULE, output / LARGE_ICON_MODULE.name)
    for module in DEVICE_MODULES:
        shutil.copy2(PROJECT_ROOT / module, output / module)
    board_icon_bytes = build_board_icons(output)
    large_icon_bytes = (output / LARGE_ICON_MODULE.name).stat().st_size

    library = ImageLibrary(
        source,
        width=args.width,
        height=args.height,
        metadata_file=Path(args.metadata),
    )

    manifest = {
        "version": 2,
        "width": args.width,
        "height": args.height,
        "baked_media": True,
        "assets": [],
        "build": {},
    }

    media_bytes = 0
    thumbnail_bytes = 0
    for index, asset in enumerate(library.assets):
        filename = safe_name(index, asset.path.name)
        output_path = media_dir / filename
        prepared = prepare_asset(asset, output_path)
        if not prepared:
            continue
        thumb_bytes = prepare_thumbnail(asset, thumbs_dir / ("%d.jpg" % index))
        media_bytes += prepared["bytes"]
        thumbnail_bytes += thumb_bytes

        meta = library.metadata_entry(asset.path.name)
        manifest["assets"].append(
            {
                "index": index,
                "name": asset.path.name,
                "file": "/media/" + filename,
                "tags": list(meta.get("tags", [])),
                "favorite": bool(meta.get("favorite", False)),
                # Provenance only. Hardware never applies these settings again.
                "source_settings": asset.settings.to_dict(),
                "baked": True,
                "bytes": prepared["bytes"],
                "thumbnail_bytes": thumb_bytes,
                "frame_count": prepared["frames"],
                "duration_ms": prepared["duration_ms"],
            }
        )
        print(
            "Prepared:",
            asset.path.name,
            "->",
            filename,
            "(%s)" % human_bytes(prepared["bytes"]),
        )

    controller_path = build_controller_asset(www_dir / "index.html")
    controller_bytes = Path(controller_path).stat().st_size

    manifest["build"] = {
        "asset_count": len(manifest["assets"]),
        "media_bytes": media_bytes,
        "thumbnail_bytes": thumbnail_bytes,
        "controller_bytes": controller_bytes,
        "large_icon_bytes": large_icon_bytes,
        "board_icon_bytes": board_icon_bytes,
        # Filled after the manifest is serialized.
        "manifest_bytes": 0,
        "payload_bytes": 0,
    }

    manifest_path = output / "manifest.json"
    # Two-pass write gives the report an exact manifest size without making the
    # manifest recursively depend on its own serialized byte count.
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    manifest_bytes = manifest_path.stat().st_size
    manifest["build"]["manifest_bytes"] = manifest_bytes
    manifest["build"]["payload_bytes"] = (
        media_bytes + thumbnail_bytes + controller_bytes + large_icon_bytes + board_icon_bytes + manifest_bytes
    )
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    # Capture the final serialized size and update total one last time. A few
    # digits may change when the fields above are written, so use the final file.
    final_manifest_bytes = manifest_path.stat().st_size
    manifest["build"]["manifest_bytes"] = final_manifest_bytes
    manifest["build"]["payload_bytes"] = (
        media_bytes + thumbnail_bytes + controller_bytes + large_icon_bytes + board_icon_bytes + final_manifest_bytes
    )
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")

    target_storage = storage_snapshot(args.target_volume)
    report_path = write_build_report(output, manifest, target_storage)
    build_report = {
        "build": manifest["build"],
        "target_volume": target_storage,
        "largest_assets": [
            {
                "name": item["name"],
                "bytes": item["bytes"],
                "frame_count": item["frame_count"],
                "duration_ms": item["duration_ms"],
            }
            for item in sorted(
                manifest["assets"], key=lambda row: row["bytes"], reverse=True
            )[:12]
        ],
    }
    with open(output / "build_report.json", "w", encoding="utf-8") as handle:
        json.dump(build_report, handle, indent=2)
        handle.write("\n")

    print()
    print("MatrixPortal build ready:", output)
    print("Assets:", len(manifest["assets"]))
    print("GIF media:", human_bytes(media_bytes))
    print("Controller + thumbnails:", human_bytes(controller_bytes + thumbnail_bytes))
    print("Generated payload:", human_bytes(manifest["build"]["payload_bytes"]))
    print("Storage report:", report_path)
    if target_storage and target_storage.get("available"):
        print("CIRCUITPY free before copy:", human_bytes(target_storage["free_bytes"]))
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
    parser.add_argument(
        "--target-volume",
        default=None,
        help="Optional mounted CIRCUITPY path (for example /Volumes/CIRCUITPY) to compare build size with exact free space.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
