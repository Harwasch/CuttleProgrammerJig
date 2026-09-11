"""Magnet test fixture for the Cuttle CANServo_Driver V0.4.

Seven printed parts:
  board_plate      holds the board flat, clear of its bottom-side components,
                   located on four pins; carries the hall posts and the pegs
                   the encoder gantry drops onto
  encoder_gantry   reaches over the lobe and journals the rotor
  rotor            knob, shaft and magnet cup; spins by finger
  hall_carriage    slides on the two posts, arm reaching over the SOT-23
  ring_10, ring_6  press-in adapters so a Ø10 or Ø6 magnet seats face-flush
                   in the same Ø13 pocket
  gap_gauge        stepped comb that sets the hall separation by a printed
                   dimension rather than by reading a scale

Run:  python3 fixture.py     -> writes STEP + STL into magfixture/out/
"""
import os
import sys

from build123d import *
from shapely.geometry import Point
from shapely.ops import unary_union

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


def hall_post_xy():
    return [(M.HALL_XY[0] + sx * M.HALL_POST_DX / 2, M.HALL_POST_Y)
            for sx in (-1, 1)]


def gantry_peg_xy():
    return [(54.0, sy * 5.0) for sy in (-1, 1)]


# -------------------------------------------------------------- board plate --
def build_board_plate():
    """Seat, relief pocket, four locating pins, and both tower mounts.

    The seat geometry is the programming jig's, reused rather than copied: the
    board rests on its six mounting-hole bosses plus the three sections that
    carry no bottom-side parts, and everything else drops into one pocket.
    """
    part = extrude(rrect(M.PLATE_X, M.PLATE_Y, M.PLATE_FILLET, -M.PLATE_T),
                   amount=M.PLATE_T)
    part -= extrude(G.sk(G.nest_recess(), Plane.XY.offset(-M.RECESS)),
                    amount=M.RECESS)

    # Locating pins. MH1/MH4 hold the main section; MH5/MH6 hold the lobe,
    # which is on the far side of a flex neck and would otherwise float -- and
    # the lobe is where the encoder airgap is set.
    for name in M.LOCATORS:
        x, y = G.HOLES[name]
        part += Pos(x, y) * extrude(Circle(M.LOCATOR_D / 2),
                                    amount=M.LOCATOR_H - 0.5)
        part += Pos(x, y, M.LOCATOR_H - 0.5) * extrude(
            Circle(M.LOCATOR_D / 2), amount=0.5, taper=30)

    for x, y in hall_post_xy():
        part += Pos(x, y) * extrude(Circle(M.HALL_POST_D / 2),
                                    amount=M.HALL_POST_TOP)
        part += Pos(x, y, M.HALL_POST_TOP - 0.6) * extrude(
            Circle(M.HALL_POST_D / 2), amount=0.6, taper=30)
    for x, y in gantry_peg_xy():
        part += Pos(x, y) * extrude(Circle(M.GANTRY_PEG_D / 2),
                                    amount=M.GANTRY_PEG_H)
        part += Pos(x, y, M.GANTRY_PEG_H - 0.5) * extrude(
            Circle(M.GANTRY_PEG_D / 2), amount=0.5, taper=30)
    return part


# ----------------------------------------------------------- encoder gantry --
def build_encoder_gantry():
    """Reaches over the lobe and journals the rotor.

    A separate part so the board drops straight in and this goes on afterwards.
    The underside of the reach is a 45 degree gusset rather than a flat
    cantilever, so it prints standing as modelled with no support anywhere.
    """
    prof = [(63.0, 0.0), (63.0, M.GANTRY_TOP), (41.0, M.GANTRY_TOP),
            (41.0, 14.0), (50.0, 14.0), (58.0, 6.0), (52.0, 6.0), (52.0, 0.0)]
    face = make_face(Polyline(*[(x, 0.0, z) for x, z in prof], close=True))
    part = extrude(Plane.XZ * Plane.XZ.to_local_coords(face),
                   amount=M.GANTRY_LEG_W / 2, both=True)

    part -= Pos(*M.ENC_XY, 0) * extrude(Circle(M.ROTOR_BORE_D / 2),
                                        amount=M.GANTRY_TOP + 1)
    for x, y in gantry_peg_xy():
        part -= Pos(x, y, -0.1) * extrude(Circle(M.GANTRY_PEG_HOLE_D / 2),
                                          amount=M.GANTRY_PEG_H + 0.6)
    return part


# ------------------------------------------------------------------- rotor --
def build_rotor():
    """Knob, shaft, magnet cup. The knob's underside lands on the gantry, so
    the shaft length alone sets the airgap -- nothing to adjust or measure."""
    top = M.GANTRY_TOP
    part = Pos(*M.ENC_XY, top) * extrude(Circle(M.ROTOR_KNOB_D / 2),
                                         amount=M.ROTOR_KNOB_T)
    for i in range(M.ROTOR_FLUTES):
        a = 2 * 3.141592653589793 * i / M.ROTOR_FLUTES
        fx = M.ENC_XY[0] + (M.ROTOR_KNOB_D / 2) * __import__("math").cos(a)
        fy = M.ENC_XY[1] + (M.ROTOR_KNOB_D / 2) * __import__("math").sin(a)
        part -= Pos(fx, fy, top) * extrude(Circle(1.6), amount=M.ROTOR_KNOB_T)

    face_z = M.ROTOR_MAG_FACE_Z
    part += Pos(*M.ENC_XY, face_z) * extrude(Circle(M.ROTOR_SHAFT_D / 2),
                                             amount=top - face_z)
    part -= Pos(*M.ENC_XY, face_z - 0.1) * extrude(
        Circle(M.ROTOR_POCKET_D / 2), amount=M.ENC_MAG_T + 0.1)
    return part


