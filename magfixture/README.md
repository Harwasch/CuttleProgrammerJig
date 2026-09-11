# Magnet test fixture — Cuttle CANServo_Driver V0.4

Holds the board flat and presents a magnet to each of its two magnetic
sensors, so both can be exercised on the bench.

| sensor | package | centre | package top |
|---|---|---|---|
| **AS5600L** rotary encoder | SOIC-8 | (+46.81, +0.10) | 1.76 mm above the board |
| **SOT-23** linear hall | 3-pin | (−23.25, +0.07) | 1.20 mm above the board |

Both positions are **measured**, not transcribed: the KiCad STEP export carries
each component's footprint name as a label, and `tools/find_sensors.py` reads
them straight out of it. Re-run it after a board revision.

The encoder sits on the lobe past the +X flex neck, so that lobe gets its own
two locating pins at MH5/MH6 — it is the part of the board that sets the
encoder airgap, and it would otherwise float on the flex.

## What it does

**Encoder.** A Ø6 × 2.5 mm diametric magnet in a rotor, journalled directly
over the package and spun by finger. The airgap is **1.00 mm** face to package,
inside the AS5600 datasheet's 0.5–3.0 mm window, and it is set by the rotor's
own shaft length against a knob that lands on the gantry — there is nothing to
adjust and nothing to measure.

**Linear hall.** A magnet on a carriage running on two posts, adjustable from
**1 mm to 13 mm** face-to-face. Two posts rather than one because the arm
reaches 14.6 mm in over the board and a single post would let it tilt.

It takes **any of three magnets** — Ø6, Ø10 or Ø13 — all seating on the same
face datum. The Ø13 presses straight into the carriage pocket; the smaller two
go in via a press-in adapter ring. A stepped pocket would have been simpler but
is exactly wrong here: the smallest magnet would end up highest, and it is the
one that has to reach 1 mm from the package.

## Bill of materials

| Qty | Item | Notes |
|---:|---|---|
| 1 | Ø6 × 2.5 mm magnet, **diametric** | encoder — must be diametrically magnetised or the AS5600 reads nothing useful |
| 1 | Ø6 × 2.5, Ø10 or Ø13 magnet, **axial** | linear hall |
| 1 | M3 heat-set insert, 4 mm | carriage clamp |
| 1 | M3 × 16 thumbscrew | clamps the carriage to the post |

## Parts

| Part | Print | Notes |
|---|---|---|
| `board_plate` | flat, features up | Seat, relief pocket, four locating pins, both hall posts, the gantry pegs |
| `encoder_gantry` | as modelled | Drops onto two pegs; the reach is a 45° gusset, so no support anywhere |
| `rotor` | **inverted**, knob down | Ø9 body, Ø6 magnet pocket |
| `hall_carriage` | flat | Ø13 pocket opening downward |
| `ring_10`, `ring_6` | flat | Press-in adapters |
| `gap_gauge` | flat | One tongue per separation |

No supports on anything. Worst unsupported span is 8.0 mm.

## Assembly

1. Press the encoder magnet into the rotor until its face is flush with the
   rotor's bottom. **Check the polarity is diametric** — it should attract and
   repel a second magnet around its circumference, not through its faces.
2. Drop the rotor down through the gantry's journal from above. The knob cannot
   follow it through; it lands on the gantry's top face and sets the airgap.
3. Melt the M3 insert into the carriage and fit the thumbscrew.
4. Press the hall magnet into the carriage pocket, face flush with the
   carriage's underside — directly for Ø13, through `ring_10` or `ring_6`
   otherwise. Press the ring in flush first, then the magnet into the ring.
5. Slide the carriage onto the two posts.

## Using it

Drop the board onto the four pins — MH1/MH4 hold the main section, MH5/MH6 the
encoder lobe — then lower the gantry onto its pegs.

**Encoder:** turn the knob. Nothing to set.

**Linear hall:** slacken the thumbscrew, slip the gap gauge's step between the
magnet face and the package, let the carriage down onto it, tighten, withdraw
the gauge. That sets the separation by a printed dimension you can check with
calipers rather than by reading a scale. Steps are 1, 2, 3, 4, 5, 6, 8, 10 and
13 mm.

## Checks

```bash
cd magfixture
python3 fixture.py      # STEP + STL into out/
python3 verify.py       # 40 checks
python3 tools/render.py
```

`verify.py` measures sensor targeting, carriage travel and its clearance to the
PCBA across the whole sweep, every fit as printed, board seating, and overhangs
in each part's print orientation. It shares the board geometry and the print
model with the programming jig in [`../cad`](../cad) rather than keeping a
second copy that can drift.

## Measure these before printing

`HALL_MAG_T_MAX` (8 mm) is the deepest hall magnet the pocket takes — check
yours fits, since you may use a Ø10 or Ø13 of unknown thickness. Everything
else is driven by the board's own STEP or by the AS5600 datasheet.
