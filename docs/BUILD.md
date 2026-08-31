# Building the jig

## Bill of materials

| Qty | Item | Notes |
|---:|---|---|
| 7 | P50-B1 spring test probe | Ø0.68 mm tube, 16.35 mm, 30° spear tip, 75 g |
| 7 | R50-2S receptacle | Ø0.86 mm body, 17.5 mm, solder slot |
| 1 | `fit_gauge` print | calibration coupon, printed once |
| 4 | Compression spring, 0.6 × 7 mm | from the kit — **select on solid height, not free length: it must stack shorter than 10 mm** |
| 1 | GH-201 horizontal toggle clamp | 75 × 25 × 17 mm, 27 kg |
| 4 | M3 heat-set insert, 4 mm | Kadrick-type, Ø4.5 knurl / Ø3.9 tip — into the clamp deck |
| 4 | M3 × 12 socket screw | toggle clamp to the deck |
| 4 | M3 × 12 screw | base plate to stand |
| 1 | small zip tie | loom strain relief at the exit |
| — | 7 × silicone wire, **30 AWG** | probe tails; see Wiring |

Print everything in **PETG**, not PLA — the jig sits under continuous spring
load and PLA creeps, and PETG takes heat-set inserts well. ABS also works if
you would rather, but nothing here needs its temperature resistance.

### Which printer

Every part fits every machine you have — the largest is the stand at
137 × 83 × 50 mm, well inside an X1C's 256 mm bed, let alone an H2D or H2C. So
build volume is not the deciding factor; two other things are.

**Keep the fit gauge and the base plate on the same machine, nozzle and
filament.** The gauge exists to measure *that machine's* hole shrinkage. Print
the gauge on one printer and the plate on another and the calibration is void —
this matters more than which printer you pick.

**The base plate is the only part where precision matters.** It carries the
seven Ø1.0 mm probe bores and the four locator pins, and it is small (42 cm³).
Put it on whichever machine you trust most for small features, at 0.12–0.15 mm
layers. If you have a **0.2 mm nozzle** for any of them, this is the one part
worth the extra time — a Ø1.0 × 9 mm bore is right at the limit for a 0.4 mm
nozzle, and it is the residual risk called out below.

**The stand is 124 cm³ of plain walls** with no precision requirement. Put it
on whichever machine is fastest or most convenient; it is roughly 7 hours
either way.

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

Orientation: `base_plate` posts up (flat underside on the bed), `nest` lip up,
`cover` **pads up** (inverted from how it is modelled), `stand` on its own base.
In those orientations every feature is a vertical wall or a vertical hole. The
largest unsupported span anywhere is 15 mm, inside the clamp tower, which
bridges without help. `verify.py` checks this each build.

## Calibrate the probe bores first

There is no drilling. The probe bores print to final size — but FDM renders a
small vertical hole undersize by an amount specific to your printer, nozzle,
material and speed, so you calibrate once:

1. Print `fit_gauge.stl` (65 × 14 mm, about 15 minutes) in the **same material
   and profile** you will use for the base plate. It has eight bores labelled
   85 to 120, in hundredths of a millimetre.
2. Try an R50 sleeve in each. You want the smallest hole it enters with firm
   thumb pressure and does not rattle in.
3. Put that number in `PIN_BORE_D` in [`cad/params.py`](../cad/params.py) and
   run `python3 jig.py`.

The default, 1.00, is a typical result for a 0.4 mm nozzle. The bore is 9 mm
long on a 17.5 mm sleeve, so even a sloppy fit barely moves the tip: at 0.04 mm
of play the probe lands within 0.28 mm of the pad centre against a 0.35 mm
budget, and `verify.py` prints that sum.

## Assembly

1. Calibrate `PIN_BORE_D` with the gauge and print the parts.
2. Push an **R50-2S sleeve** into each bore from the top, tail first, through
   the Ø1.4 mm lead-in, until its top is flush with the platform. The tail then
   projects 5.7 mm below the plate into open air. The bore locates the sleeve;
   it does not necessarily retain it — see Wiring.
