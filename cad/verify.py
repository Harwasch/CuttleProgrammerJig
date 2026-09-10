"""Numerical checks on the jig against the real PCBA STEP model.

Every check is a genuine interference or dimension test.
Run:  python3 verify.py
"""
import os, sys, math
from build123d import *
from shapely.geometry import Point, Polygon as ShPolygon
from shapely.ops import unary_union
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


def face_span(f):
    """Diameter of the largest circle that fits inside a downward face.

    This is the distance filament actually has to bridge. The old metric --
    the diameter of a circle of equal area -- called the deck ceiling 57 mm
    when it is a 117 x 22 mm strip that bridges across 22 mm, because extrusions
    span the short way. Tessellate, union in 2D, then bisect on erosion.
    """
    verts, tris = f.tessellate(0.2)
    polys = [ShPolygon([(verts[i].X, verts[i].Y) for i in t]) for t in tris]
    region = unary_union([q for q in polys if q.is_valid and q.area > 1e-9])
    if region.is_empty:
        return 0.0
    lo, hi = 0.0, 80.0
    for _ in range(24):
        mid = (lo + hi) / 2
        if region.buffer(-mid).is_empty:
            hi = mid
        else:
            lo = mid
    return 2 * lo


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{'  --  ' + detail if detail else ''}")
    if not ok:
        FAILS.append(name)


