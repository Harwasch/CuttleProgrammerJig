"""Cuttle CANServo_Driver pogo programming jig - all tunable dimensions.

Coordinate system
-----------------
X, Y : the JIG frame, identical to board_geometry.json.
       Origin = centroid of the four 2.2 mm holes on the main rigid section.
Z    : 0 = the base's hard-stop plateau, i.e. the face the nest lands on when
       the clamp is fully closed. +Z is up. Everything else is derived.

The one number to verify with calipers before printing is PIN_PROTRUSION.
"""

# ---------------------------------------------------------------- board -----
PCB_T                = 1.627   # board thickness, from the gerber job file
PART_H_BOTTOM        = 2.585   # tallest bottom-side part, from the STEP
PART_H_TOP_MAIN      = 1.285   # tallest top-side part on the main rigid section

# ------------------------------------------------------------ pogo pins -----
# P50-B1 probe in an R50-2S receptacle.
PIN_PROTRUSION       = 3.35    # probe tip above the receptacle's top face  <-- VERIFY
PIN_STROKE_MAX       = 2.65    # full travel of a P50 before it bottoms out
COMPRESSION          = 1.20    # working stroke, 45% of full - the design target
PIN_FORCE_G          = 75      # per probe at working stroke

RECEPT_LEN           = 17.5    # R50-2S overall length
RECEPT_BODY_D        = 0.86    # sleeve body diameter
RECEPT_HEAD_D        = 0.98    # sleeve head diameter
RECEPT_HEAD_L        = 2.5     # head length
PIN_BORE_D           = 0.85    # PRINTED pilot -> ream/drill to 0.90 mm
PIN_BORE_L           = 6.0     # precision bore length that holds the sleeve
PIN_HEAD_BORE_D      = 1.05    # counterbore for the sleeve head
PIN_CLEAR_D          = 1.8     # loose clearance below the precision bore

# --------------------------------------------------------------- travel -----
TRAVEL               = 3.00    # nest lift: rest -> hard stop
NEST_T               = 6.00    # PCB seat height above the nest's own underside
NEST_LIP             = 0.80    # raised lip forming the drop-in board recess
NEST_LIP_CLEAR       = 0.35    # gap between the lip and the board outline

# Derived: top of the pin platform, above the hard-stop plateau.
Z_PIN_TOP            = NEST_T + COMPRESSION - PIN_PROTRUSION      # = 3.85

# --------------------------------------------------------- nest windows -----
PROBE_ISLAND_R       = 1.50    # radius of the platform boss around each probe
PLATFORM_GAP         = 0.50    # nest window to pin platform clearance
PART_CLEAR_XY        = 0.40    # inflation applied to bottom-part footprints
PART_CLEAR_Z         = 0.40    # vertical clearance under bottom-side parts

# ------------------------------------------------- guide posts + springs -----
POST_D               = 5.00    # guide post diameter
POST_HOLE_D          = 5.30    # matching hole in the nest and the cover
POST_TOP_Z           = 16.00   # post top, tall enough to guide the cover
POST_XY              = [(-38.0, 8.5), (-38.0, -8.5),
                        ( 24.0, 8.5), ( 24.0, -8.5)]

SPRING_WIRE_D        = 0.60    # 0.6 x 7 mm compression spring from the kit
SPRING_OD            = 7.00
SPRING_ACTIVE_COILS  = 9       # estimate for a 15 mm free length
SPRING_FREE          = 15.00   # free length
SPRING_POCKET_D      = 7.60
BASE_SPRING_DEPTH    = 7.00    # counterbore in the base
NEST_SPRING_DEPTH    = 3.00    # counterbore in the nest underside

# The board's top side is densely populated over the probe cluster, so the
# hold-down lands on five small pads chosen to sit clear of every part and of
# the board edge, with their centroid close to the probe force centroid.
COVER_PADS           = [(-28.30, -6.05), (-27.55, -1.30), (-27.30, 6.95),
                        (-14.80,  7.95), (-14.30, -8.05)]
COVER_PAD_R          =   1.60  # hold-down contact pad radius
COVER_PAD_H          =   1.80  # standoff; tallest top part under the cover is 1.29 mm

# --------------------------------------------------------- board locators ---
LOCATOR_D            = 2.05    # short pins on the nest, into the 2.2 mm holes
LOCATOR_H            = 3.00    # height above the PCB seat
LOCATOR_HOLES        = ["MH1", "MH4"]     # diagonal pair, best angular control

# ------------------------------------------------------------- nest plate ---
NEST_X               = (-58.0, 55.0)
NEST_Y               = ( -14.0, 14.0)
NEST_FILLET          =   3.0

# ------------------------------------------------------------- base plate ---
# The base plate is the precision part: it prints flat on its underside with
# the posts and the pin platform pointing up, so nothing overhangs.
PLATE_Z_BOTTOM       =  -8.0
PLATE_X              = (-64.0, 61.0)
PLATE_Y              = ( -20.0, 20.0)
PLATE_FILLET         =   4.0
MOUNT_SCREW_D        =   3.4   # M3 clearance, base plate -> stand
MOUNT_SCREW_XY       = [(-59.0, -15.5), (-59.0, 15.5), (56.0, -15.5), (56.0, 15.5)]

# ------------------------------------------------------------------ stand ---
# One monolithic part: the open frame under the base plate and the clamp tower
# are the same walls, not a bolt-on bracket.
STAND_Z_BOTTOM       = -30.0   # 22 mm of open space under the plate for wiring
STAND_WALL           =   4.0
TOWER_TOP_Z          =  12.0   # clamp mounting deck
TOWER_DECK_T         =   5.0
WIRE_EXIT_Z          = (-26.0, -12.0)   # loom exit, on the far side from the clamp
TIE_BAR_W            =   4.0           # vertical divider, to tie the loom against
WIRE_SLOT_W          =  20.0

# ----------------------------------------------------------------- cover ----
COVER_T              =   4.0   # hold-down cover thickness
COVER_POSTS          = [(-38.0, 8.5), (-38.0, -8.5)]     # cover rides these
COVER_MARGIN         =   4.0
COVER_TAB_L          =   9.0   # lift-off grip tab
COVER_DIMPLE_R       =   4.0   # seat for the clamp spindle tip, at the pad centroid

# -------------------------------------------------------- clamp interface ---
# GH-201 horizontal toggle clamp: 75 x 25 x 17 mm, 6 x 4 mm mounting slots.
# The riser is a separate part on a slotted rail so it can be tuned to the
# clamp you actually have without reprinting the base.
RAIL_SLOT_D          =   4.4   # M4 clearance
# The clamp tower is part of the stand. Its deck slots are longer than the
# clamp's own so the GH-201 still slides fore and aft; height comes from the
# spindle. Changing TOWER_TOP_Z means reprinting the stand.
PEDESTAL_X           = (-44.0,  -6.0)
PEDESTAL_Y           = (-52.0, -20.0)
CLAMP_SLOT_TRAVEL    =   8.0   # extra length on the deck slots, for reach trim
NUT_CHANNEL_W        =   7.2   # M4 nut across flats, sliding fit
NUT_CHANNEL_H        =   3.6
RAIL_SLOT_D          =   4.4   # M4 clearance
CLAMP_BASE_W         =  25.0   # GH-201 body, checked against the riser deck
CLAMP_BASE_L         =  75.0
CLAMP_SLOT_L         =   6.0
CLAMP_SLOT_W         =   4.0
CLAMP_SLOT_DX        =  15.9   # <-- measure yours; drawing shows 15.9 x 11.1
CLAMP_SLOT_DY        =  11.1

# ------------------------------------------------------------ printing -----
