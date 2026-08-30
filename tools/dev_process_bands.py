"""What the process did to itself, counted from the committed record.

This repository measures its product obsessively and its process not at
all. Round 66 alone produced numbers nobody collected: six filings
resting on premises nobody had checked, five guards in one item that
could not discriminate, three red CI rounds spent on three wrong
designs for one check.

The AI-native SDLC playbook's Maintenance stage watches a metric with a
rolling baseline and acts when a control band is breached. Its own
Plays preamble promises every play will cover "How you measure whether
it worked" - and then no play does. This is the missing half, aimed at
the one process whose record is complete enough to count: the 421 task
files, whose Outcome sections have carried the same headings since
`UX-336` printed the skeleton.

**It reports; it does not verdict**, and the second reason is the one
worth keeping. A band needs a baseline and one reading is not one -
sizing a threshold on a single sample is what `UX-420` did with
`CI_DRIFT_FACTOR`, and its first armed run reported thirty-one files on
an unchanged suite. But the sharper problem is that half these rows are
**ambiguous by direction**: "found a guard of its own that could not
discriminate" rising means either more bad guards or better detection,
and a band would fire on improvement. The falsify rate is the one row
that reads the same way from both ends, and it is where a band should
start.

    python tools/dev_process_bands.py
    python tools/dev_process_bands.py --window 40 --json
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
#: Each is a phrase the repository already writes by convention, not a
#: field anyone has to remember to fill in. A metric that needs a new
#: ritual is a metric that stops being collected in three rounds.
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
     "found the premise it was filed on was false",
     re.compile(r"false premise|premise[^.]{0,40}(was|is) false|"
                r"rested on a false|whole Motivation.{0,40}false", re.I)),
)


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
    totals["deviation_stated"] = sum(1 for _n, f in rows
                                     if f["deviation_stated"])
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
        whole = rate(sum(1 for _n, f in rows if f[key]), len(rows))
        near = rate(sum(1 for _n, f in recent if f[key]), len(recent))
        lines.append(f"{headline:52s}  {whole:5.1%}   {near:5.1%}")
    stated = rate(sum(1 for _n, f in rows if f["deviation_stated"]), len(rows))
    lines += [
        "",
        f"{'states a Deviation section at all':52s}  {stated:5.1%}",
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
                                     for key, _h, _p in SIGNALS}}, indent=2))
        return 0
    print("\n".join(report(rows, args.window)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
