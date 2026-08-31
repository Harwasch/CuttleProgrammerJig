"""Plan diagram of what the nest actually touches."""
import os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Point
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import geom as G, params as P

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
fig, ax = plt.subplots(figsize=(22, 5.6))


def poly(p, **kw):
    for g in (list(p.geoms) if p.geom_type.startswith("Multi") else [p]):
        ax.fill(*g.exterior.xy, **kw)
        for r in g.interiors:
            ax.fill(*r.xy, fc="white", ec="none", zorder=kw.get("zorder", 1) + 1)


poly(G.OUTLINE, fc="#f2f2f2", ec="k", lw=.9, zorder=1)
poly(G.nest_recess(), fc="#ffffff", ec="#bbbbbb", lw=.5, zorder=2)
poly(G.bare_sections(), fc="#8fc98f", ec="#2a7a2a", lw=.8, zorder=3)
poly(G.seat_bosses(), fc="#4d8fd9", ec="#1b4f8f", lw=.9, zorder=4)
for x0, x1, y0, y1, h in G.PARTS["bottom"]:
    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#d0d0d0",
                               ec="#999", lw=.3, zorder=2.5))
mx, my, ms, mh = P.MCU_BOSS
ax.add_patch(plt.Rectangle((mx - ms / 2, my - ms / 2), ms, ms, fc="#c85fc8",
                           ec="#7a2d7a", lw=1.2, zorder=6))
ax.annotate(f"MCU boss\nstops {P.MCU_BOSS_CLEAR} mm short", (mx, my - 3.4),
            fontsize=7, ha="center", va="top", color="#7a2d7a", zorder=9)
for t in G.TEST_POINTS:
    ax.add_patch(plt.Circle((t["x"], t["y"]), P.PROBE_CLEAR_D / 2, fc="none",
                            ec="#d94a4a", lw=1.2, ls="--", zorder=7))
    ax.add_patch(plt.Circle((t["x"], t["y"]), 0.6, fc="#d94a4a", zorder=8))
for n in P.SEAT_BOSSES:
    x, y = G.HOLES[n]
    pin = (P.LOCATOR_D if n in P.LOCATOR_PRIMARY else
           P.LOCATOR_D2 if n in P.LOCATOR_SECONDARY else 0)
    if pin:
        # the pin belongs to the base plate; the nest only clears it
        ax.add_patch(plt.Circle((x, y), pin / 2 + P.LOCATOR_NEST_CLEAR, fc="white",
                                ec="#111", lw=1.0, ls=(0, (3, 2)), zorder=9))
        ax.add_patch(plt.Circle((x, y), pin / 2, fc="#111", zorder=10))
    lab = f"{n}\nO{G.boss_radius(n) * 2:.1f}" + (f" pin O{pin:.2f}" if pin else " no pin")
    ax.annotate(lab, (x, y + G.boss_radius(n) + .4), fontsize=6.5, ha="center",
                va="bottom", zorder=9)
for x, y in P.POST_XY:
    ax.add_patch(plt.Circle((x, y), P.POST_HOLE_D / 2, fc="white", ec="b", lw=1, zorder=7))
ax.set_aspect("equal"); ax.grid(alpha=.3, lw=.3)
ax.set_title("nest — BLUE seat bosses at the mounting holes, GREEN bare sections "
             "(no bottom-side parts at all), WHITE single relief pocket, GREY "
             "components, RED probe clearance.  BLACK pins belong to the base "
             "plate; dashed = the nest's pass-through")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "nest_plan.png"), dpi=100)
print("wrote nest_plan.png")
