"""Nonblocking CircuitPython HTTP control server.

The render loop owns timing and calls ``poll()`` each frame. This avoids desktop
threads entirely and works with any socket source supported by
``adafruit_httpserver``.

``access_policy`` is intentionally optional. Passing no policy keeps today's
controller behavior unchanged. A future login/session implementation can be
plugged in as a callable ``policy(request) -> bool`` without changing runtime,
media, command routing, or display code.
"""

from control_bus import ControlBus


class MatrixPortalControlServer:
    def __init__(
        self,
        socket_source,
        ip_address,
        port=5000,
        root_path="/www",
        thumb_path="/www/thumbs",
        bus=None,
        https=False,
        certfile=None,
        keyfile=None,
        access_policy=None,
    ):
        try:
            from adafruit_httpserver import (
                GET,
                POST,
                FileResponse,
                JSONResponse,
                Response,
                Server,
            )
        except ImportError as exc:
            raise RuntimeError(
                "MatrixPortalControlServer requires adafruit_httpserver"
            ) from exc

        self._GET = GET
        self._POST = POST
        self._FileResponse = FileResponse
        self._JSONResponse = JSONResponse
        self._Response = Response
        self.bus = bus or ControlBus()
        self.ip_address = str(ip_address)
        self.port = int(port)
        self.root_path = root_path
        self.thumb_path = thumb_path
        self.access_policy = access_policy

        kwargs = {"debug": False}
        if https:
            kwargs.update(https=True, certfile=certfile, keyfile=keyfile)
        self.server = Server(socket_source, root_path, **kwargs)

        # Keep request memory bounded. Controller command payloads are small.
        self.server.request_buffer_size = 2048
        self.server.socket_timeout = 0.15
        self._register_routes()

    @property
    def access_control_enabled(self):
        return self.access_policy is not None

    def _allowed(self, request):
        if self.access_policy is None:
            return True
        try:
            return bool(self.access_policy(request))
        except Exception:
            # Authentication errors fail closed without taking down animation.
            return False

    def _unauthorized(self, request, json=False):
        if json:
            return self._JSONResponse(
                request,
                {"ok": False, "error": "unauthorized"},
                status=(401, "Unauthorized"),
            )
        return self._Response(request, "Unauthorized", status=(401, "Unauthorized"))

    def _register_routes(self):
        server = self.server
        GET = self._GET
        POST = self._POST
        FileResponse = self._FileResponse
        JSONResponse = self._JSONResponse
        Response = self._Response
        bus = self.bus
        root_path = self.root_path
        thumb_path = self.thumb_path
        owner = self

        @server.route("/", GET)
        def index(request):
            if not owner._allowed(request):
                return owner._unauthorized(request)
            return FileResponse(request, "index.html", root_path)

        @server.route("/api/state", GET)
        def state(request):
            if not owner._allowed(request):
                return owner._unauthorized(request, json=True)
            return JSONResponse(request, bus.get_state())

        @server.route("/api/command", POST)
        def command(request):
            if not owner._allowed(request):
                return owner._unauthorized(request, json=True)
            payload = request.json()
            if bus.add_payload(payload):
                return JSONResponse(request, {"ok": True})
            return JSONResponse(request, {"ok": False}, status=(400, "Bad Request"))

        @server.route("/thumb/<index>", GET)
        def thumbnail(request, index="0"):
            if not owner._allowed(request):
                return owner._unauthorized(request)
            # Thumbnails are intentionally pre-generated on desktop. The board
            # should never spend festival runtime decoding/resizing previews.
            try:
                filename = "%d.jpg" % int(index)
            except (TypeError, ValueError):
                return Response(request, "Bad thumbnail", status=(400, "Bad Request"))
            return FileResponse(request, filename, thumb_path)

    def update_state(self, state):
        self.bus.update_state(state)

    def get_state(self):
        return self.bus.get_state()

    def add_command(self, command, value=None):
        self.bus.add_command(command, value)

    def get_commands(self):
        return self.bus.get_commands()

    def start(self):
        self.server.start(self.ip_address, self.port)
        scheme = "https" if getattr(self.server, "https", False) else "http"
        return "%s://%s:%d" % (scheme, self.ip_address, self.port)

    def poll(self):
        try:
            return self.server.poll()
        except OSError:
            # WiFi can briefly drop packets; the visual loop should keep running.
            return None

    def stop(self):
        self.server.stop()
