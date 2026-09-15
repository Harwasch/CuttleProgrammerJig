# Building the jig

## Bill of materials

| Qty | Item | Notes |
|---:|---|---|
| 7 | P50-B1 spring test probe | Ø0.68 mm tube, 16.35 mm, 30° spear tip, 75 g |
| 7 | R50-2S receptacle | Ø0.86 mm body, 17.5 mm, solder slot |
| 1 | `fit_gauge` print | calibration coupon, printed once |
| 4 | Compression spring, 0.6 × 7 mm | from the kit — **select on solid height, not free length: it must stack shorter than 10 mm** |
| 1 | GH-201 horizontal toggle clamp | 75 × 25 × 17 mm, 27 kg |
| 8 | M3 heat-set insert, 4 mm | Kadrick-type, Ø4.5 knurl / Ø3.9 tip — 4 into the clamp deck, 4 into the stand's corner bosses |
| 4 | M3 × 12 socket screw | toggle clamp to the deck |
| 1 | ST-LINK/V2 | genuine, in its case — lives in the bay under the deck |
| 1 | 20-pin IDC socket + ribbon, **or** 6 × female jumper leads | probe tails to the ST-Link header |
| 1 | small zip tie | strain relief on the 3.3 V feed |
| — | 7 × silicone wire, **30 AWG** | probe tails; see Wiring |

| 4 | M3 × 12 socket screw | base plate to stand |

### The ST-Link bay

`STLINK_CASE` in [`cad/params.py`](../cad/params.py) is **100 × 50 × 30 mm**,
plus `STLINK_HEADER_ROOM` (15 mm, for the 20-pin ribbon) and `STLINK_USB_ROOM`
(12 mm, for the plug and its boot). That makes a **127 × 52 × 32 mm** cavity in
a 137 × 83 × 40 mm interior, so there is room to spare in every direction.

The case drops in from above before the lid goes on — no slide-in opening to
line up — and four ribs on the floor stop it wandering. Only the USB cable
leaves, through a 16 × 14 mm hole in the +X wall.

Trim `HEADER_ROOM` and `USB_ROOM` once you can see how your cables actually
bend. Both are parameters; only the stand reprints, and the stand carries
nothing precise.

Print everything in **PETG**, not PLA — the jig sits under continuous spring
load and PLA creeps, and PETG takes heat-set inserts well. ABS also works if
you would rather, but nothing here needs its temperature resistance.

### Which printer

Every part fits every machine you have — the two largest are both
145 × 91 mm in plan, well inside an X1C's 256 mm bed, let alone an H2D or H2C.
So build volume is not the deciding factor; two other things are.

**Keep the fit gauge and the base plate on the same machine, nozzle and
filament.** The gauge exists to measure *that machine's* hole shrinkage. Print
the gauge on one printer and the plate on another and the calibration is void —
this matters more than which printer you pick.

**The base plate is the only part where precision matters.** It carries the
seven Ø1.2 mm probe bores, four guide posts, two stepped board locators and two
registration pins, and it is 122 cm³. Run it at 0.12–0.15 mm layers on whichever
machine you trust most for small features. If you have a **0.2 mm nozzle**, this
is the part worth the extra time.

**The stand is 110 cm³ of plain walls** with no precision requirement at all —
four walls, a floor, four corner bosses and two holes. Put it on whichever
machine is fastest. If the bore calibration turns out wrong, only the plate
reprints.

The bosses are not cylinders sitting against the walls: the wall ring and the
four bosses are built as one 2D outline and morphologically closed, so each
boss blends into its corner on a 3 mm fillet. Left as bare cylinders, two of
them met the wall exactly tangentially — a wedge closing to zero degrees, which
no nozzle can fill — and the other two stood 1 mm clear of it as free pillars
with a slot behind. `verify.py` now checks the cross-section is one connected
piece and that re-closing it adds nothing.

I have no basis for ranking the H2C, H2D and X1C against each other for
dimensional accuracy on features this small, so I would not choose between them
on that — pick the one whose profile you have most confidence in, and let the
fit gauge tell you what it actually produces.

## Print settings

