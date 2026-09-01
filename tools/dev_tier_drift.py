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
import os
import pathlib
import statistics
import subprocess
import sys
import tempfile
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

#: And the job whose whole log **is** that document - `UX-457`.
#:
#: The artifact above is the right thing to download and the wrong
#: thing to reach: GitHub serves artifact bytes from
#: `productionresultssa19.blob.core.windows.net` and run-log zips from
#: `results-receiver.actions.githubusercontent.com`, and round 71 was
#: refused by both (403, CONNECT rejected) from the environment the
#: round was worked in - while the API that reads one job's log was
#: not. So `ci.yml` has a job that downloads the artifact and `cat`s
#: it, and a reader who cannot download can read that job instead.
#:
#: Both names, in every message, because which one is reachable depends
#: on who is reading.
CI_CANDIDATE_JOB = "tier-reference"

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


#: `UX-455`: how a candidate is re-measured before it is reported.
#:
#: The floors in `tests/tiers.py` are seconds a file costs with nothing
#: else on the CPU. The report this tool parses is a `-n auto` run. For
#: most files those are the same number - measured over the 145 files
#: whose `tiers.py` comment records their seconds, the median
#: parallel/recorded ratio on an unchanged tree is **1.010** (q1 0.916,
#: q3 1.099), so there is no factor to divide out and nothing to widen.
#:
#: For some files they are not. `test_the_agent_configuration_holds.py`
#: measured **0.72s** alone (three runs, 0.72/0.73/0.72) and **1.31s**
#: in the same parallel run - a ratio of 1.82, outside that q3 - and
#: 1.0 is the medium floor, so the parse named a file nobody should
#: move. Round 71 met that as one of three rows in a red
#: `make test-tiers`, and a parse that reports a file nobody should
#: move is a parse people learn to skim.
#:
#: So a candidate is re-measured **alone, in one process** before it is
#: reported. That is the quantity the floors are in, and it is an upper
#: bound on the file's cost inside a single-process suite - a file run
#: alone pays all of its own imports. For a gate that only reports
#: files as *too slow*, an upper bound is the conservative direction:
#: a candidate the confirmation clears is under the floor in the
#: stricter reading too.
#:
#: It costs a re-run of the named files only, which is normally none
#: and was 21s on the run that found this. `--no-confirm` skips it, for
#: reading what the parallel report alone said.
CONFIRM_TIMEOUT_S = 600


def confirm(rows, python=None):
    """`(kept, cleared)` - candidates re-measured alone, single process.

    `cleared` is `[(file, parallel_seconds, alone_seconds)]`, reported
    rather than dropped silently: a file the parallel run accused and
    the confirmation cleared is exactly what `UX-455` was filed on, and
    a reader who is told nothing learns nothing about their own runner.
    """
    kept, cleared = [], []
    for row in rows:
        name, seconds, was, _now = row
        alone = alone_seconds(name, python)
        if alone is None:                                # pragma: no cover
            kept.append(row)                             # cannot confirm
            continue
        if RANK[tier_for(alone)] > RANK[was]:
            kept.append((name, alone, was, tier_for(alone)))
        else:
            cleared.append((name, seconds, alone))
    return kept, cleared


def alone_seconds(name, python=None):
    """One file's setup+call+teardown, run by itself in one process.

    `None` when the run could not be made - a missing file, a pytest
    that would not start. The caller keeps such a row rather than
    dropping it: a confirmation that did not happen is not a clearance.
    """
    with tempfile.TemporaryDirectory() as scratch:
        report = pathlib.Path(scratch) / "alone.xml"
        environment = dict(os.environ, PYTEST_XDIST="")
        try:
            done = subprocess.run(
                [python or sys.executable, "-m", "pytest", name, "-q", "-p",
                 "no:xdist", f"--junitxml={report}"],
                cwd=str(REPO), env=environment, capture_output=True,
                timeout=CONFIRM_TIMEOUT_S)
        except (OSError, subprocess.SubprocessError):    # pragma: no cover
            return None
        # Only pytest's "tests ran" codes carry a measurement: 0 all
        # passed, 1 some failed - both mean the bodies executed and were
        # timed. 5 is *collected nothing*, 4 a usage error, and both of
        # those still write a junit document, an empty one that sums to
        # 0.0s. Read as a measurement that would clear every candidate
        # the re-run could not reach, which is a confirmation that
        # confirms by failing.
        if done.returncode not in (0, 1):
            return None
        if not report.is_file():                         # pragma: no cover
            return None
        try:
            root = ET.parse(report).getroot()
        except ET.ParseError:                            # pragma: no cover
            return None
    return sum(float(case.get("time") or 0.0)
               for case in root.iter("testcase"))


