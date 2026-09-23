#!/usr/bin/env python3
"""Compile the phone controller into one static HTML asset.

Run on the desktop. MatrixPortal should serve the finished file directly instead
of importing any desktop controller/UI composition modules at runtime.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import controller_ui


def build(output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    html = controller_ui.PHONE_HTML
    output.write_text(html, encoding="utf-8")
    print("Controller asset:", output)
    print("Bytes:", len(html.encode("utf-8")))
    return output


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="controller_build/index.html",
        help="Destination for the compiled controller HTML",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build(args.output)
