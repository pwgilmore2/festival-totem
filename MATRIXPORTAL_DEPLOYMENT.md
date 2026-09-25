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

Place transparent icons up to 72×40 in `assets/icons/large/`. The Mac build
compiles them into `large_icon_data.py`, a PIL-free Python module included in
the build. Copy it beside `embedded_icon_library.py` on the board. The native
size compositor centers the canvas and clips pixels beyond the 64×32 panel;
full-size and oversized icons may clip another two pixels during Orbit. The
`Liquid Stranger` sample uses the user's original 60×28 dripping-letter
silhouette with a new color treatment. Edit its PNG and rebuild for any
further changes. Test icon RAM and frame timing on hardware.

`BUILD_REPORT.txt` is meant for humans and lists the largest GIFs first so oversized assets are easy to spot.

The build report itself is not part of the required device payload.

## Runtime media model

Front and back each own an independent `gifio.OnDiskGif` decoder/file pointer. Only one synchronous GIF decode is intentionally serviced per scheduler iteration, preventing both sides from creating a large flash/decode spike at the same instant.

Application scheduling remains cooperative/non-blocking: GIF deadlines, rendering, HTTP polling, audio work, state publication, and diagnostics each receive their own timer/deadline rather than using frame-pacing sleeps.

Physical tests on CircuitPython 10.3.1 invalidated that framebuffer assumption:
passing a Python-owned RGB565 array into `rgbmatrix.RGBMatrix` caused a hard
fault even at bit depth 1 without doublebuffer. The verified display path uses
a 16-bit `displayio.Bitmap` and `framebufferio.FramebufferDisplay`, which left
2,037,824 bytes of free RAM after canvas allocation. The backend now maps
logical panel pixel indices to this bitmap and calls `display.refresh()`. Its
runtime adapter passed its first on-device color-square check on 2026-09-25;
the full renderer, frame-rate and GIF/effects combinations still need tests.

## Measuring real S3 performance

Desktop frame times are not used as estimates for the S3.

On 2026-09-24, the physical board showed stable pixels with the minimal
`framebufferio` diagnostic at bit depth 1. Both panels display a requested
RGB sequence as RBG; `matrixportal_backend.py` now swaps G/B pin assignments.
The original custom-framebuffer first-light test at bit depth 3 hard-faulted;
do not assume that backend is device validated. To move to animated media
without that backend, run `python tools/create_matrixportal_gif_demo.py` and
copy the resulting `matrixportal_gif_demo_bundle` contents to CIRCUITPY. The
single GIF decoder's bitmap is shared by both panels and emits frame counts,
worst decode time and free RAM every five seconds. Two synthetic tiny GIFs are
provided because the repo checkout has no user GIFs in `assets/images/`.
This is a display/media stepping stone, not the final phone-controlled app.

After the 2-GIF demo worked on physical panels, a separate `matrixportal_phone_demo.py`
was added for a minimal phone networking check. Copy it as `code.py` along
with the same `media/` folder; it starts a temporary WPA access point
`Festival-Totem-Test` with the bench password stored at the top of the file,
and serves a two-button selector at the printed `http://` address. The
phone demo is unverified on the S3 and is not the compiled full phone UI.

First verify panel mapping with `matrixportal_first_light.py`: copy it as
`CIRCUITPY/code.py` and copy `matrixportal_backend.py` beside it. The panel
connected directly to MatrixPortal should cycle dim red/green/blue every two
seconds, while the chained panel cycles dim blue/red/green. This requires no
GIF assets or installed library bundle. If CircuitPython raises an exception,
read the serial console before changing the panel wiring. Connect/disconnect
HUB75 cables only when power is off. The test has no device-side validation
until run on the physical board.

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

The compiled page includes scene controls under the Vibe slideshow buttons. The shared runtime implements
combined Clock + Weather (default time-based day/dusk/night sky; optional Black), four-day Wakaan Set Times, and a waveform drawn from the normalized
audio signals; those scenes stop GIF rendering and release the decoder on a
hardware adapter. The Mirrored panel mode renders one face and copies the final pixels
to the other, suspending its decoder. Text and icon controls can fade onto a
black background and back to GIFs. These paths have desktop tests but require
the final device `code.py` and physical measurements before being considered
working on MatrixPortal. Clock time is sent by the phone on page load and resynced while the page is open, using America/Chicago and its DST offset. Selecting Clock + Weather also asks the phone to refresh weather from Open-Meteo using festival venue coordinates; optional phone GPS on HTTPS and manual entries remain available. The S3 does not fetch weather, and the clock continues with the last saved weather if a refresh fails. The confirmed official alphabetical artist roster appears in the phone editor, without unannounced day assignments or set times. Acts can be entered without times and organized into Wednesday through Saturday; time-based advancement begins when times are entered. Set times persist in phone localStorage only. The top phone-audio button and Waveform both request the browser mic, which still needs HTTPS. Vibe has a collapsed Scenes drawer, distinct colored and uppercase audio presets, a gradient Shuffle control, and taller colored audio level meters. Vibe preset choices and audio meters are in Vibe; editable audio mappings, preset management, clock/weather settings, set-time editor, quick text editing, and the shared Overlay Behavior (background and icon motion) control are in folded Manage → Setup groups. Panels has one three-mode choice: Independent, Linked (separately rendered) or Mirrored (one render copied). GIF Library and Edit / Tags also use folded groups. Black, Dimmed, and None apply to both icon and text. Dimmed multiplies the underlying GIF by 0.65 before drawing either overlay; profile that per-pixel pass on the S3. Shared Off/Subtle/Intense overlay audio varies brightness without changing glyph size or adding neighboring glow pixels. Preferences persist in phone localStorage; the board receives commands again when the controller reconnects.
Until an on-device schedule file and clock sync are added, a restart without
reconnecting the phone loses those values.

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

### Overlay polish before board testing

Text dissolves in/out and between message, font, size and color edits. Static text shares icon Bounce/Orbit; long text keeps its scrolling layout. Manage → Setup → Overlay Behavior now owns background, motion and shared music response; Display contains panel modes and targeting. Text transitions retain only small settings snapshots, with a deterministic dissolve adapter writing into the existing framebuffer. Icon rendering no longer allocates a pixel list or per-pixel Random objects. These changes have desktop regression coverage; frame cost and memory still need physical S3 measurements. The final device integration blockers above remain open.