| Setting | Value | Why |
|---|---|---|
| Layer height | 0.15 mm | probe bores and the 0.8 mm nest lip |
| Perimeters | 4 | posts, probe islands and locator pins are small and loaded |
| Infill | 30 % | |
| Hole horizontal expansion | **0** | you calibrate with the gauge instead |
| Supports | **none** | see below |

Orientation: `base_plate` flat on its underside (posts, pins and clamp tower
all pointing up), `stand` on its own base, `nest` lip up, `cover` **pads up**
(inverted from how it is modelled).

In those orientations every feature is a vertical wall or a vertical hole. The
largest unsupported span anywhere is **12.0 mm**, the roof of the clamp tower's
cavity, which bridges without help. The next is the cover's spindle dish at
5.7 mm. `verify.py` measures the largest circle that fits inside every downward
face — the distance filament actually spans — and requires it to be under
25 mm. It considers **every** face whose normal falls past 45°, not just
exactly-horizontal planes: filtering on planes alone made the dimple invisible,
and it could be opened into a hole clean through the cover with no complaint.

## Calibrate the probe bores first

There is no drilling. The probe bores print to final size — but FDM renders a
small vertical hole undersize by an amount specific to your printer, nozzle,
material and speed, so you calibrate once:

1. Print `fit_gauge.stl` (80 × 14 × 5 mm, about 10 minutes) in the **same
   material and profile** you will use for the base plate. It has ten **blind
   counterbores 2.5 mm deep** labelled 90 to 135, in hundredths of a
   millimetre. The P100 gauge steps 195 to 240 with 7.5 mm counterbores.

   The depth matters: the counterbore is one receptacle head deep, so the coupon reproduces
   exactly the feature it is calibrating. It used to be an 11 mm through hole
   for what is a 2.5 mm counterbore — a deeper hole tapers more and reads
   tighter, biasing the one measurement the whole design hangs on.
2. Press an R50 sleeve into each (P100: an R100, on a gauge stepping 1.95 to
   2.40). You want the smallest bore whose **head seats
   flush** with a firm thumb push and does not rattle. The answer must have a
   bore too tight below it **and** one visibly loose above it — if the sleeve
   only enters the largest, the range has not bracketed your printer and you
   need to shift `GAUGE_BORES` up and print again.
3. Put that number in `PIN_BORE_D` in [`cad/params.py`](../cad/params.py),
   set `PRINT_HOLE_SHRINK` to `PIN_BORE_D` minus your sleeve's measured head
   diameter, and run `python3 jig.py`.

   **Both, together.** `PRINT_HOLE_SHRINK` is what every other fit in the
   design is computed from — the guide posts, the registration pins, the
   locator shanks, the heat-set insert holes. It used to be a literal buried
   inside `verify.py`, so recalibrating for a new printer silently left all of
   them sized for the old one.

The value shipped here, **1.20**, is a measured result, not a default: on the
machine and profile it was taken from, the sleeve entered the 120 bore and
nothing smaller. That means the profile renders a small vertical hole about
0.22 mm under nominal — a modelled Ø1.20 comes out near Ø0.98 and grips the
sleeve head. That is more shrink than a typical PLA profile gives (0.08 to
0.14 mm), so treat it as a starting point on any other machine, nozzle,
material or speed and re-run the gauge.

### The bore is stepped, and that is what sets the probe height

A counterbore exactly one head deep (2.5 mm) sits over a bore sized for the
sleeve's **body**. The head cannot enter the body bore, so it bottoms with its
top flush with the platform — the sleeve's Z is geometry, not how hard you
pushed.

That matters more than it sounds. `PIN_PROTRUSION` is the number the entire
stack-up derives from, and until this was stepped the lead-in printed at Ø1.18
and the bore at Ø0.98 — both at or over the Ø0.98 head — so the sleeve slid
straight through and its height was set by feel.

The sleeve is then held at two places — the counterbore on its head and the
body bore on its body, 5.25 mm apart at 0.020 mm radial — and it is the
distance between those two that limits tilt, not either one alone. The whole
chain totals 0.442 mm worst case and 0.193 mm RSS against a 0.500 mm budget;
`verify.py` prints every link.

## The P100 variant

The default build is a **P50-B1 probe in an R50-2S receptacle**. Setting
`JIG_PINS=P100` builds for a **P100-B1 in an R100-4S** instead — a much larger
pin, and not a drop-in.

