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

Sensor positions and package heights are MEASURED from the STEP's own
component labels (AS5600L-ASOM_AMS and SOT-23), not transcribed from a
drawing - see tools/find_sensors.py.
"""
import os
import sys

# the board geometry lives in the programming jig's package; reuse it rather
# than keeping a second copy that can drift
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "cad"))
import params as BOARD                                        # noqa: E402

PCB_T = BOARD.PCB_T                                           # 1.627
bore, shaft, fit = BOARD.bore, BOARD.shaft, BOARD.fit
PRINT_HOLE_SHRINK = BOARD.PRINT_HOLE_SHRINK
PRINT_BOSS_GROW = BOARD.PRINT_BOSS_GROW

# ----------------------------------------------------------------- sensors ---
# centre XY and package top, as heights ABOVE THE BOARD TOP FACE
ENC_XY               = (46.81, 0.10)
ENC_PKG_H            = 1.76    # AS5600L-ASOM, SOIC-8
HALL_XY              = (-23.25, 0.07)
HALL_PKG_H           = 1.20    # SOT-23

# absolute, in fixture Z
ENC_PKG_TOP          = PCB_T + ENC_PKG_H          # 3.387
HALL_PKG_TOP         = PCB_T + HALL_PKG_H         # 2.827

# ----------------------------------------------------------------- magnets ---
ENC_MAG_D            = 6.0     # diametrically magnetised, per the AS5600
ENC_MAG_T            = 2.5     # datasheet's recommended magnet
ENC_AIRGAP           = 1.0     # magnet face to package top; datasheet 0.5-3.0

# The hall side takes any of three, all seated face-flush in one pocket by
# means of press-in adapter rings. A stepped pocket cannot do this: the
# smallest magnet would end up highest, and it is the one that has to reach
# 1 mm from the package.
HALL_MAG_DS          = [6.0, 10.0, 13.0]
HALL_MAG_T_MAX       = 8.0     # deepest magnet the pocket takes  <-- CHECK YOURS
HALL_GAP_MIN         = 1.0     # face-to-face travel the carriage must cover
HALL_GAP_MAX         = 13.0

# ------------------------------------------------------------- board plate ---
PLATE_X              = (-60.0, 64.0)
PLATE_Y              = (-26.0, 16.0)
PLATE_T              = 6.0     # seat plane down to the underside
PLATE_FILLET         = 4.0
RECESS               = 3.0     # relief pocket under the components
LOCATOR_D            = shaft(2.10)          # -> prints 2.10 in a routed Ø2.20
LOCATOR_H            = PCB_T + 2.0          # proud of the board for loading
LOCATORS             = ["MH1", "MH4", "MH5", "MH6"]   # main section, then lobe

# -------------------------------------------------------------- hall tower ---
# Two posts, not one: the carriage arm reaches 14.6 mm in over the board, and a
# single post would let it rotate and tilt.
HALL_POST_D          = shaft(6.0)
HALL_POST_HOLE_D     = bore(6.30)           # 0.15 mm radial as printed
HALL_POST_Y          = -14.5
HALL_POST_DX         = 11.0                 # spacing either side of the sensor
HALL_POST_TOP        = 30.0
HALL_CARRIAGE_T      = 8.0
HALL_ARM_W           = 9.0
HALL_BODY_BACK       = 14.0   # -X overhang of the carriage body, so the clamp
                              # screw has real depth before it meets the post
# Sized to PRINT at a light press on the Ø13 magnet, not to print at 13.20.
HALL_POCKET_D        = bore(13.0 - 0.02)    # -> prints 12.98
HALL_POCKET_DEPTH    = HALL_MAG_T_MAX
# Adapter rings press into that same pocket with 0.03 mm of interference, so a
# Ø10 or Ø6 magnet ends up on the SAME face datum as the Ø13 one.
RING_OD              = shaft(13.0 - 0.02 + 0.03)
INSERT_M3_H          = BOARD.INSERT_M3_H
INSERT_M3_HOLE_D     = BOARD.INSERT_M3_HOLE_D
INSERT_M3_HOLE_DEPTH = 6.0

# ---------------------------------------------------------- encoder gantry ---
# A separate part so the board drops straight in and the gantry goes on after,
# and so it can print with its beam face on the bed - no bridge, no support.
GANTRY_TOP           = 20.0
GANTRY_BEAM_T        = 6.0
GANTRY_LEG_X         = [38.0, 57.0]         # straddles the lobe in X
GANTRY_LEG_W         = 16.0   # wide enough for the locating pegs at +/-5
GANTRY_PEG_D         = shaft(5.0)
GANTRY_PEG_HOLE_D    = bore(5.30)
GANTRY_PEG_H         = 6.0

# ------------------------------------------------------------------- rotor ---
# The body is ONE diameter all the way down, and the journal is bored to suit.
# With a slim shaft and a fat magnet cup the rotor was oversize at BOTH ends --
# knob Ø14 above, cup Ø9 below, journal Ø5.5 between -- so it could not be
# assembled from either direction. Now the whole body passes down through the
# journal and only the knob stays on top, where it also sets the airgap.
ROTOR_SHAFT_D        = shaft(9.0)
ROTOR_BORE_D         = bore(9.30)           # 0.15 mm radial: spins by finger
ROTOR_KNOB_D         = 16.0
ROTOR_KNOB_T         = 5.0
ROTOR_POCKET_D       = bore(ENC_MAG_D - 0.02)   # light press on the magnet
ROTOR_FLUTES         = 8

# Derived: the knob's underside rests on the gantry's top face, so the shaft
# length alone sets the airgap. Nothing to adjust, nothing to measure.
ROTOR_MAG_FACE_Z     = ENC_PKG_TOP + ENC_AIRGAP
ROTOR_SHAFT_L        = GANTRY_TOP - ROTOR_MAG_FACE_Z

# --------------------------------------------------------------- gap gauge ---
# A stepped comb. Slip the step you want between the magnet face and the
# package, drop the carriage onto it, tighten. That sets the separation by a
# printed dimension you can check with calipers, rather than by reading a scale.
GAUGE_STEPS          = [1, 2, 3, 4, 5, 6, 8, 10, 13]
GAUGE_STEP_W         = 9.0
GAUGE_BODY_T         = 3.0
GAUGE_TONGUE_L       = 14.0
