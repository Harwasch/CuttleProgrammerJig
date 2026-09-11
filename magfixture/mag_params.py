"""Magnet test fixture for the Cuttle CANServo_Driver V0.4 - all dimensions.

Holds the board flat and presents two magnets to its two magnetic sensors:

  AS5600L  rotary encoder, SOIC-8 on the lobe past the +X flex neck.
           A diametric magnet must sit centred over it and SPIN.
  SOT-23   linear hall sensor, on the centreline at the tapering end of the
           main section. An axial magnet must move from 1 mm to 13 mm of
           face-to-face separation.

Coordinate system
-----------------
X, Y : the BOARD frame, identical to cad/board_geometry.json, so every sensor
       position below comes straight out of the KiCad STEP export.
Z    : 0 = the board's underside where it sits on the fixture. +Z is up.

Sensor XY comes from the STEP's own component labels (AS5600L-ASOM_AMS and
SOT-23) - see tools/find_sensors.py. Package HEIGHT is taken from
cad/board_parts.json, the same keep-out data the interference checks use, so
the airgap the fixture builds and the airgap the checks measure cannot
disagree. (The STEP labels gave 1.76 and 1.20; the keep-out boxes give 1.84
and 1.285, 0.08 mm taller, because they include the lead standoff.)
"""
import os
import sys

# the board geometry lives in the programming jig's package; reuse it rather
# than keeping a second copy that can drift
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "cad"))
import params as BOARD                                        # noqa: E402
import geom as G                                              # noqa: E402

PCB_T = BOARD.PCB_T                                           # 1.627
bore, shaft, fit = BOARD.bore, BOARD.shaft, BOARD.fit
PRINT_HOLE_SHRINK = BOARD.PRINT_HOLE_SHRINK
PRINT_BOSS_GROW = BOARD.PRINT_BOSS_GROW


def _pkg_h(xy):
    """Height of the tallest top-side keep-out box covering this point."""
    x, y = xy
    hs = [h for x0, x1, y0, y1, h in G.PARTS["top"]
          if x0 <= x <= x1 and y0 <= y <= y1]
    if not hs:
        raise ValueError(f"no top-side part covers {xy}")
    return max(hs)


# ----------------------------------------------------------------- sensors ---
ENC_XY               = (46.81, 0.10)     # AS5600L-ASOM, SOIC-8, on the lobe
HALL_XY              = (-23.25, 0.07)    # SOT-23, on the centreline
ENC_PKG_H            = _pkg_h(ENC_XY)    # 1.840
HALL_PKG_H           = _pkg_h(HALL_XY)   # 1.285

# absolute, in fixture Z
ENC_PKG_TOP          = PCB_T + ENC_PKG_H          # 3.467
HALL_PKG_TOP         = PCB_T + HALL_PKG_H         # 2.912

# ----------------------------------------------------------------- magnets ---
ENC_MAG_D            = 6.0     # diametrically magnetised, per the AS5600
ENC_MAG_T            = 2.5     # datasheet's recommended magnet
ENC_AIRGAP           = 1.0     # magnet face to package top; datasheet 0.5-3.0

# The hall side takes any of three, all seated face-flush in one pocket by
# means of press-in adapter rings. A stepped pocket cannot do this: the
# smallest magnet would end up highest, and it is the one that has to reach
# 1 mm from the package.
HALL_MAG_DS          = [6.0, 10.0, 13.0]
HALL_MAG_T_MAX       = 8.0     # deepest magnet the pocket takes
HALL_GAP_MIN         = 1.0     # face-to-face travel the sleeve must cover
HALL_GAP_MAX         = 13.0

# ------------------------------------------------------------ fixture body ---
# ONE part: plate, locating pins, hall column and encoder portal. The encoder
# stand used to be a separate bolt-on - an extra thing to lose, and an extra
# stack-up between the magnet and the board.
PLATE_X              = (-60.0, 64.0)
PLATE_Y              = (-31.0, 19.0)
PLATE_T              = 6.0     # seat plane down to the underside
PLATE_FILLET         = 4.0
RECESS               = 3.0     # relief pocket under the components
LOCATOR_D            = shaft(2.10)          # -> prints 2.10 in a routed Ø2.20
LOCATOR_H            = PCB_T + 2.0          # proud of the board for loading
LOCATORS             = ["MH1", "MH4", "MH5", "MH6"]   # main section, then lobe

