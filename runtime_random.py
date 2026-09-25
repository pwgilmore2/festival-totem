"""Random helpers shared by desktop Python and CircuitPython's smaller module."""

import random as _random


class _SeededRandom:
    """Small independent generator for deterministic per-frame visual patterns."""

    def __init__(self, seed=0):
        self.state = int(seed) & 0xFFFFFFFF

    def random(self):
        self.state = (1664525 * self.state + 1013904223) & 0xFFFFFFFF
        return self.state / 4294967296.0

    def randrange(self, start, stop=None):
        if stop is None:
            start, stop = 0, start
        if stop <= start:
            raise ValueError("empty range")
        return int(start) + int(self.random() * (int(stop) - int(start)))

    def randint(self, start, stop):
        return self.randrange(start, stop + 1)

    def uniform(self, start, stop):
        return start + (stop - start) * self.random()

    def choice(self, values):
        return values[self.randrange(len(values))]


Random = getattr(_random, "Random", _SeededRandom)


def random():
    return _random.random()


def randrange(start, stop=None):
    if stop is None:
        return int(_random.random() * start)
    return int(start) + int(_random.random() * (int(stop) - int(start)))


def uniform(start, stop):
    return start + (stop - start) * _random.random()


def choice(values):
    return values[randrange(len(values))]


def shuffle(values):
    for index in range(len(values) - 1, 0, -1):
        other = randrange(index + 1)
        values[index], values[other] = values[other], values[index]
