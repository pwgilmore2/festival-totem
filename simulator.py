import io

import pygame

from PIL import Image

from display import VirtualDisplay

from effects import (
    EFFECTS,
    hsv_to_rgb,
)

from controller import (
    TotemController,
)

from text import (
    draw_scrolling_text,
)

from particles import (
    ParticleSystem,
)

from image_assets import (
    ImageLibrary,
)

from phone_server import (
    PhoneControlServer,
)


# ============================================================
# DISPLAY CONFIGURATION
# ============================================================

WIDTH = 64
HEIGHT = 32

PIXEL_SIZE = 8

PANEL_WIDTH = (
    WIDTH * PIXEL_SIZE
)

PANEL_HEIGHT = (
    HEIGHT * PIXEL_SIZE
)

PANEL_GAP = 24

UI_HEIGHT = 190

WINDOW_WIDTH = (
    PANEL_WIDTH * 2
    + PANEL_GAP
)

WINDOW_HEIGHT = (
    PANEL_HEIGHT
    + UI_HEIGHT
)


# ============================================================
# PYGAME
# ============================================================

pygame.init()

screen = pygame.display.set_mode(
    (
        WINDOW_WIDTH,
        WINDOW_HEIGHT,
    )
)

pygame.display.set_caption(
    "Festival Totem Simulator"
)

clock = pygame.time.Clock()

font = pygame.font.SysFont(
    None,
    24,
)

small_font = pygame.font.SysFont(
    None,
    20,
)


# ============================================================
# VIRTUAL DISPLAYS
# ============================================================

front_display = VirtualDisplay(
    WIDTH,
    HEIGHT,
)

back_display = VirtualDisplay(
    WIDTH,
    HEIGHT,
)


# ============================================================
# PARTICLES
# ============================================================

particles = ParticleSystem(
    WIDTH,
    HEIGHT,
    count=60,
)


# ============================================================
# IMAGE LIBRARY
# ============================================================

image_library = ImageLibrary(
    "assets/images",
    WIDTH,
    HEIGHT,
)

current_image = 0

IMAGE_MODES = [
    "crop",
    "fit",
    "pixel",
    "optimize",
    "dither",
]


# ============================================================
# IMAGE EDITING
# ============================================================

crop_editor = False


def get_current_asset():

    if len(
        image_library
    ) == 0:

        return None

    return image_library.get(
        current_image
    )


def get_asset_metadata(
    asset,
):

    if asset is None:

        return {
            "tags": [],
            "favorite": False,
        }


    entry = (
        image_library
        .metadata_entry(
            asset.path.name
        )
    )


    return entry


def save_current_asset():

    asset = get_current_asset()

    if asset is None:

        return


    asset.settings.clamp()

    asset.clear_cache()

    image_library.save_asset(
        asset
    )


def select_image(
    index,
):

    global current_image


    if len(
        image_library
    ) == 0:

        return


    try:

        index = int(
            index
        )

    except Exception:

        return


    index = max(
        0,
        min(
            len(image_library) - 1,
            index,
        ),
    )


    current_image = index


    controller.set_effect(
        "Image"
    )


    controller.time = 0.0


def change_image(
    amount,
):

    global current_image


    if len(
        image_library
    ) == 0:

        return


    current_image = (
        current_image
        + amount
    ) % len(
        image_library
    )


    controller.time = 0.0


def change_image_mode(
    amount,
):

    asset = get_current_asset()

    if asset is None:

        return


    settings = (
        asset.settings
    )


    try:

        index = (
            IMAGE_MODES.index(
                settings.mode
            )
        )

    except ValueError:

        index = 0


    index = (
        index + amount
    ) % len(
        IMAGE_MODES
    )


    settings.mode = (
        IMAGE_MODES[
            index
        ]
    )


    save_current_asset()


# ============================================================
# THUMBNAILS
# ============================================================

def get_thumbnail(
    index,
):

    if len(
        image_library
    ) == 0:

        return None


    try:

        index = int(
            index
        )

    except Exception:

        return None


    if (
        index < 0
        or index >= len(
            image_library
        )
    ):

        return None


    asset = (
        image_library.get(
            index
        )
    )


    if (
        asset is None
        or not asset.frames
    ):

        return None


    try:

        source_frame = (
            asset.frames[0]
        )


        preview = (
            asset.prepare_frame(
                source_frame,
                asset.settings,
            )
        )


        preview = (
            preview.resize(
                (
                    256,
                    128,
                ),
                Image.Resampling.NEAREST,
            )
        )


        output = io.BytesIO()


        preview.save(
            output,
            format="JPEG",
            quality=82,
            optimize=True,
        )


        return output.getvalue()


    except Exception as error:

        print(
            "Thumbnail error:",
            error,
        )

        return None


