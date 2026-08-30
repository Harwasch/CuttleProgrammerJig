"""Extract component keep-out volumes from the KiCad STEP export.

Writes cad/board_parts.json: axis-aligned footprints + heights for every solid
that sits above or below the board, expressed in the JIG frame (see
extract_board.py). Copper/pad/via films thinner than FILM_T are ignored.
"""
import json, os, sys
from build123d import import_step

HERE = os.path.dirname(os.path.abspath(__file__))
STEP = os.path.join(HERE, "..", "ref", "CANServo_Driver_v0.4.step")
OUT = os.path.join(HERE, "..", "board_parts.json")
OX, OY = 169.4216, -107.5716
FILM_T = 0.12          # ignore solids thinner than this (copper, pads, vias)
FLAT_TOL = 0.02


def main():
    print(f"importing {os.path.basename(STEP)} ...")
    pcba = import_step(STEP)
    solids = pcba.solids()
    print(f"  {len(solids)} solids")

    # The board slab is the solid with the largest XY footprint.
    boxes = [(s.bounding_box(), s) for s in solids]
    slab = max(boxes, key=lambda t: (t[0].max.X - t[0].min.X) * (t[0].max.Y - t[0].min.Y))[0]
    zlo, zhi = slab.min.Z, slab.max.Z
    print(f"  board slab z = {zlo:.4f} .. {zhi:.4f} ({zhi - zlo:.4f} mm)")

    top, bottom = [], []
    for b, _ in boxes:
        rec = [round(b.min.X - OX, 3), round(b.max.X - OX, 3),
               round(b.min.Y - OY, 3), round(b.max.Y - OY, 3)]
        if b.max.Z <= zlo + FLAT_TOL:
            h = zlo - b.min.Z
            if h > FILM_T:
                bottom.append(rec + [round(h, 3)])
        elif b.min.Z >= zhi - FLAT_TOL:
            h = b.max.Z - zhi
            if h > FILM_T:
                top.append(rec + [round(h, 3)])

    data = {
        "note": "[xmin, xmax, ymin, ymax, height] per solid, in the JIG frame, mm. "
                "Height is measured from the board surface on that side.",
        "source": "CANServo_Driver_v0.4.step",
        "board_model_thickness_mm": round(zhi - zlo, 4),
        "bottom": sorted(bottom, key=lambda r: -r[4]),
        "top": sorted(top, key=lambda r: -r[4]),
    }
    json.dump(data, open(OUT, "w"), indent=1)
    print(f"  bottom parts {len(bottom)} (max {max(r[4] for r in bottom):.3f} mm)")
    print(f"  top    parts {len(top)} (max {max(r[4] for r in top):.3f} mm)")
    print(f"wrote {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
