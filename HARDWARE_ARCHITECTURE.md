# Festival totem hardware architecture (working build)

## Display size and orientation

The build uses **two 32×64 HUB75 panels**, oriented landscape as 64 pixels
wide by 32 pixels tall. The simulator, baked GIFs and MatrixPortal backend
therefore use a 64×32 coordinate system for each face. Before mounting, check
the actual panel labels, scan type, IN/OUT connector orientation, physical
dimensions and power rating; set the rear rotation during the mapping test
if its installed orientation needs it.

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
      → 5 V/5 A rated USB-C power pigtail → MatrixPortal S3 USB-C input

MatrixPortal HUB75 → front IN → front OUT → back IN
All three power branches use the buck's regulated 5 V output and ground.
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
MatrixPortal's +5 V mounting terminal. The controller's new planned input is
a rated USB-C-to-bare-wire power cable on a third distribution branch, with
positive and ground wired to the buck's regulated 5 V output. The cable is
ordered but has not yet been bench-tested on this board. Verify its actual
polarity, connector behavior, regulator output, and stable boot under load;
its 5 A rating describes capacity, not the controller's draw. The controller
and panels will then share a ground reference. Avoid connecting a computer's
USB power at the same time as the externally supplied pigtail; disconnect
the external feed before USB programming.

A fuse protects the wire and supply path, not a guaranteed maximum operating
current. Select its rating only after checking the buck's continuous output,
wire gauge, connector and switch ratings. The planned 8–10 A fuse is a
candidate, not a validated value for every combination of components. A
separately fused controller branch sized to its smaller cable is sensible
because the main fuse sized for both panels may not protect that branch.

Adafruit recommends **5 V at 4 A per 64×32 panel** as a supply planning
figure, or **8 A for two**. A 5 V/10 A buck has little spare headroom at that
planning point. Verify its continuous rating and cooling inside the enclosure,
then measure real current with the intended animations at several brightness
levels. Avoid a full-white startup frame. The new plan uses a single PD output rather than two battery ports. Confirm
the TOBSUN converter's permitted input range and the PD trigger's actual
output before relying on a 20 V setting: the converter's photographed label
specifies 12 V/24 V input, not an explicit continuous input-voltage range.

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
3. Add separate panel branches, then the fused USB-C controller pigtail
   from the same regulated 5 V distribution. Check polarity and board boot
   before connecting all three loads and monitoring voltage under load.
4. Run the red/blue panel mapping smoke test, inspect scan artifacts and
   rotation, then record RAM, FPS and decode/present latency.
5. Run the complete controller and media build only after the mapping test
   passes; measure power and battery runtime at the chosen brightness.

Sources: [Adafruit multiple-panel wiring and 5 V current planning](https://learn.adafruit.com/rgb-led-matrices-matrix-panels-with-circuitpython/advanced-multiple-panels);
[MatrixPortal S3 pinouts and USB-fed terminal warning](https://learn.adafruit.com/adafruit-matrixportal-s3/pinouts);
[CircuitPython RGBMatrix framebuffer and refresh API](https://docs.circuitpython.org/en/latest/shared-bindings/rgbmatrix/).
