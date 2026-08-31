"""Cuttle CANServo_Driver pogo programming jig.

Four printed parts:
  base_plate  precision part -- 7 probe bores, 4 guide posts, spring pockets
  stand       one piece: open frame under the plate plus the clamp tower
  nest        floating board carrier, rides the posts on springs
  cover       hold-down that presses only on bare board, guided by two posts

Run:  python3 jig.py            -> writes STEP + STL into cad/out/
"""
import os
from build123d import *
from shapely.geometry import Point
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

    for x, y in P.MOUNT_SCREW_XY:
        part -= Pos(x, y, z0 - 0.1) * extrude(
            Circle(P.MOUNT_SCREW_D / 2), amount=-z0 + 0.2)
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

    # All four main-section holes take a pin. Two locate; the other two are
    # undersize so they engage without fighting the first pair.
    for names, dia in ((P.LOCATOR_PRIMARY, P.LOCATOR_D),
                       (P.LOCATOR_SECONDARY, P.LOCATOR_D2)):
        for name in names:
            x, y = G.HOLES[name]
            part += Pos(x, y, P.NEST_T) * extrude(Circle(dia / 2), amount=P.LOCATOR_H)
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

    # dimple at the centroid of the contact pads: where the clamp spindle lands
    cxp = sum(p[0] for p in P.COVER_PADS) / len(P.COVER_PADS)
    cyp = sum(p[1] for p in P.COVER_PADS) / len(P.COVER_PADS)
    top = P.COVER_PAD_H + P.COVER_T
    part -= Pos(cxp, cyp, top) * Sphere(P.COVER_DIMPLE_R)

    for x, y in P.COVER_POSTS:
        part -= Pos(x, y, -0.1) * extrude(Circle(P.POST_HOLE_D / 2),
                                          amount=P.COVER_PAD_H + P.COVER_T + 0.2)
    # clearance for any nest locator pin that falls under the cover
    for name in P.LOCATOR_PRIMARY + P.LOCATOR_SECONDARY:
        x, y = G.HOLES[name]
        if xr[0] < x < xr[1] and yr[0] < y < yr[1]:
            part -= Pos(x, y, -0.1) * extrude(Circle(P.LOCATOR_D / 2 + 1.0),
                                              amount=P.COVER_PAD_H + P.COVER_T + 0.2)
    return part




# ------------------------------------------------------------------- stand --
def build_stand():
    """One monolithic part, one full rectangular footprint.

    FDM notes: every feature here is a vertical wall or a vertical hole. The
    shell is open top and bottom, so there is no roof to bridge; the base plate
    lands on a bay wall that runs all the way to the bench rather than on
    cantilevered bosses; the clamp tower is solid up to a shallow nut channel;
    and the loom slot is split by a post so its top edge spans 8 mm, not 20.
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
    ry0, ry1 = P.STAND_Y[0] + W, P.STAND_Y[1] - W
    for x in P.RIB_X:
        part += Pos(x, (ry0 + ry1) / 2, z0 + h / 2) * Box(W, ry1 - ry0, h)
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

    # base-plate screws: full-height columns, so nothing hangs in air
    for x, y in P.MOUNT_SCREW_XY:
        part += Pos(x, y, z0) * extrude(Circle(4.5), amount=h)
        part -= Pos(x, y, z1 - 10.0) * extrude(Circle(1.4), amount=10.2)

    # loom exit, straight out through the bay wall and the outer wall
    zc = (P.WIRE_EXIT_Z[0] + P.WIRE_EXIT_Z[1]) / 2
    zh = P.WIRE_EXIT_Z[1] - P.WIRE_EXIT_Z[0]
    ymid = (P.PLATE_Y[1] + P.STAND_Y[1]) / 2
    part -= Pos(0, ymid, zc) * Box(P.WIRE_SLOT_W,
                                   P.STAND_Y[1] - P.PLATE_Y[1] + 4 * W, zh)
    for sy in (P.PLATE_Y[1] - W / 2, P.STAND_Y[1] - W / 2):
        part += Pos(0, sy, zc) * Box(P.TIE_BAR_W, W, zh)

    # clamp mounting: deck slots over a captive-nut channel open at the back
    cx = (P.PEDESTAL_X[0] + P.PEDESTAL_X[1]) / 2
    cy = (P.PEDESTAL_Y[0] + P.PEDESTAL_Y[1]) / 2
    deck = P.TOWER_TOP_Z - P.TOWER_DECK_T
    for sx in (-1, 1):
        x = cx + sx * P.CLAMP_SLOT_DX / 2
        for sy in (-1, 1):
            part -= Pos(x, cy + sy * P.CLAMP_SLOT_DY / 2, deck - 0.1) * extrude(
                SlotOverall(P.CLAMP_SLOT_W + P.CLAMP_SLOT_TRAVEL, P.RAIL_SLOT_D,
                            rotation=90), amount=P.TOWER_DECK_T + 0.2)
        y0 = P.PEDESTAL_Y[0] - 1.0
        y1 = cy + P.CLAMP_SLOT_DY / 2 + (P.CLAMP_SLOT_W + P.CLAMP_SLOT_TRAVEL) / 2 + 2.0
        part -= Pos(x, (y0 + y1) / 2, deck - P.NUT_CHANNEL_H / 2) * \
            Box(P.NUT_CHANNEL_W, y1 - y0, P.NUT_CHANNEL_H)
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
    "base_plate": build_base_plate,
    "nest": build_nest,
    "cover": build_cover,
    "stand": build_stand,
    "fit_gauge": build_fit_gauge,
}


def assembly(open_position=False):
    """All five parts plus the board, positioned as they sit in use."""
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
