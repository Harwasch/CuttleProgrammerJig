"""Which printed parts actually differ between the two pin families.

The claim in the README -- that a P100 jig is a new base plate, a new stand and
a new fit gauge, and that the nest and the cover carry straight over -- is the
kind of thing that quietly stops being true. This measures it: each part is
built in a fresh interpreter per family and compared on volume, bounding box
and topology.

Run:  python3 tools/compare_families.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = """
import json, jig
out = {}
for n, fn in jig.PARTS_TO_BUILD.items():
    s = fn()
    bb = s.bounding_box()
    out[n] = [round(s.volume, 4), len(s.faces()), len(s.edges()),
              [round(v, 4) for v in (bb.min.X, bb.min.Y, bb.min.Z,
                                     bb.max.X, bb.max.Y, bb.max.Z)]]
print(json.dumps(out))
"""


def build(family):
    env = dict(os.environ, JIG_PINS=family)
    r = subprocess.run([sys.executable, "-c", CODE], env=env,
                       cwd=os.path.join(HERE, ".."),
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{family} build failed:\n{r.stderr}")
    return json.loads(r.stdout)


def main():
    a, b = build("P50"), build("P100")
    shared, differs = [], []
    for name in a:
        (shared if a[name] == b[name] else differs).append(name)
    for name in sorted(differs):
        print(f"  DIFFERS  {name:12s} "
              f"{a[name][0]:9.1f} -> {b[name][0]:9.1f} mm3")
    for name in sorted(shared):
        print(f"  same     {name:12s} {a[name][0]:9.1f} mm3, "
              f"{a[name][1]} faces, {a[name][2]} edges")
    print(f"\n{len(differs)} part(s) change, {len(shared)} carry straight over")


if __name__ == "__main__":
    main()
