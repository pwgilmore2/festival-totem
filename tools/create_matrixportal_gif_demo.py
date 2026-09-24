"""Generate two small test GIFs and a ready-to-copy MatrixPortal demo bundle."""

import shutil
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "matrixportal_gif_demo_bundle"
COLORS = ("#ff2020", "#20ff50", "#2050ff", "#ffff30")


def build(path, kind):
    frames = []
    for i in range(24):
        frame = Image.new("RGB", (64, 32), "black")
        draw = ImageDraw.Draw(frame)
        if kind == "orbit":
            x = 28 + int(22 * __import__("math").cos(i * 2 * __import__("math").pi / 24))
            y = 12 + int(9 * __import__("math").sin(i * 2 * __import__("math").pi / 24))
            draw.ellipse((x, y, x + 7, y + 7), fill=COLORS[(i // 6) % 4])
        else:
            for x in range(0, 64, 3):
                height = 4 + ((x // 3 + i) * (x // 3 + 3)) % 18
                draw.line((x, 16 - height // 2, x, 16 + height // 2),
                          fill=COLORS[(x // 12 + i // 6) % 4])
        frames.append(frame)
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=100, loop=0, optimize=True, disposal=2)


def main():
    media = OUT / "media"
    media.mkdir(parents=True, exist_ok=True)
    build(media / "test_orbit.gif", "orbit")
    build(media / "test_wave.gif", "wave")
    shutil.copyfile(ROOT / "matrixportal_gif_demo.py", OUT / "code.py")
    archive = shutil.make_archive(str(OUT), "zip", root_dir=OUT)
    print(archive, "bytes:", Path(archive).stat().st_size)


if __name__ == "__main__":
    main()
