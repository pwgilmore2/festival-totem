class VirtualDisplay:

    def __init__(self, width=64, height=32):
        self.width = width
        self.height = height

        self.pixels = [
            [(0, 0, 0) for _ in range(width)]
            for _ in range(height)
        ]

    def clear(self):
        self.fill((0, 0, 0))

    def fill(self, color):
        for y in range(self.height):
            for x in range(self.width):
                self.pixels[y][x] = color

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y][x] = color

    def get_pixel(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.pixels[y][x]

        return (0, 0, 0)

    def copy_from(self, other):
        for y in range(self.height):
            for x in range(self.width):
                self.pixels[y][x] = other.get_pixel(x, y)

    def blend_from(self, other):
        for y in range(self.height):
            for x in range(self.width):

                source = other.get_pixel(x, y)

                if source != (0, 0, 0):
                    self.set_pixel(x, y, source)