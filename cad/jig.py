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
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

import params as P
import geom as G

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


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

    # raised probe platform, then cut it back under every bottom-side part
    platform = extrude(G.sk(G.probe_islands()), amount=P.Z_PIN_TOP)
    for fp, zfloor in G.bottom_part_sweep():
        platform -= extrude(G.sk(fp, Plane.XY.offset(zfloor)), amount=P.Z_PIN_TOP + 1)
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
        part -= p * Pos(0, 0, top - P.PIN_LEAD_L) * extrude(
            Circle(P.PIN_LEAD_D / 2), amount=P.PIN_LEAD_L + 0.1)
        bore_top = top - P.PIN_LEAD_L
        part -= p * Pos(0, 0, bore_top - P.PIN_BORE_L) * extrude(
            Circle(P.PIN_BORE_D / 2), amount=P.PIN_BORE_L)
        clr_top = bore_top - P.PIN_BORE_L
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
    xr = (min(xs) - P.COVER_MARGIN, max(xs) + P.COVER_MARGIN)
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
    part -= Pos(cxp, cyp, top) * Sphere(P.COVER_DIMPLE_R)

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
def build_stand():
    """One monolithic part, one full rectangular footprint.

    FDM notes: every feature here is a vertical wall or a vertical hole. The
    shell is open top and bottom, so there is no roof to bridge; the base plate
    lands on a bay wall that runs all the way to the bench rather than on
    cantilevered bosses; the clamp tower is solid up to a shallow nut channel;
    and the loom slot is split by a post so its top edge spans 8 mm, not 20.

    The clamp bolts into M3 heat-set inserts in the deck.
    """
    z0, z1 = P.STAND_Z_BOTTOM, P.PLATE_Z_BOTTOM
    W = P.STAND_WALL
    h = z1 - z0

    def shell(xr, yr, fil, height, top=None):
        """Outer prism minus its own interior -- walls only, open top and bottom."""
        outer = extrude(rrect(xr, yr, fil, z0), amount=height)
        inner = extrude(rrect((xr[0] + W, xr[1] - W), (yr[0] + W, yr[1] - W),
                              max(fil - W, 1.0), z0 - 0.1), amount=height + 0.2)
        return outer - inner

    # outer shell, and the bay whose wall top carries the base plate
    part = shell(P.STAND_X, P.STAND_Y, 6.0, h)
    part += shell(P.PLATE_X, P.PLATE_Y, P.PLATE_FILLET, h)

    # ribs tying the bay to the outer shell, inset so nothing overhangs the
    # filleted corners, and placed clear of the probe cluster (x -32 to -17)
    # ...but only in the gap between the bay wall and the outer wall: the bay
    # interior is the ST-Link's now, and a rib through it would cut the case in
    # half. The -Y gap is 31 mm, the +Y gap only 2 mm.
    for x in P.RIB_X:
        for ya, yb in ((P.STAND_Y[0] + W, P.PLATE_Y[0]), (P.PLATE_Y[1], P.STAND_Y[1] - W)):
            if yb - ya > 0.5:
                part += Pos(x, (ya + yb) / 2, z0 + h / 2) * Box(W, yb - ya, h)
    rx0, rx1 = P.STAND_X[0] + W, P.STAND_X[1] - W
    for y in (P.PLATE_Y[0], P.PLATE_Y[1]):
        part += Pos((rx0 + rx1) / 2, y, z0 + h / 2) * Box(rx1 - rx0, W, h)

    # Clamp tower, sharing the shell's walls. Solid only in the top band that
    # carries the nut channels and the deck; hollow below, divided by a cross
    # rib so the cavity roof bridges about 13 mm rather than 30.
    part += extrude(rrect(P.PEDESTAL_X, P.PEDESTAL_Y, P.PLATE_FILLET, z0),
                    amount=P.TOWER_TOP_Z - z0)
    tx, ty = P.PEDESTAL_X, P.PEDESTAL_Y
    part -= extrude(rrect((tx[0] + W, tx[1] - W), (ty[0] + W, ty[1] - W), 2.0, z0 - 0.1),
                    amount=P.TOWER_SOLID_Z - z0 + 0.1)
    tcx, tcy = (tx[0] + tx[1]) / 2, (ty[0] + ty[1]) / 2
    part += Pos(tcx, tcy, (z0 + P.TOWER_SOLID_Z) / 2) * \
        Box(W, ty[1] - ty[0] - 2 * W, P.TOWER_SOLID_Z - z0)
    part += Pos(tcx, tcy, (z0 + P.TOWER_SOLID_Z) / 2) * \
        Box(tx[1] - tx[0] - 2 * W, W, P.TOWER_SOLID_Z - z0)

    # Deck support. Printed as one part the deck has to bridge the bay, so the
    # bay walls corbel inward over the last 6 mm -- a 45 degree underside, which
    # needs no support -- taking the span from 34 mm to 22 mm. The probe tails
    # reach y=+/-8.8, so 22 mm still clears them by 2.2 mm a side.
    cz0, cz1 = P.WIRE_BAY_Z, z1
    inx = (P.PLATE_X[0] + W, P.PLATE_X[1] - W)
    y_lo, y_hi = P.PLATE_Y[1] - W, P.PLATE_Y[1] - W - P.DECK_CORBEL
    band = extrude(rrect(P.PLATE_X, P.PLATE_Y, P.PLATE_FILLET, cz0), amount=cz1 - cz0)
    void = Pos((inx[0] + inx[1]) / 2, 0) * loft([
        Plane.XY.offset(cz0) * Rectangle(inx[1] - inx[0], 2 * y_lo),
        Plane.XY.offset(cz1) * Rectangle(inx[1] - inx[0], 2 * y_hi)])
    part += band - void

    # ST-Link floor, and the slide-in opening at the +X end. The case is
    # captured sideways by the bay walls and from above by the corbel, which is
    # narrower than the case is wide, so it cannot lift out.
    part += extrude(rrect(P.PLATE_X, P.PLATE_Y, P.PLATE_FILLET, z0),
                    amount=P.STLINK_FLOOR_T)
    sl, sw, sh = P.STLINK_BODY
    c = P.STLINK_CLEAR
    part -= Pos((P.STLINK_X0 + sl) / 2 + 40.0, 0, P.STLINK_BAY_Z + (sh + c) / 2) * \
        Box(sl + 80.0, sw + 2 * c, sh + c)

    # loom exit -- now only the external 3.3 V feed; the SWD loom stays inside.
    # It has to cut through the corbel as well as both walls.
    zc = (P.WIRE_EXIT_Z[0] + P.WIRE_EXIT_Z[1]) / 2
    zh = P.WIRE_EXIT_Z[1] - P.WIRE_EXIT_Z[0]
    ya, yb = y_hi - 1.0, P.STAND_Y[1] + 1.0
    part -= Pos(0, (ya + yb) / 2, zc) * Box(P.WIRE_SLOT_W, yb - ya, zh)
    for sy in (P.PLATE_Y[1] - W / 2, P.STAND_Y[1] - W / 2):
        part += Pos(0, sy, zc) * Box(P.TIE_BAR_W, W, zh)
    return part


