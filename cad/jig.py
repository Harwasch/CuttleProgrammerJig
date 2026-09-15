"""Cuttle CANServo_Driver pogo programming jig.

Three printed parts:
  body        deck and stand fused: 7 probe bores, 4 guide posts, 2 stepped
              board locators, 2 registration pins, the clamp tower, the wire
              bay and the ST-Link bay beneath it
  nest        floating board carrier, rides the posts on springs
  cover       hold-down that presses only on bare board, guided by all four
              posts and pressed on the centre of the post/spring quad

plus fit_gauge, a calibration coupon that is printed once and thrown away.

Run:  python3 jig.py            -> writes STEP + STL into cad/out/
"""
import os
from build123d import *
from shapely.geometry import LineString, Point, box as shbox
from shapely.ops import unary_union

import params as P
import geom as G

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
if P.PIN_FAMILY != "P50":
    OUT = os.path.join(OUT, P.PIN_FAMILY.lower())


def rrect(xr, yr, r, z=0.0):
    """A filleted rectangle face at height z."""
    w, h = xr[1] - xr[0], yr[1] - yr[0]
    f = Plane.XY.offset(z) * Rectangle(w, h)
    f = Pos((xr[0] + xr[1]) / 2, (yr[0] + yr[1]) / 2) * f
    return fillet(f.vertices(), r) if r > 0 else f


