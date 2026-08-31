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

# Probe bores are printed to final size -- no drilling. FDM renders a small
# vertical hole undersize, by an amount that depends on your printer, nozzle,
# material and speed, so PIN_BORE_D is a MODELLED diameter to be calibrated
# once against the fit gauge (cad/out/fit_gauge.stl). Print the gauge, find
# the hole the sleeve just pushes into, set that number here, print the plate.
# 1.00 is a typical starting point: most 0.4 mm-nozzle profiles render it
# around 0.86-0.92 mm.
PIN_BORE_D           = 1.00
PIN_BORE_L           = 9.0     # bore length holding the sleeve; longer is
                               # better, it is what limits sleeve tilt
PIN_LEAD_D           = 1.40    # short lead-in at the top, eases insertion
PIN_LEAD_L           = 1.20
PIN_CLEAR_D          = 2.20    # loose clearance below the bore
GAUGE_BORES          = [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]

# --------------------------------------------------------------- travel -----
TRAVEL               = 3.00    # nest lift: rest -> hard stop
NEST_T               = 6.00    # PCB seat height above the nest's own underside
NEST_LIP             = 0.80    # raised lip forming the drop-in board recess
NEST_LIP_CLEAR       = 0.50    # gap between the lip and the board outline. The
                               # board is held by base-plate pins while the
                               # recess moves with the nest, so this has to
                               # clear the nest's own play as well.

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
SPRING_FREE          = 15.00   # free length -- but SELECT ON SOLID HEIGHT: it
                               # must stack shorter than BASE_SPRING_DEPTH +
                               # NEST_SPRING_DEPTH (10 mm) or the nest never
                               # reaches its stop. A 15-coil spring solids at
                               # 10.2 mm and would not work.
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
COVER_LEADIN         =   1.00  # chamfer on the guide holes: only 5.8 mm of the
                               # cover rides 24 mm of reach, so it needs a lead-in

# --------------------------------------------------------- board locators ---
# The pins stand on the BASE PLATE, not on the nest, and pass up through
# clearance holes in the nest into the board. That deletes two links from the
# chain that sets where a probe tip lands -- the nest's own position on the
# guide posts, and the print accuracy of a pin mounted on it -- because the
# board then registers directly to the part that holds the probes. Worst case
# over the whole chain drops from 0.674 mm to 0.344 mm against a 0.6 mm pad.
#
# They were on the nest while they also had to carry the springs; the springs
# moved to the Ø5 guide posts, so the pins now carry no load and a slender
# printed pin is fine.
#
# All four main-section holes are used. Two locate (full size, diagonal pair,
# 29.6 mm apart for the least angular error); the other two are undersize so
# they cannot fight the first two if print and board tolerances disagree.
LOCATOR_D            = 2.10    # primary pins, into the board's 2.2 mm holes
LOCATOR_D2           = 1.80    # secondary pins, engage without constraining
LOCATOR_TOP_Z        = 12.00   # pin top; board underside is 9.0 at rest, so
                               # this keeps 3 mm engaged with the clamp open
LOCATOR_NEST_CLEAR   = 0.35    # radial clearance in the nest's pass-through,
                               # covering the nest's own play on the posts
LOCATOR_PRIMARY      = ["MH1", "MH4"]
LOCATOR_SECONDARY    = ["MH2", "MH3"]
SEAT_BOSSES          = ["MH1", "MH2", "MH3", "MH4", "MH5", "MH6"]
BOSS_R_MAX           = 4.00    # capped; each boss also respects its own
BOSS_PART_CLEAR      = 0.30    # clearance to the nearest bottom-side part

# The nest seats the board on those bosses and on the bare sections, and drops
# everything else clear in ONE pocket -- no ribs threaded between components.
NEST_RECESS          = 3.00    # pocket depth below the seat
BARE_SECTIONS        = [(-56.0, -33.2), (15.4, 41.0)]   # tab+flexes: no parts
MCU_BOSS             = (-27.26, 2.92, 4.40, 0.855)      # x, y, size, part height
MCU_BOSS_CLEAR       = 0.10    # boss stops just short of the package
PROBE_CLEAR_D        = 4.00    # holes for the base's probe islands

# ------------------------------------------------------------- nest plate ---
NEST_X               = (-58.0, 55.0)
NEST_Y               = ( -15.0, 15.0)
NEST_FILLET          =   3.0