def spread(times, reference):
    """What this run said about CI's own run-to-run noise, or None.

    The quartiles of `measured / recorded` with the run's shift divided
    out - so a value of 1.0 is a file that moved exactly as much as the
    whole runner did, and `max` is the widest one file departed from its
    peers. **The shift is `shift_of`'s**, the one the gate uses, so
    `files` (every file both documents name) and `shift_files` (the ones
    that voted on the shift) are both reported and are different
    numbers. That is the quantity `CI_DRIFT_FACTOR` should be
    sized against, and there is no measurement of it yet: it is stated
    as the starting value it is. So the command that records writes the
    spread beside the numbers, and a later round reads a history of it
    off the reference's own git log rather than having to run CI twice
    on purpose.
    """
    known = reference.get("files") or {}
    by_name = {name: times[name] / known[name] for name in known
               if times.get(name) and known[name] > 0}
    if len(by_name) < 4:
        return None
    # `UX-476`: the median is taken over `shift_population` - the same
    # files the **gate** divides by - and not over everything. They are
    # different numbers on a real run: measured on the two runs that
    # opened that row, `spread` recorded 0.677 while the gate normalised
    # by 0.81, sixteen minutes apart on one reference. So the quartiles
    # accumulating in this document described a distribution the gate
    # never applied, and `UX-458` sized `CI_DRIFT_FACTOR` from them -
    # fixing guide §5, an instrument reading a proxy for the thing it
    # names.
    middle = shift_of(by_name, known)
    ratios = sorted(by_name.values())
    normalised = [ratio / middle for ratio in ratios]
    quarter = len(normalised) // 4
    return {"files": len(normalised),
            "shift_files": len(shift_population(by_name, known)),
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
                 f"artifact, or the log of its {CI_CANDIDATE_JOB} job, "
                 f"which is this same tool's --record taken on "
                 f"the runner whose clock this document is in - not from "
                 f"a local --record (UX-418, UX-447)."),
        "files": {name: round(seconds, 2)
                  for name, seconds in sorted(times.items())},
    }
    saw = spread(times, reference or {})
    if saw:
        document["spread"] = saw
    return document


def adopt(reference, candidate):
    """`UX-503`: the rows the reference does not carry yet, added to it.

    `(document, added)` - the reference with the new names in it, and
    what was added. **Only names the reference lacks.** An entry it
    already holds is never rewritten here: changing one is a refresh,
    which is a human's decision about whether a file is meant to cost
    what it now costs, and this runs unattended.

    The candidate's seconds are the *candidate run's* clock, so each
    added row is divided by the shift between the two documents before
    it lands - the same normalisation `against` applies when reading,
    put in once at write time so the reference stays one clock. Without
    it a run 1.3x slow writes a row 30 % high and the file is
    unjudgeable against it for as long as it stands, which is the
    cross-clock comparison `UX-418` ruled out arriving by the back door.

    Two states refuse rather than guess, both returning no additions:

    - **the two documents share no file**, so there is no shift to
      divide by and the candidate cannot be placed on this clock;
    - **the shift is outside `IMAGE_BAND`**, which is `against`'s
      `stale` - the reference is not describing this runner any more,
      and rows adopted into it would be measured against a document
      that is about to be replaced wholesale.
    """
    known = reference.get("files") or {}
    times = candidate.get("files") or {}
    ratios = {name: times[name] / known[name] for name in known
              if times.get(name) and known[name] > 0}
    if not ratios:
        return reference, {}
    shift = shift_of(ratios, known)
    if not IMAGE_BAND[0] <= shift <= IMAGE_BAND[1]:
        return reference, {}
    added = {name: round(seconds / shift, 2)
             for name, seconds in times.items() if name not in known}
    if not added:
        return reference, {}
    document = dict(reference)
    document["files"] = {name: seconds for name, seconds
                         in sorted({**known, **added}.items())}
    # Which rows are *not* from the recording run `measured_on` names,
    # accumulated over adoptions and dropped by the next wholesale
    # `record` - a reader comparing two rows deserves to know one of
    # them was placed on this clock by division rather than measured on
    # it.
    document["adopted"] = sorted(
        set(reference.get("adopted") or []) & set(known) | set(added))
    return document, added


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
    # something at stake. A new fast file needs no entry. `UX-503`:
    # such a row is carried out with `was` None and split off by
    # `repeated` into `recorded`, so it is printed rather than failed
    # on - there is no recorded number for it to be slower than.
    floor = tiers.MEDIUM_FLOOR_S * shift
    for name, seconds in times.items():
        if name not in known and seconds >= floor:
            rows.append((name, seconds, None, None))
    return ("drift" if rows else "ok"), shift, sorted(
        rows, key=lambda row: -row[1])


