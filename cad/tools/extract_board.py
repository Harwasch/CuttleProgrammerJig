"""Extract CANServo_Driver board geometry from the V0.4 gerbers.

Writes cad/board_geometry.json in the JIG coordinate system:
origin = centroid of the four 2.2 mm holes on the main rigid section,
+X along the board, +Y up, millimetres.

Everything downstream (jig.py) reads that JSON, so re-running this against a
newer gerber set is the only step needed to retarget the jig to a new board rev.
"""
import re, math, json, os, sys
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, polygonize

HERE = os.path.dirname(os.path.abspath(__file__))
GERBER_DIR = os.path.join(HERE, "..", "ref", "gerbers_v0.4")
OUT = os.path.join(HERE, "..", "board_geometry.json")
STEM = "CANServo_Driver"

OX, OY = 169.4216, -107.5716   # jig origin expressed in gerber coordinates
ARC_TOL = 0.02                 # arc tessellation sagitta, mm


def read_prims(path):
    """Parse a gerber into ('L',x0,y0,x1,y1,..) / ('A',x0,y0,x1,y1,cx,cy,cw) primitives."""
    txt = open(path, errors="replace").read().replace("\r", "")
    x = y = 0.0
    interp = "G01"
    prims = []
    for line in txt.split("\n"):
        s = line.strip()
        if s in ("G01*", "G02*", "G03*"):
            interp = s[:3]
            continue
        m = re.match(r"^X?([-\d]+)?Y?([-\d]+)?(?:I([-\d]+))?(?:J([-\d]+))?D0?([123])\*$", s)
        if not m:
            continue
        nx = int(m.group(1)) / 1e6 if m.group(1) else x
        ny = int(m.group(2)) / 1e6 if m.group(2) else y
        i = int(m.group(3)) / 1e6 if m.group(3) else 0.0
        j = int(m.group(4)) / 1e6 if m.group(4) else 0.0
        if m.group(5) == "1":
            if interp == "G01":
                prims.append(("L", x, y, nx, ny, None, None, None))
            else:
                prims.append(("A", x, y, nx, ny, x + i, y + j, interp == "G02"))
        x, y = nx, ny
    return prims


def arc_points(x0, y0, x1, y1, cx, cy, cw):
    """Tessellated arc points, excluding the start point."""
    r = math.hypot(x0 - cx, y0 - cy)
    a0 = math.atan2(y0 - cy, x0 - cx)
    a1 = math.atan2(y1 - cy, x1 - cx)
    if cw and a1 >= a0 - 1e-12:
        a1 -= 2 * math.pi
    if not cw and a1 <= a0 + 1e-12:
        a1 += 2 * math.pi
    sweep = a1 - a0
    step = 2 * math.acos(max(-1.0, min(1.0, 1 - ARC_TOL / r))) if r > ARC_TOL else math.pi / 4
    n = min(max(int(abs(sweep) / step) + 1, 4), 512)
    return [(cx + r * math.cos(a0 + sweep * k / n), cy + r * math.sin(a0 + sweep * k / n))
            for k in range(1, n + 1)]


def snap_endpoints(prims, tol=0.03):
    """KiCad's Edge_Cuts export can leave micron-scale gaps between adjacent
    graphics. Merge endpoints that are within tol so the profile polygonizes."""
    nodes = []
    def node(x, y):
        for k, (nx, ny) in enumerate(nodes):
            if math.hypot(x - nx, y - ny) <= tol:
                return k
        nodes.append((x, y))
        return len(nodes) - 1
    out, moved = [], 0.0
    for p in prims:
        a, b = node(p[1], p[2]), node(p[3], p[4])
        (ax, ay), (bx, by) = nodes[a], nodes[b]
        moved = max(moved, math.hypot(ax - p[1], ay - p[2]), math.hypot(bx - p[3], by - p[4]))
        out.append((p[0], ax, ay, bx, by, p[5], p[6], p[7]))
    if moved > 1e-9:
        print(f"snapped Edge_Cuts endpoints, largest correction {moved * 1000:.1f} um")
    return out


