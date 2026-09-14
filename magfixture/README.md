# Magnet test fixture — Cuttle CANServo_Driver V0.4

Holds the board flat and presents a magnet to each of its two magnetic
sensors, so both can be exercised on the bench.

| sensor | package | centre | package top |
|---|---|---|---|
| **AS5600L** rotary encoder | SOIC-8 | (+46.81, +0.10) | 1.838 mm above the board |
| **SOT-23** linear hall | 3-pin | (−23.25, +0.07) | 1.285 mm above the board |

Both positions are **measured**, not transcribed: the KiCad STEP export carries
each component's footprint name as a label, and `tools/find_sensors.py` reads
them straight out of it. The package *heights* come from `cad/board_parts.json`
— the same keep-out data the interference checks use — so the airgap the
fixture builds and the airgap the checks measure cannot disagree.

## What it does

**Encoder.** A Ø6 × 2.5 mm diametric magnet in a rotor, journalled directly
over the package and spun by finger. The airgap is **1.00 mm** face to package,
inside the AS5600 datasheet's 0.5–3.0 mm window, and it is set by the rotor's
own shaft length against a knob that lands on the journal hub — nothing to
adjust, nothing to measure. The magnet stays within **0.242 mm** of the die
centre worst case, inside the datasheet's ±0.25 mm.

**Linear hall.** A magnet on a sleeve running on one column, adjustable from
**1 mm to 13 mm** face-to-face.

It takes **any of three magnets** — Ø6, Ø10 or Ø13 — all seating on the same
face datum. The Ø13 presses straight into the sleeve pocket; the smaller two go
in via a press-in adapter ring. A stepped pocket would have been simpler but is
exactly wrong here: the smallest magnet would end up highest, and it is the one
that has to reach 1 mm from the package. A Ø4 hole through the pocket ceiling
pushes any of them back out — you cannot pull a neodymium magnet out of a blind
hole.

## What changed, and why

**One part, not three.** The plate, the hall column and the encoder portal are
now a single printed body. The encoder stand used to bolt on, which was a thing
to lose and a stack-up between the magnet and the board.

**A column, not posts.** Two Ø6 × 30 mm free-standing cylinders snapped at the
root, and they were always going to: a printed cylinder lays its layer bonds
square across the bending load, offers 42 mm³ of section modulus between them,
and cannot be flared into the plate. The 14 × 10 mm column carries **228 mm³**
— 1.09 MPa at the root under a 10 N shove at the top of its travel, a 23×
margin on PETG's layer-bond strength — resists twist without needing a second
member, and sits on a gusset that spreads the root stress instead of
concentrating it in one layer line.

**A portal, not a cantilever.** The encoder reach used to be a 9 mm ledge
anchored on one side. Two walls carry a deck, so the deck's underside is a true
bridge anchored at both ends.

**A dowel and a diamond on the lobe.** The lobe pins needed a pin radius of
freedom along the line joining them. *Moving* them together by that much does
not give it — the lobe's hole pitch is 13.723 mm and fixed inside the rigid
lobe, the pins print Ø2.10 in a routed Ø2.20, so a 1.010 mm pitch change leaves
the second pin missing its hole by 0.960 mm and the lobe will not go on at all.
Dowel-and-diamond does give it: **MH5 is a round pin and is the datum**, MH6 is
relieved to 1.09 mm along the pitch line and stays full width across it, so the
pair floats **±0.555 mm** on pitch while still stopping the lobe rotating.

And since the main section is on the far side of a flex neck — where the
lamination, not the drawing, decides where it ends up — the **lobe** is the
datum and MH1/MH4 are undersize (Ø1.80, 0.20 mm radial) so the main section
follows it instead of fighting it. The encoder is the tight requirement; a hall
magnet 6 to 13 mm across does not care about a fifth of a millimetre.

## Bill of materials

