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

#: `UX-447`: **where a refreshed reference comes from.**
#:
#: `--record` on a contributor's own machine writes *that machine's*
#: seconds, and `UX-418` established those cannot be compared to CI's in
#: any form. So every message below that says "re-record" also says from
#: what: this is the artifact `ci.yml` uploads on every `test (3.11)`
#: run, holding the same document `--record` writes, taken on the runner
#: whose clock the reference is in.
#:
#: Named here rather than spelled into four strings, and
#: `tests/unit/test_the_refresh_route_is_written_down.py` holds it equal
#: to the workflow's own `name:` - so a rename cannot leave the advice
#: pointing at nothing, which is what the item was filed on.
CI_CANDIDATE_ARTIFACT = "ci-reference-candidate"

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

#: `UX-442`: how many **consecutive** runs a file must exceed both gates
#: above in before it is reported. One is what shipped, and one is what
#: this constant exists to stop.
#:
#: `test (3.11)` went red on `279900f`, whose diff is one backlog file
#: and one index row. The suite passed; the drift step did not. The same
#: file across four CI runs of that branch, read from the documents
#: those runs recorded:
#:
#: ```text
#:   run   test_the_page_has_a_reader.py   run's shift   run's spread max
#:    1                   7.13                   -               -
#:    2                   7.13                   -               -
#:    3                   7.53                 1.227           5.87
#:    4                  13.85                 1.180           4.872
#: ```
#:
#: Three samples at 7.1-7.5 and one at 13.9, and **the outlier run was
#: not a contended run**: its shift and spread are both lower than run
#: 3's, which passed. `UX-423` measured the dispersion of the *shift*, so
#: a globally slow runner is not read as drift. Nothing measured the
#: dispersion of one file, and a file that boots a browser can swing six
#: seconds once in four runs.
#:
#: **What two costs.** Real drift is reported one run later than it used
#: to be, and a branch's first run reports nothing at all, because there
#: is no previous run to agree with it. That is the price of not crying
#: wolf, and it is the whole price - the gates themselves are unchanged
#: (`UX-418` measured them; this adds a repetition rule rather than
#: retuning either).
#:
#: **Why not a second, higher bound that trips on one sample.** It would
#: need a number, and the only series anybody has is the four runs above.
#: Sizing a constant from one excursion is the mistake `UX-420` paid
#: three red CI rounds for. A hang is already caught by the small tier's
#: `timeout 120` backstop; drift, by definition, repeats.
#:
#: An excursion is remembered between runs in the **carry** file
#: (`--carry`), which CI restores and saves around the step. Without one
#: the tool has no memory, says so, and decides on the single sample it
#: has.
CI_DRIFT_RUNS = 2

#: Outside this, the whole reference is stale rather than any one file
#: drifting - a new runner image, a Python bump, a changed default
#: parallelism. Wide on purpose: inside it the median is divided out
#: and nothing is lost, and the cost of guessing narrow is a red build
#: that names the wrong thing.
IMAGE_BAND = (0.6, 1.7)

#: The shift is estimated only from files that run at least this long.
#: `UX-423`. The shift stands for "how much slower this runner is", and
#: a ratio of two hundredth-of-a-second numbers does not carry that.
#: Two runs of the whole suite on one machine at one commit, so every
#: departure from the median is noise and nothing else:
#:
#: ```text
#:   band (run 1 seconds)   files  median  p90 |r-1|   worst
#:   0 - 0.1                  144   1.000      0.983   4.208
#:   0.1 - 0.5                 46   0.978      0.294   1.292
#:   0.5 - 1                   24   1.030      0.402   1.390
#:   1 - 5                     74   0.961      0.260   1.777
#:   5+                        57   0.994      0.124   1.170
#: ```
#:
#: A file under a tenth of a second ran **x4.21** its own time with
#: nothing changed. 144 of 345 files are in that band, so 42% of the
#: population the median was taken over carried no information about
#: the runner.
#:
#: **What this did and did not buy, stated because the filing implied
#: more.** A median is robust, so the point estimate barely moved -
#: 0.983 over all files against 0.980 over these. What tightened is the
#: precision, and that is the honest claim:
#:
#: ```text
#:   shift over files >= 0.0s: 0.983  from 345 files, IQR 0.151
#:   shift over files >= 1.0s: 0.980  from 131 files, IQR 0.099
#:   shift over files >= 5.0s: 0.994  from  57 files, IQR 0.044
#: ```
#:
#: `MEDIUM_FLOOR_S` rather than a new number, because it is already
#: this repository's line for "this file is not trivial", and inventing
#: a second one would need a sample nobody has. 5.0s is tighter still
#: and was not taken: 57 files is a thin population for a median, and
#: choosing between them on one machine's pair of runs is the sizing-on
#: -one-sample mistake `UX-420` paid three red CI rounds for.
SHIFT_FLOOR_S = tiers.MEDIUM_FLOOR_S

