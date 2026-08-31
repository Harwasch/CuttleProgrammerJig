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


def nest_window():
    """Through-window in the nest plate.

    Relieved only where it must be: under every bottom-side part, and around
    every probe island (island + PLATFORM_GAP) so the nest can travel past the
    platform. Everywhere else the nest keeps full-thickness board support --
    which matters here because three probes sit 0.5-1.4 mm from the outline.
    """
    relief = part_boxes("bottom", grow=P.PART_CLEAR_XY)
    probes = [Point(t["x"], t["y"]).buffer(P.PROBE_ISLAND_R + P.PLATFORM_GAP, ARC_SEGS)
              for t in TEST_POINTS]
    return unary_union(relief + probes).buffer(0)


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
