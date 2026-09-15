"""Check measured pogo hardware against what the jig was built for.

Measure what you can, pass it in, and this says whether the plate you are
about to print (or already printed) still works, which params.py lines to
change, and whether the change needs a reprint.

  JIG_PINS=P100 python3 tools/check_pins.py --protrusion 8.4 --head 7.6

Every argument is optional; anything you leave out is reported as unmeasured
rather than assumed good.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import params as P                                            # noqa: E402

OK, BAD, SKIP = "  ok  ", " FAIL ", "  --  "


def band(name, got, lo, hi, model, unit="mm"):
    if got is None:
        print(f"[{SKIP}] {name:34s} not measured  (model {model:g} {unit})")
        return True
    good = lo - 1e-9 <= got <= hi + 1e-9
    print(f"[{OK if good else BAD}] {name:34s} {got:6.2f}  "
          f"(model {model:g}, window {lo:.2f}..{hi:.2f})")
    return good


def main():
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--protrusion", type=float,
                   help="probe tip above the receptacle's top face, probe seated")
    a.add_argument("--head", type=float,
                   help="length of the enlarged top section of the receptacle")
    a.add_argument("--receptacle", type=float, help="receptacle overall length")
    a.add_argument("--head-dia", type=float, help="receptacle head diameter")
    a.add_argument("--body-dia", type=float, help="receptacle body diameter")
    a.add_argument("--stroke", type=float, help="probe full travel before it bottoms")
    v = a.parse_args()

    print(f"pin family {P.PIN_FAMILY}, seat z={P.Z_PIN_TOP:+.3f}, "
          f"counterbore {P.PIN_HEAD_BORE_L:.1f} mm deep\n")

    bp = P.PIN_BODY_BORE_D - P.PRINT_HOLE_SHRINK
    hp = P.PIN_BORE_D - P.PRINT_HOLE_SHRINK
    bore_d = P.Z_PIN_TOP - P.PLATE_Z_BOTTOM
    room = P.PLATE_Z_BOTTOM - P.STAND_Z_BOTTOM
    ok = all([
        band("receptacle overall length", v.receptacle,
             3.0 + bore_d, room - 4.0 + bore_d, P.RECEPT_LEN),
        band("probe full travel", v.stroke,
             P.COMPRESSION / 0.7, 99.0, P.PIN_STROKE_MAX),
        band("receptacle head diameter", v.head_dia,
             max(hp - 0.06, bp + 0.02), hp + 0.02, P.RECEPT_HEAD_D),
        band("receptacle body diameter", v.body_dia,
             bp - 0.16, bp - 0.02, P.RECEPT_BODY_D),
    ])

    # The one that decides everything. The receptacle's head bottoms on a
    # shoulder at a FIXED depth, so the tip ends up at
    #   (seat - HEAD_L_modelled) + head_measured + protrusion_measured
    # and an error in either lands on the working stroke one for one.
    print()
    dh = None if v.head is None else v.head - P.RECEPT_HEAD_L
    dp = None if v.protrusion is None else v.protrusion - P.PIN_PROTRUSION
    if dh is None and dp is None:
        print("[" + SKIP + "] working stroke                     "
              "neither head length nor protrusion measured -- this is the pair "
              "the whole stack-up rests on")
        ok = False
    else:
        err = (dh or 0.0) + (dp or 0.0)
        c = P.COMPRESSION + err
        lo, hi = 0.8, 0.7 * P.PIN_STROKE_MAX
        good = lo <= c <= hi
        ok = ok and good
        parts = []
        if dh is not None:
            parts.append(f"head {dh:+.2f}")
        if dp is not None:
            parts.append(f"protrusion {dp:+.2f}")
        partial = "" if (dh is not None and dp is not None) else "  (PARTIAL)"
        print(f"[{OK if good else BAD}] working stroke as built            "
              f"{c:5.2f} mm of {P.PIN_STROKE_MAX:.2f}  "
              f"[{', '.join(parts)}]{partial}")
        print(f"        window {lo:.2f}..{hi:.2f} mm -- under it the probe may not "
              f"make contact, over it it bottoms out")

    print()
    stroke_ok = ok if (dh is not None or dp is not None) else False
    edits = []
    if dp is not None and abs(dp) > 1e-9:
        edits.append(("PIN_PROTRUSION", P.PIN_PROTRUSION, v.protrusion, True))
    if dh is not None and abs(dh) > 1e-9:
        edits.append(("RECEPT_HEAD_L", P.RECEPT_HEAD_L, v.head, True))
    for nm, cur, got, rp in (
            ("RECEPT_LEN", P.RECEPT_LEN, v.receptacle, False),
            ("RECEPT_HEAD_D", P.RECEPT_HEAD_D, v.head_dia, True),
            ("RECEPT_BODY_D", P.RECEPT_BODY_D, v.body_dia, True),
            ("PIN_STROKE_MAX", P.PIN_STROKE_MAX, v.stroke, False)):
        if got is not None and abs(got - cur) > 1e-9:
            edits.append((nm, cur, got, rp))
    if edits:
        print(f"edit these in params.py, under the {P.PIN_FAMILY} branch:")
        for nm, cur, got, rp in edits:
            print(f"    {nm:16s} {cur:g}  ->  {got:g}"
                  + ("     (moves geometry)" if rp else "     (checks only)"))
        print("\nthen:  JIG_PINS=%s python3 jig.py && JIG_PINS=%s python3 verify.py"
              % (P.PIN_FAMILY, P.PIN_FAMILY))
        if stroke_ok:
            print("A plate printed to the OLD numbers is still inside the stroke\n"
                  "window, so this is a model correction, not a reprint.")
        else:
            print("The stroke is outside its window, so a plate printed to the old\n"
                  "numbers will not work: rebuild and REPRINT the base plate.")
    else:
        print("nothing to change" if ok else
              "measurements are outside the windows above -- see the FAILs")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
