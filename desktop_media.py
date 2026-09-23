"""Desktop/PIL media adapter for the shared totem runtime.

All image editing, metadata persistence and thumbnail generation stay on the
Mac. The runtime only talks to this small interface, allowing MatrixPortal to
provide a different streaming implementation without importing PIL.
"""

import io

from PIL import Image

from image_assets import ImageLibrary, PROCESSING_PROFILES


MODES = ("crop", "pixel", "optimize", "dither")


class DesktopMediaAdapter:
    def __init__(self, folder="assets/images", width=64, height=32):
        self.library = ImageLibrary(folder, width, height)
        self._library_state_cache = None

    def __len__(self):
        return len(self.library)

    def get(self, index):
        return self.library.get(index)

    def name(self, index):
        asset = self.get(index)
        return asset.path.name if asset else None

    def find_index(self, name):
        if not name:
            return None
        for index, asset in enumerate(self.library.assets):
            if asset.path.name == name:
                return index
        return None

    def select(self, side, index):
        # Desktop ImageAsset rendering is random-access, so selection itself
        # needs no I/O. MatrixPortal's adapter opens the corresponding stream.
        return 0 <= int(index) < len(self)

    def render(self, side, index, display, t):
        asset = self.get(index)
        if asset:
            asset.render(display, t, asset.settings)
        else:
            display.clear()

    def _metadata(self, asset):
        if not asset:
            return {"tags": [], "favorite": False}
        return self.library.metadata_entry(asset.path.name)

    def info(self, index):
        asset = self.get(index)
        if not asset:
            return {
                "image_name": None,
                "image_mode": None,
                "image_settings": None,
                "image_tags": [],
                "image_favorite": False,
            }
        metadata = self._metadata(asset)
        return {
            "image_name": asset.path.name,
            "image_mode": asset.settings.mode,
            "image_settings": asset.settings.to_dict(),
            "image_tags": list(metadata.get("tags", [])),
            "image_favorite": bool(metadata.get("favorite", False)),
        }

    def library_state(self):
        if self._library_state_cache is None:
            state = []
            for index, asset in enumerate(self.library.assets):
                metadata = self._metadata(asset)
                state.append(
                    {
                        "index": index,
                        "name": asset.path.name,
                        "tags": list(metadata.get("tags", [])),
                        "favorite": bool(metadata.get("favorite", False)),
                    }
                )
            self._library_state_cache = state
        return self._library_state_cache

    def invalidate_state(self):
        self._library_state_cache = None

    def reload(self):
        self.library.load()
        self.invalidate_state()

    def thumbnail(self, index):
        try:
            asset = self.get(int(index))
        except Exception:
            return None
        if not asset or not asset.frames:
            return None
        try:
            preview = asset.prepare_frame(asset.frames[0], asset.settings).resize(
                (256, 128), Image.Resampling.NEAREST
            )
            out = io.BytesIO()
            preview.save(out, format="JPEG", quality=82, optimize=True)
            return out.getvalue()
        except Exception as exc:
            print("Thumbnail error:", exc)
            return None

    def _save_asset(self, asset):
        if not asset:
            return
        asset.settings.clamp()
        asset.clear_cache()
        self.library.save_asset(asset)

    def handle_command(self, command, value, reference_index):
        """Handle desktop-only metadata/image-editing commands.

        Returns True when the command belongs to the media adapter, even if no
        asset is selected. Hardware adapters can simply reject these commands.
        """
        asset = self.get(reference_index) if len(self) else None

        if command in ("mode_prev", "mode_next"):
            if asset:
                try:
                    position = MODES.index(asset.settings.mode)
                except ValueError:
                    position = 0
                delta = -1 if command == "mode_prev" else 1
                asset.settings.mode = MODES[(position + delta) % len(MODES)]
                self._save_asset(asset)
            return True

        if command == "toggle_favorite":
            if asset:
                current = bool(self._metadata(asset).get("favorite", False))
                self.library.set_favorite(asset, not current)
                self.invalidate_state()
            return True

        if command == "set_favorite_index":
            if isinstance(value, dict):
                try:
                    target = self.get(int(value.get("index")))
                except Exception:
                    target = None
                if target:
                    self.library.set_favorite(target, bool(value.get("favorite", False)))
                    self.invalidate_state()
            return True

        if command == "set_tags":
            if asset and isinstance(value, list):
                tags = list(
                    dict.fromkeys(str(item).strip() for item in value if str(item).strip())
                )
                self.library.set_tags(asset, tags)
                self.invalidate_state()
            return True

        if command == "batch_add_tag":
            if isinstance(value, dict):
                tag = str(value.get("tag", "")).strip()
                indices = value.get("indices", [])
                changed = False
                if tag and isinstance(indices, list):
                    seen = set()
                    for raw_index in indices:
                        try:
                            index = int(raw_index)
                        except (TypeError, ValueError):
                            continue
                        if index in seen or not 0 <= index < len(self):
                            continue
                        seen.add(index)
                        target = self.get(index)
                        if not target:
                            continue
                        metadata = self._metadata(target)
                        tags = list(metadata.get("tags", []))
                        if tag not in tags:
                            tags.append(tag)
                            self.library.set_tags(target, tags)
                            changed = True
                if changed:
                    self.invalidate_state()
            return True

        if command == "set_processing_profile":
            if asset:
                profile = str(value)
                if profile in PROCESSING_PROFILES:
                    asset.settings.processing_profile = profile
                    self._save_asset(asset)
            return True

        if command == "reset_processing":
            if asset:
                asset.settings.reset_processing()
                self._save_asset(asset)
            return True

        if command not in (
            "zoom",
            "crop_x",
            "crop_y",
            "contrast",
            "saturation",
            "gamma",
            "toggle_sharpen",
            "toggle_dither",
            "reset_image",
        ):
            return False

        if not asset:
            return True
        settings = asset.settings
        changed = False
        if command in ("zoom", "crop_x", "crop_y", "contrast", "saturation", "gamma"):
            try:
                setattr(settings, command, float(value))
                changed = True
            except (TypeError, ValueError):
                pass
        elif command == "toggle_sharpen":
            settings.sharpen = not settings.sharpen
            changed = True
        elif command == "toggle_dither":
            settings.dither = not settings.dither
            changed = True
        elif command == "reset_image":
            settings.reset()
            changed = True

        if changed:
            self._save_asset(asset)
        return True