3. With the plate still off the stand and turned upside down, solder a wire to
   each sleeve tail, then wick a drop of thin CA into each sleeve/bore joint
   from below to lock it. Label the wires as you go.
4. Screw the `base_plate` down onto the `stand` with four M3.
5. Melt four **M3 heat-set inserts** into the blind holes in the clamp deck,
   then bolt the GH-201 down with M3 × 12. Set your iron to about 240 °C for
   PETG, press each insert in square, and let it set before loading it.

   The holes are Ø4.0 × 5 mm deep for a 4 mm insert, with 5 mm of solid tower
   underneath. Load is only about 4 N per bolt, so this is far stronger than it
   needs to be — the inserts are for a clean repeatable thread, not strength.
6. Drop a spring into each of the four base counterbores, over the guide
   posts, then lower the `nest` onto the posts. It passes over the four locator
   pins without touching them.
7. The board drops onto the **base plate's** locator pins, through the nest, and
   seats on six nest bosses — one at each of its own mounting holes — plus the
   SWD tab and both flex necks, which carry no bottom-side parts at all. MH1 and
   MH4 at Ø2.10 locate it; MH2 and MH3 at Ø1.80 engage without fighting them.

   The pins are on the base plate rather than the nest so the board registers
   directly to the part that holds the probes. That removes the nest's own play
   on the guide posts from the chain that decides where a probe tip lands —
   worst case 0.674 mm down to 0.444 mm, against 0.5 mm of usable pad.
7. Push a **P50-B1 probe** into each sleeve until it seats. Tips should now
   stand 3.35 mm proud of the platform.
8. Adjust the clamp spindle. It presses **downward** from the clamp's mounting
   plane, and the deck sits at z = 20 mm against a cover top of 13.4 mm, so the
   spindle should end up about 6.6 mm proud — mid-range on its thread. Set it so
   the handle closes with a firm over-centre snap and the nest is driven fully
   onto its hard stop, then confirm with the continuity check below. If the
   handle closes limply, the spindle is too high and the nest is not bottoming.

## Wiring

Solder with the base plate **off the stand and inverted** — then the tails are
7 free-standing stubs on a flat surface with nothing around them. Once the
stand is on, the space is still open (22 mm of clear height under a plate whose
tails only reach down 5.7 mm) but you are working in a well.

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
| 7 | VDD_3V3 | 3.3 V supply | second pin doubles the current capacity |

**Power:** feeding the VDD_3V3 test points back-powers the board's 3.3 V rail
directly, downstream of its own regulator. Do not apply VIN at the same time
unless you have confirmed the regulator tolerates being back-fed. With only
3.3 V applied, the gate drivers and CAN transceiver stay unpowered, which is
what you want for flashing the MCU. Each probe is rated 3 A, so two VDD_3V3
pins is far more headroom than the few tens of mA the MCU needs.

## Using it

1. Open the clamp, lift the cover off by its tab.
2. Drop the board into the nest recess; it seats on two locator pins.
3. Replace the cover — it drops over the two left-hand guide posts and can
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

**`PIN_BORE_D` (1.00 mm)** — calibrated from the fit gauge, as above. This is
the one number that depends on your printer rather than on the parts.

**Known residual risk, not designed out:** the probe bore is Ø1.0 × 9 mm, a 9:1
aspect vertical hole, which is what FDM is least good at. The gauge calibrates
diameter but will not catch a bore that comes out tapered down its depth. If a
sleeve enters the gauge cleanly but will not seat fully in the plate, that is
the cause — shorten `PIN_BORE_L` to 6 mm and reprint the plate; the cost is
0.007 mm of extra probe tilt, which is nothing against the 0.444 mm budget.

**`CLAMP_SPINDLE_TO_ROW` (24.6 mm) — measure this before printing the stand.**
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
but the deck height itself is now part of the stand, so changing it means
reprinting the stand.
