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

The probe bores print to final size — but FDM renders a small vertical hole
undersize by an amount specific to your printer, nozzle, material and speed, so
you calibrate once. **Calibrate with the RECEPTACLE**, which is what sits in the
bore. Reading the gauge with the probe in hand instead is the one mistake that
has actually been made here, and it cost a base plate: the P50-B1's barrel is
Ø0.68 and the R50-2S's head is Ø0.98, so the answer came out 0.30 mm small and
no sleeve would seat.

1. Print `fit_gauge.stl` (111 × 30 × 12.5 mm, about 35 minutes) in the **same material and profile** you will use for
   the base plate. Two rows of ten, labelled in hundredths of a millimetre:

   | row | depth | how to read it | sets |
   |---|---|---|---|
   | **HEAD** | one receptacle head | push the sleeve in **head first**; the smallest bore the head goes fully into with a firm thumb push, the step down to the body ending flush with the face | `PIN_BORE_D` |
   | **BODY** | one body bore | push the sleeve in **tail first**; the smallest bore the body slides down without force | `PIN_BODY_BORE_D` |

   Two rows because the plate needs two bores and at this size they cannot be
   derived from one another: shrink changes fast enough down here that the
   counterbore and the body bore end up barely 0.05 mm apart as modelled, which
   is less than the uncertainty in either.

   Each row is bored to the depth of the feature it stands for, because a
   deeper hole tapers more and reads tighter. Every bore has an eject hole
   through the back — a press fit in a blind hole otherwise stays there.

2. The answer must have a bore too tight below it **and** one visibly loose
   above it. If the sleeve only enters the largest, the range has not bracketed
   your printer: shift `GAUGE_BORES` up and print again. The P50 range steps
   1.30 to 1.75 and the P100 range 1.80 to 2.25.

3. Put the two numbers in `PIN_BORE_D` and `PIN_BODY_BORE_D` in
   [`cad/params.py`](../cad/params.py), add the point
   `(PIN_BORE_D, PIN_BORE_D − your head diameter)` to `HOLE_SHRINK_CAL`, and
   run `python3 jig.py`.

### Getting the receptacles in

They go in tail first, and a 0.86 mm brass tube buckles easily, so do not pinch
the tube — push on the head with something flat. The bore is a 0.020 mm radial
slip over 8 mm, which is a firm push, not a fight; if it fights you, the bore
is undersize and the gauge is telling you so. A cone leads from the counterbore
into the body bore so the tube cannot catch square on the step.

### If the P50 bores will not come out

At Ø0.98 a printed hole is two and a half nozzle widths across and the printer
is removing something like 40 % of it. If the gauge will not give you a clean
answer, the bores are **drillable, and the geometry is already sized for it**:
Ø1.00 and Ø0.90 are stock drill sizes, and they land exactly where the design
wants them — a Ø1.00 counterbore on a Ø0.98 head is 0.01 mm of slip, a Ø0.90
body bore on a Ø0.86 body is the 0.02 mm the design asks for, and a Ø0.98 head
still cannot enter a Ø0.90 bore, so the depth stop survives. Print the plate,
run both drills down each bore by hand using the printed hole as the pilot, and
the fit stops depending on the print model at all.

The P100 family does not have this problem — Ø1.90 and Ø1.71 are comfortable
for FDM — which is worth knowing if you have both sets of pins.

### Hole shrink is a function of diameter AND depth

The P50 gauge's two rows are the same diameters at different depths, so it
measured both at once:

| bore | depth | part that just entered | shrink |
|---|---|---|---|
| Ø1.35 | 2.5 mm | Ø0.98 R50 **head** (1.30 not quite) | **0.37** |
| Ø1.35 | 8.0 mm | Ø0.86 R50 **body**, a little play (1.30 not at all) | **0.45** |
| Ø2.00 | 7.5 mm | Ø1.90 R100 head | **0.10** |

The first two differ only in depth: **5.5 mm deeper costs 0.08 mm of printed
diameter**. Ignoring that is what buckled a batch of receptacles — the body
bore was offset from the counterbore on the assumption that both shrank the
same, which put an *interference* fit 8 mm long on a 0.86 mm brass tube.

Both bores are now solved at their own depth. On the P50 they land on the same
**Ø1.35 modelled** and print **Ø0.98** and **Ø0.90** — exactly what the two
gauge rows read. So on this printer **the step that stops the sleeve is
produced by depth, not by modelled diameter**, and `verify.py` measures it as
printed rather than assuming it. That is a real dependency: a printer without
the depth effect would have no step at all, and `PIN_BORE_D` would have to be
opened up to create one.

An earlier Ø1.20 reading is withdrawn — it was taken with the probe in hand
rather than the receptacle, and the probe's barrel is Ø0.68 against the
receptacle's Ø0.98 head, so it answered a different question by 0.30 mm.

The depth term rests on that one pair of rows. **Nothing has been measured at
Ø4 and up**, which is where the guide posts, the registration pins, the insert
holes and the magnet fixture's rotor journal live. Those use
`PRINT_HOLE_SHRINK`, a separate constant at 0.22, deliberately not tied to the
calibration list — every one of those features has been printed at that figure
and works, and a 40 % small-hole loss has no business up there. Shrink cannot
rise again as the hole grows, so the honest bracket is 0 to 0.10 and
`verify.py` checks across it.

To close that, print **`shrink_gauge`** (56 × 32 × 5 mm, about 15 minutes):
four plain through holes modelled at Ø4, Ø6, Ø9 and Ø12 with the number
engraved beside each. Run the caliper's inside jaws down each one; shrink at
that diameter is the engraved number minus what you read. Add the points to
`HOLE_SHRINK_CAL` and everything downstream re-derives.

