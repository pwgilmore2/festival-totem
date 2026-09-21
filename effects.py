import pygame
import math
import random


def hsv_to_rgb(h, s=1.0, v=1.0):

    color = pygame.Color(0, 0, 0)

    color.hsva = (
        h % 360,
        s * 100,
        v * 100,
        100
    )

    return color.r, color.g, color.b


def rainbow(display, t):

    for y in range(display.height):
        for x in range(display.width):

            hue = (
                x / display.width * 360
                + t * 80
            )

            display.set_pixel(
                x,
                y,
                hsv_to_rgb(hue)
            )


def waves(display, t):

    for y in range(display.height):
        for x in range(display.width):

            wave = (
                math.sin(
                    x * 0.25
                    + y * 0.15
                    + t * 4
                )
                + 1
            ) / 2

            hue = 180 + wave * 80
            brightness = 0.2 + wave * 0.8

            display.set_pixel(
                x,
                y,
                hsv_to_rgb(
                    hue,
                    1,
                    brightness
                )
            )


def plasma(display, t):

    for y in range(display.height):
        for x in range(display.width):

            value = (
                math.sin(x * 0.15 + t * 2)
                + math.sin(y * 0.2 + t * 1.5)
                + math.sin(
                    (x + y) * 0.1
                    + t * 2
                )
            )

            value = (value + 3) / 6

            display.set_pixel(
                x,
                y,
                hsv_to_rgb(
                    value * 360
                )
            )


def stars(display, t):

    display.clear()

    random.seed(42)

    for i in range(80):

        x = random.randrange(display.width)
        y = random.randrange(display.height)

        brightness = (
            math.sin(t * 3 + i) + 1
        ) / 2

        brightness = 0.1 + brightness * 0.9

        color = (
            int(255 * brightness),
            int(255 * brightness),
            int(255 * brightness)
        )

        display.set_pixel(
            x,
            y,
            color
        )

# This dictionary is what the simulator
# will use to discover available effects.

EFFECTS = {
    "Rainbow": rainbow,
    "Waves": waves,
    "Plasma": plasma,
    "Stars": stars,
}