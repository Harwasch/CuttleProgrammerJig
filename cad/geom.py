"""Shared geometry: board data loading, keep-out maths, shapely -> build123d."""
import json, os
from build123d import Polyline, make_face, Plane
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
import params as P

ARC_SEGS = 12       # shapely buffer quadrant segments -> 48 facets per circle

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = json.load(open(os.path.join(HERE, "board_geometry.json")))
PARTS = json.load(open(os.path.join(HERE, "board_parts.json")))

OUTLINE = Polygon(BOARD["outline"])
TEST_POINTS = BOARD["test_points"]
HOLES = {n: (x, y) for n, x, y in [
    ("MH1", -12.75, 7.550), ("MH2", -12.75, -7.550),
    ("MH3", 12.75, 7.550), ("MH4", 12.75, -7.550),
    ("MH5", 43.75, 6.962), ("MH6", 43.75, -6.761)]}


def part_boxes(side, min_h=0.0, grow=0.0):
    """Footprints of parts on `side` taller than min_h, inflated by `grow`."""
    return [box(x0 - grow, y0 - grow, x1 + grow, y1 + grow)
            for x0, x1, y0, y1, h in PARTS[side] if h > min_h]


def sk(poly, plane=Plane.XY):
    """shapely Polygon/MultiPolygon -> a build123d face (or sum of faces)."""
    polys = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
    total = None
    for p in polys:
        if p.is_empty or p.area < 1e-9:
            continue
        f = make_face(Polyline(*[tuple(c) for c in p.exterior.coords[:-1]], close=True))
        for ring in p.interiors:
            f -= make_face(Polyline(*[tuple(c) for c in ring.coords[:-1]], close=True))
        total = f if total is None else total + f
    return plane * total


def probe_islands():
    """Plan footprint of the pin-platform bosses, one per probe."""
    return unary_union([Point(t["x"], t["y"]).buffer(P.PROBE_ISLAND_R, ARC_SEGS)
                        for t in TEST_POINTS])


def boss_radius(name):
    """Largest seat boss that still clears the nearest bottom-side part."""
    x, y = HOLES[name]
    p = Point(x, y)
    near = min(b.distance(p) for b in part_boxes("bottom"))
    return min(P.BOSS_R_MAX, max(1.6, near - P.BOSS_PART_CLEAR))


def seat_bosses():
    """Footprints the board actually rests on, at full seat height.

    Clipped to the board outline: a boss has nothing to support beyond the
    board edge, and letting one run past would eat into the recess lip.
    """
    discs = unary_union([Point(*HOLES[n]).buffer(boss_radius(n), ARC_SEGS)
                         for n in P.SEAT_BOSSES])
    return discs.intersection(OUTLINE).buffer(0)


def bare_sections():
    """Board sections with no bottom-side parts at all -- the left tab and both
    flex necks. These take full-height support, which is what keeps the flex
    flat without any of it hanging in space."""
    strips = [box(lo, -30, hi, 30) for lo, hi in P.BARE_SECTIONS]
    return unary_union(strips).intersection(OUTLINE).buffer(0)


def nest_recess():
    """The single pocket that drops the nest clear of the components.

    Everything inside the board outline goes down by NEST_RECESS except the
    seat bosses and the bare sections. One pocket, no ribs threaded between
    parts, so there is nothing thin to print.
    """
    keep = seat_bosses().union(bare_sections())
    return OUTLINE.difference(keep).buffer(0)


def probe_clear():
    """Holes through the nest for the base's probe islands."""
    return unary_union([Point(t["x"], t["y"]).buffer(P.PROBE_CLEAR_D / 2, ARC_SEGS)
                        for t in TEST_POINTS])


def board_recess():
    """Drop-in pocket in the nest top: the board outline plus a placement gap."""
    return OUTLINE.buffer(P.NEST_LIP_CLEAR, join_style=2)


def bottom_part_sweep():
    """(footprint, z_floor) prisms a bottom-side part occupies when clamped down.

    With the nest fully down the board underside sits at z = NEST_T, so a part
    of height h fills NEST_T-h .. NEST_T. Anything the base pokes into that
    volume is a collision, so the platform gets cut back to z_floor.
    """
    out = []
    for x0, x1, y0, y1, h in PARTS["bottom"]:
        z = P.NEST_T - h - P.PART_CLEAR_Z
        if z < P.Z_PIN_TOP:                       # only these can actually clash
            out.append((box(x0 - P.PART_CLEAR_XY, y0 - P.PART_CLEAR_XY,
                            x1 + P.PART_CLEAR_XY, y1 + P.PART_CLEAR_XY), z))
    return out


def board_slab(seat_z):
    """The bare PCB as a solid, underside at seat_z."""
    from build123d import extrude, Pos, Circle
    slab = extrude(sk(OUTLINE, Plane.XY.offset(seat_z)), amount=P.PCB_T)
    for c in BOARD["cutout_circles"]:
        slab -= Pos(c["x"], c["y"], seat_z - 0.1) * extrude(
            Circle(c["dia"] / 2), amount=P.PCB_T + 0.2)
    return slab


def keepout_solid(side, seat_z):
    """Conservative solid for every part on `side`. Equal heights are grouped
    into bands so this costs ~40 booleans instead of ~1000."""
    from build123d import extrude
    bands = {}
    for x0, x1, y0, y1, h in PARTS[side]:
        bands.setdefault(round(h, 3), []).append(box(x0, y0, x1, y1))
    total = None
    for h, boxes in bands.items():
        u = unary_union(boxes)
        z0 = seat_z - h if side == "bottom" else seat_z + P.PCB_T
        s = extrude(sk(u, Plane.XY.offset(z0)), amount=h)
        total = s if total is None else total + s
    return total


def pcba_solid(seat_z):
    """Board slab plus both sides' part keep-outs, underside at seat_z."""
    return (board_slab(seat_z) + keepout_solid("bottom", seat_z)
            + keepout_solid("top", seat_z))
