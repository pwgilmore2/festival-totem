"""Small PIL-free icon library usable by the shared runtime and CircuitPython.

Desktop can still use file-backed PNG icons. Hardware uses the exact embedded
32x32 masters so importing the runtime never requires Pillow.
"""

from overlay_exact_assets import EXACT_SPRITES, sprite_rgba


class EmbeddedIconAsset:
    def __init__(self, name, pixels):
        self.name = name
        self.pixels = pixels
        self.path = None


class EmbeddedIconLibrary:
    def __init__(self):
        self.assets = []
        self.by_name = {}
        self.errors = []
        self.reload()

    def reload(self):
        self.assets = []
        self.by_name = {}
        self.errors = []
        for name in EXACT_SPRITES:
            rows = tuple(tuple(tuple(pixel) for pixel in row) for row in sprite_rgba(name))
            asset = EmbeddedIconAsset(name, rows)
            self.assets.append(asset)
            self.by_name[name] = asset
        return self

    def names(self):
        return [asset.name for asset in self.assets]

    def get(self, name):
        if name in self.by_name:
            return self.by_name[name]
        return self.assets[0] if self.assets else None
