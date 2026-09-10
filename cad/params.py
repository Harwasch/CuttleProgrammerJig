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
# 1.20 is the MEASURED result on this build: the sleeve entered the gauge's
# 120 bore and nothing smaller, so the profile is rendering a small vertical
# hole about 0.22 mm under nominal -- more shrink than the 0.08-0.14 mm a PLA
# profile usually gives, which is normal for PETG. Recalibrate if you change
# printer, nozzle, material or speed.
PIN_BORE_D           = 1.20    # what the gauge measured: the head just enters
# STEPPED, so the sleeve has somewhere to STOP. Previously the lead-in printed
# at 1.18 and the bore at 0.98 -- both at or over the Ø0.98 head -- so the head
# passed straight through and depth was set purely by how hard you pushed. That
# made PIN_PROTRUSION, which the whole stack-up derives from, an assembly
# variable rather than a geometric one.
#
# Now: a counterbore exactly one head long, then a bore sized for the BODY. The
# head cannot enter the body bore, so it bottoms with its top flush with the
# platform, by construction.
PIN_HEAD_BORE_L      = RECEPT_HEAD_L                    # 2.5 mm, one head
PIN_BODY_BORE_D      = PIN_BORE_D - (RECEPT_HEAD_D - RECEPT_BODY_D) + 0.04
PIN_BORE_L           = 8.0     # body guidance below the head; this is what
                               # actually limits sleeve tilt now
PIN_MOUTH_CHAMFER    = 0.15    # replaces the old oversized lead-in. Small: on
                               # the two crowded bores it is the widest feature
                               # and so sets the thinnest wall.
PIN_CLEAR_D          = 2.20    # loose clearance below the bore
# The gauge must bracket the answer on BOTH sides -- a sleeve that only enters
# the largest bore tells you nothing about whether that bore is a press fit or
# already loose. 1.20 landed on the old top slot, so the range moved up.
GAUGE_BORES          = [0.90, 0.95, 1.00, 1.05, 1.10,
                        1.15, 1.20, 1.25, 1.30, 1.35]

# ------------------------------------------------------- the print model ----
# Calibrated from the fit gauge, and the SINGLE source for every fit in this
# file. These used to be literals buried inside verify.py, so changing
# PIN_BORE_D for a different printer -- the whole documented tuning workflow --
# silently left every other fit computed for the old machine.
#
# Recalibrate BOTH together: PIN_BORE_D is what the gauge measures, and
# PRINT_HOLE_SHRINK is PIN_BORE_D minus the sleeve head it just accepts.
PRINT_HOLE_SHRINK    = 0.22    # a vertical hole renders this much UNDER nominal
PRINT_BOSS_GROW      = 0.08    # a vertical boss renders this much OVER nominal


def bore(nominal):
    """Model a hole so it PRINTS at `nominal`."""
    return nominal + PRINT_HOLE_SHRINK


def shaft(nominal):
    """Model a boss so it PRINTS at `nominal`."""
    return nominal - PRINT_BOSS_GROW


def fit(hole_d, shaft_d):
    """Radial clearance as printed, for a modelled hole/shaft pair."""
    return ((hole_d - PRINT_HOLE_SHRINK) - (shaft_d + PRINT_BOSS_GROW)) / 2


# --------------------------------------------------------------- travel -----
# TRAVEL is DERIVED at the bottom of the spring block. Nothing in the geometry
# limits upward travel -- the posts are plain cylinders with no head -- so the
# rest position is wherever the spring reaches free length. Asserting 3.00 here
# while the pockets summed to 10 mm against a 15 mm spring put the real rest
# position at 5.00 mm, and every open-position number was wrong by 2 mm: the
# locator pins ended up BELOW the board top instead of 1.37 mm proud.
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
PART_CLEAR_XY        = 0.30    # inflation applied to bottom-part footprints.
                               # 0.40 left only 0.25 mm of collar on SWDIO,
                               # against an RSS board-location error of 0.19