# The lobe pair needed a pin radius of freedom along the line joining them.
# MOVING both pins inward by that much does not give it: the lobe's hole pitch
# is 13.723 mm and fixed inside the rigid lobe, the pins print Ø2.10 in a
# routed Ø2.20, so a 1.010 mm pitch change leaves the second pin missing its
# hole by 0.960 mm and the lobe cannot go on at all.
#
# What DOES give it is dowel-and-diamond. MH5 is a round pin and is the datum.
# MH6 is relieved to LOBE_DIAMOND_W along the pitch line and stays full width
# across it, so it still stops the lobe rotating while letting the pitch float
# by a pin radius. Same freedom, and the lobe drops on.
LOBE_PIN_PULL_IN     = LOCATOR_D / 2        # 1.010 of freedom along the pitch
LOBE_DIAMOND_W       = LOCATOR_D - LOBE_PIN_PULL_IN
LOBE_DATUM           = "MH5"

# The main section is on the far side of a flex neck, and how the flex was
# laminated -- not the drawing -- sets where it ends up relative to the lobe.
# So the LOBE is the datum, because the encoder is the tight requirement, and
# the main section gets pins loose enough to follow it. A hall magnet 6 to
# 13 mm across does not care about a fifth of a millimetre.
MAIN_LOCATOR_D       = shaft(1.80)          # 0.20 mm radial in the same Ø2.20

# -------------------------------------------------------------- hall column ---
# A COLUMN, not posts. Two Ø6 x 30 mm free-standing cylinders gave 42 mm3 of
# section modulus and snapped at the root: a printed cylinder puts its layer
# bonds square across the bending load and cannot be flared into the plate.
# A 14 x 10 rectangular column is 233 mm3 -- 5.5x stiffer, 2.5x the root area,
# it resists rotation without needing a second member, and it takes a plinth.
HALL_COL_W           = shaft(14.0)          # X, prints 14.00
HALL_COL_T           = shaft(10.0)          # Y, prints 10.00
HALL_COL_R           = 2.0                  # corner radius, column and bore
HALL_COL_TOP         = 36.0
HALL_COL_Y           = -20.0                # column centre in Y, clear of the
                                            # board edge at y = -10.05
# A gusset at the root, sized off the column rather than off nothing: the
# flare is at least a quarter of the thinner column dimension, and it leans
# less than 45 degrees so it prints without support. It also has to END below
# the sleeve's lowest position (z = 3.912 at a 1 mm gap) or the sleeve cannot
# come down that far.
HALL_PLINTH_H        = 3.4
HALL_PLINTH_FLARE    = 2.8
HALL_COL_CHAMFER     = 1.0                  # lead-in for the sleeve

HALL_BORE_W          = bore(14.30)          # 0.15 mm per side as printed
HALL_BORE_T          = bore(10.30)
HALL_SLEEVE_WALL     = 4.0
HALL_SLEEVE_H        = 18.0    # bore engagement. The arm reaches 19.6 mm to
                               # the sensor, so every 0.1 mm of tilt at the
                               # bore becomes 0.2 mm at the magnet; 18 mm of
                               # engagement keeps that under a quarter of a mm.
HALL_ARM_T           = 10.0    # arm thickness, the bottom of the sleeve
HALL_ARM_W           = 14.0
HALL_BOSS_T          = 5.0     # pad on the -Y face so the clamp insert has
                               # full depth before it breaks into the bore
# Sized to PRINT at a light press on the Ø13 magnet, not to print at 13.20.
HALL_POCKET_D        = bore(13.0 - 0.02)    # -> prints 12.98
HALL_POCKET_DEPTH    = HALL_MAG_T_MAX
HALL_EJECT_D         = 4.0     # through the pocket ceiling: you cannot pull a
                               # neodymium magnet out of a blind hole
