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

**And it compares rank, not seconds, because those floors are seconds
on one machine.** Two CI runs taught that, in order:

1. The step called three medium files large at 20.4-21.5s. On the
   machine the tiers were measured on they are 11.3-13.5s. Nothing had
   drifted. A fixed slack was the first answer and was wrong by a
   factor on the first foreign clock it met.
2. A derived scale was the second answer, and it is wrong too: measured
   on CI, the **median** listed file runs at 1.05x this repository's
   recorded numbers while `test_report_stays_readable_at_scale` runs at
   1.61x and `test_marginal_efficiency_gate` at 1.73x. Neither had
   grown - here they are 1.05-1.10x their records. The difference is
   *per file*, so there is no single scale to find.

What survives a change of machine is the **order**. The tiers are a
ranking, so a file has drifted when it is slower than the middle of the
tier above it **in the same report** - two numbers from one run, one
clock. `boundaries()` below is that rule.

The cost is stated rather than hidden: this catches a file that has
outrun its neighbours, not one a second over its floor. `--exact`
restores the floor comparison for a report taken on the machine they
were measured on, which is where seconds are the right question.

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


def boundaries(times, minimum=8):
    """`{tier: the median measured time of the tier above it}`.

    **The comparison is a rank, not a number of seconds**, and that is
    the whole design. Two CI runs taught it: the floors in
    `tests/tiers.py` are seconds on one machine, and a report can come
    from another, where the same file takes a different time. A fixed
    slack could not fix that (wrong by a factor on the first foreign
    clock it met) and neither could a derived one - measured on CI, the
    *median* listed file runs at 1.05x this repository's recorded
    numbers while two particular files run at 1.61x and 1.73x. The
    difference is per-file, so no single scale exists to find.

    What is portable is the order. The tiers are a ranking by
    construction, so a file drifts when it is slower than the *middle*
    of the tier above it **in the same report** - both numbers measured
    on one machine, one run, one clock.

    `minimum` is how many members of the tier above must appear before
    a median means anything; below it the boundary is not returned and
    `main` refuses rather than comparing against a number it derived
    from three files.
    """
    out = {}
    for tier, names in (("small", tiers.MEDIUM), ("medium", tiers.LARGE)):
        seen = sorted(times[name] for name in names if times.get(name))
        if len(seen) >= minimum:
            middle = len(seen) // 2
            out[tier] = (seen[middle] if len(seen) % 2
                         else (seen[middle - 1] + seen[middle]) / 2)
    return out


def tier_for(seconds, scale=1.0):
    """The tier a measurement puts a file in, by the declared floors.

    Used by `--exact`, for a report taken on the machine the floors were
    measured on - where seconds are the right question and this is the
    more sensitive rule. Across machines, see `boundaries`.
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


def drift(times, limits):
    """`[(file, seconds, listed, over)]`, worst first.

    `limits` is `boundaries(...)`: a file is reported when it is slower
    than the middle of the tier above the one it is listed in. Only
    that direction - a file that got faster wastes nothing, and
    reporting it would red the build on an ordinary good run.
    """
    found = []
    for name, seconds in times.items():
        was = listed_tier(name)
        limit = limits.get(was)
        if limit is not None and seconds > limit:
            found.append((name, seconds, was, limit))
    return sorted(found, key=lambda row: -row[1])


def by_floors(times, scale=1.0):
    """The `--exact` rule: the declared floors, on their own clock."""
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
                        help="compare against the declared floors instead, "
                             "for a report taken on the machine they were "
                             "measured on - more sensitive, and only "
                             "meaningful on that machine")
    args = parser.parse_args(argv)

    times = measured(args.report)
    if not times:
        print(f"{args.report}: no testcase named a file under {REPO} - "
              f"this step measured nothing", file=sys.stderr)
        return 2
    if args.exact:
        found = by_floors(times)
        line = (f"{len(times)} file(s) measured against the declared floors "
                f"(medium {tiers.MEDIUM_FLOOR_S}s, large "
                f"{tiers.LARGE_FLOOR_S}s)")
        detail = [f"  {name}  {seconds:.1f}s  listed {was}, measured {now}"
                  for name, seconds, was, now in found]
    else:
        limits = boundaries(times)
        if not limits:
            print(f"{args.report}: too few listed files in it to place a "
                  f"boundary. Refusing to compare against a median drawn "
                  f"from almost nothing.", file=sys.stderr)
            return 2
        found = drift(times, limits)
        line = (f"{len(times)} file(s) measured; this run's boundaries are "
                + ", ".join(f"{tier} > {limit:.1f}s"
                            for tier, limit in sorted(limits.items()))
                + " (the median of the tier above, in this report)")
        detail = [f"  {name}  {seconds:.1f}s  listed {was}, and slower than "
                  f"this run's median {ABOVE[was]} file ({limit:.1f}s)"
                  for name, seconds, was, limit in found]
    # Printed whether or not anything drifted: the boundary is what
    # decides, and the run that reddens is not the first place it should
    # be visible.
    if not found:
        if not args.quiet:
            print(f"tiers ok: {line}")
        return 0
    print(line, file=sys.stderr)
    print(f"{len(found)} file(s) measured above the tier tests/tiers.py "
          f"lists them in:", file=sys.stderr)
    for row in detail:
        print(row, file=sys.stderr)
    print("\nRe-measure each on this machine and move it in tests/tiers.py "
          "with its seconds, or make it faster. The floors are the "
          f"authority for placing a file (medium {tiers.MEDIUM_FLOOR_S}s, "
          f"large {tiers.LARGE_FLOOR_S}s on the machine they were measured "
          "on); this only reports one that has outrun its neighbours.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