PART_CLEAR_Z         = 0.40    # vertical clearance under bottom-side parts

# ------------------------------------------------- guide posts + springs -----
POST_D               = 5.00    # guide post diameter
# Four posts in four holes is over-constrained: any difference in print scaling
# between the two parts binds them however round the holes are. The old 5.30
# left 0.30 mm modelled, which this printer's 0.22 mm hole shrink and ~0.08 mm
# boss growth consumed exactly -- an as-printed line-to-line press fit. The
# posts now only guide and carry the springs; REG_* below does the locating.
POST_HOLE_D          = 5.80    # ~0.50 mm diametral as printed, 0.25 radial
POST_TOP_Z           = 16.00   # post top, tall enough to guide the cover
POST_XY              = [(-38.0, 8.5), (-38.0, -8.5),
                        ( 24.0, 8.5), ( 24.0, -8.5)]

# ------------------------------------------- nest-to-base registration -----
# Two pins, not four posts: a round hole at the primary and a slot at the
# secondary is kinematically exact, so a print-scaling difference between the
# parts shifts the slot along its axis instead of jamming. The pins stand on
# the base plate and stay engaged over the whole 3 mm lift.
REG_PIN_D            = 4.00    # pin on the base plate
REG_HOLE_D           = 4.45    # nest hole; ~0.15 mm diametral as printed
REG_SLOT_EXTRA       = 0.80    # secondary hole stretched this much along the
                               # line joining the two, absorbing scale error
REG_PIN_CYL_Z        = 5.00    # cylindrical up to here...
REG_PIN_TOP_Z        = 6.50    # ...then a cone to here, as a lead-in
REG_XY               = [(-45.0, 14.5), (35.0, -14.5)]   # primary first

SPRING_WIRE_D        = 0.60    # 0.6 x 7 mm compression spring from the kit
SPRING_OD            = 7.00
SPRING_ACTIVE_COILS  = 9       # estimate for a 15 mm free length
SPRING_FREE          = 15.00   # free length. This SETS the travel -- see below.
SPRING_POCKET_D      = 7.60
BASE_SPRING_DEPTH    = 7.00    # counterbore in the base
NEST_SPRING_DEPTH    = 5.00    # counterbore in the nest underside. At 3.00 the
                               # pockets summed to 10 against a 15 mm spring and
                               # the rest lift was 5.00, not 3.00.

# Derived: the nest rises until the spring reaches free length. That is the ONLY
# thing setting the rest position, so it is computed, never declared.
TRAVEL               = SPRING_FREE - (BASE_SPRING_DEPTH + NEST_SPRING_DEPTH)
SPRING_SOLID         = (SPRING_ACTIVE_COILS + 2) * SPRING_WIRE_D

# The board's top side is densely populated over the probe cluster, so the
# hold-down lands on five small pads chosen to sit clear of every part and of
# the board edge, with their centroid close to the probe force centroid.
# The first five sit over the dense probe end, found by search. The last four
# are in the bare strip from x=-4 to +15 and exist to bracket the press point
# at x=-7, so the hold-down load lands either side of it instead of all inboard.
COVER_PADS           = [(-28.30, -6.05), (-27.55, -1.30), (-27.30, 6.95),
                        (-14.80,  7.95), (-14.30, -8.05),
                        (  1.00,  7.50), (  1.00, -7.50),
                        (  7.50,  7.50), (  7.50, -7.50)]
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
# STEPPED. A pin on the base plate has to stay in the board at both ends of the
# 3 mm lift, so its tip must reach z=12 while the board drops to z=6 -- as a
# plain Ø2.10 column that is 12 mm of 5.7:1 and it snaps. Fattening everything
# below the seat to Ø3.00 leaves only 6 mm of Ø2.10 standing proud: 2.9:1, and
# about 8x the stiffness at the tip. The alternative, moving the pins onto the
# nest, makes them short but adds the nest's own position to the chain that
# decides where a probe lands -- measured at +0.232 mm worst case, which is
# what takes it over the 0.500 mm pad budget.
# MODELLED to print at 2.10. The board's Ø2.20 hole is routed, not printed, so
# only the pin's growth applies: a modelled 2.10 printed 2.18 and left 0.010 mm
# of radial clearance -- a jam fit on two pins 29.7 mm apart that an operator
# loads by hand many times a day.
LOCATOR_D            = shaft(2.10)
# 2.50, not 3.00. At Ø3.00 in a Ø3.40 hole the shank had 0.050 mm of radial
# clearance as printed -- TIGHTER than the 0.075 mm the registration pins allow
# -- so the pass-through, which locates nothing, took load before the
# registration did and over-constrained the nest.
LOCATOR_SHANK_D      = 2.50
LOCATOR_NEST_HOLE_D  = 3.40    # -> 0.30 mm radial, comfortably the loosest
LOCATOR_TOP_Z        = 12.00   # pin top; board underside is 9.0 at rest, so
                               # this keeps 3 mm engaged with the clamp open