#: Below this many files over the floor, the floor is abandoned and the
#: whole population is used. A median of four ratios is worse than a
#: median of four hundred noisy ones, and a suite that shrinks must not
#: silently lose its estimator.
SHIFT_MIN_FILES = 20

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
                 f"Refresh from a CI run's {CI_CANDIDATE_ARTIFACT} "
                 f"artifact, which is this same tool's --record taken on "
                 f"the runner whose clock this document is in - not from "
                 f"a local --record (UX-418, UX-447)."),
        "files": {name: round(seconds, 2)
                  for name, seconds in sorted(times.items())},
    }
    saw = spread(times, reference or {})
    if saw:
        document["spread"] = saw
    return document


def shift_population(ratios, known):
    """The names whose ratio is allowed to estimate the runner's shift.

    Files at or over `SHIFT_FLOOR_S` in the **reference**, not in this
    run: a file that got genuinely slower must not join the population
    by getting slower, or a regression drags the baseline toward
    itself.
    """
    over = [name for name in ratios if known.get(name, 0) >= SHIFT_FLOOR_S]
    return over if len(over) >= SHIFT_MIN_FILES else list(ratios)


def shift_of(ratios, known):
    """The run's shift: the median ratio among files worth measuring."""
    return statistics.median(ratios[name]
                             for name in shift_population(ratios, known))