# --------------------------------------------------------------- base plate --
def build_base_plate():
    z0 = P.PLATE_Z_BOTTOM
    part = extrude(rrect(P.PLATE_X, P.PLATE_Y, P.PLATE_FILLET, z0), amount=-z0)

    # The probe seat. Where it lands relative to the hard-stop plateau is set by
    # the pin family, not by choice: seat = NEST_T + COMPRESSION - PROTRUSION.
    # A P50 stands 3.35 mm out of its receptacle and wants the seat 3.85 mm UP,
    # so the plate grows a platform. A P100 stands 8.35 mm out and wants it
    # 0.75 mm DOWN, so the plate gets a relief instead and the plateau stays
    # whole -- which also means no bottom-side part can reach it, and none of
    # the relief cutting below is needed.
    if P.Z_PIN_TOP > 0:
        platform = extrude(G.sk(G.probe_islands()), amount=P.Z_PIN_TOP)
        for fp, zfloor in G.bottom_part_sweep():
            cut = fp
            if zfloor + P.PART_CLEAR_Z >= P.Z_PIN_TOP:
                # This part's underside clears the platform top, so it passes
                # over the islands and they can keep their full collar. Cutting
                # them anyway left 0.15 mm of wall on two bores and breached a
                # third.
                cut = fp.difference(G.probe_islands())
            if cut.is_empty:
                continue
            platform -= extrude(G.sk(cut, Plane.XY.offset(zfloor)),
                                amount=P.Z_PIN_TOP + 1)
        part += platform

    # guide posts, rising from the floor of their own spring pockets
    for x, y in P.POST_XY:
        part -= Pos(x, y, -P.BASE_SPRING_DEPTH) * extrude(
            Circle(P.SPRING_POCKET_D / 2), amount=P.BASE_SPRING_DEPTH)
        post = Pos(x, y, -P.BASE_SPRING_DEPTH) * extrude(
            Circle(P.POST_D / 2), amount=P.POST_TOP_Z + P.BASE_SPRING_DEPTH)
        part += post

    # Probe bores, printed to final size. A short lead-in, then a long bore --
    # 9 mm of engagement on a 17.5 mm sleeve, so tilt contributes almost
    # nothing to where the tip lands -- then loose clearance to the underside.
    for tp in G.TEST_POINTS:
        p = Pos(tp["x"], tp["y"])
        top = P.Z_PIN_TOP
        # mouth chamfer, then a counterbore exactly one head deep, then a bore
        # sized for the BODY. The head cannot enter the body bore, so it bottoms
        # flush with the platform instead of stopping wherever you stopped
        # pushing.
        if top < 0:
            # Seat below the plateau: sink a relief from the plateau down to
            # it, wide enough to pass the head so the receptacle can still be
            # pulled out upwards.
            part -= p * Pos(0, 0, top) * extrude(
                Circle(P.bore(P.PIN_RELIEF_D) / 2), amount=-top)
        part -= p * Pos(0, 0, top) * extrude(
            Circle(P.PIN_BORE_D / 2 + P.PIN_MOUTH_CHAMFER),
            amount=-P.PIN_MOUTH_CHAMFER, taper=45)
        part -= p * Pos(0, 0, top - P.PIN_HEAD_BORE_L) * extrude(
            Circle(P.PIN_BORE_D / 2), amount=P.PIN_HEAD_BORE_L + 0.01)
        body_top = top - P.PIN_HEAD_BORE_L
        part -= p * Pos(0, 0, body_top - P.PIN_BORE_L) * extrude(
            Circle(P.PIN_BODY_BORE_D / 2), amount=P.PIN_BORE_L)
        clr_top = body_top - P.PIN_BORE_L
        part -= p * Pos(0, 0, z0 - 0.1) * extrude(
            Circle(P.PIN_CLEAR_D / 2), amount=clr_top - z0 + 0.1)

    # Nest registration. The four guide posts are deliberately loose now -- four
    # posts in four holes is over-constrained and binds on any print-scaling
    # difference -- so the nest is located by exactly two features instead: a
    # round pin at the primary and the same pin in a slot at the secondary.
    # That is kinematically exact, so scale error slides the slot along its own
    # axis rather than jamming the pair. Ø4 x 6.5 mm is 1.6:1, not the 5.7:1 of
    # the board locators that used to stand here.
    for x, y in P.REG_XY:
        part += Pos(x, y) * extrude(Circle(P.REG_PIN_D / 2), amount=P.REG_PIN_CYL_Z)
        part += Pos(x, y, P.REG_PIN_CYL_Z) * extrude(
            Circle(P.REG_PIN_D / 2),
            amount=P.REG_PIN_TOP_Z - P.REG_PIN_CYL_Z, taper=30)

    # Board locators, stepped. Everything below the seat -- which the board can
    # never reach, because the nest bottoms there -- is Ø3.00, so only the last
    # 6 mm stands as Ø2.10. See LOCATOR_SHANK_D for why that matters.
    for name in P.LOCATOR_PRIMARY:
        x, y = G.HOLES[name]
        part += Pos(x, y) * extrude(Circle(P.LOCATOR_SHANK_D / 2), amount=P.NEST_T)
        part += Pos(x, y, P.NEST_T) * extrude(
            Circle(P.LOCATOR_D / 2), amount=P.LOCATOR_TOP_Z - P.NEST_T - 0.6)
        part += Pos(x, y, P.LOCATOR_TOP_Z - 0.6) * extrude(
            Circle(P.LOCATOR_D / 2), amount=0.6, taper=30)

    # Clamp tower. It belongs to the plate rather than the stand so the whole
    # clamp loop -- spindle, cover, board, nest, springs, plate, tower -- closes
    # inside one part, and so its walls stop running down through the middle of
    # the stand's interior, which is the ST-Link's now. Hollow below
    # TOWER_SOLID_Z with a cross rib, so the cavity roof bridges about 13 mm.
    tx, ty = P.PEDESTAL_X, P.PEDESTAL_Y
    W = P.STAND_WALL
    part += extrude(rrect(tx, ty, P.PLATE_FILLET, z0), amount=P.TOWER_TOP_Z - z0)
    part -= extrude(rrect((tx[0] + W, tx[1] - W), (ty[0] + W, ty[1] - W), 2.0, z0),
                    amount=P.TOWER_SOLID_Z - z0)
    tcx, tcy = (tx[0] + tx[1]) / 2, (ty[0] + ty[1]) / 2
    part += Pos(tcx, tcy, (z0 + P.TOWER_SOLID_Z) / 2) * \
        Box(W, ty[1] - ty[0] - 2 * W, P.TOWER_SOLID_Z - z0)
    part += Pos(tcx, tcy, (z0 + P.TOWER_SOLID_Z) / 2) * \
        Box(tx[1] - tx[0] - 2 * W, W, P.TOWER_SOLID_Z - z0)
    for x, y in clamp_insert_xy():
        part -= Pos(x, y, P.TOWER_TOP_Z - P.INSERT_M3_HOLE_DEPTH) * extrude(
            Circle(P.INSERT_M3_HOLE_D / 2), amount=P.INSERT_M3_HOLE_DEPTH + 0.1)

    # lid screws, counterbored so the heads sit below the plateau
    for x, y in P.MOUNT_SCREW_XY:
        part -= Pos(x, y, z0 - 0.1) * extrude(
            Circle(P.MOUNT_SCREW_D / 2), amount=-z0 + 0.2)
        part -= Pos(x, y, -3.0) * extrude(Circle(3.2), amount=3.1)

    return part


