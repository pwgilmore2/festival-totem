import random
import math


class Particle:

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.reset()

    def reset(self):

        self.x = random.uniform(0, self.width - 1)
        self.y = random.uniform(0, self.height - 1)

        self.speed = random.uniform(2.0, 8.0)

        self.phase = random.uniform(
            0,
            math.pi * 2
        )

        self.brightness = random.uniform(
            0.5,
            1.0
        )

    def update(self, dt):

        self.y -= self.speed * dt

        self.x += (
            math.sin(
                self.y * 0.3 + self.phase
            )
            * dt
            * 2
        )

        if self.y < 0:
            self.y = self.height - 1
            self.x = random.uniform(
                0,
                self.width - 1
            )

        if self.x < 0:
            self.x = self.width - 1

        if self.x >= self.width:
            self.x = 0

    def draw(self, display):

        x = int(self.x)
        y = int(self.y)

        twinkle = (
            math.sin(
                self.y * 0.5 + self.phase
            ) + 1
        ) / 2

        brightness = (
            0.35 +
            twinkle * 0.65
        ) * self.brightness

        color = (
            int(255 * brightness),
            int(255 * brightness),
            int(255 * brightness)
        )

        display.set_pixel(
            x,
            y,
            color
        )


class ParticleSystem:

    def __init__(
        self,
        width,
        height,
        count=40
    ):

        self.particles = [
            Particle(
                width,
                height
            )
            for _ in range(count)
        ]

    def update(self, dt):

        for particle in self.particles:
            particle.update(dt)

    def draw(self, display):

        for particle in self.particles:
            particle.draw(display)