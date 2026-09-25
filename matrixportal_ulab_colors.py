"""Vector RGB565 color effects on a displayio.Bitmap's verified 16-bit view.

The full panel is calculated before any pixel is changed. Callers can safely
fall back to the original packed-Python implementation if ulab lacks a needed
operation on a particular firmware build.
"""

from array import array


def _mask(np, values, mask):
    return np.bitwise_and(values, np.array([mask], dtype=np.uint16))


def _shift(np, values, bits, left=False):
    amount = np.array([bits], dtype=np.uint16)
    if left:
        return np.left_shift(values, amount)
    return np.right_shift(values, amount)


def _or(np, a, b):
    return np.bitwise_or(a, b)


def _swap(np, a):
    return _or(np, _shift(np, _mask(np, a, 255), 8, True), _shift(np, a, 8))


def _channels(np, values):
    r5 = _shift(np, values, 11)
    g6 = _mask(np, _shift(np, values, 5), 63)
    b5 = _mask(np, values, 31)
    return (_or(np, _shift(np, r5, 3, True), _shift(np, r5, 2)),
            _or(np, _shift(np, g6, 2, True), _shift(np, g6, 4)),
            _or(np, _shift(np, b5, 3, True), _shift(np, b5, 2)))


def _interpolate(np, a, b, t):
    # ulab integer arrays overflow at 16 bits during interpolation.
    real = getattr(np, "float", float)
    return np.array(np.array(a, dtype=real) * (1.0 - t)
                    + np.array(b, dtype=real) * t, dtype=np.uint16)


def _brighten(np, a, multiplier):
    return np.array(np.minimum(np.array(a, dtype=getattr(np, "float", float)) * multiplier, 255),
                    dtype=np.uint16)


def apply(raw, stride, origin, width, height, swapped, degrees,
          split_amount, brighten_amount, np):
    """Calculate and write a panel; keep the other chained face untouched."""
    source = np.frombuffer(raw, dtype=np.uint16).reshape((height, stride))
    center = np.array(source[:, origin:origin + width], dtype=np.uint16)
    split = split_amount > .02
    if split:
        offset = min(width - 1, max(1, int(round(split_amount * 5))))
        red = np.zeros((height, width), dtype=np.uint16)
        blue = np.zeros((height, width), dtype=np.uint16)
        red[:, :width-offset] = center[:, offset:]
        red[:, width-offset:] = center[:, width-1:width]
        blue[:, offset:] = center[:, :width-offset]
        blue[:, :offset] = center[:, :1]
    else:
        red = blue = center
    if swapped:
        center = _swap(np, center)
        if split:
            red = _swap(np, red)
            blue = _swap(np, blue)
        else:
            red = blue = center

    rr, rg, rb = _channels(np, red)
    if split:
        cr, gg, cb = _channels(np, center)
        br, bg, bb = _channels(np, blue)
    else:
        cr, gg, cb, br, bg, bb = rr, rg, rb, rr, rg, rb
    hue = abs(degrees) >= .5
    if hue:
        phase = (degrees % 360) / 120.0
        t = phase if phase < 1 else phase - 1 if phase < 2 else phase - 2
        if phase < 1:
            r = _interpolate(np, rr, rg, t)
            g = _interpolate(np, gg, cb, t)
            b = _interpolate(np, bb, br, t)
        elif phase < 2:
            r = _interpolate(np, rg, rb, t)
            g = _interpolate(np, cb, cr, t)
            b = _interpolate(np, br if split else cb, bg, t)
        else:
            r = _interpolate(np, rb, rr, t)
            g = _interpolate(np, cr, gg, t)
            b = _interpolate(np, bg if split else rg, bb, t)
    else:
        r, g, b = rr, gg, bb
    if brighten_amount > .001:
        multiplier = 1.0 + max(0.0, float(brighten_amount))
        r = _brighten(np, r, multiplier)
        g = _brighten(np, g, multiplier)
        b = _brighten(np, b, multiplier)
    result = _or(np, _or(np, _shift(np, _mask(np, r, 248), 8, True),
                         _shift(np, _mask(np, g, 252), 3, True)),
                 _shift(np, b, 3))
    if swapped:
        result = _swap(np, result)
    # Commit only after the entire result was calculated successfully. A
    # narrow row assignment avoids an extra 128x32 temporary and never writes
    # to the other panel. Bitmap.dirty() is called by backend.present().
    original = array("H", raw)
    try:
        for y in range(height):
            raw[y * stride + origin:y * stride + origin + width] = memoryview(result[y])
    except Exception:
        for y in range(height):
            start = y * stride + origin
            raw[start:start + width] = original[start:start + width]
        raise
