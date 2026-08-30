"""Cuttle CANServo_Driver pogo programming jig.

Five printed parts:
  base_plate  precision part -- 7 probe bores, 4 guide posts, spring pockets
  stand       open frame that lifts the plate for wiring, carries the clamp pedestal
  nest        floating board carrier, rides the posts on springs
  cover       hold-down that presses only on bare board, guided by two posts
  clamp_riser spacer block carrying the GH-201 toggle clamp

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

    # probe bores: head counterbore, precision bore, then loose clearance
    for tp in G.TEST_POINTS:
        p = Pos(tp["x"], tp["y"])
        top = P.Z_PIN_TOP
        part -= p * Pos(0, 0, top - P.RECEPT_HEAD_L) * extrude(
            Circle(P.PIN_HEAD_BORE_D / 2), amount=P.RECEPT_HEAD_L + 0.1)
        bore_top = top - P.RECEPT_HEAD_L
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
    top = P.NEST_T + P.NEST_LIP
    part = extrude(rrect(P.NEST_X, P.NEST_Y, P.NEST_FILLET), amount=top)

    # drop-in board recess, then the relief window straight through
    part -= extrude(G.sk(G.board_recess(), Plane.XY.offset(P.NEST_T)), amount=P.NEST_LIP)
    part -= extrude(G.sk(G.nest_window(), Plane.XY.offset(-0.1)), amount=top + 0.2)

    for x, y in P.POST_XY:
        part -= Pos(x, y, -0.1) * extrude(Circle(P.POST_HOLE_D / 2), amount=top + 0.2)
        part -= Pos(x, y) * extrude(Circle(P.SPRING_POCKET_D / 2),
                                    amount=P.NEST_SPRING_DEPTH)
    for name in P.LOCATOR_HOLES:
        x, y = G.HOLES[name]
        part += Pos(x, y, P.NEST_T) * extrude(Circle(P.LOCATOR_D / 2), amount=P.LOCATOR_H)
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
    # clearance for the nest's board locator that falls under the cover
    for name in P.LOCATOR_HOLES:
        x, y = G.HOLES[name]
        if xr[0] < x < xr[1] and yr[0] < y < yr[1]:
            part -= Pos(x, y, -0.1) * extrude(Circle(P.LOCATOR_D / 2 + 1.0),
                                              amount=P.COVER_PAD_H + P.COVER_T + 0.2)
    return part




# ------------------------------------------------------------------- stand --
def build_stand():
    """Open frame that lifts the base plate clear of the bench for wiring and
    carries the vertical face the clamp riser bolts to."""
    z0, z1 = P.STAND_Z_BOTTOM, P.PLATE_Z_BOTTOM
    h = z1 - z0
    part = extrude(rrect(P.PLATE_X, P.PLATE_Y, P.PLATE_FILLET, z0), amount=h)
    inner = (P.PLATE_X[0] + P.STAND_WALL, P.PLATE_X[1] - P.STAND_WALL)
    innery = (P.PLATE_Y[0] + P.STAND_WALL, P.PLATE_Y[1] - P.STAND_WALL)
    part -= extrude(rrect(inner, innery, 2.0, z0 - 0.1), amount=h + 0.2)

    # wire exit, both long sides
    for sy in (1, -1):
        part -= Pos(0, sy * (P.PLATE_Y[1] - P.STAND_WALL / 2), z0 + h - P.WIRE_SLOT_W / 2) * \
                Box(P.WIRE_SLOT_W, P.STAND_WALL * 2, P.WIRE_SLOT_W)

    # screw bosses for the base plate
    for x, y in P.MOUNT_SCREW_XY:
        part += Pos(x, y, z1 - 8.0) * extrude(Circle(4.0), amount=8.0)
        part -= Pos(x, y, z1 - 8.2) * extrude(Circle(1.4), amount=8.4)

    # pedestal the clamp riser bolts onto, level with the rest of the stand top
    ped = extrude(rrect(P.PEDESTAL_X, P.PEDESTAL_Y, 4.0, z0), amount=h)
    part += ped
    pin = (P.PEDESTAL_X[0] + P.STAND_WALL, P.PEDESTAL_X[1] - P.STAND_WALL)
    piny = (P.PEDESTAL_Y[0] + P.STAND_WALL, P.PEDESTAL_Y[1])
    part -= extrude(rrect(pin, piny, 2.0, z0 - 0.1), amount=h - 4.0 + 0.1)
    for x, y in P.RISER_BOLT_XY:                      # M4 heat-set / self-tap
        part += Pos(x, y, z1 - 9.0) * extrude(Circle(4.5), amount=9.0)
        part -= Pos(x, y, z1 - 9.2) * extrude(Circle(1.9), amount=9.4)
    return part


# ------------------------------------------------------------ clamp riser --
def build_clamp_riser():
    """Spacer block carrying the GH-201. Re-print just this if your clamp's
    reach or spindle height differs; nothing else in the jig changes."""
    z0, zt = P.PLATE_Z_BOTTOM, P.RISER_TOP_Z
    part = extrude(rrect(P.RISER_X, P.RISER_Y, 3.0, z0), amount=zt - z0)
    # hollow it out, keeping a 4 mm top deck and 4 mm walls
    inx = (P.RISER_X[0] + 4, P.RISER_X[1] - 4)
    iny = (P.RISER_Y[0] + 4, P.RISER_Y[1] - 4)
    part -= extrude(rrect(inx, iny, 2.0, z0 - 0.1), amount=(zt - z0) - 4.0 + 0.1)
    for x, y in P.RISER_BOLT_XY:                    # down into the stand pedestal
        part += Pos(x, y, z0) * extrude(Circle(4.5), amount=zt - z0 - 4.0)
        part -= Pos(x, y, z0 - 0.1) * extrude(Circle(P.RAIL_SLOT_D / 2), amount=zt - z0 + 0.2)
    cx = (P.RISER_X[0] + P.RISER_X[1]) / 2
    cy = (P.RISER_Y[0] + P.RISER_Y[1]) / 2
    for sx in (-1, 1):                              # GH-201 mounting slots
        for sy in (-1, 1):
            part -= Pos(cx + sx * P.CLAMP_SLOT_DX / 2, cy + sy * P.CLAMP_SLOT_DY / 2,
                        zt - 4.5) * extrude(
                SlotOverall(P.CLAMP_SLOT_L, P.CLAMP_SLOT_W), amount=5.0)
    return part


PARTS_TO_BUILD = {
    "base_plate": build_base_plate,
    "nest": build_nest,
    "cover": build_cover,
    "stand": build_stand,
    "clamp_riser": build_clamp_riser,
}


def assembly(open_position=False):
    """All five parts plus the board, positioned as they sit in use."""
    dz = P.TRAVEL if open_position else 0.0
    seat = P.NEST_T + dz
    a = {
        "base_plate": build_base_plate(),
        "stand": build_stand(),
        "clamp_riser": build_clamp_riser(),
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
    asm = assembly()
    comp = Compound(children=[Part(s.wrapped, label=k) for k, s in asm.items()])
    export_step(comp, os.path.join(OUT, "assembly_closed.step"))
    print(f"\nwrote STEP + STL for {len(PARTS_TO_BUILD)} parts and the assembly into {OUT}")
