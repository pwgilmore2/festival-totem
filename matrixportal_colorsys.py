"""Only the colorsys operation needed by text_engine on CircuitPython."""


class colorsys:
    @staticmethod
    def hsv_to_rgb(h, s, v):
        h = h % 1.0
        sector = int(h * 6)
        fraction = h * 6 - sector
        p = v * (1 - s)
        q = v * (1 - fraction * s)
        t = v * (1 - (1 - fraction) * s)
        return ((v, t, p), (q, v, p), (p, v, t), (p, q, v),
                (t, p, v), (v, p, q))[sector % 6]
