"""Magnet test fixture for the Cuttle CANServo_Driver V0.4.

Five printed parts:
  fixture_body  ONE part: the plate the board sits on, its four locating pins,
                the column the hall sleeve rides, and the portal that journals
                the encoder rotor over the lobe
  rotor         knob, shaft and magnet cup; drops into the portal and spins
  hall_sleeve   slides on the column, arm reaching over the SOT-23
  ring_10       press-in adapters so a Ø10 or Ø6 magnet seats on the same face
  ring_6        datum as a bare Ø13 one
  gap_gauge     stepped comb that sets the hall separation by a printed
                dimension rather than by reading a scale

Run:  python3 fixture.py     -> writes STEP + STL into magfixture/out/
"""
import math
import os
import sys

from build123d import *

import mag_params as M

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "cad"))
import geom as G                                              # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def rrect(xr, yr, r, z=0.0):
    w, h = xr[1] - xr[0], yr[1] - yr[0]
    f = Plane.XY.offset(z) * Rectangle(w, h)
    f = Pos((xr[0] + xr[1]) / 2, (yr[0] + yr[1]) / 2) * f
    return fillet(f.vertices(), r) if r > 0 else f


def centred_rrect(cx, cy, w, t, r, z=0.0):
    return rrect((cx - w / 2, cx + w / 2), (cy - t / 2, cy + t / 2), r, z)


def locator_spec():
    """(x, y, shape) for each locating pin.

    MH5 is a round pin and is the datum for the whole board, because the lobe
    it holds is what the encoder airgap is measured from. MH6 is a diamond --
    full width across the line joining the two lobe holes, relieved along it --
    so the pair tolerates a pin radius of pitch error and the lobe still drops
    on. MH1 and MH4 hold the main section, which is past a flex neck: how the
    flex was laminated sets where that section actually sits, so its pins are
    undersize and follow the lobe rather than fighting it.
    """
    lobe = [n for n in M.LOCATORS if n in ("MH5", "MH6")]
    out = []
    for name in M.LOCATORS:
        x, y = G.HOLES[name]
        if name not in lobe:
            out.append((x, y, "loose"))
        elif name == M.LOBE_DATUM:
            out.append((x, y, "round"))
        else:
            out.append((x, y, "diamond"))
    return out


def _pin_face(kind):
    if kind == "loose":
        return Circle(M.MAIN_LOCATOR_D / 2)
    if kind == "round":
        return Circle(M.LOCATOR_D / 2)
    # relieved along Y, the line joining MH5 and MH6
    return Circle(M.LOCATOR_D / 2) & Rectangle(M.LOCATOR_D, M.LOBE_DIAMOND_W)


def col_xy():
    return (M.HALL_XY[0], M.HALL_COL_Y)


def portal_wall_y():
    """(y0, y1) of each portal wall, inner face outward."""
    g = M.PORTAL_GAP_Y / 2
    return [(-g - M.PORTAL_WALL_T, -g), (g, g + M.PORTAL_WALL_T)]


# ------------------------------------------------------------ fixture body --
def build_fixture_body():
    """Plate, pins, hall column and encoder portal, all in one piece.

    The seat geometry is the programming jig's, reused rather than copied: the
    board rests on its six mounting-hole bosses plus the three sections that
    carry no bottom-side parts, and everything else drops into one pocket.
    """
    part = extrude(rrect(M.PLATE_X, M.PLATE_Y, M.PLATE_FILLET, -M.PLATE_T),
                   amount=M.PLATE_T)
    part -= extrude(G.sk(G.nest_recess(), Plane.XY.offset(-M.RECESS)),
                    amount=M.RECESS)

    for x, y, kind in locator_spec():
        f = _pin_face(kind)
        part += Pos(x, y) * extrude(f, amount=M.LOCATOR_H - 0.5)
        part += Pos(x, y, M.LOCATOR_H - 0.5) * extrude(f, amount=0.5, taper=30)

    part += _hall_column()
    part += _encoder_portal()
    return part