# --------------------------------------------------------- hall carriage ----
def build_hall_carriage():
    """Rides both posts, reaches over the SOT-23, clamps with one M3."""
    y0 = M.HALL_POST_Y
    body = rrect((M.HALL_XY[0] - M.HALL_POST_DX / 2 - M.HALL_BODY_BACK,
                  M.HALL_XY[0] + M.HALL_POST_DX / 2 + 6.0),
                 (y0 - 6.0, y0 + 6.0), 3.0)
    arm = rrect((M.HALL_XY[0] - M.HALL_ARM_W / 2,
                 M.HALL_XY[0] + M.HALL_ARM_W / 2),
                (y0, M.HALL_XY[1]), 0.0)
    head = Pos(*M.HALL_XY) * Circle(M.HALL_POCKET_D / 2 + 2.5)
    part = extrude(body + arm + head, amount=M.HALL_CARRIAGE_T)

    for x, y in hall_post_xy():
        part -= Pos(x, y, -0.1) * extrude(Circle(M.HALL_POST_HOLE_D / 2),
                                          amount=M.HALL_CARRIAGE_T + 0.2)
    # magnet pocket, opening DOWNWARD so the face is the carriage's own
    # underside -- one datum for all three magnet diameters
    part -= Pos(*M.HALL_XY, -0.1) * extrude(Circle(M.HALL_POCKET_D / 2),
                                            amount=M.HALL_POCKET_DEPTH + 0.1)
    # clamp screw, into a heat-set insert, bearing on the -X post
    px, py = hall_post_xy()[0]
    back = M.HALL_XY[0] - M.HALL_POST_DX / 2 - M.HALL_BODY_BACK
    part -= Pos(back - 0.1, py, M.HALL_CARRIAGE_T / 2) * Rot(0, 90, 0) * \
        extrude(Circle(M.INSERT_M3_HOLE_D / 2), amount=M.INSERT_M3_HOLE_DEPTH + 0.1)
    # ...then M3 clearance the rest of the way to the post it bears on
    part -= Pos(back + M.INSERT_M3_HOLE_DEPTH, py, M.HALL_CARRIAGE_T / 2) * \
        Rot(0, 90, 0) * extrude(
            Circle(1.7), amount=(px - M.HALL_POST_D / 2) - back
                                - M.INSERT_M3_HOLE_DEPTH)
    return part


def _ring(inner_d):
    od = M.RING_OD
    h = min(M.HALL_POCKET_DEPTH - 1.0, 6.0)
    r = extrude(Circle(od / 2), amount=h)
    r -= Pos(0, 0, -0.1) * extrude(Circle(inner_d / 2), amount=h + 0.2)
    return r


def build_ring_10():
    return _ring(M.bore(10.0 - 0.02))


def build_ring_6():
    return _ring(M.bore(6.0 - 0.02))


# --------------------------------------------------------------- gap gauge --
def build_gap_gauge():
    """A stepped comb. Slip the step you want between the magnet face and the
    package, drop the carriage onto it, tighten, withdraw."""
    n = len(M.GAUGE_STEPS)
    w = n * M.GAUGE_STEP_W
    # body sits BELOW z=0 so every tongue stands proud of it -- with the body
    # above z=0 the 1 mm and 2 mm steps were buried inside it and unusable
    part = extrude(rrect((0, w), (0, 12.0), 2.0, -M.GAUGE_BODY_T),
                   amount=M.GAUGE_BODY_T)
    for i, s in enumerate(M.GAUGE_STEPS):
        x0 = i * M.GAUGE_STEP_W
        part += Pos(x0 + M.GAUGE_STEP_W / 2, 12.0 + M.GAUGE_TONGUE_L / 2,
                    s / 2) * Box(M.GAUGE_STEP_W - 1.5, M.GAUGE_TONGUE_L, s)
        part += Pos(x0 + M.GAUGE_STEP_W / 2, 6.0, -M.GAUGE_BODY_T / 2) * \
            Box(M.GAUGE_STEP_W - 1.5, 12.0, M.GAUGE_BODY_T)
        part -= Pos(x0 + M.GAUGE_STEP_W / 2, 6.0, 0.0) * extrude(
            Text(str(s), font_size=4.5, align=(Align.CENTER, Align.CENTER)),
            amount=-0.6)
    return part


PARTS_TO_BUILD = {
    "board_plate": build_board_plate,
    "encoder_gantry": build_encoder_gantry,
    "rotor": build_rotor,
    "hall_carriage": build_hall_carriage,
    "ring_10": build_ring_10,
    "ring_6": build_ring_6,
    "gap_gauge": build_gap_gauge,
}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in PARTS_TO_BUILD.items():
        p = fn()
        bb = p.bounding_box()
        print(f"{name:16s} vol {p.volume:9.1f} mm3   bbox "
              f"{bb.size.X:6.2f} x {bb.size.Y:6.2f} x {bb.size.Z:6.2f}")
        export_step(p, os.path.join(OUT, f"{name}.step"))
        export_stl(p, os.path.join(OUT, f"{name}.stl"))
    print(f"\nwrote STEP + STL for {len(PARTS_TO_BUILD)} parts into {OUT}")