def carried(path):
    """`UX-442`: what the runs before this one found over both gates.

    A list of `{name: normalised reading}` maps, most recent first, at
    most `CI_DRIFT_RUNS - 1` long - which is exactly the memory the rule
    needs and no more.

    A missing or unreadable carry is an empty history rather than an
    error: the first run on a branch has no previous run, and a cache
    that did not restore must not fail the build over its own absence.

    `UX-476` gave each name its **reading**. A carry written by the
    older shape is a list of names, and is read as names with no
    readings rather than discarded - the run that restores a cache from
    before this change still has its memory, and only loses the numbers
    it never wrote.
    """
    try:
        held = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    runs = held.get("runs")
    if not isinstance(runs, list):
        return []
    out = []
    for one in runs[:CI_DRIFT_RUNS - 1]:
        if isinstance(one, dict):
            out.append(dict(one))
        elif isinstance(one, list):
            out.append({name: None for name in one})
    return out


def carry(path, readings, source, history):
    """Write what this run found, for the next run to agree or disagree.

    Written on **every** `--against` run, including the runs that find
    nothing: a file that excurses, recovers and excurses again has not
    drifted twice in a row, and an empty run is what says so.
    """
    runs = [dict(readings)] + [dict(one) for one in history]
    pathlib.Path(path).write_text(json.dumps(
        {"runs": runs[:CI_DRIFT_RUNS - 1], "measured_on": source},
        indent=2) + "\n", encoding="utf-8")


def explained_by(base):
    """The test files this branch's diff could plausibly have slowed.

    `tools/dev_touching.select` maps a diff to the test files that
    *name* what it changed - the selector `make test-touching` runs on.
    Here it answers a different question with the same map: **is there
    anything in the diff that could account for this file costing
    more?**

    `None` where it cannot be computed - no base given, or git could not
    resolve one. That is the honest answer on a shallow CI checkout, and
    `repeated` treats it as "no evidence either way" and confirms on
    agreement alone, which is the behaviour before `UX-476`. A gate that
    went quiet because a fetch failed would be worse than one that
    reports.
    """
    if not base:
        return None
    # The base has to *resolve* first. `dev_touching.changed_files`
    # swallows git's error and returns an empty diff, and an empty diff
    # reads as "nothing in the branch explains anything" - which would
    # downgrade every row to `unexplained` precisely when the evidence
    # is missing, silencing the gate on a failed fetch. Measured: a
    # `--base nope/nothing` returned `set()` before this check.
    resolved = subprocess.run(["git", "rev-parse", "--verify", "--quiet",
                               f"{base}^{{commit}}"],
                              capture_output=True, text=True, cwd=REPO)
    if resolved.returncode != 0:
        return None
    try:
        from tools import dev_touching
        chosen, why = dev_touching.select(dev_touching.changed_files(base))
        if "*" in why:
            # `dev_touching`'s shared-harness fallback: `conftest.py` or
            # `tiers.py` changed, so `select` returns the **whole
            # suite** under the single reason `"*"`. That is right for
            # the question it was built for - which tests to *run*,
            # where missing one is the only real failure - and it is no
            # answer at all to this one. A set that names every file
            # explains every excursion, so the gate confirms on one
            # sample and `UX-476`'s `unexplained` bucket is empty by
            # construction. Measured on this branch: 397 of 397 test
            # files "explained", from two harness files touched earlier
            # in the round.
            #
            # `None` is the honest answer - no evidence either way -
            # and `repeated` then confirms on agreement across runs,
            # which is `UX-442`'s behaviour and the documented meaning
            # of `None` above. `UX-494`.
            return None
        return set(chosen)
    except Exception:                                # pragma: no cover
        return None