def _hall_column():
    """One rectangular column on a flared plinth.

    Two Ø6 cylinders snapped at the root. A cylinder is the worst possible
    printed section for this: its layer bonds lie square across the bending
    load, and there is nowhere to put material where the stress is highest.
    A 14 x 10 rectangle carries 5.5x the section modulus, resists twist about
    its own axis without needing a second member, and takes a plinth that
    spreads the root stress into the plate instead of concentrating it in one
    layer line.
    """
    cx, cy = col_xy()
    w, t, h = M.HALL_COL_W, M.HALL_COL_T, M.HALL_PLINTH_H
    taper = math.degrees(math.atan(M.HALL_PLINTH_FLARE / h))
    col = extrude(centred_rrect(cx, cy, w + 2 * M.HALL_PLINTH_FLARE,
                                t + 2 * M.HALL_PLINTH_FLARE, M.HALL_COL_R),
                  amount=h, taper=taper)
    col += extrude(centred_rrect(cx, cy, w, t, M.HALL_COL_R), amount=M.HALL_COL_TOP)
    top = col.faces().sort_by(Axis.Z)[-1]
    return chamfer(top.edges(), M.HALL_COL_CHAMFER)


def _encoder_portal():
    """Two walls, a deck, and a hub. Deck plus hub give 12 mm of bore, which is
    what keeps the magnet -- hanging 5.5 mm below it -- inside the AS5600's
    centring window; splitting it that way leaves the encoder visible."""
    z0, z1 = M.PORTAL_DECK_Z
    part = None
    for y0, y1 in portal_wall_y():
        w = extrude(rrect(M.PORTAL_X, (y0, y1), 0.0), amount=z0)
        part = w if part is None else part + w
    ybot = portal_wall_y()[0][0]
    ytop = portal_wall_y()[1][1]
    part += extrude(rrect(M.PORTAL_X, (ybot, ytop), 0.0, z0), amount=z1 - z0)
    part += Pos(*M.ENC_XY, z1) * extrude(Circle(M.ROTOR_HUB_D / 2),
                                         amount=M.ROTOR_HUB_TOP - z1)
    part -= Pos(*M.ENC_XY, z0 - 0.1) * extrude(
        Circle(M.ROTOR_BORE_D / 2), amount=M.JOURNAL_L + 0.2)
    return part


# ------------------------------------------------------------------- rotor --
def build_rotor():
    """Knob, shaft, magnet cup. The knob's underside lands on the deck, so the
    shaft length alone sets the airgap -- nothing to adjust or measure."""
    top = M.GANTRY_TOP
    part = Pos(*M.ENC_XY, top) * extrude(Circle(M.ROTOR_KNOB_D / 2),
                                         amount=M.ROTOR_KNOB_T)
    for i in range(M.ROTOR_FLUTES):
        a = 2 * math.pi * i / M.ROTOR_FLUTES
        fx = M.ENC_XY[0] + (M.ROTOR_KNOB_D / 2) * math.cos(a)
        fy = M.ENC_XY[1] + (M.ROTOR_KNOB_D / 2) * math.sin(a)
        part -= Pos(fx, fy, top) * extrude(Circle(2.0), amount=M.ROTOR_KNOB_T)

    face_z = M.ROTOR_MAG_FACE_Z
    part += Pos(*M.ENC_XY, face_z) * extrude(Circle(M.ROTOR_SHAFT_D / 2),
                                             amount=top - face_z)
    part -= Pos(*M.ENC_XY, face_z - 0.1) * extrude(
        Circle(M.ROTOR_POCKET_D / 2), amount=M.ENC_MAG_T + 0.1)
    return part


# -------------------------------------------------------------- hall sleeve --
def build_hall_sleeve():
    """Rectangular sleeve on the column, arm reaching over the SOT-23.

    Built with its arm underside -- which is also the magnet face datum -- at
    z = 0, so it can simply be translated up to whatever separation is wanted.
    """
    cx, cy = col_xy()
    bw = M.HALL_BORE_W + 2 * M.HALL_SLEEVE_WALL
    bt = M.HALL_BORE_T + 2 * M.HALL_SLEEVE_WALL
    body = centred_rrect(cx, cy, bw, bt, M.HALL_COL_R + M.HALL_SLEEVE_WALL)

    boss_y0 = cy - bt / 2 - M.HALL_BOSS_T
    boss = rrect((cx - 5.0, cx + 5.0), (boss_y0, cy), 0.0)
    part = extrude(body + boss, amount=M.HALL_SLEEVE_H)

    arm = rrect((cx - M.HALL_ARM_W / 2, cx + M.HALL_ARM_W / 2),
                (cy, M.HALL_XY[1]), 0.0)
    head = Pos(*M.HALL_XY) * Circle(M.HALL_POCKET_D / 2 + 2.5)
    part += extrude(arm + head, amount=M.HALL_ARM_T)

    part -= Pos(cx, cy, -0.1) * extrude(
        centred_rrect(0, 0, M.HALL_BORE_W, M.HALL_BORE_T, M.HALL_COL_R),
        amount=M.HALL_SLEEVE_H + 0.2)

    # magnet pocket, opening DOWNWARD so its mouth is the sleeve's own
    # underside -- one face datum for all three magnet diameters
    part -= Pos(*M.HALL_XY, -0.1) * extrude(Circle(M.HALL_POCKET_D / 2),
                                            amount=M.HALL_POCKET_DEPTH + 0.1)
    # ...and a hole through the ceiling, because you cannot pull a neodymium
    # magnet back out of a blind pocket
    part -= Pos(*M.HALL_XY, M.HALL_POCKET_DEPTH) * extrude(
        Circle(M.HALL_EJECT_D / 2), amount=M.HALL_ARM_T)

    # clamp screw: heat-set insert in the boss, M3 clearance on to the column
    zc = M.HALL_SLEEVE_H / 2
    part -= Pos(cx, boss_y0 - 0.1, zc) * Rot(-90, 0, 0) * extrude(
        Circle(M.INSERT_M3_HOLE_D / 2), amount=M.INSERT_M3_HOLE_DEPTH + 0.1)
    part -= Pos(cx, boss_y0 + M.INSERT_M3_HOLE_DEPTH, zc) * Rot(-90, 0, 0) * \
        extrude(Circle(M.M3_CLEAR_D / 2),
                amount=(cy - M.HALL_BORE_T / 2) - boss_y0
                       - M.INSERT_M3_HOLE_DEPTH)
    return part


