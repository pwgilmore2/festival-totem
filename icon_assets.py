"""File-backed 32x32 icon assets.

Drop transparent PNGs into assets/icons.  Files are loaded losslessly and
rendered 1:1.  The embedded authored masters remain a fallback so the simulator
still works before the folder is populated.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from overlay_exact_assets import ICONS as EMBEDDED_ICONS, sprite_rgba

ICON_SIZE = 32
DEFAULT_ICON_DIR = Path("assets/icons")


def _display_name(path: Path):
    return path.stem.replace("_32x32", "").replace("_", " ").strip().title()


@dataclass(frozen=True)
class IconAsset:
    name: str
    pixels: tuple
    path: Path | None = None

    @classmethod
    def from_png(cls, path: Path):
        with Image.open(path) as im:
            im = im.convert("RGBA")
            if im.size != (ICON_SIZE, ICON_SIZE):
                raise ValueError(f"{path.name} must be exactly 32x32; got {im.size[0]}x{im.size[1]}")
            rows = []
            px = im.load()
            for y in range(ICON_SIZE):
                rows.append(tuple(tuple(px[x, y]) for x in range(ICON_SIZE)))
        return cls(_display_name(path), tuple(rows), path)


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
        if self.directory.exists():
            for path in sorted(self.directory.glob("*.png")):
                try:
                    asset = IconAsset.from_png(path)
                except Exception as exc:
                    self.errors.append(str(exc))
                    continue
                self.assets.append(asset)
                self.by_name[asset.name] = asset

        # Empty folder / fresh checkout: keep the authored embedded masters as
        # a zero-config fallback. Once PNGs exist, the folder is authoritative.
        if not self.assets:
            for name in EMBEDDED_ICONS:
                rows = tuple(tuple(tuple(px) for px in row) for row in sprite_rgba(name))
                asset = IconAsset(name, rows, None)
                self.assets.append(asset)
                self.by_name[name] = asset
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
