"""One-shot, non-destructive Bitmap buffer timing on CircuitPython.

Do not use the RGBMatrix buffer here: the physical board rejected direct
matrix writes. This checks only the displayio.Bitmap owned by the backend.
"""

import time


def run(bitmap):
    try:
        from ulab import numpy
        print("ULAB: present; frombuffer", hasattr(numpy, "frombuffer"))
        if hasattr(numpy, "frombuffer"):
            pixels = numpy.frombuffer(memoryview(bitmap), dtype=numpy.uint16)
            print("ULAB: Bitmap view length", len(pixels),
                  "bitwise_and", hasattr(numpy, "bitwise_and"),
                  "right_shift", hasattr(numpy, "right_shift"))
            if (len(pixels) == bitmap.width * bitmap.height
                    and hasattr(numpy, "bitwise_and")
                    and hasattr(numpy, "right_shift")):
                values = numpy.array(range(2048), dtype=numpy.uint16)
                mask = numpy.array([0xF800], dtype=numpy.uint16)
                shift = numpy.array([11], dtype=numpy.uint16)
                started = time.monotonic()
                red = numpy.right_shift(numpy.bitwise_and(values, mask), shift)
                print("ULAB: 2048 mask/shift ms", (time.monotonic() - started) * 1000,
                      "last", red[2047])
    except ImportError:
        print("ULAB: unavailable on this firmware")
    except Exception as exc:
        print("ULAB: Bitmap operation unavailable", type(exc).__name__, str(exc))
    width, height = bitmap.width, bitmap.height
    first, last = bitmap[0, 0], bitmap[width - 1, height - 1]
    try:
        view = memoryview(bitmap)
        if len(view) != width * height:
            cast = getattr(view, "cast", None)
            view = cast("H") if cast else None
        if view is None or len(view) != width * height:
            print("BITMAP BUFFER: not a 16-bit pixel view")
            return
        bitmap[0, 0] = 0x1234
        bitmap[width - 1, height - 1] = 0xABCD
        matches = view[0] == 0x1234 and view[width * height - 1] == 0xABCD
        bitmap[0, 0], bitmap[width - 1, height - 1] = first, last
        if not matches:
            print("BITMAP BUFFER: pixel order mismatch; direct path disabled")
            return
        start = time.monotonic()
        total = 0
        for i in range(2048):
            total += view[i]
        read_ms = (time.monotonic() - start) * 1000
        start = time.monotonic()
        for i in range(2048):
            view[i] = view[i]
        write_ms = (time.monotonic() - start) * 1000
        bitmap.dirty(0, 0, 64, 32)
        print("BITMAP BUFFER: 2048 read ms", read_ms, "write ms", write_ms,
              "length", len(view), "checksum", total)
    except Exception as exc:
        bitmap[0, 0], bitmap[width - 1, height - 1] = first, last
        print("BITMAP BUFFER: unavailable", type(exc).__name__, str(exc))