### Root flares

A pin standing on a flat face meets it in a square corner, and that corner is
where a printed column breaks: the layer bond carries the whole bending moment
with nothing to spread it into. Every pin that has room now rises out of a
1.5 mm tapered skirt, sized to the largest its own mating clearance allows as
printed:

| pin | root | limited by | clearance left |
|---|---|---|---|
| guide post | Ø5.08 → Ø5.58 | the spring's Ø5.80 bore sliding over it | 0.11 mm |
| board locator | Ø2.58 → Ø2.98 | the nest's Ø3.40 pass-through | 0.10 mm |
| probe collar | Ø3.08 → Ø3.58 | the nest's Ø4.00 probe window | 0.10 mm |

On the locator — the tallest thing on the plate — that is **1.54× the section
modulus** at the root. The registration pins get none: the nest leaves them
0.075 mm, and at Ø4.00 × 6.5 mm they are 1.6:1, the stoutest thing standing
there. Giving them one would mean relieving the nest's underside and
reprinting it.

**The nest does not change.** All three flares fit inside clearances that
already existed.

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
| body bore, as modelled | Ø1.35 | Ø1.85 |
| body bore, as printed | Ø0.90 × 8.0 mm | Ø1.71 × 5.0 mm |
| counterbore, as modelled | Ø1.35 | Ø2.00 |
| hole shrink, counterbore / body bore | 0.37 / 0.45 mm | 0.10 / 0.13 mm |
| fit gauge range | 1.30–1.75 | 1.80–2.25 |
| base plate | 8 mm thick | 14 mm thick |
| outline | 145 × 91 mm | 145 × 101 mm |
| lid screws | M3 × 12 | M3 × 16 |
| tail proud of the plate | 5.65 mm | 25.75 mm |

The body bore lands at **Ø1.71 as printed**, against the vendor's own stated
drilling size of 1.70 mm for this receptacle — the same 0.04 mm of diametral
clearance the P50 bore uses, landing within 0.01 mm of what the vendor
recommends for a drilled plate. (An earlier draft of this page called that an
independent check on the print model. It is not: `body + 0.04` is a design
rule and the algebra cancels the shrink out entirely, so it says nothing about
whether the print model transfers. The agreement with the vendor is still
worth having; it is just evidence about the clearance rule, not the printer.)

**`nest` and `cover` are unchanged** — identical volume, bounding box and
topology in both families, which `tools/compare_families.py` checks rather than
asserts. Print a new `base_plate`, `stand` and `fit_gauge`; keep the rest.

The P100's thinnest collar is **0.826 mm**, between VDD_3V3 and SWDIO 4.27 mm
apart — more than the P50's 0.35 mm, because with the seat recessed there is no
island to be cut back and the wall is shared with the neighbouring bore instead.

**Calibrate first, as always**, on the P100 gauge: it steps 1.95 to 2.40 and you
are looking for the bore an R100 head just enters.

### What to measure before printing a P100 plate

The receptacle's head bottoms on a shoulder at a **fixed** depth, so the probe
tip ends up at

```
(seat − RECEPT_HEAD_L) + head_as_measured + protrusion_as_measured
```

which means an error in **either** `RECEPT_HEAD_L` or `PIN_PROTRUSION` lands on
the working stroke one for one. Those two are the pair the whole stack-up rests
on, and both are read off the vendor drawing rather than measured. Their
combined error has to stay inside **−0.80 / +0.85 mm**, which is the 1.60 mm
working stroke moving between the 0.80 mm minimum and 70 % of the 3.50 mm full
travel.

| Measure | Model | How | Window |
|---|---|---|---|
| **`PIN_PROTRUSION`** | 8.35 | Seat a probe in a receptacle, measure the assembly's overall length, subtract the bare receptacle's. That difference is how far the tip stands proud. | see above |
| **`RECEPT_HEAD_L`** | 7.5 | Length of the enlarged section at the top, from the top face down to where the OD drops to the plain Ø1.67 body. This is the counterbore depth. | see above |
| `RECEPT_HEAD_D` | 1.90 | OD of that top section | 1.84–1.92 |
| `RECEPT_BODY_D` | 1.67 | OD of the plain tube | 1.55–1.69 |
| `PIN_STROKE_MAX` | 3.50 | Probe free length minus its length pressed fully home | ≥ 2.29 |
| `RECEPT_LEN` | 39.0 | Overall | 16.25–47.25 |

`PIN_BORE_D` is already done: the gauge read **2.00**.

The fit gauge reads `RECEPT_HEAD_L` for you as a by-product: its bores are
blind and exactly `RECEPT_HEAD_L` deep, so push a receptacle in **head first**
and the step where it drops to the body diameter should come out flush with the
coupon's face. Proud or sunk by *x* means your head is longer or shorter by *x*.

Then hand the numbers to the checker, which reports each against its window,
combines the two that matter, and tells you whether it is a model correction or
a reprint:

```bash
JIG_PINS=P100 python3 tools/check_pins.py \
    --protrusion 8.4 --head 7.6 --head-dia 1.91 --body-dia 1.68
```

`STLINK_CASE` and the four `CLAMP_*` numbers are unchanged from the P50 build,
but the P100 plate is a new print with new insert positions — so if you never
verified `CLAMP_SPINDLE_TO_ROW` (24.6 mm, spindle axis to the nearer mounting
row, inferred from the drawing), do it now, because fixed inserts give up the
fore-and-aft trim the clamp's own slots allowed.

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