def repeated(rows, history, explained=None):
    """Split `against`'s rows into confirmed, unexplained and waiting.

    `UX-442` confirmed a row when every one of the `CI_DRIFT_RUNS - 1`
    runs behind this one found the same file over both gates, reasoning
    that an excursion does not repeat.

    **`UX-476` found that it does, and why it must.** Every run is
    compared against the *same* recording run, so a file whose record
    was taken on a lucky run crosses on every subsequent run and "twice
    in a row" is guaranteed rather than improbable. Three untouched
    files on one branch were reported that way, one of them at x1.78
    and x1.66 on consecutive runs while the same file cost x0.93 of its
    record on a developer machine. Two runs against one record are not
    two pieces of evidence; they are one measurement counted twice.

    So confirming now needs evidence of a **different kind**: something
    in the diff that could account for the cost. `explained` is the set
    of test files `dev_touching` selects for this branch's changes, and
    a row is:

    - **confirmed** when it agreed across the window *and* the diff
      names it - a real tier change has a cause, and this is what keeps
      `UX-418`'s defect caught;
    - **unexplained** when it agreed and the diff does not - reported
      with its readings, because "two runs say 21s and the reference
      says 12.6s" is a fact worth printing, but not failed on: the
      remedy for it is re-recording that entry, not making a file
      faster that nobody made slower;
    - **waiting** when it did not agree across the window.

    `explained` is `None` when the diff could not be read at all, and
    then every agreed row is confirmed - `UX-442`'s behaviour, kept so
    that a failed fetch is loud rather than silently green.

    What this stops catching, stated: a file that really did get slower
    with nothing in the diff naming it. It is printed under
    `unexplained` rather than failing the build, so it is visible; and
    on the branch that opened this row that population was three files
    and all three were false alarms.

    **A file with no reference entry is `recorded`, not confirmed.**
    `UX-503`: it is not an excursion and it is not drift - it is a file
    the reference does not describe yet, which is true of every run
    between a guard landing and the next refresh. The run that meets it
    already has the only number anybody wants, and `--record` has
    already written that number into this run's candidate; failing the
    build on it bought a second commit and a forty-line skill section,
    and caught nothing. Judged for drift on the run *after* the
    reference carries it, like every other file.
    """
    # `UX-503`: split first, so an absent file never reaches the drift
    # decision at all. It has no reference entry to be slower *than*,
    # which is what made confirming it - and the old branch below
    # confirmed it on the **first** run, ahead of `UX-442`'s window -
    # a statement about the reference's coverage rather than about the
    # file.
    recorded = [row for row in rows if row[2] is None]
    rows = [row for row in rows if row[2] is not None]
    if history is None:
        return list(rows), [], [], recorded
    enough = len(history) >= CI_DRIFT_RUNS - 1
    confirmed, unexplained, waiting = [], [], []
    for row in rows:
        if not (enough and all(row[0] in one for one in history)):
            waiting.append(row)
        elif explained is None or row[0] in explained:
            confirmed.append(row)
        else:
            unexplained.append(row)
    return confirmed, unexplained, waiting, recorded


