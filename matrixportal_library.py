"""Read-only MatrixPortal media library and shared-runtime adapter.

All visual processing is baked on the desktop. This module only reads the build
manifest, selects already-prepared GIF files and streams them through gifio.
"""

import json

from matrixportal_media import DualGifPlayers


class MatrixPortalAssetLibrary:
    def __init__(self, manifest_path="/manifest.json"):
        self.manifest_path = manifest_path
        self.assets = []
        self.width = 64
        self.height = 32
        self.baked_media = False
        self.build_info = {}
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
        self.baked_media = bool(data.get("baked_media", False))
        self.build_info = dict(data.get("build", {}) or {})
        self.assets = assets

    def __len__(self):
        return len(self.assets)

    def get(self, index):
        if not self.assets:
            return None
        return self.assets[int(index) % len(self.assets)]

    def names(self):
        return [str(asset.get("name", "")) for asset in self.assets]

    def storage_bytes(self):
        return int(self.build_info.get("payload_bytes", 0) or 0)

    def media_bytes(self):
        return int(self.build_info.get("media_bytes", 0) or 0)

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
                    "bytes": int(asset.get("bytes", 0) or 0),
                    "frame_count": int(asset.get("frame_count", 0) or 0),
                    "duration_ms": int(asset.get("duration_ms", 0) or 0),
                    "baked": bool(asset.get("baked", self.baked_media)),
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

    def advance(self, now=None, max_decodes=1):
        return self.players.advance(now, max_decodes=max_decodes)

    def render_side(self, side, display):
        self.players.players[side].render(display)

    def render(self, displays):
        self.players.render(displays)

    def close(self):
        self.players.close()


class MatrixPortalMediaAdapter:
    """MatrixPortal implementation of the TotemRuntime media contract.

    The adapter is intentionally read-only at runtime. Crop/color/tag editing is
    done on the Mac and baked into manifest/media files before deployment.
    """

    read_only = True
    baked_media = True

    def __init__(self, manifest_path="/manifest.json"):
        self.library = MatrixPortalAssetLibrary(manifest_path)
        self.deck = MatrixPortalMediaDeck(self.library)

    def __len__(self):
        return len(self.library)

    def name(self, index):
        asset = self.library.get(index)
        return str(asset.get("name", "")) if asset else None

    def find_index(self, name):
        if not name:
            return None
        for index, asset in enumerate(self.library.assets):
            if str(asset.get("name", "")) == name:
                return index
        return None

    def select(self, side, index):
        return self.deck.select(side, index)

    def suspend(self, side):
        """Release a GIF decoder while its panel renders a standalone scene."""
        self.deck.players.players[side].close()

    def render(self, side, index, display, t):
        # TotemRuntime calls select() whenever the logical index changes. The
        # render path therefore only blits the already-decoded current frame.
        if self.deck.indices.get(side) != int(index):
            self.deck.select(side, index)
        self.deck.render_side(side, display)

    def advance(self, now=None, max_decodes=1):
        """Advance at most max_decodes streams; call from the S3 timer loop."""
        return self.deck.advance(now, max_decodes=max_decodes)

    def info(self, index):
        asset = self.library.get(index)
        if not asset:
            return {
                "image_name": None,
                "image_mode": None,
                "image_settings": None,
                "image_tags": [],
                "image_favorite": False,
                "image_baked": True,
                "image_bytes": 0,
            }
        # source_settings are provenance from the Mac authoring session. They
        # are never re-applied on hardware; the selected GIF is already final.
        settings = asset.get("source_settings", asset.get("settings"))
        return {
            "image_name": str(asset.get("name", "")),
            "image_mode": "Baked",
            "image_settings": settings if isinstance(settings, dict) else None,
            "image_tags": list(asset.get("tags", [])),
            "image_favorite": bool(asset.get("favorite", False)),
            "image_baked": bool(asset.get("baked", True)),
            "image_bytes": int(asset.get("bytes", 0) or 0),
        }

    def library_state(self):
        return self.library.controller_state()

    def build_state(self):
        return {
            "baked_media": bool(self.library.baked_media),
            "media_read_only": True,
            "storage": dict(self.library.build_info),
        }

    def reload(self):
        self.library.load()

    def handle_command(self, command, value, reference_index):
        # Hardware media is deliberately immutable. Editing remains a desktop
        # preparation step so festival runtime never writes/reprocesses assets.
        return False

    def close(self):
        self.deck.close()