def build_body():
    """Deck and stand as ONE printed part.

    They were two, bolted together with four M3. With the ST-Link wired in
    permanently they are never separated in service, so the screws bought
    nothing. The cost is that the deck underside is now a bridge -- see the
    corbel in build_stand -- and that recalibrating PIN_BORE_D means reprinting
    the whole body, so confirm the bore with the fit gauge FIRST.
    """
    part = build_base_plate() + build_stand()

    # Clamp mounting: four blind holes for M3 heat-set inserts, placed so the
    # spindle lands on the cover's dimple. Fixed inserts give up the trim the
    # slots allowed, so CLAMP_SPINDLE_TO_ROW has to be measured, not assumed.
    for x, y in clamp_insert_xy():
        part -= Pos(x, y, P.TOWER_TOP_Z - P.INSERT_M3_HOLE_DEPTH) * extrude(
            Circle(P.INSERT_M3_HOLE_D / 2), amount=P.INSERT_M3_HOLE_DEPTH + 0.1)
    return part


# --------------------------------------------------------------- fit gauge --
def build_fit_gauge():
    """Calibration coupon: one row of bores stepping through GAUGE_BORES.

    Print it in the material and profile you will use for the base plate, find
    the hole an R50 sleeve just pushes into, and put that number in
    PIN_BORE_D. That replaces drilling the plate afterwards.
    """
    n = len(P.GAUGE_BORES)
    pitch, t = 7.5, P.PIN_BORE_L + 2.0
    w, d = n * pitch + 5.0, 14.0
    part = extrude(rrect((-w / 2, w / 2), (-d / 2, d / 2), 2.0), amount=t)
    for i, dia in enumerate(P.GAUGE_BORES):
        x = (i - (n - 1) / 2) * pitch
        part -= Pos(x, 3.0, -0.1) * extrude(Circle(dia / 2), amount=t + 0.2)
        # label in hundredths of a mm: 85, 90, ... 120
        part -= Pos(x, -4.0, t - 0.6) * extrude(
            Text(f"{round(dia * 100)}", font_size=3.4,
                 align=(Align.CENTER, Align.CENTER)), amount=0.7)
    return part


# ------------------------------------------- hardware, for renders only -----
def build_probes():
    """The seven R50 sleeves and the P50 tips standing in them. Not a printed
    part -- it exists so the renders show where the solder joints actually are."""
    out = None
    for tp in G.TEST_POINTS:
        p = Pos(tp["x"], tp["y"])
        sleeve = p * Pos(0, 0, P.Z_PIN_TOP - P.RECEPT_LEN) * extrude(
            Circle(P.RECEPT_BODY_D / 2), amount=P.RECEPT_LEN)
        shaft = p * Pos(0, 0, P.Z_PIN_TOP) * extrude(
            Circle(0.25), amount=P.PIN_PROTRUSION - 0.55)
        tip = p * Pos(0, 0, P.Z_PIN_TOP + P.PIN_PROTRUSION - 0.55) * extrude(
            Circle(0.25), amount=0.55, taper=45)
        out = sleeve + shaft + tip if out is None else out + sleeve + shaft + tip
    return out


PARTS_TO_BUILD = {
    "body": build_body,
    "nest": build_nest,
    "cover": build_cover,
    "fit_gauge": build_fit_gauge,
}


def assembly(open_position=False):
    """Every part plus the board, positioned as they sit in use."""
    dz = P.TRAVEL if open_position else 0.0
    seat = P.NEST_T + dz
    a = {
        "body": build_body(),
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
