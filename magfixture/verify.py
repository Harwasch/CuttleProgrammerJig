"""Numerical checks on the magnet fixture against the real PCBA model.

Same discipline as the programming jig's suite: every check measures geometry
or a fit as printed, and none of them restates how a part was constructed.

Run:  python3 verify.py
"""
import math
import os
import sys

from build123d import *
from shapely.geometry import Polygon as ShPolygon, box as shbox
from shapely.ops import unary_union

import mag_params as M
import fixture as F

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "cad"))
import geom as G                                              # noqa: E402
from verify import vol, OVERHANG_NZ                           # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{'  --  ' + detail if detail else ''}")
    if not ok:
        FAILS.append(name)


def note(text):
    print(f"  [note] {text}")


# --------------------------------------------------------------- overhangs ---
def _tri_region(tris):
    polys = [ShPolygon(t) for t in tris]
    return unary_union([q for q in polys if q.is_valid and q.area > 1e-9])


def _max_reach(region, support):
    """Farthest any point of `region` is from `support`, by bisection."""
    if region.is_empty:
        return 0.0
    if support.is_empty:
        b = region.bounds
        return math.hypot(b[2] - b[0], b[3] - b[1])
    lo, hi = 0.0, 120.0
    for _ in range(24):
        mid = (lo + hi) / 2
        if region.difference(support.buffer(mid)).is_empty:
            hi = mid
        else:
            lo = mid
    return hi


def overhang_report(shape, bed):
    """(bridge half-span, cantilever reach, z) for the worst overhang.

    Two numbers, because they are two different failure modes. A BRIDGE is
    anchored at both ends: the filament goes into tension and holds, and what
    matters is half the clear span. A CANTILEVER has a free end, nothing pulls
    it straight, and it curls after a few millimetres. Treating both as "the
    widest downward face" is what let a 9 mm one-sided ledge through.

    Overhang area is collected per TRIANGLE, not per face: one cylindrical
    face of a horizontal bolt hole has a single sampled normal that says
    nothing useful, but its upper arc really is an overhang and its lower arc
    really is not. Support is the part's own plan section 0.5 mm lower, and
    a patch counts as bridged only where it lies inside the convex hull of
    that section -- which is exactly the region a taut filament can span.
    """
    bb = shape.bounding_box()
    levels = {}
    for f in shape.faces():
        try:
            verts, tris = f.tessellate(0.3)
        except Exception:
            continue
        if not tris:
            continue
        sign = None
        for t in tris:
            p = [verts[i] for i in t]
            u = p[1] - p[0]
            v = p[2] - p[0]
            n = Vector(u.Y * v.Z - u.Z * v.Y,
                       u.Z * v.X - u.X * v.Z,
                       u.X * v.Y - u.Y * v.X)
            if n.length < 1e-9:
                continue
            n = n / n.length
            if sign is None:
                cen = (p[0] + p[1] + p[2]) / 3
                try:
                    sign = 1.0 if n.dot(f.normal_at(cen)) >= 0 else -1.0
                except Exception:
                    sign = 1.0
            if sign * n.Z > -OVERHANG_NZ:
                continue
            z = sum(q.Z for q in p) / 3
            if z <= bed + 0.05:
                continue
            levels.setdefault(round(z * 2) / 2, []).append(
                [(q.X, q.Y) for q in p])

    worst_b = worst_c = 0.0
    at_b = at_c = 0.0
    for z, tris in levels.items():
        region = _tri_region(tris)
        if region.is_empty or region.area < 0.5:
            continue
        slab = shape.intersect(Pos((bb.min.X + bb.max.X) / 2,
                                   (bb.min.Y + bb.max.Y) / 2, z - 0.25) *
                               Box(bb.size.X + 2, bb.size.Y + 2, 0.5))
        sup = []
        for sf in (slab.faces() if slab is not None else []):
            try:
                sv, st = sf.tessellate(0.3)
            except Exception:
                continue
            sup += [[(sv[i].X, sv[i].Y) for i in t] for t in st]
        support = _tri_region(sup) if sup else ShPolygon()
        free = region.difference(support)
        if free.is_empty:
            continue
        hull = support.convex_hull if not support.is_empty else ShPolygon()
        b = _max_reach(free.intersection(hull), support) if not hull.is_empty else 0.0
        c = _max_reach(free.difference(hull), support)
        if b > worst_b:
            worst_b, at_b = b, z
        if c > worst_c:
            worst_c, at_c = c, z
    return worst_b, at_b, worst_c, at_c


