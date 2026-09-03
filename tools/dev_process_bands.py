"""What the process did to itself, counted from the committed record.

    python tools/dev_process_bands.py
    python tools/dev_process_bands.py --window 40 --json

This repository measures its product obsessively and its process not at
all. Three signals count phrases the Outcome already writes; the fourth
reads the `Premise:` field `dev_close_task.py --outcome` writes, because
the phrase form read 0 % of a round that recorded seven (`UX-586`).

**It reports; it does not verdict.** A band needs a baseline and one
reading is not one (`UX-420`, whose first armed run reported 31 files
on an unchanged suite). The sharper reason is that half these rows are
ambiguous by direction: a rising "found a guard that could not
discriminate" means more bad guards *or* better detection, and a band
would fire on improvement. The falsify rate reads the same from both
ends and is where a band should start. `UX-497` has the argument.
"""
import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
SCENARIOS = REPO / "docs/backlog/scenarios"

#: `(key, headline, pattern)`. Every pattern is matched against the
#: **Outcome** only - a Motivation describing somebody else's
#: non-discriminating guard is not this item recording one of its own.
#:
#: The first three are phrases the repository already writes by
#: convention. The fourth is a **declared field** the Outcome skeleton
#: writes, `Premise: held | falsified - <one line>`: the phrase form
#: (`false premise|premise...(was|is) false`) missed "the premise is
#: falsified", "premise was wrong" and "premise is half wrong" and read
#: 0 % of a round that recorded seven - shape 1 of fixing guide SS5,
#: measured in `UX-586`. A metric needing a new ritual does stop being
#: collected, so the ritual is the skeleton's, not the writer's.
#:
#: `falsified` is the **Motivation's** claim not surviving measurement.
#: A Required Fix option that turned out unavailable is a *deviation*,
#: which is the row above; counting it here makes two rows one.
SIGNALS = (
    ("falsified",
     "recorded a mutation that reddened a new guard",
     re.compile(r"utations? verified red", re.I)),
    ("non_discriminating",
     "found a guard of its own that could not discriminate",
     re.compile(r"(did|does) not discriminate|non-discriminating", re.I)),
    ("deviated",
     "deviated from its own Required Fix",
     re.compile(r"^\s*-?\s*\*\*None\.\*\*", re.M)),   # inverted below
    ("premise_false",
     "found the premise it was filed on false (of declared)",
     re.compile(r"^\s*\**Premise\**:\**\s*\**falsified\b", re.M | re.I)),
)

#: The same field with either verdict - what `premise_stated` reads, so
#: an Outcome predating `UX-586` is counted neither way rather than
#: silently as "held".
PREMISE_DECLARED = re.compile(r"^\s*\**Premise\**:\**\s*\**(held|falsified)\b",
                              re.M | re.I)


def outcome_of(text):
    """The Outcome section, or None if the item has not been closed."""
    if "## Outcome" not in text:
        return None
    return "## Outcome" + text.split("## Outcome", 1)[1]


def read(path):
    """`{key: bool}` for one task file, or None if it has no Outcome."""
    outcome = outcome_of(path.read_text(encoding="utf-8"))
    if outcome is None:
        return None
    found = {}
    for key, _headline, pattern in SIGNALS:
        hit = bool(pattern.search(outcome))
        # `deviated` is the one signal whose pattern matches the *absence*
        # of the thing being counted: the section is mandatory and says
        # "None." when there was no deviation. A file with no Deviation
        # section at all predates the heading and is not counted either
        # way, which `unstated` records rather than hides.
        if key == "deviated":
            stated = "Deviation from the Required Fix" in outcome
            found["deviation_stated"] = stated
            hit = stated and not hit
        # `premise_false` reads a declared field and not the prose around
        # it, so an Outcome declaring none is counted in neither
        # direction and `premise_stated` says how many can be.
        if key == "premise_false":
            found["premise_stated"] = bool(PREMISE_DECLARED.search(outcome))
        found[key] = hit
    return found


def census(paths):
    """`(rows, totals)` over every closed item, oldest id first."""
    rows = []
    for path in sorted(paths):
        found = read(path)
        if found is not None:
            rows.append((path.name, found))
    totals = {key: sum(1 for _n, f in rows if f[key])
              for key, _h, _p in SIGNALS}
    for stated in ("deviation_stated", "premise_stated"):
        totals[stated] = sum(1 for _n, f in rows if f[stated])
    totals["outcomes"] = len(rows)
    return rows, totals


def rate(count, of):
    return 0.0 if not of else count / of


def report(rows, window):
    """The table, as a list of lines."""
    recent = rows[-window:]
    lines = [
        f"{len(rows)} closed item(s) carry an Outcome, of "
        f"{len(list(SCENARIOS.glob('UX-*.md')))} task file(s).",
        "",
        f"{'':52s}  all     last {window}",
    ]
    for key, headline, _pattern in SIGNALS:
        # The premise row's denominator is the items that declare the
        # field, not every closed item: a rate over rows that cannot
        # answer reads the wrong population (fixing guide §5, shape 4).
        of_all, of_near = rows, recent
        if key == "premise_false":
            of_all = [r for r in rows if r[1]["premise_stated"]]
            of_near = [r for r in recent if r[1]["premise_stated"]]
        whole = rate(sum(1 for _n, f in of_all if f[key]), len(of_all))
        near = rate(sum(1 for _n, f in of_near if f[key]), len(of_near))
        lines.append(f"{headline:52s}  {whole:5.1%}   {near:5.1%}")
    stated = rate(sum(1 for _n, f in rows if f["deviation_stated"]), len(rows))
    declared = sum(1 for _n, f in rows if f["premise_stated"])
    near_declared = sum(1 for _n, f in recent if f["premise_stated"])
    lines += [
        "",
        f"{'states a Deviation section at all':52s}  {stated:5.1%}",
        f"{'declares a Premise field at all':52s}  "
        f"{rate(declared, len(rows)):5.1%}   {rate(near_declared, len(recent)):5.1%}"
        f"    ({declared} item(s) of {len(rows)}, UX-586 on)",
        "",
        "No band is drawn, for two reasons and the second is the",
        "stronger one:",
        "",
        "  1. A band needs a baseline and one reading is not one. See",
        "     UX-420 for what sizing a threshold on a single sample",
        "     cost - its first armed run reported 31 files on a suite",
        "     nobody had touched.",
        "  2. Two of these rows are ambiguous by direction. A rising",
        "     'found a guard that could not discriminate' means either",
        "     more bad guards or better detection, and on this record",
        "     it is the second: the falsify rate rose with it. A band",
        "     on an ambiguous metric fires at improvement.",
        "",
        "So the row to band first is the falsify rate, which is",
        "unambiguous - a new guard nobody mutated is a guard nobody",
        "knows can fail, in every direction.",
    ]
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window", type=int, default=40,
                        help="how many of the most recent items the second "
                             "column covers (default 40)")
    parser.add_argument("--json", action="store_true",
                        help="the counts, for a later round to band")
    args = parser.parse_args(argv)

    paths = list(SCENARIOS.glob("UX-*.md"))
    if not paths:
        print(f"no task files under {SCENARIOS}", file=sys.stderr)
        return 2
    rows, totals = census(paths)
    if not rows:
        print("no closed item carries an Outcome section", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"totals": totals, "window": args.window,
                          "recent": {key: sum(1 for _n, f in rows[-args.window:]
                                              if f[key])
                                     for key in
                                     [k for k, _h, _p in SIGNALS]
                                     + ["premise_stated"]}}, indent=2))
        return 0
    print("\n".join(report(rows, args.window)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
