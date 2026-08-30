"""Software z-buffer renderer for the exported STLs.

Painter's algorithm mis-sorts the large flat faces on the stand against the
base plate, so this rasterises with a real depth buffer: orthographic
projection, backface culling, Lambert shading, 2x supersampling, and a depth
discontinuity pass that draws silhouette and crease lines.

Run:  python3 tools/render.py [view ...]      (default: all)
"""
import os, sys, struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import params as P

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
SS = 2                      # supersampling factor
LIGHT = np.array([0.45, -0.75, 0.62])

COLOR = dict(base_plate="#4d7fc4", nest="#dfa03a", cover="#c0574f",
             stand="#9aa0a6", clamp_riser="#7d5aa6", pcba="#12602c")


def load_stl(path):
    with open(path, "rb") as f:
        n = struct.unpack("<I", f.read(84)[80:84])[0]
        data = np.frombuffer(f.read(n * 50), dtype=np.uint8).reshape(n, 50)
    return data[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(np.float64)


def view_matrix(az, el):
    a, e = np.radians(az), np.radians(el)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    return rx @ rz


def rasterise(tris, cols, az, el, W, H, pad=6.0, focus=None):
    """Return (rgb, depth) images. Screen axes are view-space X and Z; depth is Y.

    focus = (x, y, z, half_width) in world coordinates crops the view to that
    neighbourhood, for close-ups.
    """
    M = view_matrix(az, el)
    v = tris @ M.T
    nrm = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    ln = np.linalg.norm(nrm, axis=1, keepdims=True)
    nrm = nrm / np.where(ln == 0, 1, ln)

    keep = nrm[:, 1] < 0                       # facing the camera (-Y)
    v, cols, nrm = v[keep], cols[keep], nrm[keep]

    L = LIGHT / np.linalg.norm(LIGHT)
    shade = np.clip(0.34 + 0.66 * np.clip(nrm @ L, 0, 1), 0, 1)
    rgb_tri = cols * shade[:, None]

    xs, zs = v[:, :, 0], v[:, :, 2]
    if focus is None:
        x0, x1 = xs.min() - pad, xs.max() + pad
        z0, z1 = zs.min() - pad, zs.max() + pad
    else:
        fc = np.array(focus[:3]) @ M.T
        r = focus[3]
        x0, x1 = fc[0] - r, fc[0] + r
        z0, z1 = fc[2] - r * H / W, fc[2] + r * H / W
    scale = min(W / (x1 - x0), H / (z1 - z0))
    ox = (W - (x1 - x0) * scale) / 2 - x0 * scale
    oz = (H - (z1 - z0) * scale) / 2 - z0 * scale
    px = xs * scale + ox
    pz = H - (zs * scale + oz)                 # flip: image row 0 is top

    img = np.ones((H, W, 3))
    depth = np.full((H, W), np.inf)
    d_tri = v[:, :, 1]

    for i in range(len(v)):
        ax_, ay = px[i, 0], pz[i, 0]
        bx, by = px[i, 1], pz[i, 1]
        cx, cy = px[i, 2], pz[i, 2]
        lo_x, hi_x = int(max(0, min(ax_, bx, cx))), int(min(W - 1, max(ax_, bx, cx)) + 1)
        lo_y, hi_y = int(max(0, min(ay, by, cy))), int(min(H - 1, max(ay, by, cy)) + 1)
        if lo_x >= hi_x or lo_y >= hi_y:
            continue
        yy, xx = np.mgrid[lo_y:hi_y, lo_x:hi_x]
        xx = xx + 0.5
        yy = yy + 0.5
        den = (by - cy) * (ax_ - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        w0 = ((by - cy) * (xx - cx) + (cx - bx) * (yy - cy)) / den
        w1 = ((cy - ay) * (xx - cx) + (ax_ - cx) * (yy - cy)) / den
        w2 = 1.0 - w0 - w1
        m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not m.any():
            continue
        d = w0 * d_tri[i, 0] + w1 * d_tri[i, 1] + w2 * d_tri[i, 2]
        sub = depth[lo_y:hi_y, lo_x:hi_x]
        upd = m & (d < sub)
        if not upd.any():
            continue
        sub[upd] = d[upd]
        depth[lo_y:hi_y, lo_x:hi_x] = sub
        tile = img[lo_y:hi_y, lo_x:hi_x]
        tile[upd] = rgb_tri[i]
        img[lo_y:hi_y, lo_x:hi_x] = tile
    proj = (M, scale, ox, oz, H)
    return img, depth, proj


def project(pt, proj, ss):
    """World point -> pixel coordinates in the downsampled image."""
    M, scale, ox, oz, H = proj
    p = np.asarray(pt, float) @ M.T
    return (p[0] * scale + ox) / ss, (H - (p[2] * scale + oz)) / ss


def outline(img, depth, k=0.35):
    """Darken pixels where depth jumps -- silhouettes and creases."""
    d = np.where(np.isinf(depth), np.nan, depth)
    gx = np.zeros_like(d); gy = np.zeros_like(d)
    gx[:, 1:-1] = np.abs(d[:, 2:] - d[:, :-2])
    gy[1:-1, :] = np.abs(d[2:, :] - d[:-2, :])
    g = np.nan_to_num(np.hypot(gx, gy))
    sil = np.isinf(depth)
    edge = np.zeros_like(g, dtype=bool)
    edge[:, 1:-1] |= sil[:, 2:] != sil[:, :-2]
    edge[1:-1, :] |= sil[2:, :] != sil[:-2, :]
    strength = np.clip(g / max(np.nanpercentile(g[g > 0], 97), 1e-6), 0, 1)
    f = np.clip(1.0 - k * (strength + edge.astype(float)), 0.25, 1.0)
    return img * f[:, :, None]


def scene(parts):
    """parts: [(stl_name, dz)] -> (tris, colours)."""
    tris, cols = [], []
    for name, dz in parts:
        p = os.path.join(OUT, f"{name}.stl")
        if not os.path.exists(p):
            print(f"  (missing {name}.stl)")
            continue
        t = load_stl(p)
        t[:, :, 2] += dz
        tris.append(t)
        cols.append(np.tile(matplotlib.colors.to_rgb(COLOR[name]), (len(t), 1)))
    return np.vstack(tris), np.vstack(cols)


def shot(parts, path, title, az=35, el=22, w=1400, h=900, focus=None, labels=None):
    tris, cols = scene(parts)
    img, depth, proj = rasterise(tris, cols, az, el, w * SS, h * SS, focus=focus)
    img = outline(img, depth)
    img = img.reshape(h, SS, w, SS, 3).mean(axis=(1, 3))       # downsample
    fig, ax = plt.subplots(figsize=(w / 110, h / 110))
    ax.imshow(np.clip(img, 0, 1)); ax.axis("off")
    for pt, text, dy in labels or []:
        x, y = project(pt, proj, SS)
        ax.annotate(text, (x, y), xytext=(x, y + dy), fontsize=9, ha="center",
                    color="#111", weight="bold",
                    bbox=dict(fc="white", ec="#888", lw=.6, alpha=.9,
                              boxstyle="round,pad=0.22"),
                    arrowprops=dict(arrowstyle="-", color="#444", lw=.9))
    ax.set_xlim(0, w); ax.set_ylim(h, 0)
    ax.set_title(title, fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=110, facecolor="white")
    plt.close(fig)
    print("wrote", os.path.basename(path))


COVER_Z = P.NEST_T + P.PCB_T
JIG = [("stand", 0), ("clamp_riser", 0), ("base_plate", 0)]
CLOSED = JIG + [("nest", 0), ("cover", COVER_Z)]
CLOSED_PCB = JIG + [("nest", 0), ("pcba", 0), ("cover", COVER_Z)]
OPEN_PCB = JIG + [("nest", P.TRAVEL), ("pcba", P.TRAVEL),
                  ("cover", COVER_Z + P.TRAVEL)]
EXPLODE = [("stand", -18), ("clamp_riser", -18), ("base_plate", 0),
           ("nest", 16), ("pcba", 30), ("cover", COVER_Z + 42)]

VIEWS = {
    "iso_front_right": (CLOSED_PCB, 35, 24, "assembly, board loaded - front right"),
    "iso_front_left":  (CLOSED_PCB, -35, 24, "assembly, board loaded - front left"),
    "iso_rear":        (CLOSED_PCB, 148, 26, "assembly - from behind, clamp pedestal far side"),
    "iso_high":        (CLOSED_PCB, 52, 52, "assembly - looking down"),
    "front":           (CLOSED_PCB, 0, 6, "front elevation - clamp pedestal nearest"),
    "side":            (CLOSED_PCB, 90, 6, "side elevation"),
    "top":             (CLOSED_PCB, 0, 89, "plan view"),
    "jig_only":        (JIG + [("nest", 0)], 40, 40,
                        "jig with the cover off - nest window and probe platform"),
    "probes":          ([("base_plate", 0)], 18, 62,
                        "base plate close-up - all seven probe islands, "
                        "cut back where a bottom-side part would foul them",
                        (-24.7, -1.5, 2.0, 13.5)),
    "probes_board":    ([("base_plate", 0), ("pcba", 0)], 24, 34,
                        "probe islands under the board, clamp closed",
                        (-24.7, -1.0, 4.0, 20.0)),
    "open":            (OPEN_PCB, 30, 18,
                        "clamp OPEN - nest, board and cover lifted 3 mm clear of the probes"),
    "exploded":        (EXPLODE, 34, 20, "exploded - stand, base plate, nest, board, cover"),
}


import json
_B = json.load(open(os.path.join(HERE, "..", "board_geometry.json")))
LABELS = {
    "probes": [((t["x"], t["y"], P.Z_PIN_TOP), t["net"], -46 if t["y"] > 0 else 46)
               for t in _B["test_points"]],
    "exploded": [((-58, 0, -18), "stand", -40), ((-24, -36, -6), "clamp riser", 40),
                 ((-58, 0, -4), "base plate", -34), ((-58, 0, 16), "nest", -34),
                 ((20, 0, 30 + P.NEST_T), "board", -38),
                 ((-24, 0, P.NEST_T + P.PCB_T + 42 + 5.8), "hold-down cover", -38)],
}


def main():
    want = sys.argv[1:] or list(VIEWS)
    for k in want:
        spec = VIEWS[k]
        parts, az, el, title = spec[:4]
        focus = spec[4] if len(spec) > 4 else None
        labels = LABELS.get(k)
        shot(parts, os.path.join(OUT, f"v_{k}.png"), title, az, el,
             focus=focus, labels=labels)


if __name__ == "__main__":
    main()