def series(name, reading, history):
    """This run's reading and the ones behind it, oldest last.

    The numbers `repeated` decided on, so the message can show them
    rather than assert a verdict. A run that carried names and no
    readings contributes nothing here, which is what a pre-`UX-476`
    carry does.
    """
    seen = [reading] + [one.get(name) for one in history]
    return [value for value in seen if value is not None]


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
        # `UX-476`: the reading as well as the name. `repeated` decides
        # on agreement and on the diff; the readings are what let the
        # message show the series a reader has to judge.
        over = {name: round(ratio, 2)
                for name, _s, was, ratio in rows if was is not None}
        carry(args.carry, over, args.source, history or [])
    if verdict == "empty":
        print(f"{path} names none of the {len(times)} file(s) this run "
              f"measured, so it cannot be a reference for it. Re-record "
              f"with --record - from CI's own "
              f"{CI_CANDIDATE_ARTIFACT} artifact or its "
              f"{CI_CANDIDATE_JOB} job's log, not from this machine.",
              file=sys.stderr)
        return 2
    if verdict == "stale":
        print(f"this run is x{shift:.2f} the reference recorded on "
              f"{where}, outside the {IMAGE_BAND[0]}-{IMAGE_BAND[1]} band. "
              f"That is the whole runner moving, not one file drifting - "
              f"re-record with --record and commit it - from this "
              f"run's {CI_CANDIDATE_ARTIFACT} artifact, or its "
              f"{CI_CANDIDATE_JOB} job's log - rather than "
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
    explained = explained_by(args.base)
    confirmed, unexplained, waiting, recorded = repeated(
        rows, history, explained)

    def say(row):
        # `UX-503` split the reference-less rows out into `recorded`
        # above, so every row reaching here has a number to be read
        # against.
        name, seconds, was, ratio = row
        return (f"  {name}  {seconds:.1f}s  against {was:.1f}s recorded, "
                f"x{ratio:.2f} after this run's x{shift:.2f} shift")

    def readings(row):
        """The series behind a row, newest first, as `x1.66, x1.78`."""
        seen = series(row[0], row[3], history or [])
        return ", ".join(f"x{value:.2f}" for value in seen)

    if waiting:
        # Not a failure and not silence. One sample does not separate a
        # file that got slower from a file that had a slow afternoon,
        # and the run that saw it is the only place to say so.
        print(f"{len(waiting)} file(s) over both gates on this run only, "
              f"and {CI_DRIFT_RUNS} consecutive runs are what reports "
              f"(UX-442):", file=sys.stderr)
        for row in waiting:
            print(say(row), file=sys.stderr)
    if unexplained:
        # `UX-476`. Reported with its numbers and not failed on: every
        # run compares against the same recording run, so agreement
        # across runs is evidence about the *record* as much as about
        # the file, and nothing in the diff names this one.
        print(f"\n{len(unexplained)} file(s) over both gates on "
              f"{CI_DRIFT_RUNS} consecutive runs, with nothing in this "
              f"branch's diff that names them (UX-476):", file=sys.stderr)
        for row in unexplained:
            print(f"{say(row)}   readings: {readings(row)}", file=sys.stderr)
        print(f"\nEvery run is read against the one recording run, so "
              f"agreeing runs are evidence the reference entry is "
              f"unrepresentative as much as evidence the file got slower "
              f"- and `git diff {args.base}` touches neither these files "
              f"nor anything they name. If the readings above agree with "
              f"each other, refresh the reference from this run's "
              f"{CI_CANDIDATE_ARTIFACT} artifact; if they do not, it is "
              f"one runner's afternoon and the next run will say so. "
              f"Either way this is not a failure.", file=sys.stderr)
    if recorded:
        # `UX-503`. Not a failure: the reference does not describe this
        # file yet, so there is no number it is slower *than*. The run
        # that meets it is the run that measures it, and `--record` has
        # already written that measurement into this run's candidate.
        print(f"\n{len(recorded)} file(s) over "
              f"{tiers.MEDIUM_FLOOR_S:g}s that the reference does not "
              f"carry yet - measured here, not judged (UX-503):",
              file=sys.stderr)
        for row in recorded:
            print(f"  {row[0]}  {row[1]:.1f}s", file=sys.stderr)
        print(f"Commit this run's {CI_CANDIDATE_ARTIFACT} artifact (or its "
              f"{CI_CANDIDATE_JOB} job's log) to give them a reference "
              f"entry; the run after that judges them for drift like "
              f"every other file.", file=sys.stderr)
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
          f"this run's {CI_CANDIDATE_ARTIFACT} artifact, its "
          f"{CI_CANDIDATE_JOB} job's log, or this file's "
          f"printed seconds divided by the shift above; `--record` on your "
          f"own machine writes the wrong clock (UX-418, UX-447).",
          file=sys.stderr)
    return 1