```bash
cd cad
JIG_PINS=P100 python3 jig.py       # -> cad/out/p100/
JIG_PINS=P100 python3 verify.py
python3 tools/compare_families.py  # which parts actually change
```

**It is not a base plate swap.** Two things force the rest:

The P100 probe stands **8.35 mm** out of its receptacle where the P50 stands
3.35 — 2.00 mm of tip cone plus 6.35 mm of Ø1.0 plunger rod, the whole of its
Ø1.36 barrel disappearing into the receptacle's 25.00 mm tube. Since the seat
height is `NEST_T + COMPRESSION − PIN_PROTRUSION` and nothing else in that
expression may move, the probe seat goes from **3.85 mm above** the hard-stop
plateau to **0.75 mm below** it. The plate stops growing a platform and gets a
relief instead — which is the easy half, and it also means no bottom-side
component can reach the plateau, so all the platform relief cutting disappears.

The hard half is that the R100 receptacle is **39 mm long** against the R50's
17.5. Its tail lands at z = −39.75, which is 22 mm past where the ST-Link's
roof used to be. Nothing in plan can move — the probes are where the board's
test points are — so the ST-Link moves out from under them into −Y and the box
grows by just enough to take it. That leaves a clear 39 mm-wide channel along
+Y with the full depth of the stand under it, which is where the tails and the
loom live.

| | P50 | P100 |
|---|---|---|
| probe stands proud of the receptacle | 3.35 mm | 8.35 mm |
| probe seat | 3.85 mm **above** the stop | 0.75 mm **below** it |
| working stroke | 1.20 of 2.65 mm | 1.60 of 3.50 mm |
| clamp load, closed | 10.0 N | 15.0 N |
| counterbore | Ø0.98 × 2.5 mm | Ø1.90 × 7.5 mm |
| body bore, as printed | Ø0.90 × 8.0 mm | Ø1.71 × 5.0 mm |
| fit gauge range | 0.90–1.35 | 1.95–2.40 |
| base plate | 8 mm thick | 14 mm thick |
| outline | 145 × 91 mm | 145 × 101 mm |
| lid screws | M3 × 12 | M3 × 16 |
| tail proud of the plate | 5.65 mm | 25.75 mm |

The body bore lands at **Ø1.71 as printed**, against the vendor's own stated
drilling size of 1.70 mm for this receptacle. That is not a number anyone
tuned: it falls out of the same print model calibrated on the P50 sleeve, which
is a useful independent sign that the model transfers to this size.

**`nest` and `cover` are unchanged** — identical volume, bounding box and
topology in both families, which `tools/compare_families.py` checks rather than
asserts. Print a new `base_plate`, `stand` and `fit_gauge`; keep the rest.

The P100's thinnest collar is **0.826 mm**, between VDD_3V3 and SWDIO 4.27 mm
apart — more than the P50's 0.35 mm, because with the seat recessed there is no
island to be cut back and the wall is shared with the neighbouring bore instead.

**Calibrate first, as always**, on the P100 gauge: it steps 1.95 to 2.40 and you
are looking for the bore an R100 head just enters.

Three numbers in `params.py` are read off the vendor drawing rather than
measured, and all three are flagged there: `PIN_PROTRUSION` (8.35),
`PIN_STROKE_MAX` (3.50) and `RECEPT_HEAD_L` (7.5, the dimension that separates
the −1W/−4W/−5W variants). `PIN_PROTRUSION` is the one that matters — the whole
stack-up derives from it, so measure a probe in a receptacle with calipers
before you commit to a plate.

## Assembly

1. Calibrate `PIN_BORE_D` with the gauge, measure your ST-LINK/V2 into
   `STLINK_CASE`, and only then print the parts.
2. Press an **R50-2S sleeve** (P100: **R100-4S**) into each bore from the top, tail first, until
   its head bottoms in the counterbore — its top will then be flush with the
   platform. The tail projects 5.7 mm below the deck into the wire bay. The
   counterbore locates and grips it; it does not necessarily retain it against
   a pull — see Wiring.