| Qty | Item | Notes |
|---:|---|---|
| 1 | Ø6 × 2.5 mm magnet, **diametric** | encoder — must be diametrically magnetised or the AS5600 reads nothing useful |
| 1 | Ø6 × 2.5, Ø10 or Ø13 magnet, **axial** | linear hall |
| 1 | M3 heat-set insert, 4 mm | sleeve clamp |
| 1 | M3 × 16 thumbscrew | clamps the sleeve to the column |

## Parts

| Part | Print | Notes |
|---|---|---|
| `fixture_body` | flat, features up | Plate, relief pocket, four locating pins, hall column, encoder portal |
| `rotor` | **inverted**, knob down | Ø9 body, Ø6 magnet pocket |
| `hall_sleeve` | flat, arm underside down | Rectangular bore, Ø13 pocket opening downward |
| `ring_10`, `ring_6` | flat | Press-in adapters |
| `gap_gauge` | flat | One tongue per separation |

No supports on anything. Worst bridge is **11.0 mm of half-span** (the portal
deck, anchored on both walls); nothing anywhere is an unanchored ledge.

## Assembly

1. Press the encoder magnet into the rotor until its face is flush with the
   rotor's bottom. **Check the polarity is diametric** — it should attract and
   repel a second magnet around its circumference, not through its faces.
2. Drop the rotor down through the portal's journal from above. The knob cannot
   follow it through; it lands on the hub and sets the airgap.
3. Melt the M3 insert into the sleeve's clamp boss and fit the thumbscrew.
4. Press the hall magnet into the sleeve pocket, face flush with the sleeve's
   underside — directly for Ø13, through `ring_10` or `ring_6` otherwise. Press
   the ring in flush first, then the magnet into the ring.
5. Slide the sleeve down onto the column.

## Using it

Lift the rotor out, slide the board's lobe under the portal deck, and let the
board down onto its four pins — MH5 first, which is the datum. Drop the rotor
back in.

**Encoder:** turn the knob. Nothing to set.

**Linear hall:** slacken the thumbscrew, slip the gap gauge's step between the
magnet face and the package, let the sleeve down onto it, tighten, withdraw the
gauge. That sets the separation by a printed dimension you can check with
calipers rather than by reading a scale — and it makes sleeve tilt irrelevant
to the number you end up with. Steps are 1, 2, 3, 4, 5, 6, 8, 10 and 13 mm.

To take the board out: lift the rotor, lift the board clear of its pins (3.6 mm,
against 6.5 mm of headroom under the deck), slide it out in −X.

## Checks

```bash
cd magfixture
python3 fixture.py      # STEP + STL into out/
python3 verify.py       # 62 checks
python3 tools/render.py
```

`verify.py` measures sensor targeting, sleeve travel and its clearance to the
PCBA across the whole sweep, every fit as printed, board seating, and
overhangs in each part's print orientation. It shares the board geometry and
the print model with the programming jig in [`../cad`](../cad) rather than
keeping a second copy that can drift.

The printability check tells **bridges from cantilevers**, which the jig's
version does not: it collects overhang area per tessellated triangle, takes the
part's own plan section 0.5 mm below as the support, and counts a patch as
bridged only where it lies inside the convex hull of that section. A bridge is
anchored at both ends and the filament goes into tension; a cantilever has a
free end and curls after a few millimetres. Treating both as "the widest
downward face" is what let a 9 mm one-sided ledge through, and what let the gap
gauge's tongues stick 14 mm into thin air.

## Measure these before printing

`HALL_MAG_T_MAX` (8 mm) is the deepest hall magnet the pocket takes — check
yours fits, since you may use a Ø10 or Ø13 of unknown thickness. Everything
else is driven by the board's own STEP or by the AS5600 datasheet.

If your board drops onto full-size pins at both lobe holes, set
`LOBE_PIN_PULL_IN = 0.0` in `mag_params.py`: MH6 becomes a round pin too, and
the lobe is then located to 0.05 mm instead of 0.555 mm.