def _adopt(candidate):
    """`--adopt`: give the reference the rows it does not carry yet.

    `UX-503`. Runs unattended after a merge, so every refusal below
    prints why and exits **0**: the reference staying as it is costs one
    stale row, and a red job on the default branch over a bookkeeping
    step costs everybody's attention.
    """
    if not candidate.is_file():
        print(f"{candidate}: no candidate document to adopt from - the run "
              f"that would have written it did not reach its record step",
              file=sys.stderr)
        return 0
    reference = (json.loads(CI_REFERENCE.read_text(encoding="utf-8"))
                 if CI_REFERENCE.is_file() else {})
    document, added = adopt(reference,
                            json.loads(candidate.read_text(encoding="utf-8")))
    if not added:
        print(f"{CI_REFERENCE.name} carries every file this run measured; "
              f"nothing to adopt")
        return 0
    CI_REFERENCE.write_text(json.dumps(document, indent=2) + "\n",
                            encoding="utf-8")
    print(f"adopted {len(added)} file(s) into {CI_REFERENCE.name}, on its "
          f"own clock:")
    for name, seconds in sorted(added.items()):
        print(f"  {name}  {seconds:.2f}s")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", nargs="?",
                        help="a pytest --junitxml report. Optional only "
                             "with --adopt, which reads a recorded "
                             "document rather than a report")
    parser.add_argument("--quiet", action="store_true",
                        help="print nothing when there is no drift")
    parser.add_argument("--base", metavar="REF", default=None,
                        help="the ref this branch is diffed against, so a "
                             "reported file can be checked for a cause in "
                             "the diff (UX-476). Without it, agreement "
                             "across runs decides alone, which is what "
                             "UX-442 did.")
    parser.add_argument("--record", metavar="PATH", nargs="?", const="-",
                        help="write this report as the CI reference "
                             "(`-` prints it), instead of checking. CI "
                             "runs this and uploads the result as the "
                             f"{CI_CANDIDATE_ARTIFACT} artifact and prints it in "
                             f"the {CI_CANDIDATE_JOB} job; that is "
                             "what to commit, because a local run writes "
                             "this machine's clock and not CI's")
    parser.add_argument("--adopt", metavar="CANDIDATE",
                        help=f"merge the rows {CI_REFERENCE.name} does not "
                             f"carry yet out of a recorded document (a "
                             f"{CI_CANDIDATE_ARTIFACT} artifact) into it, "
                             f"on the reference's own clock, and touch no "
                             f"entry it already holds (UX-503)")
    parser.add_argument("--no-confirm", action="store_true",
                        help="report what the parallel report said, "
                             "without re-running each named file alone "
                             "to check it against the floors' own "
                             "quantity (UX-455)")
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

    if args.adopt:
        return _adopt(pathlib.Path(args.adopt))
    if not args.report:
        parser.error("a junit report is required without --adopt")
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
    cleared = []
    if found and not args.no_confirm:
        # `UX-455`. The report above is a `-n auto` run and the floors
        # are single-process seconds; for most files those agree, and
        # for some they do not. Only the accused are re-run, so this
        # costs nothing on a green tree.
        found, cleared = confirm(found)
    if cleared:
        # Printed on a green run too. A file the parallel report accused
        # and the confirmation cleared is the finding `UX-455` was filed
        # on, and it is about the reader's runner rather than their diff.
        print(f"{len(cleared)} file(s) over a floor in the parallel report "
              f"and under it measured alone - not drift:", file=sys.stderr)
        for name, parallel, alone in cleared:
            print(f"  {name}  {parallel:.1f}s under -n auto, "
                  f"{alone:.1f}s alone", file=sys.stderr)
    if not found:
        if not args.quiet:
            print(f"tiers ok: {line}")
        return 0
    print(line, file=sys.stderr)
    print(f"{len(found)} file(s) measured above the tier tests/tiers.py "
          f"lists them in:", file=sys.stderr)
    for name, seconds, was, now in found:
        print(f"  {name}  {seconds:.1f}s  listed {was}, measured {now}"
              + ("" if args.no_confirm else " (alone, single process)"),
              file=sys.stderr)
    print("\nMove each in tests/tiers.py with the seconds above, or make "
          "it faster. The seconds are already the quantity the floors are "
          "in - each named file was re-run by itself in one process, "
          "because the report this parsed is a `-n auto` run and the "
          "floors are not (UX-455).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
