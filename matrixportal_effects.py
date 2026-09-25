"""Small CircuitPython-safe counterparts to the desktop's base effects."""

import math
import runtime_random as random


def hsv(h, saturation=1.0, value=1.0):
    h = (h % 360) / 60.0
    chroma = value * saturation
    second = chroma * (1 - abs(h % 2 - 1))
    if h < 1:
        channels = (chroma, second, 0)
    elif h < 2:
        channels = (second, chroma, 0)
    elif h < 3:
        channels = (0, chroma, second)
    elif h < 4:
        channels = (0, second, chroma)
    elif h < 5:
        channels = (second, 0, chroma)
    else:
        channels = (chroma, 0, second)
    offset = value - chroma
    return tuple(int(255 * (channel + offset)) for channel in channels)


def rainbow(display, t):
    for y in range(display.height):
        for x in range(display.width):
            display.set_pixel(x, y, hsv(x * 360 / display.width + t * 80))


def waves(display, t):
    for y in range(display.height):
        for x in range(display.width):
            wave = (math.sin(x * .25 + y * .15 + t * 4) + 1) / 2
            display.set_pixel(x, y, hsv(180 + wave * 80, 1, .2 + wave * .8))


def plasma(display, t):
    for y in range(display.height):
        for x in range(display.width):
            value = (math.sin(x * .15 + t * 2) + math.sin(y * .2 + t * 1.5)
                     + math.sin((x + y) * .1 + t * 2) + 3) / 6
            display.set_pixel(x, y, hsv(value * 360))


def stars(display, t):
    display.clear()
    rng = random.Random(42)
    for i in range(80):
        level = int(255 * (.1 + .9 * (math.sin(t * 3 + i) + 1) / 2))
        display.set_pixel(rng.randrange(display.width), rng.randrange(display.height),
                          (level, level, level))


EFFECTS = {"Rainbow": rainbow, "Waves": waves, "Plasma": plasma, "Stars": stars}
