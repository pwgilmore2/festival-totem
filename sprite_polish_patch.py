"""Post-process the approved 32x32 overlay sprites for LED readability.

The source sprite pack stays untouched. This module mutates the decoded
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
            if c is not None and sum(c) > 45:
                candidates.append(c)
    if not candidates:
        return (120, 120, 120)
    return tuple(int(sum(c[k] for c in candidates) / len(candidates)) for k in range(3))


def _transparent_components(grid):
    h = len(grid); w = len(grid[0]) if h else 0
    seen = set()
    out = []
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
            out.append((comp, touches_edge))
    return out


def _protected_negative_space(name, grid):
    """Return deliberate transparent pixels that must stay transparent."""
    if name != "Wakaan Sigil":
        return set()

    # The sigil's center triangle is its one intentional enclosed cutout.
    enclosed = [comp for comp, edge in _transparent_components(grid) if not edge]
    if not enclosed:
        return set()
    return set(max(enclosed, key=len))


def _fill_enclosed_holes(grid, protected=None):
    """Fill every enclosed transparent pocket except explicitly protected art."""
    protected = protected or set()
    for comp, touches_edge in _transparent_components(grid):
        if touches_edge:
            continue
        fillable = [(x, y) for x, y in comp if (x, y) not in protected]
        if not fillable:
            continue
        fill = _nearest_fill_color(grid, fillable)
        for x, y in fillable:
            grid[y][x] = fill
    return grid


def _fill_internal_cracks(grid, protected=None, passes=3):
    """Close transparent cracks that visually sit inside the sprite silhouette.

    Unlike flood-fill holes, these can still connect to the outside through a
    one-pixel channel. A pixel is treated as internal when sprite pixels bracket
    it horizontally/vertically or it has strong local occupancy.
    """
    protected = protected or set()
    h = len(grid); w = len(grid[0]) if h else 0
    for _ in range(passes):
        add = []
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if grid[y][x] is not None or (x, y) in protected:
                    continue
                left = any(grid[y][xx] is not None for xx in range(0, x))
                right = any(grid[y][xx] is not None for xx in range(x + 1, w))
                up = any(grid[yy][x] is not None for yy in range(0, y))
                down = any(grid[yy][x] is not None for yy in range(y + 1, h))
                occupied = sum(1 for nx, ny in _neighbors8(x, y, w, h) if grid[ny][nx] is not None)

                bracketed_both = left and right and up and down
                narrow_crack = occupied >= 4 and ((left and right) or (up and down))
                if bracketed_both or narrow_crack:
                    add.append((x, y, _nearest_fill_color(grid, [(x, y)])))
        if not add:
            break
        for x, y, c in add:
            grid[y][x] = c
    return grid


def _close_edge_nicks(grid, protected=None):
    protected = protected or set()
    h = len(grid); w = len(grid[0]) if h else 0
    add = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if grid[y][x] is not None or (x, y) in protected:
                continue
            ns = [(nx, ny) for nx, ny in _neighbors8(x, y, w, h) if grid[ny][nx] is not None]
            if len(ns) >= 5:
                add.append((x, y, _nearest_fill_color(grid, [(x, y)])))
    for x, y, c in add:
        grid[y][x] = c
    return grid


def _outline(grid, color=_DARK):
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
            if px + 1 < w and out[py][px + 1] is None:
                out[py][px + 1] = c
    return out


def _define_smiley_mouth(grid):
    h = len(grid); w = len(grid[0]) if h else 0
    for y in range(h // 2, min(h, h // 2 + 9)):
        for x in range(max(0, w // 2 - 8), min(w, w // 2 + 9)):
            c = grid[y][x]
            if c is not None and sum(c) < 180:
                grid[y][x] = _DARK
    return grid


def _polish(name):
    if name not in SPRITES:
        return
    grid = _decode(SPRITES[name])
    protected = _protected_negative_space(name, grid)

    # Fill transparency that reads as accidental missing LEDs. This is now
    # intentionally aggressive; the sprite's exterior is still preserved by
    # only filling enclosed pockets or pixels visually bracketed by artwork.
    _fill_enclosed_holes(grid, protected)
    _fill_internal_cracks(grid, protected, passes=3)
    _close_edge_nicks(grid, protected)

    if name == "Rune 2H":
        grid = _rotate45(grid)
        _fill_internal_cracks(grid, passes=2)
        _close_edge_nicks(grid)
    if name == "Smiley":
        _define_smiley_mouth(grid)

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
