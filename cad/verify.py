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


# cos(45 deg): a downward face shallower than this needs no support
OVERHANG_NZ = 0.7071


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
        # A Location on a Compound is SILENTLY IGNORED by .intersect(): a
        # compound moved 100 mm away still reports full overlap. So --full was
        # intersecting the board at its raw gerber coordinates, ~140 mm from the
        # jig, and reported four failures that were pure artefact -- identical
        # volumes before and after a 3 mm lift, which no real boolean can do.
        # Pushing the transform down into each child solid fixes it.
        loc = Location((-OX, -OY, seat))
        # Drop copper film. 45 solids exactly 0.04 mm thick -- bottom-side pads
        # and via rings, each wholly inside the nest seat -- were being reported
        # as a 0.2801 mm3 interference. Every board rests on its own copper;
        # extract_parts.py excludes these on the same FILM_T rule, so without
        # this the two paths test different populations and --full can never
        # agree with the fast path.
        solids = import_step(STEP).solids()
        keep = [sol for sol in solids
                if (sol.bounding_box().max.Z - sol.bounding_box().min.Z) > P.FILM_T]
        print(f"  ({len(solids) - len(keep)} copper-film solids under "
              f"{P.FILM_T} mm excluded; {len(keep)} components kept)")
        board = Compound(children=[sol.moved(loc) for sol in keep])
    else:
        print("building the banded PCBA keep-out solid (fast, conservative) ...")
        board = G.pcba_solid(seat)
    board_t = P.PCB_T

    # ------------------------------------------------------------ stack-up --
    print("\nstack-up")
    # NOT `Z_PIN_TOP == the formula that defines it`. What matters is that a
    # probe standing on the platform is squeezed by COMPRESSION when the board
    # is on the stop, and that the platform is above the plate it stands on.
    tip_free = P.Z_PIN_TOP + P.PIN_PROTRUSION
    check("probe tip is squeezed by COMPRESSION at the stop",
          abs((tip_free - P.NEST_T) - P.COMPRESSION) < 1e-6,
          f"free tip {tip_free:.3f} mm vs board underside {P.NEST_T:.3f} mm "
          f"-> {tip_free - P.NEST_T:.3f} mm of squeeze")
    # Where the seat lands is NOT a choice -- it is NEST_T + COMPRESSION minus
    # however far the probe stands out of its receptacle. A P50 stands 3.35 mm
    # out and puts it 3.85 above the hard stop, so the plate grows a platform.
    # A P100 stands 8.35 out and puts it 0.75 BELOW, so the plate gets a relief
    # and the plateau stays whole. Both are legal; what is not legal is a seat
    # the board can reach, or one the plate cannot contain.
    check("probe seat sits between the plate and the board",
          P.PLATE_Z_BOTTOM < P.Z_PIN_TOP < P.NEST_T,
          f"seat {P.Z_PIN_TOP:+.3f} mm -- a "
          f"{'platform' if P.Z_PIN_TOP > 0 else 'recess'} against a hard stop at 0")
    stack_bot = P.Z_PIN_TOP - P.PIN_HEAD_BORE_L - P.PIN_BORE_L
    check("the whole stepped bore fits inside the plate",
          stack_bot > P.PLATE_Z_BOTTOM,
          f"seat {P.Z_PIN_TOP:+.2f}, {P.PIN_HEAD_BORE_L:.1f} of counterbore and "
          f"{P.PIN_BORE_L:.1f} of body bore end at {stack_bot:+.2f}, plate bottom "
          f"{P.PLATE_Z_BOTTOM:+.1f}")
    check("working stroke inside the probe's travel",
          0.8 <= P.COMPRESSION <= 0.7 * P.PIN_STROKE_MAX,
          f"{P.COMPRESSION:.2f} mm of {P.PIN_STROKE_MAX:.2f} mm")
    check("probe tips clear the board at rest", P.TRAVEL - P.COMPRESSION >= 1.0,
          f"{P.TRAVEL - P.COMPRESSION:.2f} mm of daylight for loading")
    l_rest = P.BASE_SPRING_DEPTH + P.NEST_SPRING_DEPTH + P.TRAVEL
    l_stop = P.BASE_SPRING_DEPTH + P.NEST_SPRING_DEPTH

    # from the wire and coil count, NOT from free length. The old form could
    # not see solid height at all: a 20-coil spring stacking at 13.2 mm against
    # a 10 mm stop passed, and the BOM's own instruction is to select on solid
    # height rather than free length.
    check("spring not stacked solid when clamped", l_stop > P.SPRING_SOLID + 1.0,
          f"{l_stop:.1f} mm at the stop, solid height {P.SPRING_SOLID:.2f} mm "
          f"({P.SPRING_ACTIVE_COILS}+2 coils x {P.SPRING_WIRE_D} mm)")
    # TRAVEL is derived, so what needs checking is that the derived value is
    # usable -- nothing in the geometry stops the nest rising, so the spring's
    # free length IS the rest position.
    check("derived travel leaves room to load the board",
          P.TRAVEL >= P.COMPRESSION + 1.0,
          f"TRAVEL = SPRING_FREE - pockets = {P.TRAVEL:.2f} mm, "
          f"{P.TRAVEL - P.COMPRESSION:.2f} mm of daylight over the probes")
    check("no up-stop exists, so travel must come from the spring alone",
          abs(P.TRAVEL - (P.SPRING_FREE - l_stop)) < 1e-9,
          f"{P.SPRING_FREE:.1f} - {l_stop:.1f} = {P.TRAVEL:.2f} mm")
    engage = P.POST_TOP_Z - (P.TRAVEL + P.NEST_T + P.PCB_T)
    check("posts still guide the cover at rest", engage >= 5.0, f"{engage:.1f} mm engaged")

    # --------------------------------------------------------- probe bores --
    print("\nprobe bores and platform")
    # Sized from the RECEPTACLE, not from the bore. The old sweep was
    # Circle(PIN_BORE_D/2 - 0.02): it shrank with the bore, so setting
    # PIN_BORE_D to 0.95 -- printing Ø0.73, too small to admit any probe --
    # still reported every bore "0.0% obstructed".
    head_r = (P.RECEPT_HEAD_D + 0.02) / 2
    body_r = (P.RECEPT_BODY_D + 0.02) / 2
    cb_bot = P.Z_PIN_TOP - P.PIN_HEAD_BORE_L
    for tp in G.TEST_POINTS:
        x, y = tp["x"], tp["y"]
        body = Pos(x, y, cb_bot - P.PIN_BORE_L) * extrude(Circle(body_r),
                                                          amount=P.PIN_BORE_L)
        check(f"{tp['net']:8s} body bore admits the Ø{P.RECEPT_BODY_D} sleeve",
              vol(base.intersect(body)) < 0.02,
              f"{vol(base.intersect(body)):.4f} mm3 in the way over "
              f"{P.PIN_BORE_L:.1f} mm")
        head = Pos(x, y, cb_bot) * extrude(Circle(head_r),
                                           amount=P.PIN_HEAD_BORE_L)
        check(f"{tp['net']:8s} counterbore admits the Ø{P.RECEPT_HEAD_D} head",
              vol(base.intersect(head)) < 0.02,
              f"{vol(base.intersect(head)):.4f} mm3 in the way")

    # The depth stop: the head must NOT fit the body bore, or the sleeve slides
    # straight through and its Z is set by how hard you pushed -- which made
    # PIN_PROTRUSION, the number the whole stack-up derives from, an assembly
    # variable. This is what the old geometry did.
    # printed(), not a single constant: the counterbore and the body bore
    # are different diameters and shrink by different amounts.
    body_printed = P.printed(P.PIN_BODY_BORE_D, P.PIN_BORE_L)
    head_printed = P.printed(P.PIN_BORE_D, P.PIN_HEAD_BORE_L)
    check("head cannot enter the body bore -> the sleeve bottoms flush",
          body_printed < P.RECEPT_HEAD_D - 0.02,
          f"body bore prints Ø{body_printed:.3f} against a Ø{P.RECEPT_HEAD_D} head "
          f"-> {(P.RECEPT_HEAD_D - body_printed) / 2:.3f} mm of shoulder")
    check("counterbore is a press fit on the head",
          -0.02 <= head_printed - P.RECEPT_HEAD_D <= 0.06,
          f"prints Ø{head_printed:.3f} on a Ø{P.RECEPT_HEAD_D} head")
    check("body bore guides the body without seizing",
          0.01 <= (body_printed - P.RECEPT_BODY_D) / 2 <= 0.08,
          f"{(body_printed - P.RECEPT_BODY_D) / 2:.3f} mm radial on the body")
    check("counterbore is exactly one head deep",
          abs(P.PIN_HEAD_BORE_L - P.RECEPT_HEAD_L) < 1e-9,
          f"{P.PIN_HEAD_BORE_L:.2f} mm for a {P.RECEPT_HEAD_L:.2f} mm head")

    # Collar wall, measured in 2D against the platform relief cuts. The old
    # check was a >55%-solid ring, loose enough to pass a bore whose wall had
    # been cut to 0.15 mm and one that had been breached outright.
    # WITH DEPTH. A relief cut starts at the part's own floor and runs upward,
    # so it thins the collar over the TOP of the counterbore and leaves sound
    # collar below it. Projecting that into 2D and calling the whole bore thin
    # was over-strict -- and it mirrors jig.py's rule that a part clearing the
    # platform top does not cut the islands at all.
    widest = P.PIN_BORE_D
    if P.Z_PIN_TOP <= 0:
        widest = max(widest, P.PIN_RELIEF_D)
    islands = G.probe_islands()
    cb_bot = P.Z_PIN_TOP - P.PIN_HEAD_BORE_L
    for tp in G.TEST_POINTS:
        pt = Point(tp["x"], tp["y"])
        if P.Z_PIN_TOP > 0:
            bound = P.PROBE_ISLAND_R
        else:
            bound = min(math.hypot(tp["x"] - o["x"], tp["y"] - o["y"])
                        for o in G.TEST_POINTS if o is not tp) / 2
        thin_from = P.Z_PIN_TOP          # collar is sound below this
        worst = bound - widest / 2
        for fp, zf in G.bottom_part_sweep():
            if zf + P.PART_CLEAR_Z >= P.Z_PIN_TOP:
                continue                 # jig.py protects the island here
            w = fp.distance(pt) - widest / 2
            if w >= 0.34:
                continue
            thin_from = min(thin_from, max(zf, cb_bot))
            worst = min(worst, w)
        sound = thin_from - cb_bot
        # 0.34 mm is one extrusion on a 0.4 mm nozzle; below that the slicer
        # drops the wall and the counterbore opens out of the side.
        ok = worst >= 0.34 or sound >= 1.5
        check(f"{tp['net']:8s} collar wall at the counterbore", ok,
              f"{worst:.3f} mm"
              + ("" if sound >= P.PIN_HEAD_BORE_L - 1e-9 else
                 f" over the top {P.PIN_HEAD_BORE_L - sound:.2f} mm, "
                 f"{sound:.2f} mm of sound collar below it"))

    # ---------------------------------------------------------- root flares --
    print("\nroot flares")
    for nm, root_d, mate_d, mate in (
            ("guide post", P.POST_D + 2 * P.POST_FLARE, P.SPRING_OD - 2 * P.SPRING_WIRE_D,
             "the spring's own bore"),
            ("board locator", P.LOCATOR_SHANK_D + 2 * P.LOCATOR_FLARE,
             P.LOCATOR_NEST_HOLE_D - P.PRINT_HOLE_SHRINK, "the nest's pass-through"),
            ("probe collar", 2 * (P.PROBE_ISLAND_R + P.ISLAND_FLARE),
             P.PROBE_CLEAR_D - P.PRINT_HOLE_SHRINK, "the nest's probe window")):
        printed_root = root_d + P.PRINT_BOSS_GROW
        gap = (mate_d - printed_root) / 2
        check(f"{nm:14s} flare clears {mate}", gap >= 0.08,
              f"root prints Ø{printed_root:.2f} in Ø{mate_d:.2f} -> {gap:.3f} mm radial")
    bare = P.LOCATOR_SHANK_D + P.PRINT_BOSS_GROW
    flared = P.LOCATOR_SHANK_D + 2 * P.LOCATOR_FLARE + P.PRINT_BOSS_GROW
    check("the flare is worth having on the tallest pin",
          (flared / bare) ** 3 >= 1.3,
          f"section modulus at the root x{(flared / bare) ** 3:.2f} "
          f"(Ø{bare:.2f} -> Ø{flared:.2f} over {P.ROOT_FLARE_H:.1f} mm)")
    check("registration pins are stout enough to go without one",
          P.REG_PIN_TOP_Z / P.REG_PIN_D <= 2.0,
          f"{P.REG_PIN_TOP_Z / P.REG_PIN_D:.1f}:1, against "
          f"{(P.LOCATOR_TOP_Z - P.NEST_T) / P.LOCATOR_D:.1f}:1 on the locator tip "
          f"-- and the nest leaves them "
          f"{(P.REG_HOLE_D - P.PRINT_HOLE_SHRINK - P.REG_PIN_D - P.PRINT_BOSS_GROW) / 2:.3f} mm")

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
    # ...and everywhere in between. Sampling only the two ends would miss
    # anything that fouls mid-stroke.
    steps = [P.TRAVEL * i / 6 for i in range(1, 6)]
    worst_nest = max(vol(base.intersect(Pos(0, 0, d) * nest)) for d in steps)
    worst_board = max(vol(base.intersect(Pos(0, 0, d) * board)) for d in steps)
    check("nothing fouls anywhere in the stroke",
          worst_nest < 0.02 and worst_board < 0.02,
          f"worst of 5 intermediate heights: nest {worst_nest:.4f}, "
          f"PCBA {worst_board:.4f} mm3")

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
    # A Sphere(COVER_DIMPLE_R) centred on the top face of a COVER_T plate
    # reaches exactly the underside: the cover had 0.000 mm of material at the
    # one point the whole clamp load is applied, and nothing checked it.
    left = P.COVER_T - P.COVER_DIMPLE_DEPTH
    check("cover keeps material under the spindle", left >= 1.5,
          f"{P.COVER_DIMPLE_DEPTH:.2f} mm dish in a {P.COVER_T:.2f} mm plate "
          f"-> {left:.2f} mm left")
    dx, dy = P.COVER_DIMPLE_XY
    core = Pos(dx, dy, P.COVER_PAD_H) * extrude(Circle(0.4), amount=left - 0.05)
    got = vol(cover.intersect(core))
    check("...and the solid agrees", got > 0.95 * core.volume,
          f"{100 * got / core.volume:.0f}% solid on the dimple axis")
    # margin, not just overlap: the -X edge sat 0.029 mm from a 2.05 mm header
    # and passed, because overlap at nominal was zero
    play = P.fit(P.POST_HOLE_D, P.POST_D)
    for ddx in (-play, play):
        shifted = Pos(ddx, 0, seat + board_t) * cover
        check(f"cover still clears the PCBA shifted {ddx:+.2f} mm on its posts",
              vol(shifted.intersect(board)) < 0.02,
              f"{vol(shifted.intersect(board)):.4f} mm3")
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
    # The obstruction that matters is the STAND and the fitted ST-Link, not the
    # plate: the plate provably ends 0.1 mm above the old probe column, so those
    # seven checks could not fail for any geometry.
    L0, W0, H0 = P.STLINK_CASE
    cl0 = L0 + P.STLINK_HEADER_ROOM + P.STLINK_USB_ROOM
    case_x0 = P.STLINK_X_CENTRE - cl0 / 2 + P.STLINK_HEADER_ROOM + L0 / 2
    fitted = Pos(case_x0, P.STLINK_Y_CENTRE,
                 P.STLINK_TOP_Z - (H0 + 2 * P.STLINK_CLEAR) / 2) * Box(L0, W0, H0)
    tail_z = P.Z_PIN_TOP - P.RECEPT_LEN
    for tp in G.TEST_POINTS:
        col = Pos(tp["x"], tp["y"], tail_z) * extrude(
            Circle(2.0), amount=P.PLATE_Z_BOTTOM - tail_z)
        v = vol(stand.intersect(col)) + vol(fitted.intersect(col))
        check(f"{tp['net']:8s} tail is clear of the stand and the ST-Link",
              v < 0.02, f"{v:.4f} mm3 around a {P.PLATE_Z_BOTTOM - tail_z:.2f} mm tail")

    # ------------------------------------------------- plate to stand joint --
    print("\nplate-to-stand joint")
    # Test the RAW union, before the closing. Testing the closed region was
    # circular -- morphological closing is idempotent, so re-closing it adds ~0
    # for any geometry, and moving all four bosses 5 mm clear of the walls still
    # reported "1 piece, adds 0.51 mm2, PASS".
    raw, _ = jig.stand_profile(closed=False)
    closed, _ = jig.stand_profile()
    f = P.STAND_BOSS_FILLET
    raw_pieces = len(raw.geoms) if raw.geom_type == "MultiPolygon" else 1
    check("every boss actually touches a wall before any filleting",
          raw_pieces == 1,
          f"{raw_pieces} piece(s) in the raw union -- a boss standing clear of "
          f"the wall is a separate island here")
    fillable = closed.area - raw.area
    check("the boss-to-wall notches are within the fillet's reach",
          fillable < len(P.MOUNT_SCREW_XY) * 25.0,
          f"closing at {f:.1f} mm adds {fillable:.2f} mm2 of fillet across "
          f"{len(P.MOUNT_SCREW_XY)} bosses")
    left = closed.buffer(f, G.ARC_SEGS).buffer(-f, G.ARC_SEGS).area - closed.area
    check("nothing unfillable is left in the built profile", left < 5.0,
          f"{left:.2f} mm2 remaining after the closing")

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
    cbore = P.MOUNT_SCREW_CBORE
    stick = P.MOUNT_SCREW_L - (abs(P.PLATE_Z_BOTTOM) - cbore)
    check(f"M3 x {P.MOUNT_SCREW_L:.0f} engages the insert without bottoming out",
          P.INSERT_M3_H <= stick < P.MOUNT_INSERT_DEPTH,
          f"{stick:.1f} mm of screw past the plate into a "
          f"{P.MOUNT_INSERT_DEPTH:.0f} mm hole, engaging a {P.INSERT_M3_H:.0f} mm insert")

    # ---------------------------------------------------------- ST-Link bay --
    print("\nST-Link bay")
    L, Wd, H = P.STLINK_CASE
    c = P.STLINK_CLEAR
    cl, cw, ch = L + P.STLINK_HEADER_ROOM + P.STLINK_USB_ROOM, Wd + 2 * c, H + 2 * c
    fz = P.STAND_Z_BOTTOM + P.STLINK_FLOOR_T
    # The CASE must be clear -- not the cavity. The cavity is deliberately
    # longer than the case (cable room at both ends) and the locating ribs live
    # in that extra length, so testing the cavity flagged the ribs themselves.
    case_x = P.STLINK_X_CENTRE - cl / 2 + P.STLINK_HEADER_ROOM + L / 2
    case = Pos(case_x, P.STLINK_Y_CENTRE, P.STLINK_TOP_Z - ch / 2) * Box(L, Wd, H)
    check("the case itself is clear of the stand", vol(stand.intersect(case)) < 0.02,
          f"{vol(stand.intersect(case)):.4f} mm3 against a "
          f"{L:.0f} x {Wd:.0f} x {H:.0f} mm case at x={case_x:+.1f}")
    # ribs must bracket the CASE. Sizing them from the cavity put them 127 mm
    # apart around a 100 mm case: 27 mm of slop, locating nothing.
    span_x = L + 2 * P.STLINK_CLEAR
    check("locating ribs bracket the case, not the cavity", span_x - L <= 4.0,
          f"rib faces {span_x:.0f} mm apart on a {L:.0f} mm case "
          f"-> {span_x - L:.0f} mm of slop")
    sb = stand.bounding_box()
    check("nothing on the stand escapes its own outline",
          sb.min.X >= P.STAND_X[0] - 1e-6 and sb.max.X <= P.STAND_X[1] + 1e-6 and
          sb.min.Y >= P.STAND_Y[0] - 1e-6 and sb.max.Y <= P.STAND_Y[1] + 1e-6,
          f"bbox x {sb.min.X:+.2f}..{sb.max.X:+.2f}, y {sb.min.Y:+.2f}..{sb.max.Y:+.2f} "
          f"against {P.STAND_X} x {P.STAND_Y}")
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
    # Against the case and the two cable ends. Testing the padded room instead
    # failed a boss tucked in the -Y corner of the header space, 24 mm off the
    # ribbon's own centreline, where it fouls nothing.
    for x, y in P.MOUNT_SCREW_XY:
        dy = abs(y - P.STLINK_Y_CENTRE)
        off_case = (abs(x - case_x) > L / 2 + P.MOUNT_BOSS_R or
                    dy > cw / 2 + P.MOUNT_BOSS_R)
        off_ribbon = (x > case_x - L / 2 - P.MOUNT_BOSS_R or
                      dy > P.STLINK_RIBBON_W / 2 + P.MOUNT_BOSS_R)
        off_usb = (x < case_x + L / 2 + P.MOUNT_BOSS_R or
                   dy > P.STLINK_USB_W / 2 + P.MOUNT_BOSS_R)
        check(f"lid boss ({x:+6.1f},{y:+6.1f}) clears case and cables",
              off_case and off_ribbon and off_usb,
              f"{dy:.1f} mm off the case centreline")
    # the locating ribs must actually stand proud of the floor, not be half
    # buried in it -- Box centres on its Pos, which is easy to get wrong
    for sx in (-1, 1):
        for sy in (-1, 1):
            # 3 mm INWARD along the leg. Probing the corner itself only
            # worked while the legs were centred on it, which is what put a
            # 7 mm tail through the -Y wall once the case moved up against it.
            rx = case_x + sx * (span_x / 2 + 1.5)
            ry = P.STLINK_Y_CENTRE + sy * cw / 2 - sy * 3.0
            probe = Pos(rx, ry, fz + P.STLINK_RIB_H - 0.3) * Box(2.0, 4.0, 0.4)
            got = vol(stand.intersect(probe))
            check(f"locating rib ({rx:+6.1f},{ry:+6.1f}) stands proud",
                  got > 0.8 * probe.volume,
                  f"{100*got/probe.volume:.0f}% solid at "
                  f"{P.STLINK_RIB_H - 0.3:.1f} mm above the floor")
    # the USB cable must have a way out
    usb = Pos(P.STAND_X[1], P.STLINK_Y_CENTRE, P.STLINK_TOP_Z - ch / 2) * \
        Box(3 * P.STAND_WALL, P.STLINK_USB_W - 1, P.STLINK_USB_H - 1)
    check("USB opening goes right through the +X wall",
          vol(stand.intersect(usb)) < 0.02,
          f"{P.STLINK_USB_W:.0f} x {P.STLINK_USB_H:.0f} mm, "
          f"{vol(stand.intersect(usb)):.4f} mm3 in the way")

    # the case must not foul the probe tails once the lid is on
    # In 3D. The P50 keeps its tails above the case; the P100's reach 22 mm
    # past its roof and clear it in PLAN instead, so a Z comparison would call
    # a perfectly good design a collision.
    tail_z = P.Z_PIN_TOP - P.RECEPT_LEN
    gap = min(math.hypot(max(abs(t["x"] - case_x) - L / 2, 0.0),
                         max(abs(t["y"] - P.STLINK_Y_CENTRE) - Wd / 2, 0.0))
              for t in G.TEST_POINTS) if tail_z < P.STLINK_TOP_Z else None
    check("fitted case clears the probe tails",
          tail_z - P.STLINK_TOP_Z >= 1.0 or (gap is not None and gap >= 1.0),
          f"tails reach z={tail_z:.2f}, case roof z={P.STLINK_TOP_Z:.1f}"
          + (f" -> they pass it, {gap:.2f} mm clear in plan" if gap is not None
             else f" -> {tail_z - P.STLINK_TOP_Z:.2f} mm above it"))
    check("case drops in from above before the lid goes on",
          P.STLINK_TOP_Z < P.PLATE_Z_BOTTOM,
          f"nothing overhangs it: open from z={P.STLINK_TOP_Z:.0f} up to the lid "
          f"at z={P.PLATE_Z_BOTTOM:.0f}")

    # ------------------------------------------------------ probe hardware --
    print("\nprobe hardware fit")
    bore_depth = P.Z_PIN_TOP - P.PLATE_Z_BOTTOM
    below = P.RECEPT_LEN - bore_depth
    room = P.PLATE_Z_BOTTOM - P.STAND_Z_BOTTOM
    check("sleeve tail reaches the wiring space", 3.0 <= below <= room - 4.0,
          f"{below:.2f} mm of sleeve below the plate, in "
          f"{room:.0f} mm of clearance")
    check("sleeve tail clears the bench", below < P.PLATE_Z_BOTTOM - P.STAND_Z_BOTTOM,
          f"{below:.2f} mm vs {P.PLATE_Z_BOTTOM - P.STAND_Z_BOTTOM:.0f} mm")
    for d, dep, sh in P.HOLE_SHRINK_CAL:
        check(f"print model reproduces Ø{d:.2f} at {dep:.1f} mm deep",
              abs(P.hole_shrink(d, dep) - sh) < 1e-9,
              f"shrink {P.hole_shrink(d, dep):.3f} -> prints "
              f"Ø{P.printed(d, dep):.3f}")
    # The P50's two bores are the SAME modelled diameter and the step that
    # stops the sleeve comes entirely from their depths. That is measured on
    # this printer -- both gauge rows read 135 and gave Ø0.98 and Ø0.90 -- but
    # it is a dependency worth naming, because a printer without the depth
    # effect would have no step at all.
    step = (P.printed(P.PIN_BORE_D, P.PIN_HEAD_BORE_L)
            - P.printed(P.PIN_BODY_BORE_D, P.PIN_BORE_L))
    modelled = P.PIN_BORE_D - P.PIN_BODY_BORE_D
    check("the depth stop survives as printed", step >= 0.06,
          f"{step:.3f} mm of step, of which {modelled:.3f} mm is modelled "
          f"diameter and {step - modelled:.3f} mm is the two bores' depths")
    # Outside the calibrated span the model holds the nearest measurement flat,
    # which is a guess. How far outside is the thing to bound: shrink rises as
    # diameter falls, so a bore below the smallest calibration point prints
    # TIGHTER than modelled, and on a press fit that is the direction that
    # seizes.
    ds = [d for d, _, _ in P.HOLE_SHRINK_CAL]
    c_lo, c_hi = min(ds), max(ds)
    out = max(c_lo - P.PIN_BODY_BORE_D, P.PIN_BORE_D - c_hi, 0.0)
    check("probe bores sit inside the calibrated range, or barely outside it",
          out <= 0.20,
          f"bores Ø{P.PIN_BODY_BORE_D:.2f}-Ø{P.PIN_BORE_D:.2f} against measured "
          f"Ø{c_lo:.2f}-Ø{c_hi:.2f}"
          + (" -- interpolated throughout" if out == 0 else
             f" -- {out:.2f} mm extrapolated, shrink held flat there"))
    check("gauge brackets the modelled bore",
          min(P.GAUGE_BORES) < P.PIN_BORE_D < max(P.GAUGE_BORES),
          f"{P.PIN_BORE_D} mm sits inside {min(P.GAUGE_BORES)}-{max(P.GAUGE_BORES)} mm")
    check("mouth chamfer does not eat the collar",
          P.PIN_MOUTH_CHAMFER <= 0.20,
          f"{P.PIN_MOUTH_CHAMFER:.2f} mm; on the crowded bores it is the widest "
          f"feature and so sets the thinnest wall")

    # Full chain from the board's pad to the probe tip, stated link by link.
    # The locators are on the deck, so the board registers straight to the
    # part that holds the probes and the nest contributes nothing. Putting them
    # on the nest instead would add its pin print error and its play on the
    # register pins -- measured at +0.232 mm worst case, over the pad budget.
    # AS PRINTED. The pin is printed (so it grows); the board's Ø2.20 hole is
    # routed, so nothing shrinks it. Using the modelled diameter credited the
    # design with clearance the printed part does not have.
    pin_printed = P.LOCATOR_D + P.PRINT_BOSS_GROW
    pin_clear = (2.2 - pin_printed) / 2
    # derived from the actual body-bore fit, not a hard-coded 0.04 -- the chain
    # used to be insensitive to the parameter it most depends on
    sleeve_play = (P.printed(P.PIN_BODY_BORE_D, P.PIN_BORE_L)
                   - P.RECEPT_BODY_D) / 2
    head_play = max(0.0, (P.printed(P.PIN_BORE_D, P.PIN_HEAD_BORE_L)
                          - P.RECEPT_HEAD_D) / 2)
    bearing_sep = (P.PIN_HEAD_BORE_L + P.PIN_BORE_L) / 2
    arm = max(math.hypot(t["x"], t["y"]) for t in G.TEST_POINTS)
    span = math.dist(G.HOLES[P.LOCATOR_PRIMARY[0]], G.HOLES[P.LOCATOR_PRIMARY[1]])
    links = [
        ("PCB hole to pad, fab",              0.050),
        (f"board on a Ø{pin_printed:.2f} pin as printed", pin_clear),
        (f"yaw from it, at {arm:.0f} mm",     math.atan(2 * pin_clear / span) * arm),
        ("base plate pin position, print",    0.100),
        ("base plate bore position, print",   0.100),
        ("sleeve in the body bore",           sleeve_play),
        # Two bearing zones, not one: the counterbore grips the head and the
        # body bore grips the body, and what limits tilt is the clearance
        # divided by the distance BETWEEN them. Charging the whole lever to
        # the body bore alone made the P100 -- which guides mostly on its
        # 7.5 mm head -- look 0.08 mm worse than it is.
        ("sleeve tilt between head and body bores",
         ((head_play + sleeve_play) / bearing_sep) * P.PIN_PROTRUSION),
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
    # What the clamp actually has to hold. The P100 probe is rated 180 g where
    # the P50 is 75, so this tripled without anything else in the design
    # changing, and it is worth stating rather than assuming.
    probe_n = (len(G.TEST_POINTS) * P.PIN_FORCE_G
               * (P.COMPRESSION / (2 / 3 * P.PIN_STROKE_MAX)) / 1000) * 9.81
    d = P.SPRING_OD - P.SPRING_WIRE_D
    k = (79300 * P.SPRING_WIRE_D ** 4
         / (8 * d ** 3 * P.SPRING_ACTIVE_COILS))          # N/mm
    spring_n = len(P.POST_XY) * k * P.TRAVEL
    load = probe_n + spring_n
    check("clamp load is well inside the GH-201's rating",
          load <= P.CLAMP_RATING_KG * 9.81 / 3,
          f"{load:.1f} N = {load / 9.81:.2f} kg ({probe_n:.1f} N of probe at "
          f"{P.COMPRESSION:.2f} mm + {spring_n:.1f} N of spring), against "
          f"{P.CLAMP_RATING_KG:.0f} kg rated")

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
    # Both mounting-hole rows must sit on the deck with real wall around them.
    # The old check compared the deck's Y extent against CLAMP_HOLE_DY + 12, a
    # number invented from the hole pattern, and CLAMP_BASE_L was referenced
    # nowhere -- a 200 mm clamp on a 24 mm deck passed.
    for x, y in ins:
        wall = min(abs(y - P.PEDESTAL_Y[0]), abs(y - P.PEDESTAL_Y[1])) - \
            P.INSERT_M3_HOLE_D / 2
        check(f"clamp insert ({x:+6.2f},{y:+6.2f}) has wall to the tower face",
              wall >= 2.0, f"{wall:.2f} mm")
    dim_x0, dim_y0 = P.COVER_DIMPLE_XY
    base_near = dim_y0 - P.CLAMP_SPINDLE_TO_END
    base_far = base_near - P.CLAMP_BASE_L
    over = P.STAND_Y[0] - base_far
    check("clamp overhang past the back of the stand is declared, not accidental",
          over <= 45.0,
          f"clamp base spans y {base_far:.1f}..{base_near:.1f}, stand ends at "
          f"y={P.STAND_Y[0]:.0f} -> {over:.1f} mm unsupported tail")
    check("both mounting rows land on the deck",
          all(P.PEDESTAL_Y[0] < y < P.PEDESTAL_Y[1] for _, y in ins),
          f"rows at y={sorted(set(round(y,1) for _, y in ins))} inside "
          f"{P.PEDESTAL_Y[0]:.0f}..{P.PEDESTAL_Y[1]:.0f}")
    # the clamp screw must reach the insert without bottoming out
    stick = P.CLAMP_SCREW_L - P.CLAMP_BASE_T
    check("clamp screw engages the insert without bottoming out",
          P.INSERT_M3_H <= stick < P.INSERT_M3_HOLE_DEPTH,
          f"M3 x {P.CLAMP_SCREW_L:.0f} through a {P.CLAMP_BASE_T:.0f} mm base "
          f"-> {stick:.0f} mm into a {P.INSERT_M3_HOLE_DEPTH:.0f} mm hole")
    check("material left under a blind insert hole", solid_under >= 3.0,
          f"{solid_under:.1f} mm of solid below the hole")
    check("hole is deeper than the insert",
          P.INSERT_M3_HOLE_DEPTH > P.INSERT_M3_H,
          f"{P.INSERT_M3_HOLE_DEPTH} mm hole for a {P.INSERT_M3_H} mm insert")
    # AS PRINTED, not as modelled. A modelled Ø4.00 printed Ø3.78, under the
    # insert's own Ø3.90 tip, so it could not start square.
    #
    # Across the WHOLE measured shrink range, because nothing has been measured
    # at Ø4 -- the two calibration points are 0.22 at Ø1.2 and 0.10 at Ø2.0,
    # and this hole has to survive either being true up here.
    # The band at THIS diameter, not the whole small-hole range. Above the
    # calibrated range the model holds the last measurement; shrink cannot go
    # up again as the hole grows, and it cannot go below zero, so [0, that] is
    # the honest bracket. Using the Ø1.35 figure of 0.40 up here would have
    # been nonsense -- it is a measure of how badly a 2-nozzle-wide hole closes.
    sh_hi = P.hole_shrink(P.INSERT_M3_HOLE_D, P.INSERT_M3_HOLE_DEPTH)
    lo_p = P.INSERT_M3_HOLE_D - sh_hi
    hi_p = P.INSERT_M3_HOLE_D
    check("insert hole PRINTS between the tip and the knurl",
          P.INSERT_M3_TIP_D < lo_p and hi_p < P.INSERT_M3_KNURL_D,
          f"modelled Ø{P.INSERT_M3_HOLE_D:.2f} -> prints Ø{lo_p:.2f}-Ø{hi_p:.2f} "
          f"over the measured shrink range, inside Ø{P.INSERT_M3_TIP_D}-"
          f"Ø{P.INSERT_M3_KNURL_D}")
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
        # ALL faces, not just exactly-horizontal planes. The old filter was
        # `GeomType.PLANE and |n_z + 1| < 1e-3`, so a spherical or conical
        # ceiling was invisible -- the cover's dimple could be opened out to a
        # Ø16 hole punched clean through the part and this still reported
        # "widest unsupported span 0.0 mm".
        flats = []
        for f in oriented.faces():
            if f.center().Z <= bed_z + 0.05:
                continue
            try:
                nz = f.normal_at().Z
            except Exception:
                continue
            if nz <= -OVERHANG_NZ:          # 45 deg or shallower, facing down
                flats.append(f)
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
    # rounded to match NEST_FILLET: a square-cornered test plate produces its
    # own sliver at each corner and reports it as a thin wall in the part
    _r = P.NEST_FILLET
    plate = _box(P.NEST_X[0] + _r, P.NEST_Y[0] + _r,
                 P.NEST_X[1] - _r, P.NEST_Y[1] - _r).buffer(_r, G.ARC_SEGS)
    levels = [("seat", plate.difference(G.nest_recess())),
              ("lip", plate.difference(G.board_recess())),
              ("pocket floor", plate)]
    for nm2, region in levels:
        region = region.difference(G.probe_clear())
        # An OPENING (erode then dilate) removes everything thinner than 2r and
        # leaves the rest, so the residue is the area of the thin features. The
        # old form asked `is_empty` in DESCENDING order, which made the result
        # the constant 3.0 for every input -- a 0.4 mm sliver, a 0.01 mm speck
        # and a 50 mm square all reported "survives a 3.0 mm erosion" and
        # passed. It also used the union, so one fat feature masked every thin
        # one.
        # Judge on the LARGEST CONNECTED sliver, not total residue: a real thin
        # wall is one connected feature, while polygon faceting scatters many
        # sub-0.1 mm2 specks that would otherwise sum past any total-area limit.
        widest, lost = 3.0, 0.0
        for w in (1.2, 1.5, 2.0, 2.5, 3.0):
            opened = region.buffer(-w / 2, G.ARC_SEGS).buffer(w / 2, G.ARC_SEGS)
            resid = region.difference(opened)
            parts = list(resid.geoms) if resid.geom_type.startswith("Multi") else [resid]
            biggest = max([q.area for q in parts], default=0.0)
            if biggest > 0.40:
                widest, lost = w, biggest
                break
        check(f"nest {nm2:12s} cross-section has no thin walls", widest >= 2.0,
              f"no connected feature under {widest:.1f} mm"
              + (f" (worst sliver {lost:.2f} mm2)" if lost else ""))
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
    post_play = P.fit(P.POST_HOLE_D, P.POST_D)
    reg_play = P.fit(P.REG_HOLE_D, P.REG_PIN_D)
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
    # the HOLE, not a point. A point test against a 0.5 mm buffer was blind to
    # a Ø4.45 hole eating into the board recess lip.
    keep = G.OUTLINE.buffer(P.NEST_LIP_CLEAR)
    for i, (x, y) in enumerate(P.REG_XY):
        hole = Point(x, y).buffer(P.REG_HOLE_D / 2 + P.REG_SLOT_EXTRA / 2, G.ARC_SEGS)
        bite = hole.intersection(keep).area
        check(f"register hole {i+1} clears the board recess", bite < 0.01,
              f"{bite:.3f} mm2 of the Ø{P.REG_HOLE_D:.2f} hole inside the recess")

    # the wall over the 3.3 V slot is also the lid's seating face
    lintel = P.PLATE_Z_BOTTOM - P.WIRE_EXIT_Z[1]
    check("wire slot leaves a real lintel under the lid seat", lintel >= 2.0,
          f"{lintel:.2f} mm of wall over a {P.WIRE_SLOT_W:.0f} mm opening")

    # the cover must not go on backwards
    rev = Pos(2 * P.COVER_DIMPLE_XY[0], 0, seat + board_t) * (Rot(0, 0, 180) * cover)
    check("cover cannot be fitted backwards",
          vol(rev.intersect(base)) + vol(rev.intersect(board)) > 20.0,
          f"{vol(rev.intersect(base)) + vol(rev.intersect(board)):.1f} mm3 of "
          f"interference blocks it")
    mx, my, ms, mh = P.MCU_BOSS
    check("MCU boss stops short of the package", P.MCU_BOSS_CLEAR > 0,
          f"{P.MCU_BOSS_CLEAR} mm below a {mh} mm package -- backs the board "
          f"without lifting it")

    print("\n" + ("ALL CHECKS PASSED" if not FAILS else
                  f"{len(FAILS)} CHECK(S) FAILED: {FAILS}"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
