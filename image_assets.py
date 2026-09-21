import json
from pathlib import Path

from PIL import (
    Image,
    ImageEnhance,
    ImageFilter,
)


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
}


# ============================================================
# IMAGE SETTINGS
# ============================================================

class ImageSettings:

    def __init__(
        self,
        mode="crop",
        crop_x=0.5,
        crop_y=0.5,
        zoom=1.0,
        contrast=1.25,
        saturation=1.35,
        sharpen=True,
        gamma=1.0,
        dither=False,
    ):

        self.mode = mode

        self.crop_x = crop_x
        self.crop_y = crop_y

        self.zoom = zoom

        self.contrast = contrast
        self.saturation = saturation

        self.sharpen = sharpen

        self.gamma = gamma

        self.dither = dither

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    def reset(self):

        self.mode = "crop"

        self.crop_x = 0.5
        self.crop_y = 0.5

        self.zoom = 1.0

        self.contrast = 1.25
        self.saturation = 1.35

        self.sharpen = True

        self.gamma = 1.0

        self.dither = False

    # --------------------------------------------------------
    # SERIALIZE
    # --------------------------------------------------------

    def to_dict(self):

        return {
            "mode": self.mode,
            "crop_x": self.crop_x,
            "crop_y": self.crop_y,
            "zoom": self.zoom,
            "contrast": self.contrast,
            "saturation": self.saturation,
            "sharpen": self.sharpen,
            "gamma": self.gamma,
            "dither": self.dither,
        }

    # --------------------------------------------------------
    # LOAD FROM DICTIONARY
    # --------------------------------------------------------

    @classmethod
    def from_dict(cls, data):

        if not isinstance(data, dict):
            return cls()

        settings = cls()

        settings.mode = data.get(
            "mode",
            settings.mode,
        )

        settings.crop_x = float(
            data.get(
                "crop_x",
                settings.crop_x,
            )
        )

        settings.crop_y = float(
            data.get(
                "crop_y",
                settings.crop_y,
            )
        )

        settings.zoom = float(
            data.get(
                "zoom",
                settings.zoom,
            )
        )

        settings.contrast = float(
            data.get(
                "contrast",
                settings.contrast,
            )
        )

        settings.saturation = float(
            data.get(
                "saturation",
                settings.saturation,
            )
        )

        settings.sharpen = bool(
            data.get(
                "sharpen",
                settings.sharpen,
            )
        )

        settings.gamma = float(
            data.get(
                "gamma",
                settings.gamma,
            )
        )

        settings.dither = bool(
            data.get(
                "dither",
                settings.dither,
            )
        )

        settings.clamp()

        return settings

    # --------------------------------------------------------
    # SAFETY LIMITS
    # --------------------------------------------------------

    def clamp(self):

        self.crop_x = max(
            0.0,
            min(
                1.0,
                self.crop_x,
            ),
        )

        self.crop_y = max(
            0.0,
            min(
                1.0,
                self.crop_y,
            ),
        )

        self.zoom = max(
            1.0,
            min(
                5.0,
                self.zoom,
            ),
        )

        self.contrast = max(
            0.25,
            min(
                3.0,
                self.contrast,
            ),
        )

        self.saturation = max(
            0.0,
            min(
                3.0,
                self.saturation,
            ),
        )

        self.gamma = max(
            0.25,
            min(
                3.0,
                self.gamma,
            ),
        )


# ============================================================
# IMAGE ASSET
# ============================================================