# ============================================================
# CUSTOM EFFECTS
# ============================================================

def rainbow_text(
    display,
    t,
):

    hue = (
        t * 80
    ) % 360


    color = hsv_to_rgb(
        hue,
        1.0,
        1.0,
    )


    draw_scrolling_text(
        display,
        "FESTIVAL MODE",
        t,
        color=color,
        scale=1,
        speed=12,
    )


def layered_party(
    display,
    t,
):

    EFFECTS[
        "Plasma"
    ](
        display,
        t,
    )


    particles.draw(
        display
    )


def imported_image(
    display,
    t,
):

    asset = (
        get_current_asset()
    )


    if asset is None:

        display.clear()

        return


    asset.render(
        display,
        t,
        asset.settings,
    )


# ============================================================
# CONTROLLER
# ============================================================

controller = TotemController(
    {
        **EFFECTS,

        "Text":
            rainbow_text,

        "Party":
            layered_party,

        "Image":
            imported_image,
    }
)


# ============================================================
# PHONE SERVER
# ============================================================

phone_server = PhoneControlServer(
    port=8765
)


phone_server.set_thumbnail_provider(
    get_thumbnail
)


phone_url = (
    phone_server.start()
)


# ============================================================
# PHONE COMMANDS
# ============================================================

def apply_phone_command(
    command_data,
):

    global current_image


    command = (
        command_data.get(
            "command"
        )
    )


    value = (
        command_data.get(
            "value"
        )
    )


    asset = (
        get_current_asset()
    )


    # --------------------------------------------------------
    # EFFECT
    # --------------------------------------------------------

    if command == "effect":

        if (
            value
            in controller.effects
        ):

            controller.set_effect(
                value
            )

        return


    # --------------------------------------------------------
    # DIRECT IMAGE SELECTION
    # --------------------------------------------------------

    if command == "select_image":

        select_image(
            value
        )

        return


    # --------------------------------------------------------
    # FAVORITE CURRENT
    # --------------------------------------------------------

    if command == "toggle_favorite":

        if asset is None:

            return


        entry = (
            get_asset_metadata(
                asset
            )
        )


        image_library.set_favorite(
            asset,
            not entry.get(
                "favorite",
                False,
            ),
        )

        return


    # --------------------------------------------------------
    # FAVORITE FROM GALLERY
    # --------------------------------------------------------

    if command == "set_favorite_index":

        try:

            index = int(
                value.get(
                    "index"
                )
            )


            favorite = bool(
                value.get(
                    "favorite"
                )
            )


            target_asset = (
                image_library.get(
                    index
                )
            )


            if target_asset:

                image_library.set_favorite(
                    target_asset,
                    favorite,
                )


        except Exception:

            pass


        return


    # --------------------------------------------------------
    # TAGS
    # --------------------------------------------------------

    if command == "set_tags":

        if asset is None:

            return


        if not isinstance(
            value,
            list,
        ):

            return


        cleaned_tags = []


        for tag in value:

            tag = str(
                tag
            ).strip()


            if (
                tag
                and tag not in cleaned_tags
            ):

                cleaned_tags.append(
                    tag
                )


        image_library.set_tags(
            asset,
            cleaned_tags,
        )


        return


    # --------------------------------------------------------
    # MASTER
    # --------------------------------------------------------

    if command == "brightness":

        try:

            controller.brightness = max(
                0.1,
                min(
                    1.0,
                    float(value),
                ),
            )

        except Exception:

            pass

        return


    if command == "speed":

        try:

            controller.speed = max(
                0.1,
                min(
                    5.0,
                    float(value),
                ),
            )

        except Exception:

            pass

        return


    if command == "toggle_pause":

        controller.toggle_pause()

        return


    # --------------------------------------------------------
    # LIBRARY NAVIGATION
    # --------------------------------------------------------

    if command == "image_prev":

        change_image(
            -1
        )


        controller.set_effect(
            "Image"
        )


        return


    if command == "image_next":

        change_image(
            1
        )


        controller.set_effect(
            "Image"
        )


        return


    if command == "mode_prev":

        change_image_mode(
            -1
        )

        return


    if command == "mode_next":

        change_image_mode(
            1
        )

        return


    if command == "reload_library":

        old_name = None


        old_asset = (
            get_current_asset()
        )


        if old_asset:

            old_name = (
                old_asset.path.name
            )


        image_library.load()


        current_image = 0


        if old_name:

            for index, item in enumerate(
                image_library.assets
            ):

                if (
                    item.path.name
                    == old_name
                ):

                    current_image = (
                        index
                    )

                    break


        controller.time = 0.0

        return


    # --------------------------------------------------------
    # IMAGE REQUIRED BELOW
    # --------------------------------------------------------

    if asset is None:

        return


    settings = (
        asset.settings
    )


    changed = False


    if command == "zoom":

        try:

            settings.zoom = float(
                value
            )

            changed = True

        except Exception:

            pass


    elif command == "crop_x":

        try:

            settings.crop_x = float(
                value
            )

            changed = True

        except Exception:

            pass


    elif command == "crop_y":

        try:

            settings.crop_y = float(
                value
            )

            changed = True

        except Exception:

            pass


    elif command == "contrast":

        try:

            settings.contrast = float(
                value
            )

            changed = True

        except Exception:

            pass


    elif command == "saturation":

        try:

            settings.saturation = float(
                value
            )

            changed = True

        except Exception:

            pass


    elif command == "gamma":

        try:

            settings.gamma = float(
                value
            )

            changed = True

        except Exception:

            pass


    elif command == "toggle_sharpen":

        settings.sharpen = (
            not settings.sharpen
        )

        changed = True


    elif command == "toggle_dither":

        settings.dither = (
            not settings.dither
        )

        changed = True


    elif command == "reset_image":

        settings.reset()

        changed = True


    if changed:

        settings.clamp()

        save_current_asset()


