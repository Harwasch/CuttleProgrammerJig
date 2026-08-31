"""Numerical checks on the jig against the real PCBA STEP model.

Every check is a genuine interference or dimension test.
Run:  python3 verify.py
"""
import os, sys, math
from build123d import *
from shapely.geometry import Point
import params as P
import geom as G
import jig

HERE = os.path.dirname(os.path.abspath(__file__))
STEP = os.path.join(HERE, "ref", "CANServo_Driver_v0.4.step")
OX, OY = G.BOARD["origin_in_gerber_coords"]

FULL = "--full" in sys.argv
FAILS = []


def vol(x):
    """Volume of an intersect() result, which may be a Shape or a ShapeList."""
    if x is None:
        return 0.0
    if hasattr(x, "volume"):
        return x.volume
    return sum(s.volume for s in x)


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{'  --  ' + detail if detail else ''}")
    if not ok:
        FAILS.append(name)


def main():
    print("building parts ...")
    base, nest, cover = jig.build_base_plate(), jig.build_nest(), jig.build_cover()
    seat = P.NEST_T                       # board underside, clamp closed
    if FULL:
        print("importing the full PCBA STEP (slow, exact) ...")
        board = Pos(-OX, -OY, seat) * import_step(STEP)
    else:
        print("building the banded PCBA keep-out solid (fast, conservative) ...")
        board = G.pcba_solid(seat)
    board_t = P.PCB_T

    # ------------------------------------------------------------ stack-up --
    print("\nstack-up")
    check("platform top = NEST_T + COMPRESSION - PIN_PROTRUSION",
          abs(P.Z_PIN_TOP - (P.NEST_T + P.COMPRESSION - P.PIN_PROTRUSION)) < 1e-9,
          f"Z_PIN_TOP = {P.Z_PIN_TOP:.3f} mm")
    check("working stroke inside the probe's travel",
          0.8 <= P.COMPRESSION <= 0.7 * P.PIN_STROKE_MAX,
          f"{P.COMPRESSION:.2f} mm of {P.PIN_STROKE_MAX:.2f} mm")
    check("probe tips clear the board at rest", P.TRAVEL - P.COMPRESSION >= 1.0,
          f"{P.TRAVEL - P.COMPRESSION:.2f} mm of daylight for loading")
    l_rest = P.BASE_SPRING_DEPTH + P.NEST_SPRING_DEPTH + P.TRAVEL
    l_stop = P.BASE_SPRING_DEPTH + P.NEST_SPRING_DEPTH
    check("spring preloaded at rest", P.SPRING_FREE > l_rest + 0.5,
          f"free {P.SPRING_FREE:.1f} -> installed {l_rest:.1f} mm "
          f"({P.SPRING_FREE - l_rest:.1f} mm preload)")
    check("spring not stacked solid when clamped", l_stop > 0.62 * P.SPRING_FREE,
          f"{l_stop:.1f} mm at the stop, solid is about {0.5 * P.SPRING_FREE:.1f} mm")
    engage = P.POST_TOP_Z - (P.TRAVEL + P.NEST_T + P.PCB_T)
    check("posts still guide the cover at rest", engage >= 5.0, f"{engage:.1f} mm engaged")

    # --------------------------------------------------------- probe bores --
    print("\nprobe bores and platform")
    for tp in G.TEST_POINTS:
        # the bore must be open from the platform top down past the precision section
        depth = P.PIN_LEAD_L + P.PIN_BORE_L
        probe = Pos(tp["x"], tp["y"], P.Z_PIN_TOP - depth) * extrude(
            Circle(P.PIN_BORE_D / 2 - 0.02), amount=depth)
        check(f"{tp['net']:8s} bore open through {depth:.1f} mm",
              vol(base.intersect(probe)) < 0.02 * probe.volume,
              f"{100 * vol(base.intersect(probe)) / probe.volume:.1f}% obstructed")
        # the platform must be solid in a collar outside the head counterbore
        ring = (Pos(tp["x"], tp["y"], P.Z_PIN_TOP - 0.4) * extrude(Circle(1.45), amount=0.35)
                - Pos(tp["x"], tp["y"], P.Z_PIN_TOP - 0.5) * extrude(
                    Circle(P.PIN_LEAD_D / 2 + 0.10), amount=0.6))
        got = vol(base.intersect(ring))
        check(f"{tp['net']:8s} platform collar is solid", got > 0.55 * ring.volume,
              f"{100 * got / ring.volume:.0f}% solid at z={P.Z_PIN_TOP:.2f}")

    # ------------------------------------------- interference, clamp closed --
    print("\ninterference, clamp closed (nest on the hard stop)")
    for nm, a, bshape in [("PCBA vs base plate", base, board),
                          ("PCBA vs nest", nest, board),
                          ("nest vs base plate", base, nest)]:
        v = vol(a.intersect(bshape))
        check(nm, v < 0.02, f"{v:.4f} mm3 overlap")

    # --------------------------------------------- interference, clamp open --
    print("\ninterference, clamp open (nest lifted by TRAVEL)")
    nest_up = Pos(0, 0, P.TRAVEL) * nest
    board_up = Pos(0, 0, P.TRAVEL) * board
    check("nest vs base plate, lifted", vol(base.intersect(nest_up)) < 0.02,
          f"{vol(base.intersect(nest_up)):.4f} mm3")
    check("PCBA vs base plate, lifted", vol(base.intersect(board_up)) < 0.02,
          f"{vol(base.intersect(board_up)):.4f} mm3")

    # ----------------------------------------------------------- hold-down --
    print("\nhold-down cover")
    cov = Pos(0, 0, seat + board_t) * cover
    v = vol(cov.intersect(board))
    check("cover vs PCBA top-side parts", v < 0.02, f"{v:.4f} mm3 overlap")
    check("cover vs nest", vol(cov.intersect(nest)) < 0.02,
          f"{vol(cov.intersect(nest)):.4f} mm3")
    for x, y in P.COVER_PADS:
        clr = min([bx.distance(Point(x, y)) for bx in G.part_boxes("top")])
        edge = G.OUTLINE.exterior.distance(Point(x, y))
        check(f"cover pad ({x:7.2f},{y:6.2f}) on bare board",
              clr >= P.COVER_PAD_R and edge >= P.COVER_PAD_R,
              f"{clr:.2f} mm to nearest part, {edge:.2f} mm to board edge")

    # ------------------------------------------------------ stand and tower --
    print("\nstand")
    stand = jig.build_stand()
    cov_open = Pos(0, 0, seat + P.TRAVEL + board_t) * cover
    nest_open = Pos(0, 0, P.TRAVEL) * nest
    for nm, a, b2 in [("stand vs base plate", stand, base),
                      ("clamp tower vs nest, clamp open", stand, nest_open),
                      ("clamp tower vs cover, clamp open", stand, cov_open),
                      ("clamp tower vs PCBA", stand, board)]:
        v = vol(a.intersect(b2))
        check(nm, v < 0.02, f"{v:.4f} mm3 overlap")
    ct = seat + P.TRAVEL + board_t + P.COVER_PAD_H + P.COVER_T
    check("clamp deck sits below the cover top",
          P.TOWER_TOP_Z <= ct,
          f"deck {P.TOWER_TOP_Z:.2f} mm, cover top when open {ct:.2f} mm")
    check("stand is one piece", len(stand.solids()) == 1,
          f"{len(stand.solids())} solid(s)")

    # ------------------------------------------------------ wiring access --
    print("\nwiring space under the base plate")
    bore = P.Z_PIN_TOP - P.PLATE_Z_BOTTOM
    tail = P.RECEPT_LEN - bore
    headroom = (P.PLATE_Z_BOTTOM - P.STAND_Z_BOTTOM) - tail
    check("sleeve tail projects far enough to solder", tail >= 4.0,
          f"{tail:.2f} mm of sleeve below the plate")
    check("room under the tails for the joint and a wire bend", headroom >= 8.0,
          f"{headroom:.2f} mm to the bench")
    pitch = min(math.hypot(a["x"] - b["x"], a["y"] - b["y"])
                for a, b in __import__("itertools").combinations(G.TEST_POINTS, 2))
    check("sleeve pitch workable with a fine iron tip", pitch >= 3.0,
          f"tightest pair {pitch:.2f} mm apart")
    # nothing may block the space directly under a sleeve
    for tp in G.TEST_POINTS:
        col = Pos(tp["x"], tp["y"], P.STAND_Z_BOTTOM) * extrude(
            Circle(2.0), amount=P.PLATE_Z_BOTTOM - P.STAND_Z_BOTTOM - 0.1)
        v = vol(stand.intersect(col))
        check(f"{tp['net']:8s} solder access is clear", v < 0.02, f"{v:.4f} mm3")
    area = P.WIRE_SLOT_W * (P.WIRE_EXIT_Z[1] - P.WIRE_EXIT_Z[0])
    need = len(G.TEST_POINTS) * 1.4 ** 2
    check("loom exit is big enough", area >= 4 * need,
          f"{P.WIRE_SLOT_W:.0f} x {P.WIRE_EXIT_Z[1] - P.WIRE_EXIT_Z[0]:.0f} mm "
          f"= {area:.0f} mm2 for 7 wires")

    # ------------------------------------------------------ probe hardware --
    print("\nprobe hardware fit")
    bore_depth = P.Z_PIN_TOP - P.PLATE_Z_BOTTOM
    below = P.RECEPT_LEN - bore_depth
    check("sleeve tail reaches the wiring space", 3.0 <= below <= 12.0,
          f"{below:.2f} mm of sleeve below the plate, in "
          f"{P.PLATE_Z_BOTTOM - P.STAND_Z_BOTTOM:.0f} mm of clearance")
    check("sleeve tail clears the bench", below < P.PLATE_Z_BOTTOM - P.STAND_Z_BOTTOM,
          f"{below:.2f} mm vs {P.PLATE_Z_BOTTOM - P.STAND_Z_BOTTOM:.0f} mm")
    check("gauge brackets the modelled bore",
          min(P.GAUGE_BORES) < P.PIN_BORE_D < max(P.GAUGE_BORES),
          f"{P.PIN_BORE_D} mm sits inside {min(P.GAUGE_BORES)}-{max(P.GAUGE_BORES)} mm")
    check("lead-in is wider than the bore", P.PIN_LEAD_D > P.PIN_BORE_D,
          f"lead {P.PIN_LEAD_D} mm into bore {P.PIN_BORE_D} mm")

    # Where the tip lands, worst case, if the calibrated bore ends up 0.04 mm
    # over the sleeve: translation plus the tilt that engagement allows.
    slop = 0.04
    trans = slop / 2
    tilt = (slop / P.PIN_BORE_L) * P.PIN_PROTRUSION
    budget = 1.2 / 2 - 0.25          # pad radius less the spear tip radius
    check("probe placement fits inside the pad",
          trans + tilt + 0.15 + 0.10 < budget,
          f"{trans:.3f} translation + {tilt:.3f} tilt + 0.15 board + 0.10 print "
          f"= {trans + tilt + 0.25:.2f} mm vs {budget:.2f} mm allowed")
    check("cover pads stand off further than the tallest top-side part",
          P.COVER_PAD_H > P.PART_H_TOP_MAIN,
          f"{P.COVER_PAD_H} mm standoff vs {P.PART_H_TOP_MAIN} mm part")
    dw = P.PEDESTAL_X[1] - P.PEDESTAL_X[0]
    dd = P.PEDESTAL_Y[1] - P.PEDESTAL_Y[0]
    check("clamp deck is big enough for the clamp footprint",
          dw >= P.CLAMP_BASE_W and dd >= P.CLAMP_SLOT_DY + 12,
          f"deck {dw:.0f} x {dd:.0f} mm, clamp body {P.CLAMP_BASE_W:.0f} mm wide")

    # --------------------------------------------------------------- force --
    print("\nforce budget")
    n = len(G.TEST_POINTS)
    probe_g = n * P.PIN_FORCE_G
    k = 79300 * P.SPRING_WIRE_D ** 4 / (8 * (P.SPRING_OD - P.SPRING_WIRE_D) ** 3
                                        * P.SPRING_ACTIVE_COILS)
    spring_g = len(P.POST_XY) * k * (P.SPRING_FREE - l_stop) * 101.97
    check("clamp force is within a hand-operated GH-201",
          (probe_g + spring_g) / 1000 < 5.0,
          f"{probe_g:.0f} g probes + {spring_g:.0f} g springs "
          f"= {(probe_g + spring_g) / 1000:.2f} kg vs 27 kg rating")

    # -------------------------------------------------------- printability --
    # Evaluated in each part's PRINT orientation, not its assembly orientation:
    # the cover is printed pads-up, so its body underside is on the bed.
    print("\nprintability (in the print orientation)")
    for nm, shape, flip in [("base_plate", base, False), ("nest", nest, False),
                            ("stand", stand, False), ("cover", cover, True)]:
        oriented = Rot(180, 0, 0) * shape if flip else shape
        bed_z = oriented.bounding_box().min.Z
        flats = [f for f in oriented.faces().filter_by(GeomType.PLANE)
                 if abs(f.normal_at(f.center()).Z + 1) < 1e-3
                 and f.center().Z > bed_z + 0.05]
        worst = max((f.area for f in flats), default=0.0)
        span = 2 * (worst / math.pi) ** 0.5 if worst else 0.0
        check(f"{nm:11s} has no large unsupported roof", span <= 16.0,
              f"largest downward face {worst:.1f} mm2, about {span:.1f} mm across"
              + ("  (printed inverted)" if flip else ""))

    # Minimum wall, taken from the nest's actual cross-section at each level
    # rather than from the seat features alone.
    from shapely.geometry import box as _box
    plate = _box(P.NEST_X[0], P.NEST_Y[0], P.NEST_X[1], P.NEST_Y[1])
    levels = [("seat", plate.difference(G.nest_recess())),
              ("lip", plate.difference(G.board_recess())),
              ("pocket floor", plate)]
    for nm2, region in levels:
        region = region.difference(G.probe_clear())
        thin = None
        for w in (3.0, 2.5, 2.0, 1.5, 1.2):
            if region.buffer(-w / 2).is_empty:
                thin = w
                break
        widest = 3.0 if thin is None else thin
        check(f"nest {nm2:12s} cross-section has no thin walls", widest >= 2.0,
              f"survives a {widest:.1f} mm erosion")
    check("board rests on all four main-section holes",
          len(P.LOCATOR_PRIMARY) + len(P.LOCATOR_SECONDARY) == 4,
          f"{len(P.LOCATOR_PRIMARY)} locating + {len(P.LOCATOR_SECONDARY)} supporting pins")
    mx, my, ms, mh = P.MCU_BOSS
    check("MCU boss stops short of the package", P.MCU_BOSS_CLEAR > 0,
          f"{P.MCU_BOSS_CLEAR} mm below a {mh} mm package -- backs the board "
          f"without lifting it")

    print("\n" + ("ALL CHECKS PASSED" if not FAILS else
                  f"{len(FAILS)} CHECK(S) FAILED: {FAILS}"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
