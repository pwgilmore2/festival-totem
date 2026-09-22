"""Read-only MatrixPortal media library backed by the desktop build manifest."""

import json

from matrixportal_media import DualGifPlayers


class MatrixPortalAssetLibrary:
    def __init__(self, manifest_path="/manifest.json"):
        self.manifest_path = manifest_path
        self.assets = []
        self.width = 64
        self.height = 32
        self.load()

    def load(self):
        with open(self.manifest_path, "r") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("Invalid MatrixPortal manifest")
        assets = data.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError("Invalid MatrixPortal asset list")
        self.width = int(data.get("width", 64))
        self.height = int(data.get("height", 32))
        self.assets = assets

    def __len__(self):
        return len(self.assets)

    def get(self, index):
        if not self.assets:
            return None
        return self.assets[int(index) % len(self.assets)]

    def names(self):
        return [str(asset.get("name", "")) for asset in self.assets]

    def controller_state(self):
        """Small JSON-ready library payload matching the phone controller shape."""
        out = []
        for index, asset in enumerate(self.assets):
            out.append(
                {
                    "index": int(asset.get("index", index)),
                    "name": str(asset.get("name", "")),
                    "tags": list(asset.get("tags", [])),
                    "favorite": bool(asset.get("favorite", False)),
                }
            )
        return out


class MatrixPortalMediaDeck:
    """Independent front/back media selection using streaming GIF decoders."""

    def __init__(self, library):
        self.library = library
        self.players = DualGifPlayers()
        self.indices = {"front": 0, "back": 0}

    def select(self, side, index):
        asset = self.library.get(index)
        if asset is None:
            return False
        self.indices[side] = int(asset.get("index", index))
        self.players.set_path(side, asset.get("file"))
        return True

    def current(self, side):
        return self.library.get(self.indices[side])

    def advance(self, now=None):
        return self.players.advance(now)

    def render(self, displays):
        self.players.render(displays)

    def close(self):
        self.players.close()
