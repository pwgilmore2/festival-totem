# MatrixPortal S3 deployment model

The Mac is the authoring environment. The MatrixPortal S3 is the playback/runtime environment.

## Build contract

Before copying media to the totem, finish all GIF framing and processing in the simulator. The hardware build permanently bakes those choices into native-size 64×32 GIF files.

The S3 does **not** crop, zoom, reposition, resize, sharpen, dither, adjust gamma, change saturation, or otherwise process GIFs at festival runtime. It only streams the already-prepared files with `gifio.OnDiskGif`.

Build with:

```bash
python tools/prepare_matrixportal_assets.py --clean
```

The build now copies `code.py` and its CircuitPython-safe local modules into
`matrixportal_build/` alongside the assets. Copy its **contents** to CIRCUITPY,
and install the matching `adafruit_httpserver` library from the CircuitPython
10.x library bundle in `CIRCUITPY/lib/`. Set a private WPA password (at least
eight characters) in `code.py` before building. This first integrated app is
software-only until tested on the S3; it requires at least one baked GIF in
the manifest. Start with a small sample of the user's GIFs in `assets/images/`
and review the storage report against the mounted board's free space. The AP
prints its controller URL to serial. The browser microphone still requires a
secure origin; HTTP can exercise the rest of the compiled UI and commands.

After preparing assets and renaming the previous `CIRCUITPY/code.py`, run
`python3 tools/deploy_matrixportal.py` from the Mac. It checks free space,
copies and verifies every file directly, then writes `code.py` last. Install
the external 10.x `adafruit_httpserver` library separately. This avoids the
temporary-file rename that failed with the earlier rsync transfer; it has not
yet been validated on the board.

The integrated loop reports FPS, RAM, loop maximum and HTTP, command, GIF
decode/check, update, render, present, and state timings every five seconds.
Use those board numbers to decide whether the initial 20 FPS target is viable.
The first integrated run on September 25 measured about 0.66 FPS and
1.43–1.45 seconds per runtime render, with roughly 540 KB free RAM. GIF decode
and display refresh were much shorter. A subsequent hardware-only optimization
removes four per-frame panel snapshots and captures only when a transition
starts. Its physical effect remains unmeasured; log a fresh `Performance:`
window and observe whether display lines occur only on content transitions.

After that run the board repeatedly disconnected and its filesystem appeared
nearly empty. To isolate the display/media path, create a small profile build:

```bash
python3 tools/stage_bitmap_profile.py --target-volume /Volumes/CIRCUITPY
```

This uses up to two previously baked GIFs in `matrixportal_build/`, mirroring
each through the same 128×32 Bitmap backend. It excludes the full runtime and
Wi-Fi. Copy `matrixportal_profile_build/media/`, its `manifest.json` and
`matrixportal_backend.py` to CIRCUITPY, then copy its `code.py` last. The board
prints GIF index, RAM, FPS and worst decode/copy/present times. Use `--count 1`
if the second file will not fit. The profile is a diagnostic, not a replacement
for the full app. Its first physical run reported ~2 FPS because the Python
per-pixel GIF copy took up to 508 ms; decode and refresh were only 4 and 8 ms.
The revised profile opts into an optional RGB565_SWAPPED storage mode with
native `bitmaptools.blit` and needs a hardware test for speed, color and
stability. The user measured 11.4 FPS and ~4.1 ms max native copy on the
one-GIF profile and reported a stable display. The integrated `code.py` now
opts into that mode too; full runtime overlays, HTTP and transitions still need
physical testing. The backend default remains the previously verified RGB565
path.

After repairing the board FAT volume and using the direct deployer, the first
integrated physical run sustained ~14.8–15.0 FPS with 1.34–1.35 MB free RAM,
~6.5 ms average runtime render, ~7.1–7.3 ms average present and ~4.6 ms worst
decode/check. Phone UI interactions and extended stability still need testing.
The loop had scheduled its next frame after render/present; a follow-up code
change schedules the 50 ms period from frame start. That change has not yet
been measured on hardware.

On the first phone connection, state publication reached `InfoScenes.local_time()`
and raised because CircuitPython 10.3.1 lacks `time.gmtime`. The board clock
now falls back to `time.localtime(seconds)` after applying the phone-supplied
festival offset. Copy only the project-root `info_scenes.py` to CIRCUITPY,
reset, and retry with serial attached. This change awaits a physical retest.

An icon then appeared successfully, but the default Dimmed overlay reduced
render speed to ~1.7 seconds per frame (~0.52 FPS). A packed RGB565 board
`dim()` in `matrixportal_backend.py`, used by `text_engine.py`, avoids tuple
conversion on every display pixel. Copy both project-root files for the next
test; the physical performance gain has not yet been measured. The `None`
background choice in Manage → Setup → Overlay Behavior skips dimming and can
isolate the cost while testing from the phone.

The on-device retest measured ~580 ms average render with an icon still visible
and ~1.3 FPS, so packed dimming alone is too slow. The next candidate uses
`None` for its hardware default overlay background (GIF remains visible under
the icon), targets 30 FPS, and records optional dim/icon/transition timings.
The phone may restore `Dimmed` from localStorage when its page opens: choose
`None` explicitly in Manage → Setup → Overlay Behavior to save that preference.
When updating `code.py`, retain its existing private AP password; the
project-root template deliberately has an empty password.

