from PIL import Image


def prepare_image(
    filename,
    width=64,
    height=32
):
    """
    Load an image and convert it to the
    exact pixel dimensions of the LED display.
    """

    image = Image.open(filename)

    # Convert to RGB
    image = image.convert("RGB")

    source_width, source_height = image.size

    # Preserve aspect ratio while covering
    # the entire display.
    source_ratio = source_width / source_height
    display_ratio = width / height

    if source_ratio > display_ratio:

        # Image is wider than display
        new_height = height
        new_width = int(
            source_width
            * (height / source_height)
        )

    else:

        # Image is taller than display
        new_width = width
        new_height = int(
            source_height
            * (width / source_width)
        )

    image = image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )

    # Crop to exact display size
    left = (new_width - width) // 2
    top = (new_height - height) // 2

    image = image.crop(
        (
            left,
            top,
            left + width,
            top + height
        )
    )

    return image


def image_to_display(
    display,
    filename
):

    image = prepare_image(
        filename,
        display.width,
        display.height
    )

    for y in range(display.height):

        for x in range(display.width):

            color = image.getpixel(
                (x, y)
            )

            display.set_pixel(
                x,
                y,
                color
            )