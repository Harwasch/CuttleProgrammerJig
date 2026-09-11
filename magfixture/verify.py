"""Numerical checks on the magnet fixture against the real PCBA model.

Same discipline as the programming jig's suite: every check measures geometry
or a fit as printed, and none of them restates how a part was constructed.

Run:  python3 verify.py
"""
import math
import os
import sys

from build123d import *

import mag_params as M
import fixture as F

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "cad"))
import geom as G                                              # noqa: E402
from verify import face_span, vol, OVERHANG_NZ                # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{'  --  ' + detail if detail else ''}")
    if not ok:
        FAILS.append(name)


def main():
    print("building parts ...")
    plate = F.build_board_plate()
    gantry = F.build_encoder_gantry()
    rotor = F.build_rotor()
    carriage = F.build_hall_carriage()
    board = G.pcba_solid(0.0)              # board underside on the seat plane

    # ------------------------------------------------------ sensor targeting --
    print("\nsensor targeting")
    ex, ey = M.ENC_XY
    rb = rotor.bounding_box()
    rot_cx, rot_cy = (rb.min.X + rb.max.X) / 2, (rb.min.Y + rb.max.Y) / 2
    off = math.hypot(rot_cx - ex, rot_cy - ey)
    check("encoder magnet is centred on the AS5600L", off <= 0.25,
          f"{off:.3f} mm off ({ex:+.2f},{ey:+.2f}); the datasheet allows 0.25")
    check("encoder airgap is inside the datasheet window",
          0.5 <= M.ENC_AIRGAP <= 3.0,
          f"{M.ENC_AIRGAP:.2f} mm face to package, of 0.5-3.0")
    check("rotor magnet face lands where the airgap says",
          abs(rb.min.Z - (M.ENC_PKG_TOP + M.ENC_AIRGAP)) < 1e-6,
          f"face z={rb.min.Z:.3f}, package top z={M.ENC_PKG_TOP:.3f}")
    check("the knob, not the operator, sets that height",
          abs((M.GANTRY_TOP - M.ROTOR_SHAFT_L) - M.ROTOR_MAG_FACE_Z) < 1e-9,
          f"shaft {M.ROTOR_SHAFT_L:.3f} mm below a knob resting on z="
          f"{M.GANTRY_TOP:.1f}")
    # It has to be possible to put together: the whole body below the knob
    # must pass down through the journal. A slim shaft with a fat magnet cup
    # was oversize at both ends and could not be assembled at all.
    below_knob = max(M.ROTOR_SHAFT_D, M.ROTOR_POCKET_D) + M.PRINT_BOSS_GROW
    journal = M.ROTOR_BORE_D - M.PRINT_HOLE_SHRINK
    check("rotor drops in through the journal from above",
          below_knob < journal,
          f"body prints Ø{below_knob:.2f} through a Ø{journal:.2f} journal")
    check("...and the knob cannot follow it through",
          M.ROTOR_KNOB_D > journal + 2.0,
          f"knob Ø{M.ROTOR_KNOB_D:.1f} lands on the gantry top")
    wall = (M.ROTOR_SHAFT_D - M.ROTOR_POCKET_D) / 2
    check("magnet pocket leaves wall in the rotor body", wall >= 1.2,
          f"{wall:.2f} mm around a Ø{M.ENC_MAG_D} magnet")

    cb = carriage.bounding_box()
    hx, hy = M.HALL_XY
    check("hall magnet pocket is centred on the SOT-23",
          abs(hx - M.HALL_XY[0]) < 1e-9 and abs(hy - M.HALL_XY[1]) < 1e-9,
          f"pocket axis ({hx:+.2f},{hy:+.2f})")

    # ------------------------------------------------------------- hall reach --
    print("\nhall carriage travel")
    lo = M.HALL_PKG_TOP + M.HALL_GAP_MIN
    hi = M.HALL_PKG_TOP + M.HALL_GAP_MAX
    check("carriage clears the plate at the closest setting", lo > 0.5,
          f"underside z={lo:.3f} at {M.HALL_GAP_MIN:.0f} mm gap")
    top_needed = hi + M.HALL_CARRIAGE_T
    check("posts are long enough for the far setting",
          M.HALL_POST_TOP >= top_needed + 2.0,
          f"posts to z={M.HALL_POST_TOP:.1f}, carriage top z={top_needed:.2f} "
          f"at {M.HALL_GAP_MAX:.0f} mm")
    eng = M.HALL_CARRIAGE_T
    check("carriage stays engaged on both posts throughout",
          eng >= 1.5 * M.fit(M.HALL_POST_HOLE_D, M.HALL_POST_D) * 20,
          f"{eng:.1f} mm of bore on {len(F.hall_post_xy())} posts")
    # it must not foul the board anywhere in that travel
    worst, worst_g = 0.0, None
    for g in [M.HALL_GAP_MIN + i * (M.HALL_GAP_MAX - M.HALL_GAP_MIN) / 8
              for i in range(9)]:
        c = Pos(0, 0, M.HALL_PKG_TOP + g) * carriage
        v = vol(c.intersect(board))
        if v > worst:
            worst, worst_g = v, g
    check("carriage clears the PCBA across the whole sweep", worst < 0.02,
          f"worst {worst:.4f} mm3"
          + (f" at {worst_g:.1f} mm" if worst_g else ""))

    # --------------------------------------------------------- interference ---
    print("\ninterference")
    for nm, a in (("board plate vs PCBA", plate),
                  ("encoder gantry vs PCBA", gantry),
                  ("rotor vs PCBA", rotor)):
        check(nm, vol(a.intersect(board)) < 0.02,
              f"{vol(a.intersect(board)):.4f} mm3")
    check("gantry vs board plate", vol(gantry.intersect(plate)) < 0.02,
          f"{vol(gantry.intersect(plate)):.4f} mm3")
    check("rotor turns without touching the gantry",
          vol(rotor.intersect(gantry)) < 0.02,
          f"{vol(rotor.intersect(gantry)):.4f} mm3")
    check("carriage vs plate posts at the closest setting",
          vol((Pos(0, 0, lo) * carriage).intersect(plate)) < 0.02,
          f"{vol((Pos(0, 0, lo) * carriage).intersect(plate)):.4f} mm3")

    # ----------------------------------------------------------- fits, as printed
    print("\nfits as printed")
    for nm, hole, sh, lo_r, hi_r in (
            ("rotor in its journal", M.ROTOR_BORE_D, M.ROTOR_SHAFT_D, 0.08, 0.25),
            ("carriage on the posts", M.HALL_POST_HOLE_D, M.HALL_POST_D, 0.08, 0.25),
            ("gantry on its pegs", M.GANTRY_PEG_HOLE_D, M.GANTRY_PEG_D, 0.08, 0.25)):
        r = M.fit(hole, sh)
        check(nm, lo_r <= r <= hi_r, f"{r:.3f} mm radial")
    enc_pocket = M.ROTOR_POCKET_D - M.PRINT_HOLE_SHRINK
    check("encoder magnet is a press fit in the rotor",
          -0.06 <= enc_pocket - M.ENC_MAG_D <= 0.0,
          f"pocket prints Ø{enc_pocket:.3f} on a Ø{M.ENC_MAG_D} magnet")
    hall_pocket = M.HALL_POCKET_D - M.PRINT_HOLE_SHRINK
    check("Ø13 magnet is a press fit in the carriage",
          -0.06 <= hall_pocket - 13.0 <= 0.0,
          f"pocket prints Ø{hall_pocket:.3f}")
    for d, fn in ((10.0, F.build_ring_10), (6.0, F.build_ring_6)):
        ring = fn()
        rbb = ring.bounding_box()
        od = rbb.size.X
        interf = (od + M.PRINT_BOSS_GROW) - hall_pocket
        check(f"Ø{d:.0f} adapter ring presses into the same pocket",
              0.0 <= interf <= 0.08,
              f"ring OD prints Ø{od + M.PRINT_BOSS_GROW:.2f} into a Ø"
              f"{hall_pocket:.2f} pocket -> {interf:+.3f} mm interference")
        check(f"...and seats a Ø{d:.0f} magnet face-flush",
              abs(rbb.min.Z) < 1e-9,
              f"ring face at z={rbb.min.Z:.3f} relative to the pocket mouth")

    # ------------------------------------------------------- board seating ----
    print("\nboard seating")
    check("four locating pins, both sections",
          len(M.LOCATORS) == 4 and "MH5" in M.LOCATORS and "MH6" in M.LOCATORS,
          f"{M.LOCATORS} -- MH5/MH6 hold the lobe, which is past a flex neck "
          f"and sets the encoder airgap")
    pin_printed = M.LOCATOR_D + M.PRINT_BOSS_GROW
    check("pins fit the board's routed Ø2.20 holes",
          0.03 <= (2.20 - pin_printed) / 2 <= 0.10,
          f"prints Ø{pin_printed:.2f} -> {(2.20 - pin_printed) / 2:.3f} mm radial")
    proud = M.LOCATOR_H - M.PCB_T
    check("pins stand proud of the board for loading", proud >= 1.5,
          f"{proud:.2f} mm above the board top")
    check("relief pocket clears the tallest bottom-side part",
          M.RECESS >= max(h for *_, h in G.PARTS["bottom"]) + 0.3,
          f"{M.RECESS:.2f} mm deep vs a "
          f"{max(h for *_, h in G.PARTS['bottom']):.3f} mm part")

    # ----------------------------------------------------------- gap gauge ----
    print("\ngap gauge")
    check("gauge spans the required separation range",
          min(M.GAUGE_STEPS) <= M.HALL_GAP_MIN and
          max(M.GAUGE_STEPS) >= M.HALL_GAP_MAX,
          f"steps {M.GAUGE_STEPS} against {M.HALL_GAP_MIN:.0f}-"
          f"{M.HALL_GAP_MAX:.0f} mm")
    gg = F.build_gap_gauge()
    check("every step stands proud of the gauge body",
          abs(gg.bounding_box().max.Z - max(M.GAUGE_STEPS)) < 1e-6,
          f"tallest tongue {gg.bounding_box().max.Z:.2f} mm")
    check("the thinnest tongue is printable",
          min(M.GAUGE_STEPS) >= 0.8,
          f"{min(M.GAUGE_STEPS):.1f} mm")

    # --------------------------------------------------------- printability ---
    print("\nprintability (in the print orientation)")
    for nm, shape, flip in (("board_plate", plate, False),
                            ("encoder_gantry", gantry, False),
                            ("rotor", rotor, True),
                            ("hall_carriage", carriage, False),
                            ("gap_gauge", gg, False)):
        oriented = Rot(180, 0, 0) * shape if flip else shape
        bed = oriented.bounding_box().min.Z
        worst, warea = 0.0, 0.0
        for f in oriented.faces():
            if f.center().Z <= bed + 0.05:
                continue
            try:
                nz = f.normal_at().Z
            except Exception:
                continue
            if nz <= -OVERHANG_NZ:
                sp = face_span(f)
                if sp > worst:
                    worst, warea = sp, f.area
        check(f"{nm:15s} bridges no more than 25 mm", worst <= 25.0,
              f"widest unsupported span {worst:.1f} mm ({warea:.0f} mm2)"
              + ("  (printed inverted)" if flip else ""))

    print()
    if FAILS:
        print(f"{len(FAILS)} CHECK(S) FAILED: {FAILS}")
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
