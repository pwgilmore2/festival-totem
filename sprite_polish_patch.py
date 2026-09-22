"""Post-process the approved 32x32 overlay sprites for LED readability.

The source sprite pack stays untouched.  This module mutates the decoded
``SPRITES`` dictionary once at import time so UI previews and the simulator use
exactly the same polished masters.
"""

import math
from collections import deque

from overlay_sprite_assets import SPRITES

_DARK = (8, 10, 14)


def _idx(ch):
    return ord(ch) - 33


def _ch(i):
    return chr(i + 33)


def _decode(sprite):
    rows = sprite["rows"]
    palette = [tuple(c) for c in sprite["palette"]]
    h = len(rows)
    w = max((len(r) for r in rows), default=0)
    grid = [[None] * w for _ in range(h)]
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c == ".":
                continue
            i = _idx(c)
            if 0 <= i < len(palette):
                grid[y][x] = palette[i]
    return grid


def _encode(grid):
    # Preserve exact RGB values while keeping the same compact indexed format.
    colors = []
    lookup = {}
    for row in grid:
        for c in row:
            if c is None:
                continue
            c = tuple(int(max(0, min(255, v))) for v in c)
            if c not in lookup:
                lookup[c] = len(colors)
                colors.append(c)
    if len(colors) > 90:
        # These sprites are far below this; guard printable-index encoding.
        colors = colors[:90]
        lookup = {c: i for i, c in enumerate(colors)}
    rows = []
    for row in grid:
        out = []
        for c in row:
            if c is None:
                out.append(".")
            else:
                c = tuple(int(max(0, min(255, v))) for v in c)
                i = lookup.get(c)
                if i is None:
                    i = min(range(len(colors)), key=lambda j: sum((colors[j][k] - c[k]) ** 2 for k in range(3)))
                out.append(_ch(i))
        rows.append("".join(out))
    return {"palette": colors, "rows": rows}


def _neighbors4(x, y, w, h):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            yield nx, ny


def _neighbors8(x, y, w, h):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                yield nx, ny


def _nearest_fill_color(grid, component):
    h = len(grid); w = len(grid[0]) if h else 0
    candidates = []
    for x, y in component:
        for nx, ny in _neighbors8(x, y, w, h):
            c = grid[ny][nx]
            if c is not None and sum(c) > 45:  # avoid using outline black as fill
                candidates.append(c)
    if not candidates:
        return (120, 120, 120)
    return tuple(int(sum(c[k] for c in candidates) / len(candidates)) for k in range(3))


def _fill_small_holes(grid, max_area=10):
    """Fill enclosed transparent pinholes but keep deliberate large cutouts."""
    h = len(grid); w = len(grid[0]) if h else 0
    seen = set()
    for y in range(h):
        for x in range(w):
            if grid[y][x] is not None or (x, y) in seen:
                continue
            q = deque([(x, y)]); seen.add((x, y)); comp = []
            touches_edge = False
            while q:
                px, py = q.popleft(); comp.append((px, py))
                if px in (0, w - 1) or py in (0, h - 1):
                    touches_edge = True
                for nx, ny in _neighbors4(px, py, w, h):
                    if grid[ny][nx] is None and (nx, ny) not in seen:
                        seen.add((nx, ny)); q.append((nx, ny))
            if not touches_edge and len(comp) <= max_area:
                fill = _nearest_fill_color(grid, comp)
                for px, py in comp:
                    grid[py][px] = fill
    return grid


def _close_edge_nicks(grid):
    """Fill tiny one-pixel notches that are mostly surrounded by sprite pixels."""
    h = len(grid); w = len(grid[0]) if h else 0
    add = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if grid[y][x] is not None:
                continue
            ns = [(nx, ny) for nx, ny in _neighbors8(x, y, w, h) if grid[ny][nx] is not None]
            if len(ns) >= 6:
                add.append((x, y, _nearest_fill_color(grid, [(x, y)])))
    for x, y, c in add:
        grid[y][x] = c
    return grid


def _outline(grid, color=_DARK):
    """Add a one-pixel dark silhouette outside the existing artwork."""
    h = len(grid); w = len(grid[0]) if h else 0
    add = set()
    for y in range(h):
        for x in range(w):
            if grid[y][x] is None:
                continue
            for nx, ny in _neighbors8(x, y, w, h):
                if grid[ny][nx] is None:
                    add.add((nx, ny))
    for x, y in add:
        grid[y][x] = color
    return grid


def _rotate45(grid):
    """Rotate the sword master ~45 degrees with nearest-neighbor pixel sampling."""
    h = len(grid); w = len(grid[0]) if h else 0
    pts = [(x, y, grid[y][x]) for y in range(h) for x in range(w) if grid[y][x] is not None]
    if not pts:
        return grid
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    ang = math.radians(-45)
    ca, sa = math.cos(ang), math.sin(ang)
    rotated = []
    for x, y, c in pts:
        dx, dy = x - cx, y - cy
        rx = dx * ca - dy * sa
        ry = dx * sa + dy * ca
        rotated.append((rx, ry, c))
    minx = min(p[0] for p in rotated); maxx = max(p[0] for p in rotated)
    miny = min(p[1] for p in rotated); maxy = max(p[1] for p in rotated)
    rw = maxx - minx + 1; rh = maxy - miny + 1
    scale = min((w - 3) / max(1, rw), (h - 3) / max(1, rh), 1.0)
    out = [[None] * w for _ in range(h)]
    for rx, ry, c in rotated:
        px = int(round((rx - (minx + maxx) / 2) * scale + (w - 1) / 2))
        py = int(round((ry - (miny + maxy) / 2) * scale + (h - 1) / 2))
        if 0 <= px < w and 0 <= py < h:
            out[py][px] = c
            # bridge diagonal nearest-neighbor gaps without making it chunky
            if px + 1 < w and out[py][px + 1] is None:
                out[py][px + 1] = c
    return out


def _define_smiley_mouth(grid):
    h = len(grid); w = len(grid[0]) if h else 0
    # Darken existing low-center facial pixels and bridge tiny mouth breaks.
    for y in range(h // 2, min(h, h // 2 + 9)):
        for x in range(max(0, w // 2 - 8), min(w, w // 2 + 9)):
            c = grid[y][x]
            if c is not None and sum(c) < 180:
                grid[y][x] = _DARK
    return _close_edge_nicks(grid)


def _polish(name):
    if name not in SPRITES:
        return
    grid = _decode(SPRITES[name])

    # Conservative cleanup common to the whole approved pack.
    hole_limit = 6 if name == "Wakaan Sigil" else 12
    _fill_small_holes(grid, hole_limit)
    _close_edge_nicks(grid)

    if name == "Rune 2H":
        grid = _rotate45(grid)
        _close_edge_nicks(grid)
    if name == "Smiley":
        _define_smiley_mouth(grid)

    # Black/dark silhouette requested for every polished icon. For Wakaan this
    # expands outward only, so the deliberate center triangle remains open.
    _outline(grid)
    SPRITES[name] = _encode(grid)


for _name in (
    "Mushroom",
    "Heart",
    "Wakaan Sigil",
    "Sprout",
    "Rune 2H",
    "Alien",
    "Eye",
    "Skull",
    "Smiley",
    "Water Bottle",
):
    _polish(_name)
