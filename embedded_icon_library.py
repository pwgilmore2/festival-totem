"""PIL-free icon library backed by the exact authored embedded sprites.

This is the hardware-safe icon source for MatrixPortal/CircuitPython. Desktop can
continue loading editable PNGs through icon_assets.IconLibrary, while the shared
renderer only depends on the small names()/get() contract implemented here.
"""

try:
    from board_icon_index import ICONS as BOARD_ICONS
except ImportError:
    BOARD_ICONS = None


def _board_rows(path, width, height):
    with open(path, "rb") as handle:
        raw = handle.read()
    if len(raw) != width * height * 4:
        raise ValueError("Invalid RGBA icon file: " + path)
    return tuple(tuple(tuple(raw[(y * width + x) * 4:(y * width + x + 1) * 4])
                       for x in range(width)) for y in range(height))


class EmbeddedIconAsset:
    def __init__(self, name, pixels):
        self.name = name
        self.pixels = pixels
        self.path = None


class EmbeddedIconLibrary:
    def __init__(self):
        self.errors = []
        self.assets = []
        self.by_name = {}
        self.reload()

    def reload(self):
        self.assets = []
        self.by_name = {}
        self.errors = []
        if BOARD_ICONS is not None:
            for name, width, height, path in BOARD_ICONS:
                try:
                    asset = EmbeddedIconAsset(name, _board_rows(path, width, height))
                    self.assets.append(asset)
                    self.by_name[name] = asset
                except Exception as exc:
                    self.errors.append("%s: %s" % (name, exc))
            return self

        # Desktop fallback; the board build uses raw RGBA files and never imports
        # the base85/zlib authoring modules.
        from overlay_exact_assets import EXACT_SPRITES, sprite_rgba
        from large_icon_data import DATA as LARGE_ICONS, sprite_rgba as large_sprite_rgba
        for name in EXACT_SPRITES:
            try:
                rows = tuple(
                    tuple(tuple(pixel) for pixel in row)
                    for row in sprite_rgba(name)
                )
                asset = EmbeddedIconAsset(name, rows)
                self.assets.append(asset)
                self.by_name[name] = asset
            except Exception as exc:
                self.errors.append("%s: %s" % (name, exc))
        for name in LARGE_ICONS:
            try:
                if name in self.by_name:
                    raise ValueError("duplicate icon name")
                asset = EmbeddedIconAsset(name, large_sprite_rgba(name))
                self.assets.append(asset)
                self.by_name[name] = asset
            except Exception as exc:
                self.errors.append("%s: %s" % (name, exc))
        return self

    def names(self):
        return [asset.name for asset in self.assets]

    def get(self, name):
        return self.by_name.get(name)


EMBEDDED_ICON_LIBRARY = EmbeddedIconLibrary()
