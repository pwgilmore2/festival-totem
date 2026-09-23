"""PIL-free icon library backed by the exact authored embedded sprites.

This is the hardware-safe icon source for MatrixPortal/CircuitPython. Desktop can
continue loading editable PNGs through icon_assets.IconLibrary, while the shared
renderer only depends on the small names()/get() contract implemented here.
"""

from overlay_exact_assets import EXACT_SPRITES, sprite_rgba


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
        return self

    def names(self):
        return [asset.name for asset in self.assets]

    def get(self, name):
        return self.by_name.get(name)


EMBEDDED_ICON_LIBRARY = EmbeddedIconLibrary()