# -------------------------------------------------------------------- nest --
def build_nest():
    """Floating board carrier.

    The board sits on six chunky bosses at its own mounting holes plus the
    three sections that carry no bottom-side parts at all (the SWD tab and both
    flex necks). Everything else drops away in ONE pocket, so there are no ribs
    threaded between components and nothing thin to print. A boss under the MCU
    stops just short of the package: it backs up the board against probe force
    without lifting it off its seat.

    The board's locating pins stand on the base plate and pass through this
    part, so the board registers straight to the part that holds the probes.
    The nest is itself registered to the base by two dedicated pins rather than
    by the springs' guide posts, which are now deliberately loose.
    """
    top = P.NEST_T + P.NEST_LIP
    part = extrude(rrect(P.NEST_X, P.NEST_Y, P.NEST_FILLET), amount=top)

    # drop-in board recess, then the single component pocket
    part -= extrude(G.sk(G.board_recess(), Plane.XY.offset(P.NEST_T)), amount=P.NEST_LIP)
    floor = P.NEST_T - P.NEST_RECESS
    part -= extrude(G.sk(G.nest_recess(), Plane.XY.offset(floor)), amount=P.NEST_RECESS)

    # backing boss under the MCU, held clear of the package by MCU_BOSS_CLEAR
    mx, my, ms, mh = P.MCU_BOSS
    part += Pos(mx, my, floor) * extrude(
        Rectangle(ms, ms), amount=P.NEST_RECESS - mh - P.MCU_BOSS_CLEAR)

    # clearance for the base's probe islands, full depth
    part -= extrude(G.sk(G.probe_clear(), Plane.XY.offset(-0.1)), amount=top + 0.2)

    for x, y in P.POST_XY:
        part -= Pos(x, y, -0.1) * extrude(Circle(P.POST_HOLE_D / 2), amount=top + 0.2)
        part -= Pos(x, y) * extrude(Circle(P.SPRING_POCKET_D / 2),
                                    amount=P.NEST_SPRING_DEPTH)

    # Registration to the base plate: a round hole at the primary pin, and the
    # same hole stretched into a slot along the line joining the two at the
    # secondary. Both sit outboard of the board outline in Y, so they never
    # break into the board recess.
    (x0, y0), (x1, y1) = P.REG_XY
    part -= Pos(x0, y0, -0.1) * extrude(Circle(P.REG_HOLE_D / 2), amount=top + 0.2)
    ux, uy = x1 - x0, y1 - y0
    n = (ux * ux + uy * uy) ** 0.5
    ux, uy = ux / n * P.REG_SLOT_EXTRA / 2, uy / n * P.REG_SLOT_EXTRA / 2
    slot = LineString([(x1 - ux, y1 - uy), (x1 + ux, y1 + uy)]).buffer(
        P.REG_HOLE_D / 2, G.ARC_SEGS)
    part -= extrude(G.sk(slot, Plane.XY.offset(-0.1)), amount=top + 0.2)

    # Pass-through for the base plate's stepped board locators. One straight
    # hole clears the Ø3.00 shank low down and the Ø2.10 tip higher up.
    for name in P.LOCATOR_PRIMARY:
        x, y = G.HOLES[name]
        part -= Pos(x, y, -0.1) * extrude(
            Circle(P.LOCATOR_NEST_HOLE_D / 2), amount=top + 0.2)
    return part


