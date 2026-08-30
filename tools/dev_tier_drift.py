"""UX-418: a slow file is small until CI times out.

`UX-403`'s guard census mutated one guard per family and watched it go
red. Ten of eleven did. The one that did not was
`test_the_tiers_are_a_partition.py`, under the mutation *a large file
demoted to no tier*:

```text
tier partition               GREEN    14 passed in 0.58s
```

Deleting a **fifty-second** entry from `LARGE` changed nothing. Every
clause in that file reads the two lists against each other or against
the filesystem - *listed files exist*, *no file is in two tiers* - and
`small` is the **default**, so a file that belongs in a tier and is
absent from both is "small on purpose" and nothing says otherwise.

`UX-403` fixed the half that is legible without measuring: a file that
boots a real Chrome says so in its imports, and four were doing it from
the small tier. The half that is left needs a measurement, and
`test_the_tiers_are_a_partition.py` is right to refuse a wall-clock
assertion inside a test - that goes flaky and then gets muted.

So the measurement is taken where one already happens. `make test`
already runs the whole suite in CI; this reads that run's own report
and compares each file against the floors in `tests/tiers.py`. It costs
a parse, not a second suite.

**Why the junit report and not `--durations=0`.** The filing names
`--durations=0`, and its output cannot be summed: pytest hides every
entry under 0.005s behind a count -

```text
(30 durations < 0.005s hidden.  Use -vv to show these durations.)
```

- so a file of two hundred fast tests reads as nothing at all. The
junit report carries every test's total (setup+call+teardown) with no
threshold, which is the same measurement without the hole.

**The floors stay the authority.** Nothing here decides what a tier is;
it reads `LARGE_FLOOR_S` and `MEDIUM_FLOOR_S` and reports the files
whose measurement disagrees with where they are listed.

**And it calibrates first, because those floors are seconds on one
clock.** The first CI run of this step called three medium files large
at 20.4-21.5s; single-process on the machine the tiers were measured on
they are 11.3-13.5s. Nothing had drifted - CI's runner is slower. So
the scale is derived from the report: for every listed file it also
measured, `measured / recorded` reads this runner against the tiers'
own, and the median of those readings moves the floors. See
`TIER_DRIFT_MARGIN` and `recorded()` in `tests/tiers.py`.

    python tools/dev_tier_drift.py <junit.xml>
"""
import argparse
import collections
import pathlib
import sys
import xml.etree.ElementTree as ET

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tests import tiers                                        # noqa: E402

#: Ordered, so "measured above where it is listed" is a comparison.
RANK = {"small": 0, "medium": 1, "large": 2}


def file_of(classname):
    """The test file a junit `classname` came from, or None.

    `tests.unit.test_x.TestY` and `tests.unit.test_x` are both what
    pytest writes, and the report does not say which is which - so the
    longest dotted prefix that is a file on disk is the answer, rather
    than a rule about capitalisation that a class named `test_thing`
    would break.
    """
    parts = classname.split(".")
    while parts:
        path = REPO.joinpath(*parts).with_suffix(".py")
        if path.is_file():
            return str(path.relative_to(REPO))
        parts.pop()
    return None


def measured(report):
    """`{file: seconds}` summed over every testcase in a junit report."""
    total = collections.defaultdict(float)
    for case in ET.parse(report).getroot().iter("testcase"):
        name = file_of(case.get("classname") or "")
        if name:
            total[name] += float(case.get("time") or 0.0)
    return dict(total)


def clock(times):
    """How much slower this report's runner is than the tiers' own.

    For every listed file the report also measured, `measured/recorded`
    is one reading of this runner against the machine the tiers were
    taken on. The **median** of those readings is the scale.

    A median, not a mean: one file that changed since it was recorded
    is a wrong reading, and a scale that any single file can move is a
    scale a slow test can talk its way out of.

    Returns 1.0 when there is nothing to calibrate against, which is
    the honest answer and not a safe one - `main` says so rather than
    comparing against a number it did not derive.
    """
    reference = tiers.recorded()
    ratios = sorted(times[name] / reference[name] for name in reference
                    if times.get(name) and reference[name] > 0)
    if not ratios:
        return None
    middle = len(ratios) // 2
    return (ratios[middle] if len(ratios) % 2
            else (ratios[middle - 1] + ratios[middle]) / 2)