With that setting the user measured 28.09 FPS without the phone and 23.87 FPS
with the phone, but only 3.44 FPS with an icon. Each icon draw cost ~102.5 ms
per panel, while native display present remained ~7.6 ms. The next candidate
caches icons as RGB565 Bitmaps and uses native transparent `bitmaptools.blit`
for steady icons. Copy `matrixportal_backend.py` and `overlay_engine.py` from
the project root to the board; leave the existing private-password `code.py`
and GIF media in place. A fade or reactive-brightness frame still follows the
slower Python path; physical FPS for the native path is still unverified.

Physical retest confirmed icons display correctly and run at ~23.5 FPS with
the phone connected; native steady icon draw takes ~2.25 ms per panel. Next
Clock/Weather and Chaos produced ~0.85 FPS in one window, with ~1.06 seconds
per render; stage-specific attribution is still missing. Text crashed because
CircuitPython `next()` rejects a second default argument. The next candidate
fixes text, defaults the hardware runtime to Mirrored (one face rendered, then
copied), and uses native Bitmap fill and mirror blit. It adds render/info,
render/chaos and render/mirror timings. Copy the updated `overlay_engine.py`,
`matrixportal_backend.py`, `totem_runtime.py`, and finally `code.py` while
retaining the existing private password. Test Clock and Chaos separately and
report both sets of timings; desktop tests pass, physical speed is unknown.

On the mirrored board text appeared but ran at 1.89 FPS with ~387 ms render;
the mirror itself was only ~2.3 ms. After text cleared, icons returned to
~23.4 FPS. One Chaos action cost ~3.67 seconds entirely inside render/chaos.
The next candidate replaces hardware text's dimmed backing with a native
solid-black rectangle, adds render/text timing, and uses a bounded native
shape version of Chaos rather than desktop per-pixel color/spatial passes.
The hardware Chaos shapes simplify the original visuals deliberately; compare
their appearance and performance before treating this as final. Copy the five
changed modules (`matrixportal_backend.py`, `text_engine.py`,
`overlay_engine.py`, `chaos_engine.py`, `totem_runtime.py`) without replacing
the private-password `code.py`. Keep Mirrored and None · GIF selected.

Text improved only to ~7.24 FPS with `render/text` ~88 ms; user rejected the
simplified Chaos visuals as a final replacement. A subsequent Pixel-font path
caches per-glyph RGB565 Bitmaps and uses transparent native blits; rainbow
color advances four times/second for glyph reuse. To investigate preserving
the original full-frame Chaos effects, `matrixportal_bitmap_buffer_probe.py`
verifies `memoryview(displayio.Bitmap)` indexing at startup and times 2048
reads/writes without changing the image. It does **not** enable direct bitmap
buffer access during normal rendering. This differs from the known-faulty
`memoryview(rgbmatrix.RGBMatrix)` method. Updated `code.py` logs frame interval,
lateness and GC duration to find periodic GIF catches. Copy the new probe
module before the new `code.py`, keep its private password, and copy backend
and text_engine updates. Text FPS and the Bitmap buffer path require physical
measurement before committing to a full effect-engine rewrite.

The real board confirmed the Bitmap memoryview maps 4096 16-bit pixels in
display order, with 2048 reads in 5.86 ms and writes in 10.50 ms. GIF ran
27.79 FPS alone; a forced GC took ~119 ms and the longest frame interval was
219 ms. Pixel-font text ran 13.42 FPS, with `render/text` averaging 39.43 ms.
The next build uses the proven view in the Bitmap adapter, calls `dirty()`
before refresh, restores the original Chaos engine, and accelerates its
RGB565 color pipeline and zoom/shift with packed integer math and native
`bitmaptools.rotozoom` respectively. These keep the original effect controls
and math; visual and timing equivalence must be checked on the board. Forced
five-second GC is skipped while RAM is over 300 KB. The startup probe also
reports `ULAB:` availability; CircuitPython has only a subset of NumPy.

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
board_icon_index.py
board_icons/*.rgba
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

The icon data copied to the board is the raw `board_icons/*.rgba` set and its
`board_icon_index.py`. On the 10.3.1 board, the authoring modules' `base64`
and `zlib` imports are unavailable. Copy the entire regenerated build, not just
`code.py`, after each icon rebuild.

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

The first `code.py` candidate now ties together:

- `TotemRuntime`
- MatrixPortal display backend
- MatrixPortal media adapter
- nonblocking HTTP server
- cooperative timer scheduler
- phone-supplied normalized audio signals (blocked on plain HTTP by browser
  microphone security until a secure origin is arranged)
- runtime metrics/state publication

The build tool stages the local runtime and media, but the external HTTP library
must be installed and the complete build verified on physical hardware. The
physical microphone, secure browser origin and full performance benchmarks
remain outstanding.

### Overlay polish before board testing

Text dissolves in/out and between message, font, size and color edits. Static text shares icon Bounce/Orbit; long text keeps its scrolling layout. Manage → Setup → Overlay Behavior now owns background, motion and shared music response; Display contains panel modes and targeting. Text transitions retain only small settings snapshots, with a deterministic dissolve adapter writing into the existing framebuffer. Icon rendering no longer allocates a pixel list or per-pixel Random objects. These changes have desktop regression coverage; frame cost and memory still need physical S3 measurements. The final device integration blockers above remain open.
