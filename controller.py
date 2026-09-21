class TotemController:

    def __init__(self, effects):

        self.effects = effects

        self.effect_name = "Rainbow"

        self.speed = 1.0
        self.brightness = 1.0

        self.paused = False

        self.time = 0.0

    @property
    def effect(self):

        return self.effects[self.effect_name]

    def set_effect(self, name):

        if name in self.effects:
            self.effect_name = name
            self.time = 0.0

    def change_speed(self, amount):

        self.speed = max(
            0.1,
            min(5.0, self.speed + amount)
        )

    def change_brightness(self, amount):

        self.brightness = max(
            0.1,
            min(1.0, self.brightness + amount)
        )

    def toggle_pause(self):

        self.paused = not self.paused

    def update(self, dt):

        if not self.paused:
            self.time += dt * self.speed