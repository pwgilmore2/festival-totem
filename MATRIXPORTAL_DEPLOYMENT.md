# MatrixPortal S3 deployment model

The Mac is the authoring environment. The MatrixPortal S3 is the playback/runtime environment.

## Build contract

Before copying media to the totem, finish all GIF framing and processing in the simulator. The hardware build permanently bakes those choices into native-size 64×32 GIF files.

The S3 does **not** crop, zoom, reposition, resize, sharpen, dither, adjust gamma, change saturation, or otherwise process GIFs at festival runtime. It only streams the already-prepared files with `gifio.OnDiskGif`.

Build with:

```bash
python tools/prepare_matrixportal_assets.py --clean
```

When CIRCUITPY is mounted, compare the deployment directly against its real free space:

```bash
python tools/prepare_matrixportal_assets.py --clean --target-volume /Volumes/CIRCUITPY
```

Do not use the advertised flash-chip capacity as the deployment budget. CircuitPython firmware and filesystem layout consume part of the physical flash. The mounted volume's reported free space is the useful number.

## Generated build

`matrixportal_build/` contains:

```text
manifest.json
large_icon_data.py
BUILD_REPORT.txt
build_report.json
media/
  000_....gif
  001_....gif
  ...
www/
  index.html
  thumbs/
```

`manifest.json` version 2 records:

- build is baked/read-only media
- per-GIF final byte size
- per-GIF frame count
- per-GIF duration
- source authoring settings for provenance only
- total GIF bytes
- total thumbnail bytes
- controller HTML bytes
- manifest bytes
- total deployment payload

Place transparent icons up to 64×32 in `assets/icons/large/`. The Mac build
compiles them into `large_icon_data.py`, a PIL-free Python module included in
the build. Copy it beside `embedded_icon_library.py` on the board. The native
size compositor limits motion to the space left around each large icon. The
`Liquid Stranger` sample uses the user's original 60×28 dripping-letter
silhouette with a new color treatment. Edit its PNG and rebuild for any
further changes. Test icon RAM and frame timing on hardware.

`BUILD_REPORT.txt` is meant for humans and lists the largest GIFs first so oversized assets are easy to spot.

The build report itself is not part of the required device payload.

## Runtime media model

Front and back each own an independent `gifio.OnDiskGif` decoder/file pointer. Only one synchronous GIF decode is intentionally serviced per scheduler iteration, preventing both sides from creating a large flash/decode spike at the same instant.

The physical matrix uses a double-buffered RGBMatrix framebuffer. Application scheduling remains cooperative/non-blocking: GIF deadlines, rendering, HTTP polling, audio work, state publication, and diagnostics each receive their own timer/deadline rather than using frame-pacing sleeps.

## Measuring real S3 performance

Desktop frame times are not used as estimates for the S3.

For initial hardware testing, copy the hardware modules and prepared media to CIRCUITPY and temporarily use `matrixportal_smoke_test.py` as `code.py`.

The test reports approximately every five seconds:

- delivered FPS
- cooperative loop iterations/second
- free RAM
- GIF decode average/max latency
- display render/present average/max latency
- worst loop duration
- front/back GIF frames advanced

The reusable collector lives in `runtime_metrics.py`. The final S3 application should also feed HTTP-poll, audio-processing, runtime-render, transition, and Chaos timings into that collector so performance problems can be attributed to a specific stage.

## Controller deployment

The phone controller is compiled on the Mac to `www/index.html`. The S3 serves that finished static page.

The S3 should never import the desktop controller builder, Pygame, Pillow, image-editing code, or controller transform modules.

## Future chip login / access control

Authentication is intentionally **not enabled yet**. The current local controller remains frictionless while hardware behavior is still being developed.

`MatrixPortalControlServer` already accepts an optional `access_policy(request)` callable. With no policy, current behavior is unchanged. Later, access control can be added without touching the renderer or command runtime.

The intended future separation is:

```text
network connection / provisioning
        ↓
optional controller login / PIN
        ↓
HTTP API + static controller
        ↓
TotemRuntime
```

Possible final experience:

1. Connect to the totem's network or the same local Wi‑Fi.
2. Open the totem controller address.
3. Enter a short PIN/password once.
4. Receive a lightweight local session token/cookie.
5. Controller/API requests are accepted while that session is valid.

This should stay local-only; no cloud account is required for the totem to work.

A direct-access-point mode can also be added later if we want the S3 to advertise its own festival Wi‑Fi rather than requiring an existing network. Network provisioning and authentication should remain separate features so either can be changed independently.

## What remains before final deployment

The final `code.py` still needs to tie together:

- `TotemRuntime`
- MatrixPortal display backend
- MatrixPortal media adapter
- nonblocking HTTP server
- cooperative timer scheduler
- audio source
- runtime metrics/state publication

Once that exists, the build tool can be extended from "prepared media/controller bundle" to a complete one-command CIRCUITPY staging bundle containing both runtime code and assets.