def shift_spread(ratios, known):
    """`(files, iqr)` behind the shift, so a later round can band it.

    Reported rather than judged. `UX-420` sized a threshold on one
    sample and its first armed run named thirty-one files on an
    unchanged suite; `tools/dev_process_bands.py` says in its own
    output that a band needs a baseline and one reading is not one.
    This is what accumulates the readings.
    """
    kept = sorted(ratios[name] for name in shift_population(ratios, known))
    if len(kept) < 4:
        return len(kept), None
    quarter, three = kept[len(kept) // 4], kept[(len(kept) * 3) // 4]
    return len(kept), three - quarter


def against(times, reference):
    """`(verdict, shift, rows)` for a run read against CI's own numbers.

    `verdict` is `"ok"`, `"stale"` (the whole reference has moved, so
    naming files would name the wrong thing) or `"drift"`.

    The **median** ratio is divided out first, which is what makes this
    a comparison of one machine against itself *over time* rather than
    against one particular afternoon: a runner image that got 20%
    slower moves every file together and is not drift.

    That median is taken over files at or above `SHIFT_FLOOR_S` only -
    `UX-423`. A ratio of two hundredth-of-a-second numbers says nothing
    about a runner, and 42% of the reference is that small.

    A file is reported only when it is slower by a ratio **and** by a
    number of seconds - see `CI_DRIFT_SECONDS` for the run that proved
    a ratio alone reports thirty-one files on a suite nobody touched.

    This says what **one run** found. Whether that is drift or one slow
    afternoon needs the run before it, and that decision is `repeated()`
    one level up - `UX-442`.
    """
    known = reference.get("files") or {}
    ratios = {name: times[name] / known[name] for name in known
              if times.get(name) and known[name] > 0}
    if not ratios:
        return "empty", None, []
    shift = shift_of(ratios, known)
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


def carried(path):
    """`UX-442`: what the runs before this one found over both gates.

    A list of name-sets, most recent first, at most `CI_DRIFT_RUNS - 1`
    long - which is exactly the memory the rule needs and no more.

    A missing or unreadable carry is an empty history rather than an
    error: the first run on a branch has no previous run, and a cache
    that did not restore must not fail the build over its own absence.
    """
    try:
        held = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    runs = held.get("runs")
    if not isinstance(runs, list):
        return []
    return [set(one) for one in runs[:CI_DRIFT_RUNS - 1]
            if isinstance(one, list)]


def carry(path, names, source, history):
    """Write what this run found, for the next run to agree or disagree.

    Written on **every** `--against` run, including the runs that find
    nothing: a file that excurses, recovers and excurses again has not
    drifted twice in a row, and an empty run is what says so.
    """
    runs = [sorted(names)] + [sorted(one) for one in history]
    pathlib.Path(path).write_text(json.dumps(
        {"runs": runs[:CI_DRIFT_RUNS - 1], "measured_on": source},
        indent=2) + "\n", encoding="utf-8")


def repeated(rows, history):
    """Split `against`'s rows into the confirmed and the ones waiting.

    A row is confirmed when every one of the `CI_DRIFT_RUNS - 1` runs
    behind this one found the same file over both gates. A history
    shorter than that confirms nothing - the branch has not run enough
    times to tell an excursion from drift, and saying so is the point.

    `history` is `None` when the run was given no carry at all. Then
    nothing can be confirmed by agreement and every row decides on its
    single sample, which is the behaviour this item replaced; it is kept
    so that a missing `--carry` is loud rather than silently green.

    **A file with no reference entry is never held back.** It is not an
    excursion - it is a file the reference does not describe, which is
    true of every run until the reference is refreshed, and waiting a
    run to say so buys nothing.
    """
    if history is None:
        return list(rows), []
    enough = len(history) >= CI_DRIFT_RUNS - 1
    confirmed, waiting = [], []
    for row in rows:
        agreed = enough and all(row[0] in one for one in history)
        (confirmed if row[2] is None or agreed else waiting).append(row)
    return confirmed, waiting


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
    # `UX-442`. Read before anything is printed and written before
    # anything returns, so the next run's memory is this run's finding
    # whatever this run decides - a `stale` or `ok` run breaks the chain
    # exactly as it should.
    history = carried(args.carry) if args.carry else None
    if args.carry:
        over = {name for name, _s, was, _r in rows if was is not None}
        carry(args.carry, over, args.source, history or [])
    if verdict == "empty":
        print(f"{path} names none of the {len(times)} file(s) this run "
              f"measured, so it cannot be a reference for it. Re-record "
              f"with --record - from CI's own "
              f"{CI_CANDIDATE_ARTIFACT} artifact, not from this machine.",
              file=sys.stderr)
        return 2
    if verdict == "stale":
        print(f"this run is x{shift:.2f} the reference recorded on "
              f"{where}, outside the {IMAGE_BAND[0]}-{IMAGE_BAND[1]} band. "
              f"That is the whole runner moving, not one file drifting - "
              f"re-record with --record and commit it - from this "
              f"run's {CI_CANDIDATE_ARTIFACT} artifact - rather than "
              f"reading the per-file numbers below.", file=sys.stderr)
        return 1
    known = reference.get("files") or {}
    ratios = {name: times[name] / known[name] for name in known
              if times.get(name) and known[name] > 0}
    behind, iqr = shift_spread(ratios, known)
    # The shift's own precision, printed on every run so a later round
    # has the series `UX-423` could not size a band from with one.
    estimate = (f"x{shift:.2f} from {behind} file(s) over "
                f"{SHIFT_FLOOR_S:g}s"
                + (f", IQR {iqr:.2f}" if iqr is not None else ""))
    line = (f"{len(times)} file(s) measured against {path.name} "
            f"({where}), this run {estimate}")
    if verdict == "ok":
        if not args.quiet:
            print(f"tiers ok: {line}")
        return 0
    confirmed, waiting = repeated(rows, history)

    def say(row):
        name, seconds, was, ratio = row
        return (f"  {name}  {seconds:.1f}s"
                + (f"  against {was:.1f}s recorded, x{ratio:.2f} after "
                   f"this run's x{shift:.2f} shift" if was is not None
                   else "  and not in the reference at all"))

    if waiting:
        # Not a failure and not silence. One sample does not separate a
        # file that got slower from a file that had a slow afternoon,
        # and the run that saw it is the only place to say so.
        print(f"{len(waiting)} file(s) over both gates on this run only, "
              f"and {CI_DRIFT_RUNS} consecutive runs are what reports "
              f"(UX-442):", file=sys.stderr)
        for row in waiting:
            print(say(row), file=sys.stderr)
    if not confirmed:
        if not args.quiet:
            print(f"tiers ok: {line}")
        return 0
    print(line, file=sys.stderr)
    print(f"{len(confirmed)} file(s) slower than CI's own record of them:",
          file=sys.stderr)
    for row in confirmed:
        print(say(row), file=sys.stderr)
    if history is None:
        print("\nThis run was given no --carry, so one sample decided it. "
              "CI restores and saves one; a local run has no series to "
              "read (UX-442).", file=sys.stderr)
    print(f"\nMake it faster, or - if it is meant to cost this - refresh "
          f"the reference and commit it, which is how it stays true rather "
          f"than becoming an alarm nobody reads. The document to commit is "
          f"this run's {CI_CANDIDATE_ARTIFACT} artifact, or this file's "
          f"printed seconds divided by the shift above; `--record` on your "
          f"own machine writes the wrong clock (UX-418, UX-447).",
          file=sys.stderr)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", help="a pytest --junitxml report")
    parser.add_argument("--quiet", action="store_true",
                        help="print nothing when there is no drift")
    parser.add_argument("--record", metavar="PATH", nargs="?", const="-",
                        help="write this report as the CI reference "
                             "(`-` prints it), instead of checking. CI "
                             "runs this and uploads the result as the "
                             f"{CI_CANDIDATE_ARTIFACT} artifact; that is "
                             "what to commit, because a local run writes "
                             "this machine's clock and not CI's")
    parser.add_argument("--against", metavar="PATH", nargs="?",
                        const=str(CI_REFERENCE),
                        help="check against a CI reference rather than "
                             "against the floors - the only comparison "
                             "that means anything on a foreign runner")
    parser.add_argument("--carry", metavar="PATH",
                        help=f"where this run's excursions are left for the "
                             f"next one; a file is reported only after "
                             f"{CI_DRIFT_RUNS} consecutive runs find it "
                             f"(UX-442). Without it one sample decides")
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