# Adapter rings press into that same pocket with 0.03 mm of interference, so a
# Ø10 or Ø6 magnet ends up on the SAME face datum as the Ø13 one.
RING_OD              = shaft(13.0 - 0.02 + 0.03)
RING_H               = 6.0
INSERT_M3_H          = BOARD.INSERT_M3_H
INSERT_M3_HOLE_D     = BOARD.INSERT_M3_HOLE_D
INSERT_M3_HOLE_DEPTH = 6.0
M3_CLEAR_D           = 3.4

# ---------------------------------------------------------- encoder portal ---
# MONOLITHIC with the plate, and a PORTAL rather than a cantilever. As a
# separate bolt-on it was an extra part to lose; as a cantilever its underside
# was a 9 mm ledge anchored on one side only, which droops however good the
# bridging is. Two walls carry a deck, so the deck's underside is a true bridge
# anchored on both sides.
#
# The walls stand clear of the lobe in Y (lobe half-width 9.46) and the deck
# stands clear of it in Z, so the board lifts off its pins and slides out in -X
# once the rotor has been lifted out of the journal.
PORTAL_X             = (38.0, 58.0)
PORTAL_GAP_Y         = 22.0                 # clear between the walls
PORTAL_WALL_T        = 5.0
PORTAL_DECK_Z        = (10.0, 16.0)
# The journal wants 12 mm of bore to hold the magnet on centre, but a 12 mm
# deck makes the portal a solid block you cannot see the encoder through. So
# the deck is 6 mm and the other 6 mm is a hub standing on it.
ROTOR_HUB_D          = 16.0
ROTOR_HUB_TOP        = 22.0
GANTRY_TOP           = ROTOR_HUB_TOP        # the knob lands here
JOURNAL_L            = ROTOR_HUB_TOP - PORTAL_DECK_Z[0]

# ------------------------------------------------------------------- rotor ---
# The body is ONE diameter all the way down, and the journal is bored to suit.
# With a slim shaft and a fat magnet cup the rotor was oversize at BOTH ends --
# knob Ø14 above, cup Ø9 below, journal Ø5.5 between -- so it could not be
# assembled from either direction. Now the whole body passes down through the
# journal and only the knob stays on top, where it also sets the airgap.
ROTOR_SHAFT_D        = shaft(9.0)
ROTOR_BORE_D         = bore(9.20)           # 0.10 mm radial: spins by finger,
                                            # and holds the magnet on centre
ROTOR_KNOB_D         = 20.0
ROTOR_KNOB_T         = 5.0
ROTOR_POCKET_D       = bore(ENC_MAG_D - 0.02)   # light press on the magnet
ROTOR_FLUTES         = 8

# Derived: the knob's underside rests on the deck's top face, so the shaft
# length alone sets the airgap. Nothing to adjust, nothing to measure.
ROTOR_MAG_FACE_Z     = ENC_PKG_TOP + ENC_AIRGAP
ROTOR_SHAFT_L        = GANTRY_TOP - ROTOR_MAG_FACE_Z

# --------------------------------------------------------------- gap gauge ---
# A stepped comb. Slip the step you want between the magnet face and the
# package, drop the sleeve onto it, tighten. That sets the separation by a
# printed dimension you can check with calipers, rather than by reading a
# scale -- and it makes sleeve tilt irrelevant to the number you end up with.
GAUGE_STEPS          = [1, 2, 3, 4, 5, 6, 8, 10, 13]
GAUGE_STEP_W         = 9.0
GAUGE_BODY_T         = 3.0
GAUGE_TONGUE_L       = 14.0

# ------------------------------------------------------------- printability ---
# A bridge is anchored at both ends and the filament goes into tension; a
# cantilever has a free end and curls. They are not the same limit.
BRIDGE_HALF_MAX      = 12.5    # -> 25 mm between anchors
CANTILEVER_MAX       = 5.0     # unsupported ledge, one side only