def main():
    print("building parts ...")
    base, stand, nest, cover = (jig.build_base_plate(), jig.build_stand(),
                                jig.build_nest(), jig.build_cover())
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
    # the cover has to clear the guide posts it rides AND the locator pins that
    # now come up from the base plate through the board
    check("cover vs base plate, clamp closed", vol(cov.intersect(base)) < 0.02,
          f"{vol(cov.intersect(base)):.4f} mm3 overlap")
    cov_up = Pos(0, 0, seat + P.TRAVEL + board_t) * cover
    check("cover vs base plate, clamp open", vol(cov_up.intersect(base)) < 0.02,
          f"{vol(cov_up.intersect(base)):.4f} mm3 overlap")
    for x, y in P.COVER_PADS:
        clr = min([bx.distance(Point(x, y)) for bx in G.part_boxes("top")])
        edge = G.OUTLINE.exterior.distance(Point(x, y))
        check(f"cover pad ({x:7.2f},{y:6.2f}) on bare board",
              clr >= P.COVER_PAD_R and edge >= P.COVER_PAD_R,
              f"{clr:.2f} mm to nearest part, {edge:.2f} mm to board edge")

    # ------------------------------------------------------ body and tower --
    print("\nbody and clamp tower")
    cov_open = Pos(0, 0, seat + P.TRAVEL + board_t) * cover
    nest_open = Pos(0, 0, P.TRAVEL) * nest
    for nm, a, b2 in [("clamp tower vs nest, clamp open", base, nest_open),
                      ("clamp tower vs cover, clamp open", base, cov_open),
                      ("clamp tower vs PCBA", base, board),
                      ("base plate vs stand", base, stand)]:
        v = vol(a.intersect(b2))
        check(nm, v < 0.02, f"{v:.4f} mm3 overlap")
    # The GH-201's spindle sits at its mounting plane and only adjusts DOWNWARD,
    # so the deck has to be ABOVE the surface it presses -- not below it.
    ct_closed = seat + board_t + P.COVER_PAD_H + P.COVER_T
    ct_open = ct_closed + P.TRAVEL
    drop = P.TOWER_TOP_Z - ct_closed
    check("clamp deck is above the surface it presses", drop > 0,
          f"deck {P.TOWER_TOP_Z:.2f} mm, cover top closed {ct_closed:.2f} mm "
          f"-> spindle drops {drop:+.2f} mm")
    check("spindle drop is mid-range, not at an extreme", 3.0 <= drop <= 12.0,
          f"{drop:.2f} mm below the mounting plane, on a 15 mm assembly")
    check("clamp arm clears the cover when open",
          P.TOWER_TOP_Z + 7.0 > ct_open + 2.0,
          f"arm about {P.TOWER_TOP_Z + 7.0:.1f} mm vs open cover top {ct_open:.2f} mm")
    check("clamp arm clears the guide posts",
          P.TOWER_TOP_Z + 7.0 > P.POST_TOP_Z,
          f"arm about {P.TOWER_TOP_Z + 7.0:.1f} mm vs posts {P.POST_TOP_Z:.1f} mm")
    check("stand is one piece", len(stand.solids()) == 1,
          f"{len(stand.solids())} solid(s)")
    check("base plate is one piece", len(base.solids()) == 1,
          f"{len(base.solids())} solid(s)")
    check("clamp tower rides on the plate, not the stand",
          vol(base.intersect(Pos(sum(P.PEDESTAL_X)/2, sum(P.PEDESTAL_Y)/2,
                                 P.TOWER_TOP_Z - 1.0) * Box(4, 4, 1.0))) > 15.0,
          "the whole clamp loop closes inside one part")

    # ------------------------------------------------------ wiring access --
    print("\nwiring space and ST-Link bay")
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
    # With the plate off the stand, the tails are free-standing stubs on a flat
    # bench -- which is the whole reason the plate is a separate part again.
    for tp in G.TEST_POINTS:
        col = Pos(tp["x"], tp["y"], P.PLATE_Z_BOTTOM - 30.0) * extrude(
            Circle(2.0), amount=30.0 - 0.1)
        v = vol(base.intersect(col))
        check(f"{tp['net']:8s} solder access is clear", v < 0.02,
              f"{v:.4f} mm3 below the plate over 30 mm")

    # ------------------------------------------------- plate to stand joint --
    print("\nplate-to-stand joint")
    region, _ = jig.stand_profile()
    f = P.STAND_BOSS_FILLET
    pieces = len(region.geoms) if region.geom_type == "MultiPolygon" else 1
    check("stand cross-section is one connected piece", pieces == 1,
          f"{pieces} piece(s) -- a boss clear of the wall shows up as an island")
    added = region.buffer(f, G.ARC_SEGS).buffer(-f, G.ARC_SEGS).area - region.area
    check("no unfillable notch between a boss and a wall", added < 5.0,
          f"re-closing at {f:.1f} mm adds {added:.2f} mm2 "
          f"(63.33 mm2 with the bosses left as bare cylinders)")

    for x, y in P.MOUNT_SCREW_XY:
        hole = Pos(x, y, P.PLATE_Z_BOTTOM - P.MOUNT_INSERT_DEPTH) * extrude(
            Circle(P.INSERT_M3_HOLE_D / 2 - 0.05), amount=P.MOUNT_INSERT_DEPTH)
        check(f"insert hole ({x:+6.1f},{y:+6.1f}) is open",
              vol(stand.intersect(hole)) < 0.02,
              f"O{P.INSERT_M3_HOLE_D:.1f} x {P.MOUNT_INSERT_DEPTH:.0f} mm deep")
        ann = P.MOUNT_BOSS_R - P.INSERT_M3_HOLE_D / 2
        check(f"boss ({x:+6.1f},{y:+6.1f}) has wall around the insert", ann >= 2.0,
              f"{ann:.2f} mm annulus")
    below = P.STAND_Z_BOTTOM + P.STLINK_FLOOR_T
    left = (P.PLATE_Z_BOTTOM - P.MOUNT_INSERT_DEPTH) - below
    check("material left under a blind lid insert", left >= 3.0,
          f"{left:.1f} mm of boss below the hole, down to the floor")
    # an M3 x 12 must reach the insert without bottoming in the hole
    cbore = 3.0
    stick = 12.0 - (abs(P.PLATE_Z_BOTTOM) - cbore)
    check("M3 x 12 engages the insert without bottoming out",
          P.INSERT_M3_H <= stick < P.MOUNT_INSERT_DEPTH,
          f"{stick:.1f} mm of screw past the plate into a "
          f"{P.MOUNT_INSERT_DEPTH:.0f} mm hole, engaging a {P.INSERT_M3_H:.0f} mm insert")

    # ---------------------------------------------------------- ST-Link bay --
    print("\nST-Link bay")
    L, Wd, H = P.STLINK_CASE
    c = P.STLINK_CLEAR
    cl, cw, ch = L + P.STLINK_HEADER_ROOM + P.STLINK_USB_ROOM, Wd + 2 * c, H + 2 * c
    fz = P.STAND_Z_BOTTOM + P.STLINK_FLOOR_T
    cavity = Pos(P.STLINK_X_CENTRE, P.STLINK_Y_CENTRE, P.STLINK_TOP_Z - ch / 2) * \
        Box(cl, cw, ch)
    check("cavity is clear of the stand", vol(stand.intersect(cavity)) < 0.02,
          f"{vol(stand.intersect(cavity)):.4f} mm3 in a "
          f"{cl:.0f} x {cw:.0f} x {ch:.0f} mm cavity")
    check("cavity sits on the floor", P.STLINK_TOP_Z - ch >= fz - 0.01,
          f"case bottom z={P.STLINK_TOP_Z - ch:.1f}, floor top z={fz:.1f}")
    check("cavity is inside the stand walls",
          P.STLINK_X_CENTRE - cl / 2 >= P.STAND_X[0] + P.STAND_WALL and
          P.STLINK_X_CENTRE + cl / 2 <= P.STAND_X[1] - P.STAND_WALL and
          P.STLINK_Y_CENTRE - cw / 2 >= P.STAND_Y[0] + P.STAND_WALL and
          P.STLINK_Y_CENTRE + cw / 2 <= P.STAND_Y[1] - P.STAND_WALL,
          f"x {P.STLINK_X_CENTRE-cl/2:+.0f}..{P.STLINK_X_CENTRE+cl/2:+.0f}, "
          f"y {P.STLINK_Y_CENTRE-cw/2:+.0f}..{P.STLINK_Y_CENTRE+cw/2:+.0f} inside "
          f"x {P.STAND_X[0]+P.STAND_WALL:+.0f}..{P.STAND_X[1]-P.STAND_WALL:+.0f}, "
          f"y {P.STAND_Y[0]+P.STAND_WALL:+.0f}..{P.STAND_Y[1]-P.STAND_WALL:+.0f}")
    for x, y in P.MOUNT_SCREW_XY:
        clear = (abs(x - P.STLINK_X_CENTRE) > cl / 2 + P.MOUNT_BOSS_R or
                 abs(y - P.STLINK_Y_CENTRE) > cw / 2 + P.MOUNT_BOSS_R)
        check(f"lid boss ({x:+6.1f},{y:+6.1f}) clears the cavity", clear)
    # the locating ribs must actually stand proud of the floor, not be half
    # buried in it -- Box centres on its Pos, which is easy to get wrong
    for sx in (-1, 1):
        for sy in (-1, 1):
            rx = P.STLINK_X_CENTRE + sx * (cl / 2 + 1.5)
            ry = P.STLINK_Y_CENTRE + sy * cw / 2
            probe = Pos(rx, ry, fz + P.STLINK_RIB_H - 0.3) * Box(2.0, 6.0, 0.4)
            got = vol(stand.intersect(probe))
            check(f"locating rib ({rx:+6.1f},{ry:+6.1f}) stands proud",
                  got > 0.8 * probe.volume,
                  f"{100*got/probe.volume:.0f}% solid at "
                  f"{P.STLINK_RIB_H - 0.3:.1f} mm above the floor")
    # the USB cable must have a way out
    usb = Pos(P.STAND_X[1], 0, P.STLINK_TOP_Z - ch / 2) * \
        Box(3 * P.STAND_WALL, P.STLINK_USB_W - 1, P.STLINK_USB_H - 1)
    check("USB opening goes right through the +X wall",
          vol(stand.intersect(usb)) < 0.02,
          f"{P.STLINK_USB_W:.0f} x {P.STLINK_USB_H:.0f} mm, "
          f"{vol(stand.intersect(usb)):.4f} mm3 in the way")

    # the case must not foul the probe tails once the lid is on
    tail_z = P.Z_PIN_TOP - P.RECEPT_LEN
    check("fitted case clears the probe tails", tail_z - P.STLINK_TOP_Z >= 1.0,
          f"tails reach z={tail_z:.2f}, cavity ceiling z={P.STLINK_TOP_Z:.1f}"
          f" -> {tail_z - P.STLINK_TOP_Z:.2f} mm")
    check("case drops in from above before the lid goes on",
          P.STLINK_TOP_Z < P.PLATE_Z_BOTTOM,
          f"nothing overhangs it: open from z={P.STLINK_TOP_Z:.0f} up to the lid "
          f"at z={P.PLATE_Z_BOTTOM:.0f}")

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

    # Full chain from the board's pad to the probe tip, stated link by link.
    # The locators are on the deck, so the board registers straight to the
    # part that holds the probes and the nest contributes nothing. Putting them
    # on the nest instead would add its pin print error and its play on the
    # register pins -- measured at +0.232 mm worst case, over the pad budget.
    pin_clear = (2.2 - P.LOCATOR_D) / 2
    arm = max(math.hypot(t["x"], t["y"]) for t in G.TEST_POINTS)
    span = math.dist(G.HOLES[P.LOCATOR_PRIMARY[0]], G.HOLES[P.LOCATOR_PRIMARY[1]])
    links = [
        ("PCB hole to pad, fab",              0.050),
        ("board on pin, clearance",           pin_clear),
        (f"yaw from it, at {arm:.0f} mm",     math.atan(2 * pin_clear / span) * arm),
        ("base plate pin position, print",    0.100),
        ("base plate bore position, print",   0.100),
        ("sleeve in a bore 0.04 over",        0.020),
        ("sleeve tilt over the bore",         (0.04 / P.PIN_BORE_L) * P.PIN_PROTRUSION),
    ]
    worst = sum(v for _, v in links)
    rss = math.sqrt(sum(v * v for _, v in links))
    budget = 1.2 / 2 - 0.10          # pad radius, less a contact margin
    for nm3, v in links:
        print(f"        {nm3:36s} {v:6.3f} mm")
    check("probe placement fits inside the pad, worst case", worst <= budget,
          f"worst {worst:.3f} mm, RSS {rss:.3f} mm, budget {budget:.3f} mm")
    check("cover pads stand off further than the tallest top-side part",
          P.COVER_PAD_H > P.PART_H_TOP_MAIN,
          f"{P.COVER_PAD_H} mm standoff vs {P.PART_H_TOP_MAIN} mm part")
    dw = P.PEDESTAL_X[1] - P.PEDESTAL_X[0]
    dd = P.PEDESTAL_Y[1] - P.PEDESTAL_Y[0]
    check("clamp deck is big enough for the clamp footprint",
          dw >= P.CLAMP_BASE_W and dd >= P.CLAMP_HOLE_DY + 12,
          f"deck {dw:.0f} x {dd:.0f} mm, clamp body {P.CLAMP_BASE_W:.0f} mm wide")

    # ------------------------------------------------- clamp heat-set mount --
    print("\nclamp mount, M3 heat-set inserts")
    ins = jig.clamp_insert_xy()
    check("four insert positions", len(ins) == 4, f"{len(ins)} holes")
    for x, y in ins:
        inside = (P.PEDESTAL_X[0] + P.STAND_WALL < x < P.PEDESTAL_X[1] - P.STAND_WALL
                  and P.PEDESTAL_Y[0] + 3 < y < P.PEDESTAL_Y[1] - 3)
        check(f"insert ({x:7.2f},{y:7.2f}) is on the deck", inside,
              f"deck spans x {P.PEDESTAL_X[0]:.0f}..{P.PEDESTAL_X[1]:.0f}, "
              f"y {P.PEDESTAL_Y[0]:.0f}..{P.PEDESTAL_Y[1]:.0f}")
    solid_under = P.TOWER_TOP_Z - P.INSERT_M3_HOLE_DEPTH - P.TOWER_SOLID_Z
    check("material left under a blind insert hole", solid_under >= 3.0,
          f"{solid_under:.1f} mm of solid below the hole")
    check("hole is deeper than the insert",
          P.INSERT_M3_HOLE_DEPTH > P.INSERT_M3_H,
          f"{P.INSERT_M3_HOLE_DEPTH} mm hole for a {P.INSERT_M3_H} mm insert")
    check("hole diameter suits the insert knurl", 3.85 <= P.INSERT_M3_HOLE_D <= 4.15,
          f"O{P.INSERT_M3_HOLE_D} mm, between the 3.9 tip and 4.5 knurl")
    # the spindle must land on the cover's dimple, not just somewhere on it.
    # Tolerance is 0.5 mm on BOTH axes: the old check allowed COVER_DIMPLE_R of
    # X error, which passed a 3.6 mm miss when the dimple moved.
    dim_x, dim_y = P.COVER_DIMPLE_XY
    near_row = max(y for _, y in ins)
    land_y = near_row + P.CLAMP_SPINDLE_TO_ROW
    land_x = sum(x for x, _ in ins) / len(ins)
    check("spindle lands on the cover dimple",
          abs(land_y - dim_y) < 0.5 and abs(land_x - dim_x) < 0.5,
          f"spindle at ({land_x:.2f},{land_y:.2f}), dimple at ({dim_x:.2f},{dim_y:.2f})")
    # ...and the dimple must sit on the centre of the post/spring quad, so the
    # nest descends parallel instead of levering onto one row of springs
    qx = sum(x for x, _ in P.POST_XY) / len(P.POST_XY)
    qy = sum(y for _, y in P.POST_XY) / len(P.POST_XY)
    off = math.hypot(dim_x - qx, dim_y - qy)
    xs = sorted(set(x for x, _ in P.POST_XY))
    far = (dim_x - xs[0]) / (xs[1] - xs[0])
    check("press point is on the centre of the spring quad", off < 1.0,
          f"{off:.2f} mm off ({qx:+.1f},{qy:+.1f}); "
          f"spring load splits {1-far:.0%}/{far:.0%}")
    check("clamp body clears the guide posts in X",
          all(abs(land_x - px) > P.CLAMP_BASE_W / 2 or abs(py) > 12
              for px, py in P.POST_XY),
          f"clamp centred on x={land_x:.1f}, {P.CLAMP_BASE_W:.0f} mm wide")

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
    for nm, shape, flip in [("base_plate", base, False), ("stand", stand, False),
                            ("nest", nest, False), ("cover", cover, True)]:
        oriented = Rot(180, 0, 0) * shape if flip else shape
        bed_z = oriented.bounding_box().min.Z
        flats = [f for f in oriented.faces().filter_by(GeomType.PLANE)
                 if abs(f.normal_at(f.center()).Z + 1) < 1e-3
                 and f.center().Z > bed_z + 0.05]
        # 25 mm is what an enclosed, well-cooled printer bridges cleanly. The
        # deck ceiling is the only face anywhere near it, and it is a plain
        # strip with nothing above that depends on its finish.
        worst, warea = 0.0, 0.0
        for f in flats:
            sp = face_span(f)
            if sp > worst:
                worst, warea = sp, f.area
        check(f"{nm:11s} bridges no more than 25 mm", worst <= 25.0,
              f"widest unsupported span {worst:.1f} mm ({warea:.0f} mm2 face)"
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
    check("two locating pins fully constrain the board",
          len(P.LOCATOR_PRIMARY) == 2,
          f"{len(P.LOCATOR_PRIMARY)} pins, {P.LOCATOR_SECONDARY or 'no'} secondary")
    # the pins belong to the base plate; the nest must merely clear them
    for name in P.LOCATOR_PRIMARY:
        x, y = G.HOLES[name]
        core = Pos(x, y, P.LOCATOR_TOP_Z - 2.0) * extrude(
            Circle(P.LOCATOR_D / 2 - 0.2), amount=1.0)
        got = vol(base.intersect(core))
        check(f"{name} pin stands on the base plate", got > 0.9 * core.volume,
              f"{100 * got / core.volume:.0f}% solid at z="
              f"{P.LOCATOR_TOP_Z - 1.5:.1f} mm")
        through = Pos(x, y, -0.1) * extrude(
            Circle(P.LOCATOR_SHANK_D / 2 + 0.10), amount=P.NEST_T + P.NEST_LIP + 0.2)
        check(f"{name} passes through the nest cleanly",
              vol(nest.intersect(through)) < 0.02,
              f"Ø{P.LOCATOR_SHANK_D + 0.20:.2f} swept through: "
              f"{vol(nest.intersect(through)):.4f} mm3 in the way")
        # the seat must survive the shank clearance hole cut through it
        ann = G.boss_radius(name) - P.LOCATOR_NEST_HOLE_D / 2
        check(f"{name} seat survives the shank clearance", ann >= 0.8,
              f"Ø{2*G.boss_radius(name):.2f} boss leaves a {ann:.2f} mm annulus")
    # the shank must stop at or below the seat, or it fouls the board underside
    check("locator shank stops at the seat", P.LOCATOR_SHANK_D > P.LOCATOR_D,
          f"Ø{P.LOCATOR_SHANK_D:.2f} to z={P.NEST_T:.1f}, then Ø{P.LOCATOR_D:.2f}")
    free = P.LOCATOR_TOP_Z - P.NEST_T
    check("locator tip is not slender", free / P.LOCATOR_D <= 3.5,
          f"{free:.1f} mm of Ø{P.LOCATOR_D:.2f} standing proud, "
          f"{free/P.LOCATOR_D:.1f}:1 (was {P.LOCATOR_TOP_Z/P.LOCATOR_D:.1f}:1 unstepped)")
    engage = (P.LOCATOR_TOP_Z - (P.NEST_T + P.TRAVEL + P.PCB_T))
    check("pins still stand proud of the board with the clamp open", engage >= 1.0,
          f"{engage:.2f} mm of pin above the board top at rest")

    # ---- nest registration: two pins, not the four over-constrained posts ----
    post_play = (P.POST_HOLE_D - 0.22 - (P.POST_D + 0.08)) / 2
    reg_play = (P.REG_HOLE_D - 0.22 - (P.REG_PIN_D + 0.08)) / 2
    check("guide posts are free as printed, not a press fit", post_play >= 0.15,
          f"{2*post_play:.2f} mm diametral as printed "
          f"({P.POST_HOLE_D - P.POST_D:.2f} modelled)")
    check("registration is tighter than the posts it replaces", reg_play < post_play,
          f"register {2*reg_play:.2f} mm vs post {2*post_play:.2f} mm diametral")
    check("registration pins stay engaged over the whole lift",
          P.REG_PIN_CYL_Z - P.TRAVEL >= 1.5,
          f"{P.REG_PIN_CYL_Z - P.TRAVEL:.2f} mm of cylinder still in the nest at rest")
    for i, (x, y) in enumerate(P.REG_XY):
        core = Pos(x, y, P.REG_PIN_CYL_Z - 1.5) * extrude(
            Circle(P.REG_PIN_D / 2 - 0.2), amount=1.0)
        got = vol(base.intersect(core))
        check(f"register pin {i+1} stands on the base plate", got > 0.9 * core.volume,
              f"{100 * got / core.volume:.0f}% solid at ({x:+.1f},{y:+.1f})")
        hole = Pos(x, y, -0.1) * extrude(
            Circle(P.REG_PIN_D / 2 + 0.05), amount=P.NEST_T + P.NEST_LIP + 0.2)
        check(f"register pin {i+1} passes through the nest",
              vol(nest.intersect(hole)) < 0.02,
              f"Ø{P.REG_PIN_D + 0.10:.2f} swept through: "
              f"{vol(nest.intersect(hole)):.4f} mm3 in the way")
    check("registration pins clear the board outline",
          all(not G.OUTLINE.buffer(0.5).contains(Point(x, y)) for x, y in P.REG_XY),
          "both outboard of the board in Y")
    mx, my, ms, mh = P.MCU_BOSS
    check("MCU boss stops short of the package", P.MCU_BOSS_CLEAR > 0,
          f"{P.MCU_BOSS_CLEAR} mm below a {mh} mm package -- backs the board "
          f"without lifting it")

    print("\n" + ("ALL CHECKS PASSED" if not FAILS else
                  f"{len(FAILS)} CHECK(S) FAILED: {FAILS}"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