# ============================================================
# PHONE STATE
# ============================================================

def update_phone_state():

    asset = (
        get_current_asset()
    )


    image_name = None
    image_mode = None
    image_settings = None
    image_tags = []
    image_favorite = False
    image_index = 0


    if asset:

        entry = (
            get_asset_metadata(
                asset
            )
        )


        image_name = (
            asset.path.name
        )


        image_mode = (
            asset.settings.mode
        )


        image_settings = (
            asset.settings.to_dict()
        )


        image_tags = (
            entry.get(
                "tags",
                [],
            )
        )


        image_favorite = bool(
            entry.get(
                "favorite",
                False,
            )
        )


        image_index = (
            current_image + 1
        )


    library = []


    for index, item in enumerate(
        image_library.assets
    ):

        entry = (
            get_asset_metadata(
                item
            )
        )


        library.append(
            {
                "index":
                    index,

                "name":
                    item.path.name,

                "tags":
                    entry.get(
                        "tags",
                        [],
                    ),

                "favorite":
                    bool(
                        entry.get(
                            "favorite",
                            False,
                        )
                    ),
            }
        )


    phone_server.update_state(
        {
            "effect":
                controller.effect_name,

            "speed":
                controller.speed,

            "brightness":
                controller.brightness,

            "paused":
                controller.paused,

            "image_name":
                image_name,

            "image_index":
                image_index,

            "image_count":
                len(
                    image_library
                ),

            "current_image_index":
                current_image,

            "image_mode":
                image_mode,

            "image_settings":
                image_settings,

            "image_tags":
                image_tags,

            "image_favorite":
                image_favorite,

            "library":
                library,

            "effects":
                list(
                    controller.effects.keys()
                ),
        }
    )


# ============================================================
# PANEL DRAWING
# ============================================================

def draw_panel(
    display,
    offset_x,
    offset_y,
):

    for y in range(
        display.height
    ):

        for x in range(
            display.width
        ):

            color = (
                display.get_pixel(
                    x,
                    y,
                )
            )


            brightness = (
                controller.brightness
            )


            adjusted = (
                int(
                    color[0]
                    * brightness
                ),

                int(
                    color[1]
                    * brightness
                ),

                int(
                    color[2]
                    * brightness
                ),
            )


            rectangle = pygame.Rect(
                offset_x
                + x * PIXEL_SIZE,

                offset_y
                + y * PIXEL_SIZE,

                PIXEL_SIZE - 1,
                PIXEL_SIZE - 1,
            )


            pygame.draw.rect(
                screen,
                adjusted,
                rectangle,
            )


# ============================================================
# TEXT HELPER
# ============================================================

