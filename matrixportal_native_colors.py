"""Original RGB split, hue and brightness using native Bitmap operations.

Work on a separate 64x32 canvas and commit once: a failed native operation
leaves the display untouched so the ulab/pixel fallback can render that frame.
"""


def hue_weights(degrees):
    phase = (degrees % 360) / 120.0
    t = phase if phase < 1 else phase - 1 if phase < 2 else phase - 2
    if phase < 1:
        return (1-t, t, 0, 0, 1-t, t, t, 0, 1-t)
    if phase < 2:
        return (0, 1-t, t, t, 0, 1-t, 0, t, 1-t)
    return (t, 0, 1-t, 1-t, t, 0, 0, 1-t, t)


def apply(framebuffer, origin, width, height, degrees, split_amount,
          brighten_amount):
    import displayio
    import bitmaptools
    import bitmapfilter

    hue = abs(degrees) >= .5
    split = split_amount > .02
    # The fused reference samples multiple channels from shifted source
    # positions *before* hue. Sequential split/hue differs in this case.
    if hue and split:
        return False

    cached = getattr(framebuffer, "native_color_bitmaps", None)
    if cached is None:
        cached = tuple(displayio.Bitmap(width, height, 65536) for _ in range(3))
        framebuffer.native_color_bitmaps = cached
    center, red, blue = cached
    bitmaptools.blit(center, framebuffer.bitmap, 0, 0,
                     x1=origin, y1=0, x2=origin+width, y2=height)

    if split:
        offset = min(width - 1, max(1, int(round(split_amount * 5))))
        # Clamp source x at the edge as in the reference implementation.
        bitmaptools.blit(red, center, 0, 0,
                         x1=offset, y1=0, x2=width, y2=height)
        bitmaptools.blit(blue, center, offset, 0,
                         x1=0, y1=0, x2=width-offset, y2=height)
        for x in range(offset):
            bitmaptools.blit(red, center, width-offset+x, 0,
                             x1=width-1, y1=0, x2=width, y2=height)
            bitmaptools.blit(blue, center, x, 0,
                             x1=0, y1=0, x2=1, y2=height)
        bitmapfilter.mix(red, bitmapfilter.ChannelScale(1, 0, 0))
        bitmapfilter.mix(blue, bitmapfilter.ChannelScale(0, 0, 1))
        bitmapfilter.mix(center, bitmapfilter.ChannelScale(0, 1, 0))
        # Full opacity Screen adds disjoint red/green/blue channels. Normal
        # alpha blending at factor2=1 would erase the previous channels.
        options = dict(factor1=1.0, factor2=1.0,
                       blendmode=bitmaptools.BlendMode.Screen)
        bitmaptools.alphablend(center, center, red,
                               displayio.Colorspace.RGB565_SWAPPED, **options)
        bitmaptools.alphablend(center, center, blue,
                               displayio.Colorspace.RGB565_SWAPPED, **options)
    if hue:
        bitmapfilter.mix(center, bitmapfilter.ChannelMixer(*hue_weights(degrees)))
    if brighten_amount > .001:
        scale = 1.0 + max(0.0, float(brighten_amount))
        bitmapfilter.mix(center, bitmapfilter.ChannelScale(scale, scale, scale))

    bitmaptools.blit(framebuffer.bitmap, center, origin, 0)
    return True