3. With the plate **off the stand and turned upside down**, solder a wire to
   each sleeve tail, then wick a drop of thin CA into each sleeve/bore joint to
   lock it. Label the wires as you go.

   This is why the plate is a separate part. Inverted on the bench it is a flat
   surface with seven 5.7 mm stubs standing up out of it and nothing within
   30 mm of any of them. Fused to the stand, the same joints sat 22 mm down a
   22 mm slot.
4. Melt in all **eight M3 heat-set inserts** — four in the clamp deck on top of
   the tower, four in the stand's corner bosses. Set your iron to about 240 °C
   for PETG, press each one in square, and let it set before loading it.

   Then bolt the GH-201 down with M3 × 12. Its holes are Ø4.0 × 5 mm deep with
   5 mm of solid tower underneath; load is only about 4 N per bolt, so this is
   far stronger than it needs to be — the inserts are for a clean repeatable
   thread, not strength.
5. Drop the **ST-LINK/V2** into the stand between the four floor ribs, feed its
   USB cable out through the hole in the +X wall, and plug the probe loom onto
   its 20-pin header (table below). Bring the 3.3 V feed in through the slot on
   the far side from the clamp and zip-tie it.
6. Lower the plate onto the stand and fit the four **M3 × 12** (P100: **M3 × 16**, for the thicker plate) into the corner
   inserts. Heads sit in Ø6.4 × 3 mm counterbores, flush below the plateau.

   These are inserts rather than screws cut straight into the plastic because
   the plate comes off every time you service the wiring or the ST-Link, and an
   M3 self-tapped into PETG does not survive many cycles. The clamp load is
   internal anyway — the spindle presses the cover down, the springs push the
   plate down by the same amount — so the screws only stop the lid shifting.
7. Push a **P50-B1 probe** (P100: **P100-B1**) into each sleeve until it seats. Tips should now
   stand 3.35 mm proud of the platform.

   This has to happen **before** the nest goes on: once it does, each sleeve
   top is at the bottom of a Ø4 hole 6.8 mm down, and with the board over it
   there is no way to push a Ø0.68 probe in axially.
8. Drop a spring into each of the four counterbores, over the guide posts, then
   lower the `nest` on. It passes over the two locator pins and the two
   registration pins without touching either.
9. The board drops onto the **base plate's** locator pins, through the nest, and
   seats on six nest bosses — one at each of its own mounting holes — plus the
   SWD tab and both flex necks, which carry no bottom-side parts at all. MH1 and
   MH4 at Ø2.10 locate it; there are no secondary pins.

   The pins are on the base plate rather than the nest so the board registers directly
   to the part that holds the probes: worst case 0.442 mm rather than 0.674 mm,
   against 0.5 mm of usable pad. They are stepped — Ø3.00 up to the seat, then
   Ø2.10 — so only 6 mm stands proud, at 2.9:1 rather than 5.7:1.

10. Adjust the clamp spindle. It presses **downward** from the clamp's mounting
   plane, and the deck sits at z = 20 mm against a cover top of 13.4 mm, so the
   spindle should end up about 6.6 mm proud — mid-range on its thread. Set it so
   the handle closes with a firm over-centre snap and the nest is driven fully
   onto its hard stop, then confirm with the continuity check below. If the
   handle closes limply, the spindle is too high and the nest is not bottoming.

## Wiring

Solder with the plate **off the stand and inverted** — seven free-standing
stubs on a flat surface, nothing within 30 mm of any of them.

The SWD loom does not leave the assembly: it runs from the tails down to the
ST-Link's 20-pin header inside the stand. Only the external 3.3 V feed uses the
slot in the far wall, and only the USB cable leaves the box.

The tails sit on a 4.3 mm minimum pitch, so use **30 AWG silicone wire**
(≈0.8 mm OD) rather than 26 AWG. Current is a non-issue — the MCU draws tens
of milliamps and each probe is rated 3 A — and the thinner wire makes the
cluster far easier to work in. Run the loom out through the slot on the far
side from the clamp and zip-tie it to the divider post; that post, not the
solder joints, should take any pull on the cable.

| Probe | Net | ST-Link | Note |
|---|---|---|---|
| 1 | SWDIO | SWDIO | |
| 2 | SWCLK | SWCLK | |
| 3 | NRST | NRST | gives connect-under-reset |
| 4 | SWO | SWO | optional, trace output |
| 5 | GND | GND | also the 3.3 V supply return |
| 6 | VDD_3V3 | VDD / VAPP sense | |
| 7 | VDD_3V3 | external 3.3 V feed | second pin doubles the current capacity. The ST-LINK/V2's VAPP pins are a voltage **sense** input — the dongle does not source power, so this comes in through the wall slot |

