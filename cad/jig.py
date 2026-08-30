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
    """One monolithic part. The open frame under the base plate and the clamp
    tower are the same shell: the tower is the pedestal walls carried straight
    up to a mounting deck, not a bracket bolted to the side.

    Prints standing on its own base with no overhangs -- every wall is
    vertical and the only horizontal roof is the tower deck, which is closed
    by the four clamp slots' own bridging.
    """
    z0, z1 = P.STAND_Z_BOTTOM, P.PLATE_Z_BOTTOM
    W = P.STAND_WALL

    # frame under the base plate, and the tower shell, as one outer solid
    frame = extrude(rrect(P.PLATE_X, P.PLATE_Y, P.PLATE_FILLET, z0), amount=z1 - z0)
    tower = extrude(rrect(P.PEDESTAL_X, P.PEDESTAL_Y, P.PLATE_FILLET, z0),
                    amount=P.TOWER_TOP_Z - z0)
    part = frame + tower

    # hollow both, leaving the tower deck
    part -= extrude(rrect((P.PLATE_X[0] + W, P.PLATE_X[1] - W),
                          (P.PLATE_Y[0] + W, P.PLATE_Y[1] - W), 2.0, z0 - 0.1),
                    amount=(z1 - z0) + 0.2)
    # The tower stays solid (slicer infill) up to a shallow nut channel under
    # the deck. A full-height cavity would print fine but would leave you
    # fishing for an M4 nut 40 mm down a hole.
    part -= extrude(rrect((P.PEDESTAL_X[0] + W, P.PEDESTAL_X[1] - W),
                          (P.PEDESTAL_Y[0] + W, P.PEDESTAL_Y[1]), 2.0, z0 - 0.1),
                    amount=P.PLATE_Z_BOTTOM - z0 + 0.1)

    # screw bosses carrying the base plate
    for x, y in P.MOUNT_SCREW_XY:
        part += Pos(x, y, z1 - 10.0) * extrude(Circle(4.5), amount=10.0)
        part -= Pos(x, y, z1 - 10.2) * extrude(Circle(1.4), amount=10.4)

    # Loom exit on the far side from the clamp. A vertical divider splits the
    # opening in two: it gives the zip tie something to pull against, and it
    # halves the span the slot's top edge has to bridge when printing.
    ey = P.PLATE_Y[1]
    zc = (P.WIRE_EXIT_Z[0] + P.WIRE_EXIT_Z[1]) / 2
    zh = P.WIRE_EXIT_Z[1] - P.WIRE_EXIT_Z[0]
    part -= Pos(0, ey, zc) * Box(P.WIRE_SLOT_W, W * 3, zh)
    part += Pos(0, ey - W / 2, zc) * Box(P.TIE_BAR_W, W, zh)

    # Clamp mounting: slots through the deck, longer than the GH-201's own so
    # the clamp can slide toward or away from the board, over a captive-nut
    # channel. The channel is open at the back face, so an M4 nut slides in
    # from outside and the channel walls stop it turning.
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
