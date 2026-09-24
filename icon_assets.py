"""File-backed native-size icon assets for the 64x32 panels.

Drop transparent PNGs into assets/icons. Files are loaded losslessly and
rendered 1:1. The embedded authored masters remain a fallback so the simulator
still works before the folder is populated.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from overlay_exact_assets import EXACT_SPRITES, sprite_rgba

ICON_SIZE = 32
PANEL_SIZE = (64, 32)
CANVAS_ALLOWANCE = 8  # Up to four extra pixels beyond each nominal edge.
DEFAULT_ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"


def _display_name(path: Path):
    return path.stem.replace("_32x32", "").replace("_", " ").strip().title()


@dataclass(frozen=True)
class IconAsset:
    name: str
    pixels: tuple
    path: Path | None = None

    @classmethod
    def from_png(cls, path: Path, large=False):
        with Image.open(path) as im:
            im = im.convert("RGBA")
            width, height = im.size
            maximum = (PANEL_SIZE[0] + CANVAS_ALLOWANCE, PANEL_SIZE[1] + CANVAS_ALLOWANCE) if large else (ICON_SIZE + CANVAS_ALLOWANCE,) * 2
            if not (1 <= width <= maximum[0] and 1 <= height <= maximum[1]):
                raise ValueError(f"{path.name} must fit within {maximum[0]}x{maximum[1]}; got {width}x{height}")
            px = im.load()
            rows = tuple(
                tuple(tuple(px[x, y]) for x in range(width))
                for y in range(height)
            )
        return cls(_display_name(path), rows, path)


class IconLibrary:
    def __init__(self, directory=DEFAULT_ICON_DIR):
        self.directory = Path(directory)
        self.assets = []
        self.by_name = {}
        self.errors = []
        self.reload()

    def reload(self):
        self.assets = []
        self.by_name = {}
        self.errors = []

        for path in sorted(self.directory.glob("*.png")):
            try:
                asset = IconAsset.from_png(path)
            except Exception as exc:
                self.errors.append(str(exc))
                continue
            self.assets.append(asset)
            self.by_name[asset.name] = asset

        # Root 32x32 PNGs are authoritative for that set. Adding only large
        # icons must not remove the existing embedded 32x32 choices.
        if not self.assets:
            for name in EXACT_SPRITES:
                rows = tuple(tuple(tuple(px) for px in row) for row in sprite_rgba(name))
                asset = IconAsset(name, rows, None)
                self.assets.append(asset)
                self.by_name[name] = asset
        for path in sorted((self.directory / "large").glob("*.png")):
            try:
                asset = IconAsset.from_png(path, large=True)
                if asset.name in self.by_name:
                    raise ValueError(f"Duplicate icon name {asset.name!r}: {path}")
            except Exception as exc:
                self.errors.append(str(exc))
                continue
            self.assets.append(asset)
            self.by_name[asset.name] = asset
        return self

    def names(self):
        return [asset.name for asset in self.assets]

    def get(self, name):
        if name in self.by_name:
            return self.by_name[name]
        return self.assets[0] if self.assets else None

    def __len__(self):
        return len(self.assets)


ICON_LIBRARY = IconLibrary()
