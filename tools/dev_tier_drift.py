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

**It reads a report from this machine, and only this machine.** That is
a deviation from `UX-418`'s filing, which asks for a CI step, and it was
paid for with three CI runs:

1. The step called three medium files large at 20.4-21.5s; here they are
   11.3-13.5s. A fixed slack was the first answer - wrong by a factor on
   the first foreign clock it met.
2. A scale derived from the report was the second. Also wrong: on CI the
   **median** listed file runs at 1.05x its recorded number while
   `test_report_stays_readable_at_scale` runs at 1.61x and
   `test_marginal_efficiency_gate` at 1.73x, neither having grown. The
   difference is per file, so no single scale exists.
3. Comparing **rank** rather than seconds was the third, on the argument
   that the order survives a change of machine. It does not:
   `test_report_stays_readable_at_scale` is recorded below all 22 large
   files here, and on CI it read 25.3s - above 11 of them.

Three measurements, one conclusion: **per-file timings from another
runner cannot be compared to this repository's tier record in any form**
- not absolute, not scaled, not ranked - because the runners differ per
file rather than by a factor. So the comparison is like for like, on the
machine the floors were measured on, and CI keeps the small-tier timeout
it already has, which is sized against CI's own clock (see
`SMALL_TIER_CI_SLOW_S` in `tests/tiers.py`). What a CI-side check would
need is a CI-side reference, and that is filed as `UX-420` rather than
guessed at a fourth time.

Run it after a full run, which `make test-tiers` does in one command:

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

#: The tier each one is measured against - see `boundaries`.
ABOVE = {"small": "medium", "medium": "large"}


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


def tier_for(seconds):
    """The tier a measurement puts a file in, by the declared floors."""
    if seconds >= tiers.LARGE_FLOOR_S:
        return "large"
    if seconds >= tiers.MEDIUM_FLOOR_S:
        return "medium"
    return "small"


def listed_tier(name):
    if name in tiers.LARGE:
        return "large"
    if name in tiers.MEDIUM:
        return "medium"
    return "small"


def drift(times):
    """`[(file, seconds, listed, measured)]`, worst first.

    Only the direction that hides cost: a file measured *above* the tier
    it is listed in. The other direction - a file that got faster and
    now sits in a slower tier - wastes nothing and is left to the
    re-measure ritual, because reporting it would fail on an ordinary
    fast run.
    """
    found = []
    for name, seconds in times.items():
        was, now = listed_tier(name), tier_for(seconds)
        if RANK[now] > RANK[was]:
            found.append((name, seconds, was, now))
    return sorted(found, key=lambda row: -row[1])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", help="a pytest --junitxml report")
    parser.add_argument("--quiet", action="store_true",
                        help="print nothing when there is no drift")
    args = parser.parse_args(argv)

    times = measured(args.report)
    if not times:
        print(f"{args.report}: no testcase named a file under {REPO} - "
              f"this step measured nothing", file=sys.stderr)
        return 2
    found = drift(times)
    line = (f"{len(times)} file(s) measured against the declared floors "
            f"(medium {tiers.MEDIUM_FLOOR_S}s, large {tiers.LARGE_FLOOR_S}s)")
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
    print("\nRe-measure each and move it in tests/tiers.py with its "
          "seconds, or make it faster. The floors are the authority; this "
          "only reads them - and it reads them against a report from this "
          "machine, which is the only report they mean anything about.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
