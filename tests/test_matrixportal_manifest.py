import json
import tempfile
import unittest
from pathlib import Path

from matrixportal_library import MatrixPortalAssetLibrary


class MatrixPortalManifestTests(unittest.TestCase):
    def test_baked_build_metadata_round_trips(self):
        manifest = {
            "version": 2,
            "width": 64,
            "height": 32,
            "baked_media": True,
            "build": {
                "asset_count": 1,
                "media_bytes": 12345,
                "payload_bytes": 15000,
            },
            "assets": [
                {
                    "index": 0,
                    "name": "example.gif",
                    "file": "/media/000_example.gif",
                    "tags": ["test"],
                    "favorite": True,
                    "baked": True,
                    "bytes": 12345,
                    "frame_count": 24,
                    "duration_ms": 2400,
                    "source_settings": {"zoom": 1.4},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            library = MatrixPortalAssetLibrary(str(path))

        self.assertTrue(library.baked_media)
        self.assertEqual(library.media_bytes(), 12345)
        self.assertEqual(library.storage_bytes(), 15000)
        state = library.controller_state()[0]
        self.assertTrue(state["baked"])
        self.assertEqual(state["bytes"], 12345)
        self.assertEqual(state["frame_count"], 24)
        self.assertEqual(state["duration_ms"], 2400)


if __name__ == "__main__":
    unittest.main()