# ------------------------------------------------------------------- cover --
def build_cover():
    xs = [x for x, _ in P.COVER_POSTS] + [p[0] for p in P.COVER_PADS]
    ys = [y for _, y in P.COVER_POSTS] + [p[1] for p in P.COVER_PADS]
    xr = (max(min(xs) - P.COVER_MARGIN, P.COVER_X_MIN), max(xs) + P.COVER_MARGIN)
    yr = (min(ys) - P.COVER_MARGIN, max(ys) + P.COVER_MARGIN)

    pads = unary_union([Point(x, y).buffer(P.COVER_PAD_R, G.ARC_SEGS) for x, y in P.COVER_PADS])
    body = extrude(rrect(xr, yr, 3.0, P.COVER_PAD_H), amount=P.COVER_T)
    part = body + extrude(G.sk(pads), amount=P.COVER_PAD_H)

    # grip tab on the +Y side -- away from the clamp, and clear of the 7 mm
    # SWD header that sits on the left tab of the board
    tab = Pos((xr[0] + xr[1]) / 2, yr[1] + P.COVER_TAB_L / 2 - 1,
              P.COVER_PAD_H + P.COVER_T / 2) * Box(16.0, P.COVER_TAB_L + 2, P.COVER_T)
    part += tab

    # Dimple on the centroid of the post/spring quad: where the clamp spindle
    # lands. Pressing on the pad centroid instead put the load 15.45 mm off
    # centre and split the spring set 75/25, so the nest levered down.
    cxp, cyp = P.COVER_DIMPLE_XY
    top = P.COVER_PAD_H + P.COVER_T
    # raised so the sphere cuts only COVER_DIMPLE_DEPTH: centred ON the top face
    # a Sphere(COVER_DIMPLE_R) reached the underside and left zero material
    part -= Pos(cxp, cyp, top + P.COVER_DIMPLE_R - P.COVER_DIMPLE_DEPTH) * \
        Sphere(P.COVER_DIMPLE_R)

    # Guide holes, chamfered both ends: only 5.8 mm of cover rides the posts
    # against 24 mm of reach to the far pad, so it needs a lead-in to drop on
    # cleanly rather than catching.
    h = P.COVER_PAD_H + P.COVER_T
    for x, y in P.COVER_POSTS:
        part -= Pos(x, y, -0.1) * extrude(Circle(P.POST_HOLE_D / 2), amount=h + 0.2)
        c = P.COVER_LEADIN
        part -= Pos(x, y, -0.01) * extrude(
            Circle(P.POST_HOLE_D / 2 + c), amount=c, taper=45)
        part -= Pos(x, y, h + 0.01) * extrude(
            Circle(P.POST_HOLE_D / 2 + c), amount=-c, taper=45)
    # clearance for any nest locator pin that falls under the cover
    for name in P.LOCATOR_PRIMARY + P.LOCATOR_SECONDARY:
        x, y = G.HOLES[name]
        if xr[0] < x < xr[1] and yr[0] < y < yr[1]:
            part -= Pos(x, y, -0.1) * extrude(Circle(P.LOCATOR_D / 2 + 1.0),
                                              amount=P.COVER_PAD_H + P.COVER_T + 0.2)
    return part




def clamp_insert_xy():
    """The four M3 insert positions on the clamp deck.

    Derived from where the spindle has to land -- the dimple at the centroid of
    the cover's contact pads -- worked back through the clamp's own geometry,
    rather than simply centred on the deck.
    """
    dimple_x, dimple_y = P.COVER_DIMPLE_XY
    near = dimple_y - P.CLAMP_SPINDLE_TO_ROW
    cx = dimple_x
    return [(cx + sx * P.CLAMP_HOLE_DX / 2, near - sy * P.CLAMP_HOLE_DY)
            for sx in (-1, 1) for sy in (0, 1)]


# ------------------------------------------------------------------- stand --
def _shrect(xr, yr, r):
    """shapely rounded rectangle."""
    return shbox(xr[0] + r, yr[0] + r, xr[1] - r, yr[1] - r).buffer(r, G.ARC_SEGS)


def stand_profile(closed=True):
    """The stand's cross-section: wall ring plus the four lid bosses.

    Built as ONE 2D region and morphologically closed. As bare cylinders the
    corner bosses either met the wall tangentially -- a wedge closing to zero
    degrees, which no nozzle can fill -- or stood 1 mm clear of it as free
    pillars with a slot behind. Dilating then eroding by STAND_BOSS_FILLET
    fillets every reflex corner between them instead.

    `closed=False` returns the raw union, for tests that need to show the
    closing is doing something.
    """
    W = P.STAND_WALL
    outer2 = _shrect(P.STAND_X, P.STAND_Y, 6.0)
    inner2 = _shrect((P.STAND_X[0] + W, P.STAND_X[1] - W),
                     (P.STAND_Y[0] + W, P.STAND_Y[1] - W), max(6.0 - W, 1.0))
    region = outer2.difference(inner2).union(unary_union(
        [Point(x, y).buffer(P.MOUNT_BOSS_R, G.ARC_SEGS) for x, y in P.MOUNT_SCREW_XY]))
    if closed:
        f = P.STAND_BOSS_FILLET
        region = region.buffer(f, G.ARC_SEGS).buffer(-f, G.ARC_SEGS)
    return region, outer2