LOCATOR_PRIMARY      = ["MH1", "MH4"]
# No secondary pins. At Ø1.80 in a Ø2.2 hole they carried 0.20 mm of radial
# slop and located nothing, and MH2's seat boss is only Ø4.23 -- a Ø3.40 shank
# clearance would leave a 0.41 mm annulus and destroy the seat. MH2 and MH3
# stay plain bosses; MH1 and MH4 alone fully constrain the board.
LOCATOR_SECONDARY    = []
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
PROBE_WEB_MIN        = 2.00    # webs between adjacent windows narrower than
                               # this are closed out into one stadium

# ------------------------------------------------------------- nest plate ---
NEST_X               = (-58.0, 55.0)
NEST_Y               = ( -19.0, 19.0)
NEST_FILLET          =   3.0

# ------------------------------------------------------------- base plate ---
# The base plate is the precision part: it prints flat on its underside with
# the posts and the pin platform pointing up, so nothing overhangs.
# The plate is the LID of the stand, not an insert in it: it caps the walls and
# carries everything precise plus the clamp tower, so the whole clamp load loop
# closes inside one part and the stand below is a plain open box. That is what
# lets the ST-Link have the entire interior, and what puts the probe tails back
# on an open bench for soldering.
PLATE_Z_BOTTOM       =  -8.0
PLATE_FILLET         =   6.0
MOUNT_SCREW_D        =   3.4   # M3 clearance, plate -> stand
# Four screws, in the two Y strips the ST-Link cavity does not reach. The clamp
# load is internal -- the spindle pushes the cover down, the springs push the
# plate down by the same amount -- so these only stop the lid shifting.
MOUNT_SCREW_XY       = [(-66.0, -51.5), (63.0, -51.5),
                        (-66.0,  21.5), (63.0,  21.5)]
MOUNT_BOSS_R         =   4.5
# The bosses sit in the corners, where a bare cylinder either meets the wall
# tangentially (a zero-degree wedge no nozzle can fill) or misses it entirely.
# The walls and bosses are built as ONE 2D region and morphologically closed by
# this radius, which fillets every reflex corner between them.
STAND_BOSS_FILLET    =   3.0
# The plate comes off to solder the probe tails and to service the ST-Link, so
# this thread gets used repeatedly -- an M3 cutting its own thread in PETG will
# not survive that. Same heat-set insert as the clamp mount.
MOUNT_INSERT_DEPTH   =   8.0   # 4 mm insert at the top, 4 mm of run-out below,
                               # so an M3 x 12 cannot bottom out
# No mounting screws: the deck and the stand are ONE printed part. With the
# ST-Link wired in permanently the two were never going to be separated in
# service, so the four M3s were pure assembly cost.

