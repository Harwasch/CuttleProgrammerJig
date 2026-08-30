"""Annotated section through the probe cluster, drawn from params.py.

This is the drawing to check before printing: every Z relationship in the jig
is derived from PIN_PROTRUSION, COMPRESSION, NEST_T and TRAVEL.
"""
import os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import params as P

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
C = dict(base="#5b8dd9", nest="#e0a33c", pcb="#2f7d32", cover="#c05b5b",
         probe="#b8860b", part="#777777")


def panel(ax, dz, title):
    seat = P.NEST_T + dz                      # PCB underside
    pcb_top = seat + P.PCB_T
    tip = P.Z_PIN_TOP + P.PIN_PROTRUSION      # free probe tip height
    contact = min(tip, seat)                  # where the tip actually sits

    ax.add_patch(Rectangle((-34, -8), 46, 8, fc=C["base"], ec="k", lw=.8))
    ax.add_patch(Rectangle((-33, 0), 20, P.Z_PIN_TOP, fc=C["base"], ec="k", lw=.8))
    ax.text(-23, P.Z_PIN_TOP / 2, "probe platform", ha="center", va="center",
            fontsize=7, color="white")

    # probe: sleeve in the plate, tip proud of the platform
    for x in (-28, -21, -15):
        ax.add_patch(Rectangle((x - .45, P.Z_PIN_TOP - 8.5), .9, 8.5,
                               fc="none", ec=C["probe"], lw=1.1, ls="--"))
        ax.plot([x, x], [P.Z_PIN_TOP, contact], color=C["probe"], lw=2.4,
                solid_capstyle="butt")
        ax.plot(x, contact, marker="^", ms=5, color=C["probe"])

    # nest, split around the window
    for x0, x1 in [(-34, -31.5), (-9.5, 12)]:
        ax.add_patch(Rectangle((x0, dz), x1 - x0, P.NEST_T, fc=C["nest"], ec="k", lw=.8))
        ax.add_patch(Rectangle((x0, dz + P.NEST_T), x1 - x0, P.NEST_LIP,
                               fc=C["nest"], ec="k", lw=.8))
    ax.text(1, dz + P.NEST_T / 2, "nest", ha="center", va="center", fontsize=8)

    ax.add_patch(Rectangle((-33, seat), 44, P.PCB_T, fc=C["pcb"], ec="k", lw=.8))
    ax.text(6, seat + P.PCB_T / 2, "PCB", color="white", fontsize=7,
            ha="center", va="center")
    # a tall bottom-side part
    ax.add_patch(Rectangle((-12.5, seat - P.PART_H_BOTTOM), 4, P.PART_H_BOTTOM,
                           fc=C["part"], ec="k", lw=.6))
    ax.text(-10.5, seat - P.PART_H_BOTTOM - .7, f"{P.PART_H_BOTTOM} mm part",
            fontsize=6, ha="center", color="#444")

    ax.add_patch(Rectangle((-30, pcb_top), 3.2, P.COVER_PAD_H, fc=C["cover"], ec="k", lw=.6))
    ax.add_patch(Rectangle((-17, pcb_top), 3.2, P.COVER_PAD_H, fc=C["cover"], ec="k", lw=.6))
    ax.add_patch(Rectangle((-32, pcb_top + P.COVER_PAD_H), 22, P.COVER_T,
                           fc=C["cover"], ec="k", lw=.8))
    ax.text(-21, pcb_top + P.COVER_PAD_H + P.COVER_T / 2, "hold-down cover",
            color="white", fontsize=7, ha="center", va="center")

    for z, lab in [(0, "z=0  hard stop"), (P.Z_PIN_TOP, f"platform top  {P.Z_PIN_TOP:.2f}"),
                   (seat, f"PCB seat  {seat:.2f}"), (tip, f"free probe tip  {tip:.2f}")]:
        ax.axhline(z, color="k", lw=.4, ls=":", alpha=.6)
        ax.text(12.8, z, lab, fontsize=6.5, va="center", color="#333")

    if dz == 0:
        ax.annotate("", xy=(-21, seat), xytext=(-21, tip),
                    arrowprops=dict(arrowstyle="<->", color="crimson", lw=1.3))
        ax.text(-20.4, (seat + tip) / 2, f"{P.COMPRESSION:.2f} mm\nprobe stroke",
                fontsize=7, color="crimson", va="center")
    else:
        ax.annotate("", xy=(-21, contact), xytext=(-21, seat),
                    arrowprops=dict(arrowstyle="<->", color="teal", lw=1.3))
        ax.text(-20.4, (contact + seat) / 2,
                f"{P.TRAVEL - P.COMPRESSION:.2f} mm\nloading gap",
                fontsize=7, color="teal", va="center")
    ax.set_xlim(-36, 26); ax.set_ylim(-9, 20)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title, fontsize=10)


fig, axes = plt.subplots(1, 2, figsize=(15, 6))
panel(axes[0], P.TRAVEL, f"clamp OPEN - nest up {P.TRAVEL:.1f} mm on the springs")
panel(axes[1], 0.0, "clamp CLOSED - nest on the hard stop, probes compressed")
fig.suptitle("Cuttle CANServo_Driver programming jig - vertical stack-up "
             f"(P50-B1 tip {P.PIN_PROTRUSION} mm proud of its R50 sleeve)", fontsize=11)
fig.tight_layout()
p = os.path.join(OUT, "stackup.png")
fig.savefig(p, dpi=115, facecolor="white")
print("wrote", p)
