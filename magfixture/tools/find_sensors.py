"""Locate the two magnetic sensors in the board's own STEP export.

The KiCad STEP carries each component's footprint name as a label, so the
sensor positions in mag_params.py are measured rather than transcribed. Run
this after a board revision to confirm they have not moved.

Run:  python3 tools/find_sensors.py
"""
import os
import sys

from build123d import *

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "cad"))
import geom as G                                              # noqa: E402

STEP = os.path.join(HERE, "..", "..", "cad", "ref",
                    "CANServo_Driver_v0.4.step")
WANTED = {"AS5600L": "rotary encoder", "SOT-23": "linear hall sensor"}


def main():
    OX, OY = G.BOARD["origin_in_gerber_coords"]
    comp = import_step(STEP)
    board_top = max(b for b in [0.0] + [
        (Pos(-OX, -OY) * k).bounding_box().min.Z
        for k in comp.children if "PCB" in (k.label or "")])
    print(f"board top face at z = {board_top:.3f} in STEP coordinates\n")
    print(f"{'label':22} {'centre X':>9} {'centre Y':>9} {'pkg top':>9}  role")
    for k in comp.children:
        lab = k.label or ""
        role = next((v for w, v in WANTED.items() if w in lab), None)
        if role is None:
            continue
        b = (Pos(-OX, -OY) * k).bounding_box()
        cx, cy = (b.min.X + b.max.X) / 2, (b.min.Y + b.max.Y) / 2
        print(f"{lab:22} {cx:9.2f} {cy:9.2f} {b.max.Z - board_top:9.2f}  {role}")
    print("\nPaste centre X/Y into ENC_XY / HALL_XY and the package height "
          "into ENC_PKG_H / HALL_PKG_H.")


if __name__ == "__main__":
    main()