def tier_for(seconds, scale=1.0):
    """The tier a measurement puts a file in, on this report's clock.

    `scale` moves the floors, not the measurement, so the message still
    prints the seconds that were actually read - a step that reported a
    number nobody could reproduce would be worse than none.
    """
    if seconds >= tiers.LARGE_FLOOR_S * scale:
        return "large"
    if seconds >= tiers.MEDIUM_FLOOR_S * scale:
        return "medium"
    return "small"


def listed_tier(name):
    if name in tiers.LARGE:
        return "large"
    if name in tiers.MEDIUM:
        return "medium"
    return "small"


def drift(times, scale=1.0):
    """`[(file, seconds, listed, measured)]`, worst first.

    Only the direction that hides cost: a file measured *above* the
    tier it is listed in. The other direction - a file that got faster
    and now sits in a slower tier - wastes nothing and is left to the
    re-measure ritual, because reporting it would make this step fail
    on an ordinary fast run.
    """
    found = []
    for name, seconds in times.items():
        was, now = listed_tier(name), tier_for(seconds, scale)
        if RANK[now] > RANK[was]:
            found.append((name, seconds, was, now))
    return sorted(found, key=lambda row: -row[1])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", help="a pytest --junitxml report")
    parser.add_argument("--quiet", action="store_true",
                        help="print nothing when there is no drift")
    parser.add_argument("--exact", action="store_true",
                        help="compare against the floors as they stand, "
                             "for a report taken on the tiers' own clock")
    args = parser.parse_args(argv)

    times = measured(args.report)
    if not times:
        print(f"{args.report}: no testcase named a file under {REPO} - "
              f"this step measured nothing", file=sys.stderr)
        return 2
    if args.exact:
        scale, how = 1.0, "no calibration (--exact)"
    else:
        ratio = clock(times)
        if ratio is None:
            print(f"{args.report}: measured none of the {len(tiers.recorded())} "
                  f"listed files, so this runner's clock cannot be read "
                  f"against the tiers'. Refusing to compare seconds from "
                  f"one machine to floors from another.", file=sys.stderr)
            return 2
        scale = ratio * tiers.TIER_DRIFT_MARGIN
        how = (f"x{ratio:.2f} this runner against the tiers' own clock, "
               f"x{tiers.TIER_DRIFT_MARGIN} margin")
    found = drift(times, scale)
    # Printed whether or not anything drifted: the scale is the number
    # that decides, and the run that reddens is not the first place it
    # should be visible.
    line = (f"{len(times)} file(s) measured; floors x{scale:.2f} "
            f"= medium {tiers.MEDIUM_FLOOR_S * scale:.1f}s, "
            f"large {tiers.LARGE_FLOOR_S * scale:.1f}s ({how})")
    if not found:
        if not args.quiet:
            print(f"tiers ok: {line}")
        return 0
    print(line, file=sys.stderr)
    print(f"{len(found)} file(s) measured above the tier tests/tiers.py "
          f"lists them in:", file=sys.stderr)
    for name, seconds, was, now in found:
        print(f"  {name}  {seconds:.1f}s  listed {was}, measured {now}",
              file=sys.stderr)
    print("\nRe-measure each on this machine and add it to the named list "
          "in tests/tiers.py with its seconds, or make it faster. The "
          f"floors are the authority (medium {tiers.MEDIUM_FLOOR_S}s, "
          f"large {tiers.LARGE_FLOOR_S}s on the tiers' own clock); this "
          "only reads them, and calibrates before it does.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