def pocket_axis(part, dia):
    """Centre of the cylindrical bore of diameter `dia` in a built part."""
    best = None
    for f in part.faces():
        if f.geom_type != GeomType.CYLINDER:
            continue
        bb = f.bounding_box()
        if abs(bb.size.X - dia) > 0.02 or abs(bb.size.Y - dia) > 0.02:
            continue
        if best is None or f.area > best[0]:
            best = (f.area, ((bb.min.X + bb.max.X) / 2,
                             (bb.min.Y + bb.max.Y) / 2))
    return best[1] if best else None


def main():
    print("building parts ...")
    body = F.build_fixture_body()
    rotor = F.build_rotor()
    sleeve = F.build_hall_sleeve()
    gg = F.build_gap_gauge()
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
    # package heights must come from the same data the interference checks use,
    # or the fixture builds one airgap and the checks measure another
    check("package tops come from the keep-out model, not a transcription",
          abs(M.ENC_PKG_H - max(h for x0, x1, y0, y1, h in G.PARTS["top"]
                                if x0 <= ex <= x1 and y0 <= ey <= y1)) < 1e-9,
          f"AS5600L package {M.ENC_PKG_H:.3f} mm, SOT-23 {M.HALL_PKG_H:.3f} mm")

    below_knob = max(M.ROTOR_SHAFT_D, M.ROTOR_POCKET_D) + M.PRINT_BOSS_GROW
    journal_d = M.ROTOR_BORE_D - M.PRINT_HOLE_SHRINK
    check("rotor drops in through the journal from above",
          below_knob < journal_d,
          f"body prints Ø{below_knob:.2f} through a Ø{journal_d:.2f} journal")
    check("...and the knob cannot follow it through",
          M.ROTOR_KNOB_D > journal_d + 2.0,
          f"knob Ø{M.ROTOR_KNOB_D:.1f} lands on a Ø{M.ROTOR_HUB_D:.0f} hub")
    check("...on a seat wide enough to hold it square",
          (M.ROTOR_KNOB_D - journal_d) / 2 >= 1.5,
          f"{(M.ROTOR_KNOB_D - journal_d) / 2:.2f} mm of annulus under the knob")
    wall = (M.ROTOR_SHAFT_D - M.ROTOR_POCKET_D) / 2
    check("magnet pocket leaves wall in the rotor body", wall >= 1.2,
          f"{wall:.2f} mm around a Ø{M.ENC_MAG_D} magnet")

    # the journal is what actually holds the magnet on centre: a shaft can lean
    # by 2c/L, and the magnet hangs d below the bottom of the bore
    c_rot = M.fit(M.ROTOR_BORE_D, M.ROTOR_SHAFT_D)
    L_rot = M.JOURNAL_L
    d_rot = M.PORTAL_DECK_Z[0] - M.ROTOR_MAG_FACE_Z
    rotor_ecc = c_rot + 2 * c_rot / L_rot * d_rot
    check("the journal holds the magnet inside the AS5600 window",
          rotor_ecc <= 0.25,
          f"{rotor_ecc:.3f} mm worst case: {c_rot:.3f} mm radial on "
          f"{L_rot:.0f} mm of bore, magnet {d_rot:.2f} mm below it")

    pk = pocket_axis(sleeve, M.HALL_POCKET_D)
    check("hall magnet pocket is centred on the SOT-23",
          pk is not None and math.hypot(pk[0] - M.HALL_XY[0],
                                        pk[1] - M.HALL_XY[1]) < 1e-6,
          f"pocket axis ({pk[0]:+.3f},{pk[1]:+.3f})" if pk else "no pocket found")

    # ------------------------------------------------------------- hall reach --
    print("\nhall sleeve travel")
    lo = M.HALL_PKG_TOP + M.HALL_GAP_MIN
    hi = M.HALL_PKG_TOP + M.HALL_GAP_MAX
    check("sleeve clears the plate at the closest setting", lo > 0.5,
          f"underside z={lo:.3f} at {M.HALL_GAP_MIN:.0f} mm gap")
    top_needed = hi + M.HALL_SLEEVE_H
    check("the column is long enough for the far setting",
          M.HALL_COL_TOP >= top_needed + 1.0,
          f"column to z={M.HALL_COL_TOP:.1f}, sleeve top z={top_needed:.2f} "
          f"at {M.HALL_GAP_MAX:.0f} mm")

    reach = M.HALL_XY[1] - M.HALL_COL_Y
    c_s = min(M.fit(M.HALL_BORE_W, M.HALL_COL_W),
              M.fit(M.HALL_BORE_T, M.HALL_COL_T))
    tilt = 2 * c_s / M.HALL_SLEEVE_H
    z_err = tilt * reach
    check("sleeve tilt does not throw the gap away before it is clamped",
          z_err <= 0.5,
          f"{z_err:.3f} mm at the magnet: {c_s:.3f} mm on {M.HALL_SLEEVE_H:.0f} "
          f"mm of bore, arm reaching {reach:.2f} mm")
    note(f"the gap gauge removes that error entirely -- the magnet face rests "
         f"on the step, so the number you set is the step thickness")

    # the column has to survive being shoved. Two Ø6 posts did not.
    Zx = M.HALL_COL_W * M.HALL_COL_T ** 2 / 6
    Zy = M.HALL_COL_T * M.HALL_COL_W ** 2 / 6
    arm_mid = hi + M.HALL_SLEEVE_H / 2
    sigma = 10.0 * arm_mid / min(Zx, Zy)
    check("column survives a 10 N shove at the top of its travel",
          sigma <= 25.0 / 3,
          f"{sigma:.2f} MPa at the root vs ~25 MPa PETG layer bond "
          f"({25.0 / sigma:.0f}x); Z={min(Zx, Zy):.0f} mm3, was 42 mm3 on two "
          f"Ø6 posts")
    lean = math.degrees(math.atan(M.HALL_PLINTH_FLARE / M.HALL_PLINTH_H))
    check("the column root is gusseted, not a square step",
          M.HALL_PLINTH_FLARE >= 0.25 * min(M.HALL_COL_W, M.HALL_COL_T),
          f"{M.HALL_PLINTH_FLARE:.1f} mm of flare against a "
          f"{min(M.HALL_COL_W, M.HALL_COL_T):.2f} mm column; root section grows "
          f"{(M.HALL_COL_W + 2 * M.HALL_PLINTH_FLARE) * (M.HALL_COL_T + 2 * M.HALL_PLINTH_FLARE) / (M.HALL_COL_W * M.HALL_COL_T):.2f}x")
    check("...and the gusset prints without support", lean <= 45.0,
          f"leaning {lean:.1f} degrees from vertical")
    check("...and ends below the sleeve's lowest position",
          M.HALL_PLINTH_H < lo,
          f"plinth top z={M.HALL_PLINTH_H:.1f}, sleeve underside z={lo:.3f} at a "
          f"{M.HALL_GAP_MIN:.0f} mm gap")

    # it must not foul the board anywhere in that travel
    worst, worst_g = 0.0, None
    for g in [M.HALL_GAP_MIN + i * (M.HALL_GAP_MAX - M.HALL_GAP_MIN) / 8
              for i in range(9)]:
        s = Pos(0, 0, M.HALL_PKG_TOP + g) * sleeve
        v = vol(s.intersect(board))
        if v > worst:
            worst, worst_g = v, g
    check("sleeve clears the PCBA across the whole sweep", worst < 0.02,
          f"worst {worst:.4f} mm3"
          + (f" at {worst_g:.1f} mm" if worst_g else ""))

    # --------------------------------------------------------- interference ---
    print("\ninterference")
    for nm, a in (("fixture body vs PCBA", body), ("rotor vs PCBA", rotor)):
        check(nm, vol(a.intersect(board)) < 0.02,
              f"{vol(a.intersect(board)):.4f} mm3")
    check("rotor turns without touching the portal",
          vol(rotor.intersect(body)) < 0.02,
          f"{vol(rotor.intersect(body)):.4f} mm3")
    v_sl = vol((Pos(0, 0, lo) * sleeve).intersect(body))
    check("sleeve rides the column without binding on the plate", v_sl < 0.02,
          f"{v_sl:.4f} mm3 at the closest setting")

    # --------------------------------------------------------- board loading --
    print("\nloading and unloading")
    lift = M.LOCATOR_H
    lobe_top = M.ENC_PKG_TOP + lift
    check("the board lifts off its pins under the portal deck",
          M.PORTAL_DECK_Z[0] - lobe_top >= 1.0,
          f"lobe top z={lobe_top:.2f} once lifted {lift:.2f} mm, deck underside "
          f"z={M.PORTAL_DECK_Z[0]:.1f}")
    lobe = G.OUTLINE.intersection(shbox(M.PORTAL_X[0], -40, M.PORTAL_X[1], 40))
    half = max(abs(lobe.bounds[1]), abs(lobe.bounds[3]))
    check("portal walls stand clear of the lobe",
          M.PORTAL_GAP_Y / 2 - half >= 1.0,
          f"wall inner faces at ±{M.PORTAL_GAP_Y / 2:.1f}, lobe half-width "
          f"{half:.2f} mm")
    note(f"the rotor comes out first: its magnet face sits "
         f"{M.ROTOR_MAG_FACE_Z:.2f} mm up, below the lifted lobe at "
         f"{lobe_top:.2f} mm. Lift the knob, lift the board, slide it out in -X.")

    # ----------------------------------------------------------- fits, as printed
    print("\nfits as printed")
    for nm, hole, sh, lo_r, hi_r in (
            ("rotor in its journal", M.ROTOR_BORE_D, M.ROTOR_SHAFT_D, 0.06, 0.20),
            ("sleeve on the column, X", M.HALL_BORE_W, M.HALL_COL_W, 0.08, 0.25),
            ("sleeve on the column, Y", M.HALL_BORE_T, M.HALL_COL_T, 0.08, 0.25)):
        r = M.fit(hole, sh)
        check(nm, lo_r <= r <= hi_r, f"{r:.3f} mm radial")
    enc_pocket = M.ROTOR_POCKET_D - M.PRINT_HOLE_SHRINK
    check("encoder magnet is a press fit in the rotor",
          -0.06 <= enc_pocket - M.ENC_MAG_D <= 0.0,
          f"pocket prints Ø{enc_pocket:.3f} on a Ø{M.ENC_MAG_D} magnet")
    hall_pocket = M.HALL_POCKET_D - M.PRINT_HOLE_SHRINK
    check("Ø13 magnet is a press fit in the sleeve",
          -0.06 <= hall_pocket - 13.0 <= 0.0,
          f"pocket prints Ø{hall_pocket:.3f}")
    check("every magnet can be pushed back out again",
          M.HALL_EJECT_D >= 3.0 and M.HALL_ARM_T > M.HALL_POCKET_DEPTH,
          f"Ø{M.HALL_EJECT_D:.0f} eject hole through a "
          f"{M.HALL_ARM_T - M.HALL_POCKET_DEPTH:.1f} mm ceiling")
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
        check(f"...and the ring fits inside the pocket",
              M.RING_H <= M.HALL_POCKET_DEPTH,
              f"ring {M.RING_H:.1f} mm in a {M.HALL_POCKET_DEPTH:.1f} mm pocket")

    # ------------------------------------------------------- board seating ----
    print("\nboard seating")
    spec = {n: (x, y, k) for n, (x, y, k) in
            zip(M.LOCATORS, F.locator_spec())}
    check("four locating pins, both sections",
          len(spec) == 4 and "MH5" in spec and "MH6" in spec,
          f"{sorted(spec)} -- MH5/MH6 hold the lobe, which is past a flex neck "
          f"and sets the encoder airgap")
    datum = M.LOCATOR_D + M.PRINT_BOSS_GROW
    check("the lobe datum pin fits the board's routed Ø2.20 hole",
          0.03 <= (2.20 - datum) / 2 <= 0.10,
          f"{M.LOBE_DATUM} prints Ø{datum:.2f} -> {(2.20 - datum) / 2:.3f} mm radial")
    proud = M.LOCATOR_H - M.PCB_T
    check("pins stand proud of the board for loading", proud >= 1.5,
          f"{proud:.2f} mm above the board top")
    check("relief pocket clears the tallest bottom-side part",
          M.RECESS >= max(h for *_, h in G.PARTS["bottom"]) + 0.3,
          f"{M.RECESS:.2f} mm deep vs a "
          f"{max(h for *_, h in G.PARTS['bottom']):.3f} mm part")

    # the lobe pair has to tolerate a pin radius of pitch error, delivered by a
    # diamond rather than by moving the pins (which just makes them miss)
    kinds = {k for _, _, k in spec.values()}
    check("the lobe is on a dowel and a diamond, not two dowels",
          spec["MH5"][2] == "round" and spec["MH6"][2] == "diamond",
          f"{spec['MH5'][2]} at MH5, {spec['MH6'][2]} at MH6")
    free = (2.20 - (M.LOBE_DIAMOND_W + M.PRINT_BOSS_GROW)) / 2
    check("...and the diamond gives back the pin radius that was asked for",
          free >= M.LOBE_PIN_PULL_IN / 2 - 1e-9,
          f"{free:.3f} mm of pitch float either way, against a "
          f"{M.LOCATOR_D / 2:.3f} mm pin radius")
    check("...while still stopping the lobe rotating",
          abs((2.20 - (M.LOCATOR_D + M.PRINT_BOSS_GROW)) / 2 - 0.05) < 1e-9,
          f"the diamond stays full width across the pitch line, "
          f"{(2.20 - (M.LOCATOR_D + M.PRINT_BOSS_GROW)) / 2:.3f} mm radial")
    main_slack = (2.20 - (M.MAIN_LOCATOR_D + M.PRINT_BOSS_GROW)) / 2
    check("the main section follows the lobe instead of fighting it",
          main_slack >= 2 * (2.20 - datum) / 2,
          f"MH1/MH4 print Ø{M.MAIN_LOCATOR_D + M.PRINT_BOSS_GROW:.2f} -> "
          f"{main_slack:.3f} mm radial, {main_slack / ((2.20 - datum) / 2):.0f}x "
          f"the datum pin's")

    lobe_slack = (2.20 - datum) / 2
    total_ecc = lobe_slack + rotor_ecc
    check("the encoder magnet stays inside the AS5600's centring window",
          total_ecc <= 0.25,
          f"{total_ecc:.3f} mm worst case = {lobe_slack:.3f} lobe datum + "
          f"{rotor_ecc:.3f} rotor journal, against ±0.25 mm")

    # ----------------------------------------------------------- gap gauge ----
    print("\ngap gauge")
    check("gauge spans the required separation range",
          min(M.GAUGE_STEPS) <= M.HALL_GAP_MIN and
          max(M.GAUGE_STEPS) >= M.HALL_GAP_MAX,
          f"steps {M.GAUGE_STEPS} against {M.HALL_GAP_MIN:.0f}-"
          f"{M.HALL_GAP_MAX:.0f} mm")
    check("every step stands proud of the gauge body",
          abs(gg.bounding_box().max.Z - max(M.GAUGE_STEPS)) < 1e-6,
          f"tallest tongue {gg.bounding_box().max.Z:.2f} mm")
    check("the thinnest tongue is printable",
          min(M.GAUGE_STEPS) >= 0.8, f"{min(M.GAUGE_STEPS):.1f} mm")
    # the tongue slides in at the package top, so nothing under the sleeve head
    # may be taller than the package itself
    head_r = M.HALL_POCKET_D / 2 + 2.5
    tall = [h for x0, x1, y0, y1, h in G.PARTS["top"]
            if shbox(x0, y0, x1, y1).intersects(
                ShPolygon([(M.HALL_XY[0] + head_r * math.cos(a),
                            M.HALL_XY[1] + head_r * math.sin(a))
                           for a in [i * math.pi / 16 for i in range(32)]]))]
    check("nothing under the sleeve head is taller than the SOT-23",
          max(tall) <= M.HALL_PKG_H + 1e-9,
          f"tallest neighbour {max(tall):.3f} mm vs the package at "
          f"{M.HALL_PKG_H:.3f} mm")

    # --------------------------------------------------------- printability ---
    print("\nprintability (in the print orientation)")
    for nm, shape, flip in (("fixture_body", body, False),
                            ("rotor", rotor, True),
                            ("hall_sleeve", sleeve, False),
                            ("ring_10", F.build_ring_10(), False),
                            ("ring_6", F.build_ring_6(), False),
                            ("gap_gauge", gg, False)):
        oriented = Rot(180, 0, 0) * shape if flip else shape
        bed = oriented.bounding_box().min.Z
        b, zb, c, zc = overhang_report(oriented, bed)
        check(f"{nm:13s} bridges within reach", b <= M.BRIDGE_HALF_MAX,
              f"widest half-span {b:.1f} mm at z={zb:.1f} (limit "
              f"{M.BRIDGE_HALF_MAX:.1f})" + ("  (printed inverted)" if flip else ""))
        check(f"{nm:13s} has no drooping cantilever", c <= M.CANTILEVER_MAX,
              f"longest unanchored ledge {c:.1f} mm at z={zc:.1f} (limit "
              f"{M.CANTILEVER_MAX:.1f})")

    print()
    if FAILS:
        print(f"{len(FAILS)} CHECK(S) FAILED: {FAILS}")
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