# ------------------------------------------------------------------ stand ---
# One monolithic part: the open frame under the base plate and the clamp tower
# are the same walls, not a bolt-on bracket.
STAND_Z_BOTTOM       = -50.0   # floor, then the ST-Link cavity, then the wire
                               # space up to the plate underside at -8
STAND_WALL           =   4.0
# The GH-201's spindle sits at its mounting plane and only adjusts DOWNWARD, so
# the deck has to be ABOVE the surface it presses. The cover top is 13.43 mm
# closed and 16.43 mm open; 20 mm puts the spindle 6.6 mm down from its plane,
# mid-range on a 15 mm assembly, and leaves the arm around 27 mm -- clear of
# both the open cover and the 16 mm guide posts.
TOWER_TOP_Z          =  20.0   # clamp mounting deck
TOWER_SOLID_Z        =   8.0   # tower is hollow below this, solid above. 8, not
                               # 10, so an 8 mm insert hole still leaves 4 mm of
                               # solid beneath it
WIRE_EXIT_Z          = (-14.0, -10.5)   # feed for the external 3.3 V supply, on
                                        # the far side from the clamp. The SWD
                                        # loom no longer leaves the body -- it
                                        # goes straight down to the ST-Link.
                                        # The top must stay well below the wall
                                        # top: at -8.5 it left a 0.5 mm lintel
                                        # bridging 20 mm, and that face is the
                                        # lid's seating plane.
WIRE_SLOT_W          =  20.0

# ----------------------------------------------------------------- cover ----
COVER_T              =   4.0   # hold-down cover thickness
COVER_POSTS          = POST_XY                           # cover rides all four
COVER_MARGIN         =   7.0   # 4.0 left only 1.35 mm of wall outside a post
                               # hole; 7.0 leaves 4.1 mm
# ...but not on the -X side. Margin alone put the edge at x=-45.000 against a
# 2.05 mm tall header reaching x=-45.029 -- 0.029 mm, on a cover with 0.25 mm of
# radial play. That header is also on the far side of a flex neck, so its X
# position relative to the locating pins is not controlled at all.
COVER_X_MIN          = -43.5
COVER_TAB_L          =   9.0   # lift-off grip tab
# The dimple is a SHALLOW DISH, not a hemisphere. A Sphere(4.0) centred on the
# top face of a 4.0 mm plate reaches exactly the underside: the cover had
# 0.000 mm of material at the one point the entire 16 N clamp load is applied,
# and the STL was non-manifold there.
COVER_DIMPLE_R       =   4.0   # spherical radius of the dish
COVER_DIMPLE_DEPTH   =   1.2   # how deep it cuts -> 2.8 mm of cover left
# Press on the centroid of the post/spring quad, not on the centroid of the
# contact pads. Off-centre the spring set loads unevenly -- at the old x=-22.45
# it was 75/25 between the two post rows, so the nest levered down instead of
# descending parallel.
COVER_DIMPLE_XY      = (-7.0, 0.0)

# --------------------------------------------------------------- geometry ---
# The stand is one full rectangle, not an L: the board bay and the clamp bay
# share their whole width, and the open compartments either side of the tower
# double as a parts tray.
# Grown from 137 x 83: a 127 mm cavity plus the screw bosses would not fit
# inside the old interior. The plate shares these bounds -- it is the lid.
STAND_X              = (-74.0, 71.0)
STAND_Y              = (-60.0, 31.0)
PLATE_X              = STAND_X
PLATE_Y              = STAND_Y
# The clamp tower rides on the PLATE now, not the stand: on the stand its walls
# ran down through the middle of the interior and cut the ST-Link cavity in two.
PEDESTAL_X           = (-26.0,  12.0)
PEDESTAL_Y           = (-56.0, -20.0)   # +Y face 1 mm off the nest, so the near
                                        # insert row keeps 2.5 mm of wall
                                        # instead of 1.60
# Ribs must miss the loom run: the probe cluster is at x -32..-17 and the exit
# at x +/-10, so a rib at x -4 sat right in the path.