def draw_label(
    text,
    x,
    y,
    color=(220, 220, 220),
    use_small=False,
):

    selected_font = (
        small_font
        if use_small
        else font
    )


    surface = (
        selected_font.render(
            text,
            True,
            color,
        )
    )


    screen.blit(
        surface,
        (
            x,
            y,
        ),
    )


# ============================================================
# DESKTOP UI
# ============================================================

def draw_ui():

    ui_y = (
        PANEL_HEIGHT
        + 12
    )


    draw_label(
        f"Effect: {controller.effect_name}",
        10,
        ui_y,
    )


    draw_label(
        f"Speed: {controller.speed:.1f}x",
        210,
        ui_y,
    )


    draw_label(
        (
            "Brightness: "
            f"{int(controller.brightness * 100)}%"
        ),
        365,
        ui_y,
    )


    if controller.paused:

        draw_label(
            "PAUSED",
            600,
            ui_y,
            (255, 180, 80),
        )


    if (
        controller.effect_name
        == "Image"
    ):

        asset = (
            get_current_asset()
        )


        second_line = (
            ui_y + 30
        )


        third_line = (
            second_line + 26
        )


        fourth_line = (
            third_line + 26
        )


        fifth_line = (
            fourth_line + 26
        )


        if asset is None:

            draw_label(
                (
                    "No images found "
                    "in assets/images"
                ),
                10,
                second_line,
            )

            return


        settings = (
            asset.settings
        )


        metadata = (
            get_asset_metadata(
                asset
            )
        )


        favorite_mark = (
            "★"
            if metadata.get(
                "favorite",
                False,
            )
            else ""
        )


        draw_label(
            (
                f"Image "
                f"{current_image + 1}/"
                f"{len(image_library)}: "
                f"{asset.path.name} "
                f"{favorite_mark}"
            ),
            10,
            second_line,
        )


        draw_label(
            (
                f"Mode: {settings.mode}   "
                f"Zoom: {settings.zoom:.2f}   "
                f"Crop: "
                f"{settings.crop_x:.2f}, "
                f"{settings.crop_y:.2f}"
            ),
            10,
            third_line,
            use_small=True,
        )


        draw_label(
            (
                f"Contrast: "
                f"{settings.contrast:.2f}   "

                f"Saturation: "
                f"{settings.saturation:.2f}   "

                f"Gamma: "
                f"{settings.gamma:.2f}   "

                f"Sharpen: "
                f"{'ON' if settings.sharpen else 'OFF'}   "

                f"Dither: "
                f"{'ON' if settings.dither else 'OFF'}"
            ),
            10,
            fourth_line,
            use_small=True,
        )


        tags = metadata.get(
            "tags",
            [],
        )


        tag_text = (
            ", ".join(
                tags
            )
            if tags
            else "none"
        )


        draw_label(
            (
                f"Tags: {tag_text}"
            ),
            10,
            fifth_line,
            use_small=True,
        )


    else:

        draw_label(
            (
                "1 Rainbow | 2 Waves | "
                "3 Plasma | 4 Stars | "
                "5 Text | 6 Party | 7 Image"
            ),
            10,
            ui_y + 32,
            use_small=True,
        )


        draw_label(
            (
                "Phone controller: "
                f"{phone_url}"
            ),
            10,
            ui_y + 58,
            use_small=True,
        )


# ============================================================
# IMAGE EDITOR KEYBOARD
# ============================================================

def handle_crop_editor_key(
    key,
):

    global crop_editor


    asset = (
        get_current_asset()
    )


    if asset is None:

        return


    settings = (
        asset.settings
    )


    changed = False


    crop_step = 0.025

    zoom_step = 0.05


    if key == pygame.K_a:

        settings.crop_x -= (
            crop_step
        )

        changed = True


    elif key == pygame.K_d:

        settings.crop_x += (
            crop_step
        )

        changed = True


    elif key == pygame.K_w:

        settings.crop_y -= (
            crop_step
        )

        changed = True


    elif key == pygame.K_s:

        settings.crop_y += (
            crop_step
        )

        changed = True


    elif key in (
        pygame.K_EQUALS,
        pygame.K_PLUS,
        pygame.K_KP_PLUS,
    ):

        settings.zoom += (
            zoom_step
        )

        changed = True


    elif key in (
        pygame.K_MINUS,
        pygame.K_KP_MINUS,
    ):

        settings.zoom -= (
            zoom_step
        )

        changed = True


    elif key == pygame.K_r:

        settings.crop_x = 0.5

        settings.crop_y = 0.5

        settings.zoom = 1.0

        changed = True


    elif key in (
        pygame.K_c,
        pygame.K_RETURN,
        pygame.K_ESCAPE,
    ):

        crop_editor = False

        save_current_asset()

        return


    if changed:

        settings.clamp()

        save_current_asset()


