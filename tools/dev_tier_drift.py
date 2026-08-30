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


def tier_for(seconds, slack=1.0):
    """The tier a measurement puts a file in.

    `slack` scales the floors, not the measurement, so the message can
    still print the seconds that were read. It exists because CI's full
    run is `-n auto` and a test's wall clock inside a worker carries its
    neighbours' contention - see `PARALLEL_REPORT_SLACK` in
    `tests/tiers.py` for the measured spread and what it costs.
    """
    if seconds >= tiers.LARGE_FLOOR_S * slack:
        return "large"
    if seconds >= tiers.MEDIUM_FLOOR_S * slack:
        return "medium"
    return "small"


def listed_tier(name):
    if name in tiers.LARGE:
        return "large"
    if name in tiers.MEDIUM:
        return "medium"
    return "small"


def drift(times, slack=1.0):
    """`[(file, seconds, listed, measured)]`, worst first.

    Only the direction that hides cost: a file measured *above* the
    tier it is listed in. The other direction - a file that got faster
    and now sits in a slower tier - wastes nothing and is left to the
    re-measure ritual, because reporting it would make this step fail
    on an ordinary fast run.
    """
    found = []
    for name, seconds in times.items():
        was, now = listed_tier(name), tier_for(seconds, slack)
        if RANK[now] > RANK[was]:
            found.append((name, seconds, was, now))
    return sorted(found, key=lambda row: -row[1])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", help="a pytest --junitxml report")
    parser.add_argument("--quiet", action="store_true",
                        help="print nothing when there is no drift")
    parser.add_argument("--exact", action="store_true",
                        help="read the floors as they stand, for a report "
                             "taken single-process")
    args = parser.parse_args(argv)
    slack = 1.0 if args.exact else tiers.PARALLEL_REPORT_SLACK

    times = measured(args.report)
    if not times:
        print(f"{args.report}: no testcase named a file under {REPO} - "
              f"this step measured nothing", file=sys.stderr)
        return 2
    found = drift(times, slack)
    if not found:
        if not args.quiet:
            print(f"tiers ok: {len(times)} file(s) measured, none above the "
                  f"tier it is listed in "
                  f"(floors: medium {tiers.MEDIUM_FLOOR_S}s, "
                  f"large {tiers.LARGE_FLOOR_S}s, x{slack} slack)")
        return 0
    print(f"{len(found)} file(s) measured above the tier tests/tiers.py "
          f"lists them in:", file=sys.stderr)
    for name, seconds, was, now in found:
        print(f"  {name}  {seconds:.1f}s  listed {was}, measured {now}",
              file=sys.stderr)
    print("\nAdd each to the named list in tests/tiers.py with its measured "
          "seconds, or make it faster. The floors are the authority "
          f"(medium {tiers.MEDIUM_FLOOR_S}s, large {tiers.LARGE_FLOOR_S}s); "
          "this only reads them.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