class ImageAsset:

    def __init__(
        self,
        path,
        width=64,
        height=32,
        settings=None,
    ):

        self.path = Path(path)

        self.width = width
        self.height = height

        self.frames = []
        self.durations = []

        self.settings = (
            settings
            if settings is not None
            else ImageSettings()
        )

        # Processed frame cache.
        self.cache = {}

        self.load()

    # ========================================================
    # LOAD FILE
    # ========================================================

    def load(self):

        self.frames = []
        self.durations = []

        with Image.open(self.path) as image:

            frame_count = getattr(
                image,
                "n_frames",
                1,
            )

            for frame_number in range(
                frame_count
            ):

                image.seek(
                    frame_number
                )

                frame = image.convert(
                    "RGB"
                ).copy()

                self.frames.append(
                    frame
                )

                duration = image.info.get(
                    "duration",
                    100,
                )

                if (
                    not duration
                    or duration < 10
                ):
                    duration = 100

                self.durations.append(
                    duration / 1000.0
                )

    # ========================================================
    # CACHE
    # ========================================================

    def clear_cache(self):

        self.cache.clear()

    # ========================================================
    # CROP
    # ========================================================

    def crop_image(
        self,
        image,
        settings,
    ):

        source_width, source_height = (
            image.size
        )

        scale = max(
            self.width / source_width,
            self.height / source_height,
        )

        scale *= settings.zoom

        new_width = max(
            self.width,
            int(source_width * scale),
        )

        new_height = max(
            self.height,
            int(source_height * scale),
        )

        image = image.resize(
            (
                new_width,
                new_height,
            ),
            Image.Resampling.LANCZOS,
        )

        max_x = max(
            0,
            new_width - self.width,
        )

        max_y = max(
            0,
            new_height - self.height,
        )

        left = int(
            max_x * settings.crop_x
        )

        top = int(
            max_y * settings.crop_y
        )

        return image.crop(
            (
                left,
                top,
                left + self.width,
                top + self.height,
            )
        )

    # ========================================================
    # FIT
    # ========================================================

    def fit_image(self, image):

        image = image.copy()

        image.thumbnail(
            (
                self.width,
                self.height,
            ),
            Image.Resampling.LANCZOS,
        )

        canvas = Image.new(
            "RGB",
            (
                self.width,
                self.height,
            ),
            (0, 0, 0),
        )

        x = (
            self.width
            - image.width
        ) // 2

        y = (
            self.height
            - image.height
        ) // 2

        canvas.paste(
            image,
            (x, y),
        )

        return canvas

    # ========================================================
    # PIXEL MODE
    # ========================================================

    def pixel_image(
        self,
        image,
        settings,
    ):

        image = self.crop_image(
            image,
            settings,
        )

        small_width = max(
            16,
            self.width // 2,
        )

        small_height = max(
            8,
            self.height // 2,
        )

        image = image.resize(
            (
                small_width,
                small_height,
            ),
            Image.Resampling.BILINEAR,
        )

        image = image.resize(
            (
                self.width,
                self.height,
            ),
            Image.Resampling.NEAREST,
        )

        return image

    # ========================================================
    # GAMMA
    # ========================================================

    def apply_gamma(
        self,
        image,
        gamma,
    ):

        if abs(
            gamma - 1.0
        ) < 0.001:
            return image

        table = []

        for value in range(256):

            corrected = int(
                (
                    value / 255.0
                ) ** gamma
                * 255
                + 0.5
            )

            corrected = max(
                0,
                min(
                    255,
                    corrected,
                ),
            )

            table.append(
                corrected
            )

        return image.point(
            table * 3
        )

    # ========================================================
    # DITHER
    # ========================================================

    def apply_dither(
        self,
        image,
    ):

        image = image.convert(
            "RGB"
        )

        image = image.quantize(
            colors=64,
            method=Image.Quantize.MEDIANCUT,
            dither=Image.Dither.FLOYDSTEINBERG,
        )

        return image.convert(
            "RGB"
        )

    # ========================================================
    # LED OPTIMIZATION
    # ========================================================

    def optimize_image(
        self,
        image,
        settings,
    ):

        image = self.crop_image(
            image,
            settings,
        )

        image = ImageEnhance.Contrast(
            image
        ).enhance(
            settings.contrast
        )

        image = ImageEnhance.Color(
            image
        ).enhance(
            settings.saturation
        )

        if settings.sharpen:

            image = image.filter(
                ImageFilter.UnsharpMask(
                    radius=1,
                    percent=120,
                    threshold=2,
                )
            )

        image = self.apply_gamma(
            image,
            settings.gamma,
        )

        if settings.dither:

            image = self.apply_dither(
                image
            )

        return image

    # ========================================================
    # PREPARE FRAME
    # ========================================================

    def prepare_frame(
        self,
        frame,
        settings,
    ):

        frame = frame.convert(
            "RGB"
        )

        if settings.mode == "crop":

            image = self.crop_image(
                frame,
                settings,
            )

        elif settings.mode == "fit":

            image = self.fit_image(
                frame
            )

        elif settings.mode == "pixel":

            image = self.pixel_image(
                frame,
                settings,
            )

        elif settings.mode == "optimize":

            image = self.optimize_image(
                frame,
                settings,
            )

        elif settings.mode == "dither":

            image = self.optimize_image(
                frame,
                settings,
            )

            if not settings.dither:
                image = self.apply_dither(
                    image
                )

        else:

            image = self.crop_image(
                frame,
                settings,
            )

        return image

    # ========================================================
    # DETERMINE GIF FRAME
    # ========================================================

    def frame_index_for_time(
        self,
        time,
    ):

        if not self.frames:
            return 0

        if len(
            self.frames
        ) == 1:
            return 0

        total_duration = sum(
            self.durations
        )

        if total_duration <= 0:
            return 0

        position = (
            time % total_duration
        )

        for index, duration in enumerate(
            self.durations
        ):

            if position < duration:
                return index

            position -= duration

        return (
            len(self.frames) - 1
        )

    # ========================================================
    # RENDER
    # ========================================================

    def render(
        self,
        display,
        time,
        settings=None,
    ):

        if not self.frames:
            return

        if settings is None:
            settings = self.settings

        settings.clamp()

        frame_index = (
            self.frame_index_for_time(
                time
            )
        )

        cache_key = (
            frame_index,
            settings.mode,
            round(settings.crop_x, 4),
            round(settings.crop_y, 4),
            round(settings.zoom, 4),
            round(settings.contrast, 3),
            round(settings.saturation, 3),
            settings.sharpen,
            round(settings.gamma, 3),
            settings.dither,
        )

        if cache_key not in self.cache:

            image = self.prepare_frame(
                self.frames[
                    frame_index
                ],
                settings,
            )

            pixels = list(
                image.getdata()
            )

            self.cache[
                cache_key
            ] = pixels

        else:

            pixels = self.cache[
                cache_key
            ]

        index = 0

        for y in range(
            self.height
        ):

            for x in range(
                self.width
            ):

                display.set_pixel(
                    x,
                    y,
                    pixels[index],
                )

                index += 1


