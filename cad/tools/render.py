"""Shaded isometric renders of the exported STLs, for eyeballing the design."""
import sys, os, struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")


def load_stl(path):
    with open(path, "rb") as f:
        head = f.read(84)
        n = struct.unpack("<I", head[80:84])[0]
        data = np.frombuffer(f.read(n * 50), dtype=np.uint8).reshape(n, 50)
    tri = data[:, 12:48].copy().view("<f4").reshape(n, 3, 3)
    return tri.astype(np.float64)


def view_matrix(az, el):
    a, e = np.radians(az), np.radians(el)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    return rx @ rz


def draw(ax, tris, colors, az=35, el=22, light=(0.4, -0.7, 0.6)):
    """One global depth sort over every triangle, so parts occlude correctly."""
    M = view_matrix(az, el)
    v = tris @ M.T
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    n = n / np.where(ln == 0, 1, ln)
    L = np.array(light) / np.linalg.norm(light)
    shade = np.clip(0.32 + 0.68 * np.abs(n @ L), 0, 1)
    order = np.argsort(v[:, :, 1].max(axis=1))
    ax.add_collection(PolyCollection(v[order][:, :, [0, 2]],
                                     facecolors=colors[order] * shade[order][:, None],
                                     edgecolors="none"))
    return v


def render(specs, path, title, az=35, el=22, figsize=(13, 7)):
    fig, ax = plt.subplots(figsize=figsize)
    tris, cols = [], []
    for spec in specs:
        name, color = spec[0], spec[1]
        dz = spec[3] if len(spec) > 3 else 0.0
        p = os.path.join(OUT, f"{name}.stl")
        if not os.path.exists(p):
            continue
        t = load_stl(p)
        t[:, :, 2] += dz
        tris.append(t)
        cols.append(np.tile(matplotlib.colors.to_rgb(color), (len(t), 1)))
    v = draw(ax, np.vstack(tris), np.vstack(cols), az, el).reshape(-1, 3)
    pad = 4
    ax.set_xlim(v[:, 0].min() - pad, v[:, 0].max() + pad)
    ax.set_ylim(v[:, 2].min() - pad, v[:, 2].max() + pad)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title, fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=105, facecolor="white")
    plt.close(fig)
    print("wrote", path)


if __name__ == "__main__":
    render([("base_plate", "#5b8dd9", 1)], os.path.join(OUT, "r_base_plate.png"),
           "base plate - probe platform, guide posts, spring pockets")
    render([("nest", "#e0a33c", 1)], os.path.join(OUT, "r_nest.png"),
           "nest - board recess, relief window, locator pins")
    render([("nest", "#e0a33c", 1)], os.path.join(OUT, "r_nest_under.png"),
           "nest, underside - spring counterbores", az=35, el=-25)
    render([("cover", "#c05b5b", 1)], os.path.join(OUT, "r_cover.png"),
           "hold-down cover, underside - five contact pads", az=35, el=-30)
    render([("stand", "#7d7d7d", 1), ("clamp_riser", "#4aa06a", 1)],
           os.path.join(OUT, "r_stand.png"), "stand + clamp riser")
    render([("stand", "#8a8a8a", 1), ("clamp_riser", "#4aa06a", 1),
            ("base_plate", "#5b8dd9", 1), ("nest", "#e0a33c", 1),
            ("cover", "#c05b5b", 1, 7.627)],
           os.path.join(OUT, "r_assembly.png"),
           "assembly - stand, base plate, nest, hold-down cover, clamp riser",
           az=38, el=20, figsize=(15, 8))
