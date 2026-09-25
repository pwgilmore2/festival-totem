#!/usr/bin/env python3
"""Copy a prepared build to a mounted CIRCUITPY, with code.py last.

This avoids rsync's temporary-file rename on the small FAT volume. It does
not erase files already on CIRCUITPY or install external library bundles.
"""

import argparse
import hashlib
import os
import shutil
from pathlib import Path


def digest(path):
    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(65536)
            if not block:
                break
            sha.update(block)
    return sha.digest()


def copy_checked(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(source, "rb") as src, open(destination, "wb") as dst:
        while True:
            block = src.read(65536)
            if not block:
                break
            dst.write(block)
        dst.flush()
        os.fsync(dst.fileno())
    if source.stat().st_size != destination.stat().st_size or digest(source) != digest(destination):
        raise OSError("Copy verification failed: " + str(destination))


def deploy(source, target):
    source, target = Path(source), Path(target)
    if not target.is_dir() or not os.path.ismount(target):
        raise ValueError("CIRCUITPY is not mounted at " + str(target))
    if not (source / "manifest.json").is_file() or not (source / "code.py").is_file():
        raise ValueError("Rebuild the prepared assets: missing manifest.json or code.py")
    if (target / "code.py").exists():
        raise ValueError("Rename the current CIRCUITPY/code.py before deploying")
    program = (source / "code.py").read_text()
    if 'WIFI_PASSWORD = ""' in program:
        raise ValueError("Set a private WIFI_PASSWORD in the build's code.py before deploying")

    files = sorted(path for path in source.rglob("*") if path.is_file()
                   and path.name not in ("BUILD_REPORT.txt", "build_report.json")
                   and path != source / "code.py")
    needed = sum(path.stat().st_size for path in files) + (source / "code.py").stat().st_size
    available = shutil.disk_usage(target).free
    if needed + 32768 > available:
        raise ValueError("Build needs %d bytes; CIRCUITPY has %d free" % (needed, available))

    for path in files:
        relative = path.relative_to(source)
        print("Copy", relative, flush=True)
        copy_checked(path, target / relative)
    os.sync()
    print("All supporting files verified. Copy code.py last.", flush=True)
    copy_checked(source / "code.py", target / "code.py")
    os.sync()
    print("Deployment verified. Wait for the board serial output.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="matrixportal_build")
    parser.add_argument("--target", default="/Volumes/CIRCUITPY")
    args = parser.parse_args()
    deploy(args.source, args.target)
