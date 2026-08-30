# Building the jig

## Bill of materials

| Qty | Item | Notes |
|---:|---|---|
| 7 | P50-B1 spring test probe | Ø0.68 mm tube, 16.35 mm, 30° spear tip, 75 g |
| 7 | R50-2S receptacle | Ø0.86 mm body, 17.5 mm, solder slot |
| 4 | Compression spring, 0.6 × 7 mm, **15 mm free length** | from the assortment kit |
| 1 | GH-201 horizontal toggle clamp | 75 × 25 × 17 mm, 27 kg |
| 4 | M4 × 16 screw + nut | clamp riser to stand |
| 4 | M4 × 12 screw | toggle clamp to riser |
| 4 | M3 × 12 screw | base plate to stand |
| 2 | M3 × 10 screw | optional, cover retention |
| — | 7 × stranded wire, 26 AWG | probe tails to the ST-Link |

Print all five parts in **PETG or ABS**, not PLA — the jig sits under
continuous spring load and PLA creeps.

## Print settings

| Setting | Value | Why |
|---|---|---|
| Layer height | 0.15 mm | probe-bore pilots and the 0.8 mm nest lip |
| Perimeters | 4 | posts and probe islands are small and loaded |
| Infill | 40 % | |
| Hole horizontal expansion | **0** | the bores are drilled, so leave them undersize |
| Supports | none needed | every part prints without overhangs as oriented |

Orientation: `base_plate` bore-side up (posts up, flat underside on the bed),
`nest` lip up, `cover` pads up, `stand` and `clamp_riser` as modelled.

## The one machining step

The probe bores are modelled at **Ø0.85 mm — deliberately undersize** and must
be drilled to **Ø0.90 mm** (the R50 sleeve's specified drill size). A 0.9 mm
PCB or micro twist drill in a pin vise, run through the printed pilot by hand,
gives a clean, straight, accurately located bore; a printed hole alone will
not. There are seven of them, in the raised platform, each 8.5 mm deep
including the Ø1.05 mm sleeve-head counterbore at the top.

Do this before assembling anything else, and test-fit one sleeve: it should
push in with firm thumb pressure and not rotate freely.

## Assembly

1. Drill the seven probe bores to Ø0.90 mm.
2. Press an **R50-2S sleeve** into each bore from the top until its head
   bottoms in the counterbore. The sleeve's solder tail projects about 5.7 mm
   below the plate into the open wiring space.
3. Solder a wire to each sleeve tail. Work from the middle outwards.
   Label them as you go — see the wiring table below.
4. Screw the `stand` to the `base_plate` with four M3.
5. Bolt the `clamp_riser` to the stand pedestal with four M4, then the
   GH-201 to the riser with four M4 through its 6 × 4 mm slots.
6. Drop a spring into each of the four base counterbores, over the guide
   posts, then lower the `nest` onto the posts.
7. Push a **P50-B1 probe** into each sleeve until it seats. Tips should now
   stand 3.35 mm proud of the platform.
8. Adjust the clamp spindle so that, closed, it seats in the dimple on the
   cover and drives the nest fully onto the hard stop — no more.

## Wiring

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

**`CLAMP_SLOT_DX` / `CLAMP_SLOT_DY` (15.9 / 11.1 mm)** — the GH-201 mounting
slot pattern, read off the product drawing rather than measured. Check yours
with calipers before printing the riser.

`RISER_TOP_Z` (12 mm) sets how high the clamp sits. The GH-201's spindle is
adjustable over a wide range, so this should not need changing — but if the
clamp cannot reach the cover, raise it and reprint the riser alone.