# ------------------------------------------------------------- base plate ---
# The base plate is the precision part: it prints flat on its underside with
# the posts and the pin platform pointing up, so nothing overhangs.
PLATE_Z_BOTTOM       =  -8.0
PLATE_X              = (-64.0, 61.0)
PLATE_Y              = ( -21.0, 21.0)
PLATE_FILLET         =   4.0
MOUNT_SCREW_D        =   3.4   # M3 clearance, base plate -> stand
MOUNT_SCREW_XY       = [(-59.0, -15.5), (-59.0, 15.5), (56.0, -15.5), (56.0, 15.5)]

# ------------------------------------------------------------------ stand ---
# One monolithic part: the open frame under the base plate and the clamp tower
# are the same walls, not a bolt-on bracket.
STAND_Z_BOTTOM       = -30.0   # 22 mm of open space under the plate for wiring
STAND_WALL           =   4.0
# The GH-201's spindle sits at its mounting plane and only adjusts DOWNWARD, so
# the deck has to be ABOVE the surface it presses. The cover top is 13.43 mm
# closed and 16.43 mm open; 20 mm puts the spindle 6.6 mm down from its plane,
# mid-range on a 15 mm assembly, and leaves the arm around 27 mm -- clear of
# both the open cover and the 16 mm guide posts.
TOWER_TOP_Z          =  20.0   # clamp mounting deck
TOWER_DECK_T         =   5.0
TOWER_SOLID_Z        =  10.0   # tower is hollow below this, solid above; keeps
                               # the solid band ~10 mm as the deck rises
WIRE_EXIT_Z          = (-26.0, -12.0)   # loom exit, on the far side from the clamp
TIE_BAR_W            =   4.0           # vertical divider, to tie the loom against
WIRE_SLOT_W          =  20.0

# ----------------------------------------------------------------- cover ----
COVER_T              =   4.0   # hold-down cover thickness
COVER_POSTS          = [(-38.0, 8.5), (-38.0, -8.5)]     # cover rides these
COVER_MARGIN         =   4.0
COVER_TAB_L          =   9.0   # lift-off grip tab
COVER_DIMPLE_R       =   4.0   # seat for the clamp spindle tip, at the pad centroid

# --------------------------------------------------------------- geometry ---
# The stand is one full rectangle, not an L: the board bay and the clamp bay
# share their whole width, and the open compartments either side of the tower
# double as a parts tray.
STAND_X              = (-70.0, 67.0)
STAND_Y              = (-56.0, 27.0)
PEDESTAL_X           = (-44.0,  -6.0)
PEDESTAL_Y           = (-56.0, -21.0)
# Ribs must miss the loom run: the probe cluster is at x -32..-17 and the exit
# at x +/-10, so a rib at x -4 sat right in the path.
RIB_X                = [-46.0, 20.0]  # internal ribs, vertical walls only

# -------------------------------------------------------- clamp interface ---
# GH-201 horizontal toggle clamp: 75 x 25 x 17 mm, mounting holes on a
# 15.9 x 11.1 mm pattern, spindle pressing DOWN from its mounting plane.
CLAMP_BASE_W         =  25.0   # body width, checked against the deck
CLAMP_BASE_L         =  75.0
CLAMP_HOLE_DX        =  15.9   # <-- measure yours; these are off the drawing
CLAMP_HOLE_DY        =  11.1

# It bolts into M3 heat-set inserts, not nuts in a channel. Kadrick M3 measure
# 4.5 mm across the knurl and 3.9 mm at the tip, so a 4.0 mm blind hole -- the
# usual "between the two diameters" rule. Load is about 4 N per bolt, so the
# shortest plentiful insert in the kit is far more than enough.
INSERT_M3_H          =   4.0   # insert length
INSERT_M3_HOLE_D     =   4.0   # blind hole diameter
INSERT_M3_HOLE_DEPTH =   5.0   # 1 mm deeper than the insert, for displaced plastic

# Fixed inserts give up the fore-and-aft trim the slots allowed, so the mount
# position has to be right first time. MEASURE THIS on your clamp: spindle axis
# to the nearer of the two mounting-hole rows. 24.6 mm is read off the drawing
# (19.6 mm spindle-to-plate plus about 5 mm plate-edge-to-hole), not measured.
CLAMP_SPINDLE_TO_ROW =  24.6

# ------------------------------------------------------------ printing -----
