"""Simulator-only presentation cleanup.

Imported by secure_phone_server only when simulator.py is the active entry point.
Keeps the simulator presentation tweaks out of the future hardware runtime.
"""
import pygame

_SCALE = 1.25
_original_set_mode = pygame.display.set_mode
_original_rect = pygame.draw.rect
_original_sysfont = pygame.font.SysFont


def _scaled_rect(rect):
    x, y, w, h = rect
    return (
        int(round(x * _SCALE)),
        int(round(y * _SCALE)),
        max(1, int(round(w * _SCALE))),
        max(1, int(round(h * _SCALE))),
    )


def set_mode(size, *args, **kwargs):
    # simulator.py currently requests two 64x32 panels at 8x plus a debug footer.
    # Scale the panel drawing area up and drop the footer from the visible window.
    width = int(round(size[0] * _SCALE))
    panel_height = int(round(256 * _SCALE))
    return _original_set_mode((width, panel_height), *args, **kwargs)


def rect(surface, color, rectangle, *args, **kwargs):
    return _original_rect(surface, color, _scaled_rect(rectangle), *args, **kwargs)


class _QuietFont:
    def __init__(self, wrapped):
        self._wrapped = wrapped

    def render(self, *args, **kwargs):
        # draw_ui() can keep existing for debugging code compatibility while its
        # text becomes invisible in the cleaned-up simulator window.
        return pygame.Surface((1, 1), pygame.SRCALPHA)

    def __getattr__(self, name):
        return getattr(self._wrapped, name)


def sysfont(*args, **kwargs):
    return _QuietFont(_original_sysfont(*args, **kwargs))


pygame.display.set_mode = set_mode
pygame.draw.rect = rect
pygame.font.SysFont = sysfont