# ============================================================
# IMAGE LIBRARY
# ============================================================

class ImageLibrary:

    def __init__(
        self,
        folder="assets/images",
        width=64,
        height=32,
        metadata_file=None,
    ):

        self.folder = Path(
            folder
        )

        self.width = width
        self.height = height

        if metadata_file is None:

            self.metadata_file = (
                self.folder.parent
                / "image_settings.json"
            )

        else:

            self.metadata_file = Path(
                metadata_file
            )

        self.assets = []

        self.metadata = {
            "version": 1,
            "assets": {},
            "playlists": {},
        }

        self.load_metadata()
        self.load()

    # ========================================================
    # LOAD METADATA
    # ========================================================

    def load_metadata(self):

        if not self.metadata_file.exists():
            return

        try:

            with open(
                self.metadata_file,
                "r",
                encoding="utf-8",
            ) as file:

                loaded = json.load(
                    file
                )

            if isinstance(
                loaded,
                dict,
            ):

                self.metadata.update(
                    loaded
                )

            if not isinstance(
                self.metadata.get(
                    "assets"
                ),
                dict,
            ):
                self.metadata[
                    "assets"
                ] = {}

            if not isinstance(
                self.metadata.get(
                    "playlists"
                ),
                dict,
            ):
                self.metadata[
                    "playlists"
                ] = {}

        except Exception as error:

            print(
                "Could not load "
                f"{self.metadata_file}: "
                f"{error}"
            )

    # ========================================================
    # SAVE METADATA
    # ========================================================

    def save_metadata(self):

        try:

            self.metadata_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temporary_file = (
                self.metadata_file
                .with_suffix(
                    ".tmp"
                )
            )

            with open(
                temporary_file,
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    self.metadata,
                    file,
                    indent=2,
                    sort_keys=True,
                )

            temporary_file.replace(
                self.metadata_file
            )

        except Exception as error:

            print(
                "Could not save "
                f"{self.metadata_file}: "
                f"{error}"
            )

    # ========================================================
    # GET/CREATE METADATA ENTRY
    # ========================================================

    def metadata_entry(
        self,
        filename,
    ):

        assets_metadata = (
            self.metadata.setdefault(
                "assets",
                {},
            )
        )

        if filename not in assets_metadata:

            assets_metadata[
                filename
            ] = {
                "tags": [],
                "favorite": False,
                "settings": (
                    ImageSettings()
                    .to_dict()
                ),
            }

        entry = assets_metadata[
            filename
        ]

        entry.setdefault(
            "tags",
            [],
        )

        entry.setdefault(
            "favorite",
            False,
        )

        entry.setdefault(
            "settings",
            ImageSettings().to_dict(),
        )

        return entry

    # ========================================================
    # LOAD LIBRARY
    # ========================================================

    def load(self):

        self.assets.clear()

        self.folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        files = sorted(
            path
            for path in self.folder.iterdir()
            if path.suffix.lower()
            in IMAGE_EXTENSIONS
        )

        metadata_changed = False

        for path in files:

            try:

                filename = (
                    path.name
                )

                existed = (
                    filename
                    in self.metadata.get(
                        "assets",
                        {},
                    )
                )

                entry = (
                    self.metadata_entry(
                        filename
                    )
                )

                if not existed:
                    metadata_changed = True

                settings = (
                    ImageSettings.from_dict(
                        entry.get(
                            "settings",
                            {},
                        )
                    )
                )

                asset = ImageAsset(
                    path,
                    self.width,
                    self.height,
                    settings=settings,
                )

                self.assets.append(
                    asset
                )

                print(
                    f"Loaded: "
                    f"{path.name} "
                    f"("
                    f"{len(asset.frames)} "
                    f"frame(s))"
                )

            except Exception as error:

                print(
                    f"Could not load "
                    f"{path.name}: "
                    f"{error}"
                )

        if metadata_changed:
            self.save_metadata()

    # ========================================================
    # SAVE ONE ASSET
    # ========================================================

    def save_asset(
        self,
        asset,
    ):

        if asset is None:
            return

        filename = (
            asset.path.name
        )

        entry = (
            self.metadata_entry(
                filename
            )
        )

        entry[
            "settings"
        ] = (
            asset.settings.to_dict()
        )

        self.save_metadata()

    # ========================================================
    # SET TAGS
    #
    # Not used by the simulator yet.
    # This is here so phone controls can use
    # the same library later.
    # ========================================================

    def set_tags(
        self,
        asset,
        tags,
    ):

        if asset is None:
            return

        entry = self.metadata_entry(
            asset.path.name
        )

        entry["tags"] = sorted(
            set(
                str(tag).strip()
                for tag in tags
                if str(tag).strip()
            )
        )

        self.save_metadata()

    # ========================================================
    # FAVORITE
    # ========================================================

    def set_favorite(
        self,
        asset,
        favorite=True,
    ):

        if asset is None:
            return

        entry = self.metadata_entry(
            asset.path.name
        )

        entry["favorite"] = bool(
            favorite
        )

        self.save_metadata()

    # ========================================================
    # GET ASSET
    # ========================================================

    def get(
        self,
        index,
    ):

        if not self.assets:
            return None

        index %= len(
            self.assets
        )

        return self.assets[
            index
        ]

    # ========================================================
    # NAMES
    # ========================================================

    def names(self):

        return [
            asset.path.name
            for asset
            in self.assets
        ]

    # ========================================================
    # LENGTH
    # ========================================================

    def __len__(self):

        return len(
            self.assets
        )