def build_stand():
    """A plain open box. Everything precise, and the clamp tower, is on the plate.

    The stand used to carry the tower and an internal bay wall, which between
    them cut the interior into pieces too small for the ST-Link. It is now four
    walls, a floor and four screw bosses, and the whole 137 x 83 x 40 mm
    interior is one clear volume.
    """
    z0, z1 = P.STAND_Z_BOTTOM, P.PLATE_Z_BOTTOM
    W = P.STAND_WALL

    region, outer2 = stand_profile()
    part = extrude(G.sk(region, Plane.XY.offset(z0)), amount=z1 - z0)
    part += extrude(G.sk(outer2, Plane.XY.offset(z0)), amount=P.STLINK_FLOOR_T)

    # blind holes for M3 heat-set inserts -- the same part as the clamp mount
    for x, y in P.MOUNT_SCREW_XY:
        part -= Pos(x, y, z1 - P.MOUNT_INSERT_DEPTH) * extrude(
            Circle(P.INSERT_M3_HOLE_D / 2), amount=P.MOUNT_INSERT_DEPTH + 0.1)

    # Locating ribs at the corners of the ST-Link footprint. The case drops in
    # from above before the lid goes on, so it needs nothing more than this to
    # stop it sliding around.
    L, Wd, H = P.STLINK_CASE
    cl = L + P.STLINK_HEADER_ROOM + P.STLINK_USB_ROOM
    cw = Wd + 2 * P.STLINK_CLEAR
    fz = z0 + P.STLINK_FLOOR_T
    # Sized from the CASE. Taking cl (the cavity length, 127) put the ribs
    # 127 mm apart around a 100 mm case -- 27 mm of slop in X, so they located
    # nothing. The header and USB rooms are clearance at the ends, not case.
    case_x = P.STLINK_X_CENTRE - cl / 2 + P.STLINK_HEADER_ROOM + L / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = case_x + sx * (L + 2 * P.STLINK_CLEAR) / 2
            cy = P.STLINK_Y_CENTRE + sy * cw / 2
            rz = fz + P.STLINK_RIB_H / 2          # Box centres on its Pos
            # Each leg runs INWARD from the corner. Centred on it, the 14 mm
            # Y leg stuck 7 mm past the cavity and straight out through the
            # -Y wall as soon as the P100 moved the case up against it.
            part += Pos(cx + sx * 1.5, cy - sy * 7.0, rz) * \
                Box(3.0, 14.0, P.STLINK_RIB_H)
            part += Pos(cx - sx * 7.0, cy + sy * 1.5, rz) * \
                Box(14.0, 3.0, P.STLINK_RIB_H)

    # USB cable, out through the +X wall at the case's own height
    ch = H + 2 * P.STLINK_CLEAR
    part -= Pos(P.STAND_X[1], P.STLINK_Y_CENTRE, P.STLINK_TOP_Z - ch / 2) * \
        Box(4 * W, P.STLINK_USB_W, P.STLINK_USB_H)

    # feed for the external 3.3 V supply, on the far side from the clamp
    zc = (P.WIRE_EXIT_Z[0] + P.WIRE_EXIT_Z[1]) / 2
    zh = P.WIRE_EXIT_Z[1] - P.WIRE_EXIT_Z[0]
    part -= Pos(0, P.STAND_Y[1], zc) * Box(P.WIRE_SLOT_W, 4 * W, zh)
    return part


def build_fit_gauge():
    """Calibration coupon: one row of bores stepping through GAUGE_BORES.

    Print it in the material and profile you will use for the base plate, find
    the hole an R50 sleeve just pushes into, and put that number in
    PIN_BORE_D. That replaces drilling the plate afterwards.
    """
    n = len(P.GAUGE_BORES)
    # The coupon must reproduce the feature it calibrates: a BLIND counterbore
    # exactly one head deep, with the same mouth chamfer. It used to be an
    # 11 mm through hole for a 9 mm application -- a deeper hole tapers more and
    # reads tighter, biasing the one measurement the whole design hangs on.
    pitch, t = 9.0, P.PIN_HEAD_BORE_L + 2.5   # pitch fits a 3-digit label
    w, d = n * pitch + 5.0, 14.0
    part = extrude(rrect((-w / 2, w / 2), (-d / 2, d / 2), 2.0), amount=t)
    for i, dia in enumerate(P.GAUGE_BORES):
        x = (i - (n - 1) / 2) * pitch
        part -= Pos(x, 3.0, t) * extrude(
            Circle(dia / 2 + P.PIN_MOUTH_CHAMFER),
            amount=-P.PIN_MOUTH_CHAMFER, taper=45)
        part -= Pos(x, 3.0, t - P.PIN_HEAD_BORE_L) * extrude(
            Circle(dia / 2), amount=P.PIN_HEAD_BORE_L + 0.01)
        # label in hundredths of a mm, matching GAUGE_BORES
        part -= Pos(x, -4.0, t - 0.6) * extrude(
            Text(f"{round(dia * 100)}", font_size=4.0,
                 align=(Align.CENTER, Align.CENTER)), amount=0.7)
    return part


