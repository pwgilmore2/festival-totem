# Festival totem hardware architecture (working build)

## Confirm the display size before cutting the enclosure

The simulator and the current MatrixPortal backend target **two 64×32 HUB75 panels**.
Earlier parts notes also mention two **32×32** panels already on hand. The 32×32
pair is useful for a bench test, but the current 64×32 software and baked GIFs
must be changed to 32×32 before using them as the final displays. Check the
panel labels, scan type, connector orientation, actual dimensions and power
ratings before mounting or ordering a replacement pair.

The intended final assembly has front and back panels facing opposite
directions. A MatrixPortal S3 drives one 128×32 logical row: its first 64×32
region is the front and its second is the back. HUB75 data runs MatrixPortal
to the front panel **IN**, then front **OUT** to back **IN**. The back panel
can use a software 180° rotation if its physical orientation requires it.
Run `matrixportal_smoke_test.py` first: it paints the front red and back blue
so physical side mapping can be checked before full deployment.

## Power and signal paths

```text
UGREEN battery USB-C PD output
  → correctly configured 20 V PD trigger
  → 20 V-to-5 V buck, set and measured at about 5.0 V
  → fuse sized for the buck, wiring and expected load
  → switch rated for DC load and starting current
  → 5 V distribution
      → front panel power connector
      → back panel power connector

Battery separate USB output → USB-C power input on MatrixPortal S3
MatrixPortal HUB75 → front IN → front OUT → back IN
Ground reference: MatrixPortal and panels must share ground.
```

Use the distribution block for panel **power in parallel**. Do not use the
HUB75 ribbon as the panel power feed. Confirm the PD trigger requests a voltage
supported by the battery and within the buck input range. With power OFF,
check polarity, connector pinout, fuse, wire size and all screw terminals;
with the panels disconnected, measure the buck output. Then connect one panel
and test, followed by both at a low brightness limit.

**MatrixPortal S3 detail:** its +5 V and GND mounting terminals are USB-fed
**outputs**, and Adafruit recommends disconnecting those terminals from a
panel when that panel is powered externally. Do not feed buck 5 V into the
MatrixPortal's +5 V mounting terminal or join the buck's 5 V rail to the
board's USB 5 V rail. The board should be powered through its USB-C input
from a separate battery output. Arrange a common ground reference for the
HUB75 signal without tying the two positive rails together. During USB
programming, check the physical wiring again before attaching a computer.

A fuse protects the wire and supply path, not a guaranteed maximum operating
current. Select its rating only after checking the buck's continuous output,
wire gauge, connector and switch ratings. The planned 8–10 A fuse is a
candidate, not a validated value for every combination of components.

Adafruit recommends **5 V at 4 A per 64×32 panel** as a supply planning
figure, or **8 A for two**. A 5 V/10 A buck has little spare headroom at that
planning point. Verify its continuous rating and cooling inside the enclosure,
then measure real current with the intended animations at several brightness
levels. Avoid a full-white startup frame. Power banks can renegotiate or
disable an output when using several ports; test both output ports together.

## Runtime and battery check

The Mac prepares images, GIFs, metadata, tags and the phone page. The S3 stores
the prepared 64×32 GIFs, streams one decode at a time across two independent
players, renders both logical displays and serves the local phone controls.
`MATRIXPORTAL_DEPLOYMENT.md` describes the staging command and the device
smoke test. A final `code.py` that wires the modules together is still needed.

The 20,000 mAh battery label normally refers to internal cell capacity; it is
not 20 Ah at 5 V. If its stored energy is about 74 Wh, and usable energy after
conversion is roughly 55–65 Wh, a 4–6 hour goal implies **about 9–16 W
average combined draw**. This is a planning estimate, not a measured runtime.
Measure input energy and end-to-end runtime on the finished build with
representative GIFs, phone Wi-Fi active and the brightness cap you intend to
use. Reduce brightness or content power if the result falls short.

## Physical bring-up order

1. Verify actual panel size and scan compatibility, cable directions and
   enclosure layout; keep the battery and regulator accessible.
2. Bench test the PD trigger and buck without panels; measure 5 V under load.
3. Add the panel power branches and USB power for the MatrixPortal; establish
   common ground without joining the two 5 V positive rails.
4. Run the red/blue panel mapping smoke test, inspect scan artifacts and
   rotation, then record RAM, FPS and decode/present latency.
5. Run the complete controller and media build only after the mapping test
   passes; measure power and battery runtime at the chosen brightness.

Sources: [Adafruit multiple-panel wiring and 5 V current planning](https://learn.adafruit.com/rgb-led-matrices-matrix-panels-with-circuitpython/advanced-multiple-panels);
[MatrixPortal S3 pinouts and USB-fed terminal warning](https://learn.adafruit.com/adafruit-matrixportal-s3/pinouts);
[CircuitPython RGBMatrix framebuffer and refresh API](https://docs.circuitpython.org/en/latest/shared-bindings/rgbmatrix/).
