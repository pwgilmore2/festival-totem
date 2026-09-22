"""Small runtime control/state bus shared by constrained backends.

No threading, queue, socket or desktop-only imports live here. The bounded
command list prevents a noisy controller connection from growing memory without
limit on a microcontroller.
"""


class ControlBus:
    def __init__(self, max_commands=48):
        self.max_commands = max(4, int(max_commands))
        self._commands = []
        self._state = {}

    def update_state(self, state):
        # State snapshots are already assembled by the runtime. Keep only the
        # newest snapshot; hardware never needs a history of controller state.
        self._state = state if isinstance(state, dict) else {}

    def get_state(self):
        return self._state

    def add_command(self, command, value=None):
        item = {"command": command, "value": value}
        if len(self._commands) >= self.max_commands:
            # Prefer the newest live-control intent over an old slider/XY event.
            del self._commands[0]
        self._commands.append(item)

    def add_payload(self, payload):
        if not isinstance(payload, dict):
            return False
        command = payload.get("command")
        if not command:
            return False
        self.add_command(command, payload.get("value"))
        return True

    def get_commands(self):
        if not self._commands:
            return []
        out = self._commands
        self._commands = []
        return out

    def clear_commands(self):
        self._commands = []
