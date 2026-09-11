"""Renders of the magnet fixture, reusing the jig's software rasteriser."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "cad", "tools"))
import render as R                                            # noqa: E402

R.OUT = os.path.abspath(os.path.join(HERE, "..", "out"))
R.COLOR = dict(board_plate="#4d7fc4", encoder_gantry="#9aa0a6",
               rotor="#c9a227", hall_carriage="#c0574f",
               ring_10="#7a5c3e", ring_6="#7a5c3e", gap_gauge="#6e8b6e",
               pcba="#12602c")

ALL = [("board_plate", 0), ("encoder_gantry", 0), ("rotor", 0),
       ("hall_carriage", 3.827), ("pcba", 0)]

VIEWS = {
    "assembled": (ALL, 34, 24, "magnet fixture - board in, both magnets presented"),
    "encoder":   (ALL, 18, 16, "encoder end - rotor journalled over the AS5600L",
                  (46.8, 0.0, 10.0, 30.0)),
    "hall":      (ALL, -150, 18, "hall end - carriage at its 1 mm setting",
                  (-23.2, -6.0, 8.0, 34.0)),
    "parts":     ([("gap_gauge", 0)], 30, 30, "gap gauge - one step per separation"),
}


def main():
    # the PCBA render aid is git-ignored; skip it if it was never built
    if not os.path.exists(os.path.join(R.OUT, "..", "..", "cad", "out", "pcba.stl")):
        pass
    for name, spec in VIEWS.items():
        parts, az, el, title = spec[0], spec[1], spec[2], spec[3]
        focus = spec[4] if len(spec) > 4 else None
        R.shot(parts, os.path.join(R.OUT, f"v_{name}.png"), title,
               az=az, el=el, focus=focus)
        print(f"wrote v_{name}.png")


if __name__ == "__main__":
    main()