**Power:** feeding the VDD_3V3 test points back-powers the board's 3.3 V rail
directly, downstream of its own regulator. Do not apply VIN at the same time
unless you have confirmed the regulator tolerates being back-fed. With only
3.3 V applied, the gate drivers and CAN transceiver stay unpowered, which is
what you want for flashing the MCU. Each probe is rated 3 A, so two VDD_3V3
pins is far more headroom than the few tens of mA the MCU needs.

## Using it

1. Open the clamp, lift the cover off by its tab.
2. Drop the board into the nest recess; it seats on two locator pins.
3. Replace the cover — it drops over all four guide posts and can
   only go on one way round.
4. Close the clamp. The nest travels 3 mm to a hard stop.
5. Flash. Open the clamp; the springs lift the board clear of the probes.

## Checks before the first run

| Check | Expected |
|---|---|
| Continuity, each probe to its net with the clamp closed | < 1 Ω |
| Continuity with the clamp open | open circuit |
| Probe tips proud of the platform, clamp open | 3.35 mm |
| Nest lift, clamp open | 3.0 mm |
| Spring solid height (compress one fully) | under 10 mm |
| Spindle lands in the cover dimple | within Ø8 mm |
| Clamp force at close | roughly 1.6 kg |

## Tuning

Two numbers are worth verifying against the parts you actually received.
Both live in [`cad/params.py`](../cad/params.py); change one and re-run
`python3 jig.py && python3 verify.py`.

**`PIN_PROTRUSION` (3.35 mm)** — how far the P50-B1 tip stands above the
seated R50 sleeve. Measure it with the probe pressed into a sleeve. This one
number sets the platform height and therefore the probe compression; the
verification script re-derives everything from it. If your probes measure,
say, 3.6 mm, the platform simply drops 0.25 mm.

**`PIN_BORE_D` (1.20 mm) and `PRINT_HOLE_SHRINK` (0.22 mm)** — calibrated
together from the fit gauge, as above. These are the two numbers that depend on
your printer rather than on the parts, and every other fit in the design is
computed from the second one.

**Known residual risk, not designed out:** the body bore is Ø1.12 × 8 mm, a
7:1 aspect vertical hole, which is what FDM is least good at. The gauge
calibrates the counterbore but says nothing about whether the bore beneath it
comes out tapered. If a sleeve seats cleanly in the gauge but will not bottom
in the plate, that is the cause — shorten `PIN_BORE_L` to 6 mm and reprint the
plate; the cost is 0.003 mm of extra probe tilt against a 0.500 mm budget.

**Two probe collars are thin by necessity.** SWDIO and SWCLK sit 0.95 and
1.05 mm from the inflated footprint of the tallest bottom-side component, so
their collars are 0.35 and 0.45 mm on that side over the top 0.8 mm — about one
extrusion. Two thirds of each counterbore is still fully enclosed. This is set
by where the component actually is, not by a choice in the model; the other
five collars are the full Ø3.0.

**`CLAMP_SPINDLE_TO_ROW` (24.6 mm) — measure this before printing the plate.**
It is the distance from the spindle axis to the nearer of the two mounting-hole
rows, and it decides where the spindle lands on the cover. Fixed inserts have no
fore-and-aft slop to absorb an error, unlike the sliding nuts they replaced.
24.6 mm is inferred from the drawing (19.6 mm spindle-to-plate plus about 5 mm
plate-edge-to-hole), **not measured**, so check it. `verify.py` reports where
the spindle would land against the cover's Ø8 mm dimple.

**`CLAMP_HOLE_DX` / `CLAMP_HOLE_DY` (15.9 / 11.1 mm)** — the GH-201 mounting
hole pattern, also read off the drawing. Check with calipers.

`TOWER_TOP_Z` (20 mm) sets how high the clamp sits. Reach is adjustable — the
deck slots give 8 mm on top of the clamp's own, and the spindle covers height —
but the deck height itself is part of the base plate, so changing it means
reprinting the plate.