# ------------------------------------------- hardware, for renders only -----
def build_probes():
    """The seven receptacles and the probe tips standing in them. Not a printed
    part -- it exists so the renders show where the solder joints actually are."""
    out = None
    for tp in G.TEST_POINTS:
        p = Pos(tp["x"], tp["y"])
        sleeve = p * Pos(0, 0, P.Z_PIN_TOP - P.RECEPT_LEN) * extrude(
            Circle(P.RECEPT_BODY_D / 2), amount=P.RECEPT_LEN)
        r = P.RECEPT_BODY_D / 3.4
        shaft = p * Pos(0, 0, P.Z_PIN_TOP) * extrude(
            Circle(r), amount=P.PIN_PROTRUSION - 0.55)
        tip = p * Pos(0, 0, P.Z_PIN_TOP + P.PIN_PROTRUSION - 0.55) * extrude(
            Circle(r), amount=0.55, taper=45)
        out = sleeve + shaft + tip if out is None else out + sleeve + shaft + tip
    return out


def build_shrink_gauge():
    """Plain through holes at four diameters, to calibrate hole shrink where
    the design's larger features live.

    The fit gauge answers one question -- what bore takes this sleeve -- and it
    answers it at ONE diameter. That was fine until the P100 gauge read 2.00
    where the P50 gauge read 1.20 on a sleeve only 0.92 mm bigger: shrink is a
    function of diameter, not a constant, and the Ø4 to Ø12 holes in this
    design have never been measured at all. Print this, run the caliper's
    inside jaws down each hole, and shrink at that diameter is the modelled
    number engraved beside it minus what you read.
    """
    gap, margin, wall = 5.0, 5.0, 4.0
    xs, x = [], margin
    for d in P.GAUGE_PLAIN_BORES:
        x += d / 2
        xs.append(x)
        x += d / 2 + gap
    w = x - gap + margin
    big = max(P.GAUGE_PLAIN_BORES)
    hy, ly = big / 2 + wall, -6.0
    h = hy + big / 2 + wall + 12.0
    part = extrude(rrect((0, w), (ly - 6.0, ly - 6.0 + h), 2.0), amount=5.0)
    for x, d in zip(xs, P.GAUGE_PLAIN_BORES):
        part -= Pos(x, hy, -0.1) * extrude(Circle(d / 2), amount=5.2)
        part -= Pos(x, ly, 5.0) * extrude(
            Text(f"{d:g}", font_size=4.0, align=(Align.CENTER, Align.CENTER)),
            amount=-0.6)
    return part


PARTS_TO_BUILD = {
    "base_plate": build_base_plate,
    "shrink_gauge": build_shrink_gauge,
    "stand": build_stand,
    "nest": build_nest,
    "cover": build_cover,
    "fit_gauge": build_fit_gauge,
}


def assembly(open_position=False):
    """Every part plus the board, positioned as they sit in use."""
    dz = P.TRAVEL if open_position else 0.0
    seat = P.NEST_T + dz
    a = {
        "base_plate": build_base_plate(),
        "stand": build_stand(),
        "nest": Pos(0, 0, dz) * build_nest(),
        "cover": Pos(0, 0, seat + P.PCB_T) * build_cover(),
        "pcb": G.pcba_solid(seat),
    }
    return a


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in PARTS_TO_BUILD.items():
        s = fn()
        bb = s.bounding_box()
        print(f"{name:12s} vol {s.volume:9.1f} mm3   bbox "
              f"{bb.size.X:7.2f} x {bb.size.Y:6.2f} x {bb.size.Z:6.2f}")
        export_step(s, os.path.join(OUT, f"{name}.step"))
        export_stl(s, os.path.join(OUT, f"{name}.stl"))
    export_step(build_probes(), os.path.join(OUT, "probes_hw.step"))
    export_stl(build_probes(), os.path.join(OUT, "probes_hw.stl"))
    print("probes_hw     (render aid, not a printed part)")
    asm = assembly()
    comp = Compound(children=[Part(s.wrapped, label=k) for k, s in asm.items()])
    export_step(comp, os.path.join(OUT, "assembly_closed.step"))
    print(f"\nwrote STEP + STL for {len(PARTS_TO_BUILD)} parts and the assembly into {OUT}")