# ---------------------------------------------------------------- ST-Link ---
# Genuine ST-LINK/V2, wired in permanently. It drops into the stand from above
# before the plate goes on, so there is no slide-in opening to arrange -- only a
# hole in the +X wall for the USB cable.
#
# 100 x 50 x 30 is the case as measured, with your own buffer already in it.
# HEADER_ROOM and USB_ROOM are added on top of that for the 20-pin ribbon and
# the USB plug with its strain relief; trim them once you can see the real
# cable bends. Everything about the cavity comes from these five numbers.
STLINK_CASE          = (100.0, 50.0, 30.0)   # L x W x H  <-- MEASURE THIS
STLINK_HEADER_ROOM   =  15.0   # -X end, for the 20-pin ribbon
STLINK_USB_ROOM      =  12.0   # +X end, for the plug and its boot
STLINK_CLEAR         =   1.0   # all round the case itself
STLINK_TOP_Z         = -16.0   # cavity ceiling: 2.35 mm under the probe tails
STLINK_Y_CENTRE      = -20.0   # keeps both Y strips free for the screw bosses
STLINK_X_CENTRE      =  -1.5
STLINK_FLOOR_T       =   2.0
STLINK_RIB_H         =   2.5   # locating ribs on the floor, at the case corners
STLINK_USB_W         =  16.0   # hole in the +X wall for the cable and its boot
STLINK_USB_H         =  14.0

# -------------------------------------------------------- clamp interface ---
# GH-201 horizontal toggle clamp: 75 x 25 x 17 mm, mounting holes on a
# 15.9 x 11.1 mm pattern, spindle pressing DOWN from its mounting plane.
CLAMP_BASE_W         =  25.0   # body width, checked against the deck
CLAMP_BASE_L         =  75.0   # body length, along Y
# The clamp is 75 mm long on a 35 mm deck, so it WILL overhang the back of the
# jig. These say by how much, so the check can be about the mounting rows being
# properly supported rather than pretending the whole body sits on the deck.
CLAMP_SPINDLE_TO_END =  19.6   # spindle to the near end of the base  <-- MEASURE
CLAMP_SCREW_L        =  12.0   # M3 x 12 into the deck inserts
CLAMP_BASE_T         =   5.0   # thickness of the clamp's own base  <-- MEASURE
CLAMP_HOLE_DX        =  15.9   # <-- measure yours; these are off the drawing
CLAMP_HOLE_DY        =  11.1

# It bolts into M3 heat-set inserts, not nuts in a channel. Kadrick M3 measure
# 4.5 mm across the knurl and 3.9 mm at the tip, so a 4.0 mm blind hole -- the
# usual "between the two diameters" rule. Load is about 4 N per bolt, so the
# shortest plentiful insert in the kit is far more than enough.
INSERT_M3_H          =   4.0   # insert length
INSERT_M3_TIP_D      =   3.9   # the insert's own geometry, so checks can use it
INSERT_M3_KNURL_D    =   4.5
# MODELLED so it PRINTS between the tip and the knurl. A modelled 4.00 printed
# 3.78 -- under the Ø3.90 tip -- so the insert could not start square.
INSERT_M3_HOLE_D     = bore(4.00)
# 8 mm, not 5: an M3 x 12 stands 7 mm proud of the clamp base and bottomed out
# in a 5 mm hole before the head ever clamped.
INSERT_M3_HOLE_DEPTH =   8.0

# Fixed inserts give up the fore-and-aft trim the slots allowed, so the mount
# position has to be right first time. MEASURE THIS on your clamp: spindle axis
# to the nearer of the two mounting-hole rows. 24.6 mm is read off the drawing
# (19.6 mm spindle-to-plate plus about 5 mm plate-edge-to-hole), not measured.
CLAMP_SPINDLE_TO_ROW =  24.6

# ------------------------------------------------------------ printing -----
