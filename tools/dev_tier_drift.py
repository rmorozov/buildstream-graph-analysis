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
file rather than by a factor.

`UX-420` is the other half, and it follows from the same conclusion:
what CI *can* compare a run against is **CI's own previous numbers**.
One machine against itself over time is the only comparison the three
failures leave standing, so this tool also records and reads a CI-side
reference (`--record`, `--against`). See `AGAINST` below for the four
things that rule has to get right, which is the part `UX-420`'s filing
says to design first.

Run it after a full run, which `make test-tiers` does in one command:

    python tools/dev_tier_drift.py <junit.xml>
"""
import argparse
import collections
import json
import pathlib
import statistics
import sys
import xml.etree.ElementTree as ET

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tests import tiers                                        # noqa: E402

#: Ordered, so "measured above where it is listed" is a comparison.
RANK = {"small": 0, "medium": 1, "large": 2}

#: `UX-420`: where CI's own numbers live, and what reads them.
#:
#: `UX-418` established that CI's seconds cannot be compared to the
#: floors in `tests/tiers.py`, which describe a developer machine. What
#: CI *can* be compared against is CI, so this file records one full
#: run's per-file totals and later runs are read against it. One
#: machine against itself over time.
#:
#: **The reference is the part that rots**, and `UX-420`'s filing says
#: to design that first. Four ways it can, and what answers each:
#:
#: 1. **A new file arrives with no reference.** It would be checked by
#:    nothing - the same silence `UX-418` was filed on, one level along.
#:    So an unreferenced file *over the medium floor* is reported. A new
#:    fast file needs no entry, because nothing about it is at risk.
#: 2. **The runner image changes** and every file shifts together. Per
#:    file that reads as drift everywhere. So the run's **median** ratio
#:    to the reference is taken out first: a uniform shift is not drift,
#:    and if the median leaves `IMAGE_BAND` the message says the
#:    reference is stale rather than naming files.
#: 3. **A file legitimately gets slower** and the reference is never
#:    refreshed, so it alarms forever. `--record` writes a new reference
#:    from a green run; the alarm names that as the answer.
#: 4. **The reference is never taken at all.** Then the step would be a
#:    guard that cannot fail. It says so, prints what to commit, and
#:    `test_the_step_says_so_rather_than_passing_over_no_reference`
#:    holds it.
CI_REFERENCE = REPO / "tests" / "ci_reference.json"

#: How much slower than its own CI reference a file may run before it is
#: reported, *after* the run's median shift is divided out.
CI_DRIFT_FACTOR = 1.5

#: And how many seconds slower, which it must **also** be. A ratio alone
#: was the first rule and the first armed run falsified it: 31 files
#: reported on a suite that had not changed, 24 of them under a second.
#:
#: Run 33306283177, `test (3.11)`, against the reference recorded one
#: run earlier - the same suite plus a JSON file and a document:
#:
#: ```text
#:                                    measured  recorded  ratio  added
#:   test_one_page_behind_the_button       5.9       4.3   1.66  +2.4s
#:   test_one_click_from_investigation     4.4       3.1   1.74  +1.9s
#:   test_plane_two_says_what_it_ran       3.8       2.7   1.77  +1.6s
#:   test_doctor                           1.9       1.2   1.90  +0.9s
#:   test_a_clone_without_the_archive      1.3       0.5   3.29  +0.9s
#:   ... 26 more, all adding under a second
#:   test_the_skills_point_at_the_guides   0.3       0.0  18.27  +0.3s
#: ```
#:
#: **A ratio is meaningless at small magnitudes** - the x18 row is a
#: file that went from 20ms to 300ms, and the x3.29 row added nine
#: hundredths of a second more than the x1.66 row that leads the list.
#: `UX-422` names the same defect in a different guard on the same day:
#: a ratio judges a quantity the noise floor dominates.
#:
#: So a file is reported only when it is slower by **both** measures.
#: The seconds floor is what makes the ratio mean something, and it is
#: sized from the run above: the largest *addition* on an unchanged
#: suite was 2.4s, so 5.0 is that with the margin a single sample
#: deserves. It is still one sample - `spread` on each `--record` is
#: what accumulates the rest.
#:
#: This is the same rule the unreferenced-file branch below already
#: applied ("only where there is something at stake"), which the drift
#: branch should have had from the start and did not.
CI_DRIFT_SECONDS = 5.0

#: Outside this, the whole reference is stale rather than any one file
#: drifting - a new runner image, a Python bump, a changed default
#: parallelism. Wide on purpose: inside it the median is divided out
#: and nothing is lost, and the cost of guessing narrow is a red build
#: that names the wrong thing.
IMAGE_BAND = (0.6, 1.7)

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


def spread(times, reference):
    """What this run said about CI's own run-to-run noise, or None.

    The quartiles of `measured / recorded` with the run's median shift
    divided out - so a value of 1.0 is a file that moved exactly as much
    as the whole runner did, and `max` is the widest one file departed
    from its peers. That is the quantity `CI_DRIFT_FACTOR` should be
    sized against, and there is no measurement of it yet: it is stated
    as the starting value it is. So the command that records writes the
    spread beside the numbers, and a later round reads a history of it
    off the reference's own git log rather than having to run CI twice
    on purpose.
    """
    known = reference.get("files") or {}
    ratios = sorted(times[name] / known[name] for name in known
                    if times.get(name) and known[name] > 0)
    if len(ratios) < 4:
        return None
    middle = statistics.median(ratios)
    normalised = [ratio / middle for ratio in ratios]
    quarter = len(normalised) // 4
    return {"files": len(normalised),
            "shift": round(middle, 3),
            "min": round(normalised[0], 3),
            "p25": round(normalised[quarter], 3),
            "p75": round(normalised[-1 - quarter], 3),
            "max": round(normalised[-1], 3)}


def record(times, source="unknown", reference=None):
    """The reference document a later run is read against.

    `reference` is the one this replaces, and is only read to write the
    `spread` this run saw against it - see `spread`. Absent on the first
    record, and then the document simply has no spread rather than a
    fabricated one.
    """
    document = {
        "measured_on": source,
        "note": ("UX-420: one CI run's per-file totals, so a later CI run "
                 "can be read against CI rather than against the floors in "
                 "tests/tiers.py, which describe a developer machine. "
                 "Refresh with tools/dev_tier_drift.py --record."),
        "files": {name: round(seconds, 2)
                  for name, seconds in sorted(times.items())},
    }
    saw = spread(times, reference or {})
    if saw:
        document["spread"] = saw
    return document


def against(times, reference):
    """`(verdict, shift, rows)` for a run read against CI's own numbers.

    `verdict` is `"ok"`, `"stale"` (the whole reference has moved, so
    naming files would name the wrong thing) or `"drift"`.

    The **median** ratio is divided out first, which is what makes this
    a comparison of one machine against itself *over time* rather than
    against one particular afternoon: a runner image that got 20%
    slower moves every file together and is not drift.

    A file is reported only when it is slower by a ratio **and** by a
    number of seconds - see `CI_DRIFT_SECONDS` for the run that proved
    a ratio alone reports thirty-one files on a suite nobody touched.
    """
    known = reference.get("files") or {}
    ratios = {name: times[name] / known[name] for name in known
              if times.get(name) and known[name] > 0}
    if not ratios:
        return "empty", None, []
    shift = statistics.median(ratios.values())
    if not IMAGE_BAND[0] <= shift <= IMAGE_BAND[1]:
        return "stale", shift, []

    rows = []
    for name, ratio in ratios.items():
        # Both, not either: see CI_DRIFT_SECONDS. `expected` is what the
        # reference says this file costs *on this run's clock*, so the
        # seconds added are the ones the run really paid.
        expected = known[name] * shift
        if (ratio / shift > CI_DRIFT_FACTOR
                and times[name] - expected >= CI_DRIFT_SECONDS):
            rows.append((name, times[name], known[name], ratio / shift))
    # A file with no reference at all is checked by nothing, which is
    # the silence this whole item is about - but only where there is
    # something at stake. A new fast file needs no entry.
    floor = tiers.MEDIUM_FLOOR_S * shift
    for name, seconds in times.items():
        if name not in known and seconds >= floor:
            rows.append((name, seconds, None, None))
    return ("drift" if rows else "ok"), shift, sorted(
        rows, key=lambda row: -row[1])


def _against(times, path, args):
    """`--against`: this run read against CI's own recorded numbers."""
    reference = (json.loads(path.read_text(encoding="utf-8"))
                 if path.is_file() else {})
    # Absent and present-but-unrecorded are the same state: nothing to
    # compare against. The committed file starts in the second, so a
    # document can name the path while it is still waiting for its first
    # run - and either way the step says so rather than passing quietly,
    # which would make it a guard that cannot fail (rot 4).
    if not (reference.get("files") or {}):
        print(f"{path} holds no recorded numbers yet, so nothing is being "
              f"checked. Commit the document below - it is this run's own "
              f"numbers, taken on this runner - and the next run compares "
              f"against it (UX-420).", file=sys.stderr)
        print(json.dumps(record(times, args.source), indent=2))
        return 0
    verdict, shift, rows = against(times, reference)
    where = reference.get("measured_on", "unknown")
    if verdict == "empty":
        print(f"{path} names none of the {len(times)} file(s) this run "
              f"measured, so it cannot be a reference for it. Re-record "
              f"with --record.", file=sys.stderr)
        return 2
    if verdict == "stale":
        print(f"this run is x{shift:.2f} the reference recorded on "
              f"{where}, outside the {IMAGE_BAND[0]}-{IMAGE_BAND[1]} band. "
              f"That is the whole runner moving, not one file drifting - "
              f"re-record with --record and commit it, rather than "
              f"reading the per-file numbers below.", file=sys.stderr)
        return 1
    line = (f"{len(times)} file(s) measured against {path.name} "
            f"({where}), this run x{shift:.2f}")
    if verdict == "ok":
        if not args.quiet:
            print(f"tiers ok: {line}")
        return 0
    print(line, file=sys.stderr)
    print(f"{len(rows)} file(s) slower than CI's own record of them:",
          file=sys.stderr)
    for name, seconds, was, ratio in rows:
        print(f"  {name}  {seconds:.1f}s"
              + (f"  against {was:.1f}s recorded, x{ratio:.2f} after this "
                 f"run's x{shift:.2f} shift" if was is not None
                 else "  and not in the reference at all"), file=sys.stderr)
    print("\nMake it faster, or - if it is meant to cost this - re-record "
          "with --record and commit, which is how the reference stays "
          "true rather than becoming an alarm nobody reads.",
          file=sys.stderr)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", help="a pytest --junitxml report")
    parser.add_argument("--quiet", action="store_true",
                        help="print nothing when there is no drift")
    parser.add_argument("--record", metavar="PATH", nargs="?", const="-",
                        help="write this report as the CI reference "
                             "(`-` prints it), instead of checking")
    parser.add_argument("--against", metavar="PATH", nargs="?",
                        const=str(CI_REFERENCE),
                        help="check against a CI reference rather than "
                             "against the floors - the only comparison "
                             "that means anything on a foreign runner")
    parser.add_argument("--source", default="unknown",
                        help="what produced this report, recorded with it")
    args = parser.parse_args(argv)

    times = measured(args.report)
    if not times:
        print(f"{args.report}: no testcase named a file under {REPO} - "
              f"this step measured nothing", file=sys.stderr)
        return 2
    if args.record:
        # The reference being replaced, read only for the spread it lets
        # this run state about itself. It is CI_REFERENCE wherever the
        # new one is written: the prior is what CI last recorded, not
        # whatever happens to sit at the output path.
        prior = (json.loads(CI_REFERENCE.read_text(encoding="utf-8"))
                 if CI_REFERENCE.is_file() else {})
        document = (json.dumps(record(times, args.source, prior), indent=2)
                    + "\n")
        if args.record == "-":
            print(document, end="")
        else:
            pathlib.Path(args.record).write_text(document, encoding="utf-8")
            print(f"recorded {len(times)} file(s) to {args.record}")
        return 0
    if args.against:
        return _against(times, pathlib.Path(args.against), args)

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