# ============================================================
# NORMAL IMAGE KEYBOARD CONTROLS
# ============================================================

def handle_image_key(
    key,
):

    global crop_editor


    asset = (
        get_current_asset()
    )


    if key == pygame.K_COMMA:

        change_image(
            -1
        )

        return


    if key == pygame.K_PERIOD:

        change_image(
            1
        )

        return


    if asset is None:

        return


    settings = (
        asset.settings
    )


    changed = False


    if key == pygame.K_LEFTBRACKET:

        change_image_mode(
            -1
        )

        return


    elif key == pygame.K_RIGHTBRACKET:

        change_image_mode(
            1
        )

        return


    elif key == pygame.K_c:

        crop_editor = True

        return


    elif key == pygame.K_o:

        settings.contrast -= 0.05

        changed = True


    elif key == pygame.K_p:

        settings.contrast += 0.05

        changed = True


    elif key == pygame.K_k:

        settings.saturation -= 0.05

        changed = True


    elif key == pygame.K_l:

        settings.saturation += 0.05

        changed = True


    elif key == pygame.K_g:

        settings.gamma -= 0.05

        changed = True


    elif key == pygame.K_h:

        settings.gamma += 0.05

        changed = True


    elif key == pygame.K_t:

        settings.sharpen = (
            not settings.sharpen
        )

        changed = True


    elif key == pygame.K_y:

        settings.dither = (
            not settings.dither
        )

        changed = True


    elif key == pygame.K_x:

        settings.reset()

        changed = True


    if changed:

        settings.clamp()

        save_current_asset()


# ============================================================
# KEYBOARD
# ============================================================

def handle_keydown(
    key,
):

    global crop_editor


    if (
        crop_editor
        and controller.effect_name
        == "Image"
    ):

        handle_crop_editor_key(
            key
        )

        return True


    if key == pygame.K_ESCAPE:

        return False


    if key == pygame.K_1:

        controller.set_effect(
            "Rainbow"
        )


    elif key == pygame.K_2:

        controller.set_effect(
            "Waves"
        )


    elif key == pygame.K_3:

        controller.set_effect(
            "Plasma"
        )


    elif key == pygame.K_4:

        controller.set_effect(
            "Stars"
        )


    elif key == pygame.K_5:

        controller.set_effect(
            "Text"
        )


    elif key == pygame.K_6:

        controller.set_effect(
            "Party"
        )


    elif key == pygame.K_7:

        controller.set_effect(
            "Image"
        )


    elif key == pygame.K_UP:

        controller.change_speed(
            0.1
        )


    elif key == pygame.K_DOWN:

        controller.change_speed(
            -0.1
        )


    elif key == pygame.K_RIGHT:

        controller.change_brightness(
            0.05
        )


    elif key == pygame.K_LEFT:

        controller.change_brightness(
            -0.05
        )


    elif key == pygame.K_SPACE:

        controller.toggle_pause()


    elif (
        controller.effect_name
        == "Image"
    ):

        handle_image_key(
            key
        )


    return True


# ============================================================
# INITIAL PHONE STATE
# ============================================================

update_phone_state()


# ============================================================
# MAIN LOOP
# ============================================================

running = True


while running:

    dt = (
        clock.tick(60)
        / 1000.0
    )


    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False


        elif event.type == pygame.KEYDOWN:

            running = handle_keydown(
                event.key
            )


    for command_data in (
        phone_server
        .get_commands()
    ):

        apply_phone_command(
            command_data
        )


    controller.update(
        dt
    )


    if not controller.paused:

        particles.update(
            dt
        )


    controller.effect(
        front_display,
        controller.time,
    )


    back_display.copy_from(
        front_display
    )


    screen.fill(
        (15, 15, 18)
    )


    draw_panel(
        front_display,
        0,
        0,
    )


    draw_panel(
        back_display,
        PANEL_WIDTH
        + PANEL_GAP,
        0,
    )


    draw_ui()


    update_phone_state()


    pygame.display.flip()


# ============================================================
# SHUTDOWN
# ============================================================

phone_server.stop()

pygame.quit()