# ------------------------------------------------------------ adapter rings --
def _ring(inner_d, depth=None):
    """Press-in adapter. `depth` blind (the magnet bottoms out face-flush),
    otherwise through (push it flush with a straight edge)."""
    r = extrude(Circle(M.RING_OD / 2), amount=M.RING_H)
    if depth is None:
        r -= Pos(0, 0, -0.1) * extrude(Circle(inner_d / 2), amount=M.RING_H + 0.2)
    else:
        r -= Pos(0, 0, -0.1) * extrude(Circle(inner_d / 2), amount=depth + 0.1)
        r -= Pos(0, 0, depth) * extrude(Circle(1.5), amount=M.RING_H)
    return r


def build_ring_10():
    return _ring(M.bore(10.0 - 0.02))


def build_ring_6():
    # the only one of the three whose thickness is known, so it gets a floor
    # to bottom out against and an eject hole through the back
    return _ring(M.bore(6.0 - 0.02), depth=M.ENC_MAG_T)


# --------------------------------------------------------------- gap gauge --
def build_gap_gauge():
    """A stepped comb. Slip the step you want between the magnet face and the
    package, drop the sleeve onto it, tighten, withdraw."""
    n = len(M.GAUGE_STEPS)
    w = n * M.GAUGE_STEP_W
    # Body and tongues share the bed plane at z=0. With the body BELOW it the
    # tongues stuck out 14 mm into thin air with nothing under them -- a
    # cantilever, not a bridge, and it droops however well the printer bridges.
    part = extrude(rrect((0, w), (0, 12.0), 2.0), amount=M.GAUGE_BODY_T)
    for i, s_ in enumerate(M.GAUGE_STEPS):
        x0 = i * M.GAUGE_STEP_W
        part += Pos(x0 + M.GAUGE_STEP_W / 2, 12.0 + M.GAUGE_TONGUE_L / 2,
                    s_ / 2) * Box(M.GAUGE_STEP_W - 1.5, M.GAUGE_TONGUE_L, s_)
        part -= Pos(x0 + M.GAUGE_STEP_W / 2, 6.0, M.GAUGE_BODY_T) * extrude(
            Text(str(s_), font_size=4.5, align=(Align.CENTER, Align.CENTER)),
            amount=-0.6)
    return part


PARTS_TO_BUILD = {
    "fixture_body": build_fixture_body,
    "rotor": build_rotor,
    "hall_sleeve": build_hall_sleeve,
    "ring_10": build_ring_10,
    "ring_6": build_ring_6,
    "gap_gauge": build_gap_gauge,
}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in PARTS_TO_BUILD.items():
        p = fn()
        bb = p.bounding_box()
        print(f"{name:14s} vol {p.volume:9.1f} mm3   bbox "
              f"{bb.size.X:6.2f} x {bb.size.Y:6.2f} x {bb.size.Z:6.2f}")
        export_step(p, os.path.join(OUT, f"{name}.step"))
        export_stl(p, os.path.join(OUT, f"{name}.stl"))
    print(f"\nwrote STEP + STL for {len(PARTS_TO_BUILD)} parts into {OUT}")