def prims_to_lines(prims):
    out = []
    for p in prims:
        pts = [(p[1], p[2])] + ([(p[3], p[4])] if p[0] == "L" else arc_points(*p[1:]))
        if p[0] == "A":
            pts[-1] = (p[3], p[4])          # keep the snapped arc endpoint exact
        if len(pts) >= 2:
            out.append(LineString(pts))
    return out


def board_outline(prims):
    """Polygonize the profile. Returns (board polygon, list of interior rings)."""
    faces = sorted(polygonize(unary_union(prims_to_lines(prims))), key=lambda f: -f.area)
    if not faces:
        raise SystemExit("no closed profile found in Edge_Cuts")
    board = faces[0]
    return board, list(board.interiors)


def ring(coords):
    """Round + drop the duplicated closing point."""
    pts = [[round(x - OX, 4), round(y - OY, 4)] for x, y in coords]
    if pts[0] == pts[-1]:
        pts.pop()
    return pts


def circle_fit(coords):
    """If a ring is circular, return (cx, cy, dia) in jig coords, else None."""
    pts = list(coords)[:-1]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    rs = [math.hypot(x - cx, y - cy) for x, y in pts]
    if max(rs) - min(rs) > 0.03:
        return None
    return (round(cx - OX, 4), round(cy - OY, 4), round(2 * sum(rs) / len(rs), 4))


def main():
    prims = snap_endpoints(read_prims(f"{GERBER_DIR}/{STEM}-Edge_Cuts.gbr"))
    board, holes = board_outline(prims)
    print(f"Edge_Cuts primitives : {len(prims)}")
    print(f"board area           : {board.area:.2f} mm^2")
    print(f"board bbox (gerber)  : X {board.bounds[0]:.3f}..{board.bounds[2]:.3f}  "
          f"Y {board.bounds[1]:.3f}..{board.bounds[3]:.3f}")
    print(f"internal cutouts     : {len(holes)}")

    circles, profiles = [], []
    for h in holes:
        c = circle_fit(h.coords)
        (circles if c else profiles).append(c if c else ring(h.coords))
    for cx, cy, d in sorted(circles, key=lambda c: c[0]):
        print(f"   circular cutout  x={cx:8.3f} y={cy:8.3f}  dia={d:.3f}")
    for p in profiles:
        print(f"   shaped cutout    {len(p)} pts")

    flex = [ring(f.exterior.coords) for f in
            sorted(polygonize(unary_union(prims_to_lines(
                read_prims(f"{GERBER_DIR}/{STEM}-FLEX_REGION.gbr")))), key=lambda f: -f.area)
            if f.area > 1.0]

    data = {
        "source": "CANServo_Driver V0.4 gerbers",
        "note": "coordinates are in the JIG frame: origin = centroid of the four "
                "2.2 mm holes on the main rigid section, +Y up, mm",
        "origin_in_gerber_coords": [OX, OY],
        "board_thickness_mm": 1.627,
        "max_part_height_bottom_mm": 2.585,
        "max_part_height_top_mm": 7.014,
        "outline": ring(board.exterior.coords),
        "cutout_circles": [{"x": c[0], "y": c[1], "dia": c[2]} for c in circles],
        "cutout_profiles": profiles,
        "flex_regions": flex,
        # bottom-layer bare-copper discs (copper + mask opening, no pad footprint)
        "test_points": [
            {"net": "NRST",    "x": -32.25, "y":  1.70, "dia": 1.2},
            {"net": "GND",     "x": -28.25, "y": -6.30, "dia": 1.2},
            {"net": "SWO",     "x": -26.25, "y": -1.70, "dia": 1.2},
            {"net": "VDD_3V3", "x": -23.45, "y":  5.40, "dia": 1.2},
            {"net": "VDD_3V3", "x": -23.15, "y": -8.80, "dia": 1.2},
            {"net": "SWDIO",   "x": -22.25, "y":  1.30, "dia": 1.2},
            {"net": "SWCLK",   "x": -17.15, "y":  1.90, "dia": 1.2},
        ],
    }
    json.dump(data, open(OUT, "w"), indent=1)
    print(f"\nwrote {os.path.normpath(OUT)}")
    print(f"  outline {len(data['outline'])} pts, {len(circles)} circular + "
          f"{len(profiles)} shaped cutouts, {len(flex)} flex regions")


if __name__ == "__main__":
    main()
