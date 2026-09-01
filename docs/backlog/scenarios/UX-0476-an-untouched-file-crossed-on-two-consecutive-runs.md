# UX-476: the falsifier `UX-458` named arrived on the very next run

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 72, driving PR #191 to green — the drift gate named a file no commit on the branch touches, twice in a row | **Serves:** the contributor whose PR is red for a file they did not write, and whose only offered remedy is to re-record a reference they have no reason to distrust | **Topic:** guards

## Motivation

`UX-458` closed one round ago on this conclusion, and named its own
falsifier in the same section:

> The two runs a file must cross in are what make a false alarm
> unlikely, because **per-file noise does not repeat on the same file**;
> the factor only decides how much work that rule is given.
>
> **What would change this.** [...] a run where two consecutive runs
> agree on a file nobody touched — the second would falsify the premise
> the whole gate rests on, and is worth watching for rather than
> assuming away.

It did not need watching for. It was in the next two runs, and it is
what turned PR #191 red.

### `test_emphasis_is_a_budget.py`, which this branch cannot reach

```console
$ git log origin/main..HEAD --oneline -- tests/unit/test_emphasis_is_a_budget.py bga/viewer/
$                              # empty: nothing on the branch touches the file or what it renders
$ PYTHONPATH=. python3 -m pytest tests/unit/test_emphasis_is_a_budget.py -q -p no:randomly
15 passed in 11.74s            # against 12.58 recorded: x0.93 on this machine, on this branch
```

Two consecutive CI runs of that unchanged file:

```text
  run           head       raw    this run's shift   normalised   vs 12.58 recorded
  33413312096   c41a27e   12.58        —                 —         (this is the record)
  33493747354   66a3274   22.5       1.006             22.4          x1.78
  33495069593   ca22e60   16.9       0.81              20.9          x1.66
```

Both clear `CI_DRIFT_FACTOR` (1.5) **and** `CI_DRIFT_SECONDS` (5.0
added). They are consecutive. So `CI_DRIFT_RUNS = 2` reported it:

```text
2 file(s) slower than CI's own record of them:
  tests/unit/test_emphasis_is_a_budget.py  16.9s  against 12.6s recorded,
      x1.66 after this run's x0.81 shift
```

### And again, on a third file, two commits later

```text
2 file(s) slower than CI's own record of them:
  tests/unit/test_the_page_has_a_reader.py  13.7s  against 8.8s recorded,
      x1.70 after this run's x0.91 shift
```

Run 33505406758, head `fe89e0a`. `git log origin/main..HEAD --` on that
file and on `bga/viewer/` is empty, and the suite itself **passed** —
`make test` was green and the job was failed by the gate alone. So the
count is now three distinct untouched files reported on this one branch:
`test_emphasis_is_a_budget.py`, `test_why_bga_believes_what_it_believes.py`
and `test_the_page_has_a_reader.py`. All three are browser-booting files,
which is the population `UX-442`'s own four readings came from.

### The third file, measured for a third run — and it went back

This one is the sharpest evidence the row has, because it was followed
one more run.

```text
run 33505406758 (fe89e0a)   test_the_page_has_a_reader.py  13.7s vs 8.8s recorded
                            x1.70 after this run's x0.91 shift        REPORTED
run 33508941693 (91e4e12)   the whole suite at x1.00 shift, IQR 0.18
                            1 file(s) slower ... and it is not this one   SILENT
```

`CI_DRIFT_RUNS = 2` means the report on `fe89e0a` is already two
consecutive crossings. The next run put the file back inside its band
at its recorded 8.8s, with the run's own shift at 1.00 — so the series
is **cross, cross, back**, and 8.8s is what the file costs.

Round 73 followed the gate's own advice and appended 15.05s
(= 13.7 / 0.91) to `tests/ci_reference.json`, then **reverted it** when
this run arrived. That is the concrete cost of the defect: obeying the
message would have raised one file's baseline by 71% permanently, on
the strength of an excursion that the next run did not reproduce. A
reader who trusts the message cannot tell that from a real regression,
because the message is identical in both cases.

`UX-442` filed `CI_DRIFT_RUNS` on a file that read 7.1 / 7.1 / 7.5 /
13.9 across four runs, and reasoned that **an excursion does not
repeat**. This is the same kind of file — the emphasis budget boots the
real exported page — and its excursion repeated on the very next run,
while the same file on the same branch costs 0.93x its record on a
developer machine. **Two consecutive runs is not independent evidence
when a file's own noise band is wider than the factor.**

### The divisor moved 24% between the two runs, with nothing to blame

The gate's shift is a per-run estimate, and between two runs sixteen
minutes apart on the same reference it read 1.006 and then 0.81 — read
off the two gate messages above. `spread`, written into the reference
by the same runs, disagrees with both:

```text
  recorded (c41a27e)     files 314  shift 1.340  p25 0.796  p75 1.269  max 7.257
  run 33493747354        files 373  shift 1.006  p25 0.876  p75 1.193  max 2.783
  run 33495069593        files 358  shift 0.677  p25 0.738  p75 1.378  max 3.839
```

0.677 and 0.81 are the same run. They differ because they are medians
over **different populations**:

```python
# spread(): every file the two documents share.
ratios = sorted(times[name] / known[name] for name in known
                if times.get(name) and known[name] > 0)
middle = statistics.median(ratios)

# shift_population(): files at or over SHIFT_FLOOR_S *in the reference* -
# UX-423, so a ratio of two hundredth-of-a-second numbers cannot vote.
over = [name for name in ratios if known.get(name, 0) >= SHIFT_FLOOR_S]
```

`UX-458`'s whole method was to accumulate `spread` records off the
reference's git log and size `CI_DRIFT_FACTOR` from their distribution.
Those quartiles are normalised by 0.677; the gate normalises by 0.81.
**The accumulated history describes a distribution the gate never
applies** — fixing guide §5, an instrument reading a proxy for the
thing it names.

### And the history is still n=1 where `UX-458` said to read it

```console
$ for c in $(git log --format=%h -- tests/ci_reference.json); do
    printf '%s  ' "$c"
    git show "$c:tests/ci_reference.json" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin).get("spread","none"))'
  done | head -4
e300080  {'files': 314, 'shift': 1.34, 'min': 0.105, 'p25': 0.796, 'p75': 1.269, 'max': 7.257}
9ff6331  {'files': 314, 'shift': 1.34, 'min': 0.105, 'p25': 0.796, 'p75': 1.269, 'max': 7.257}
e7c3f9f  {'files': 314, 'shift': 1.34, 'min': 0.105, 'p25': 0.796, 'p75': 1.269, 'max': 7.257}
```

Three runs have produced a spread and the document carries one, because
every commit since `UX-457`'s whole re-record is a **hand-append** that
copies the old `spread` forward. `UX-458`'s Acceptance Test — *"lists
at least the agreed number of distinct spreads"* — cannot be satisfied
by appending at all; only a whole re-record writes a new one. The two
later spreads above exist only in this file, read out of two
`tier-reference` job logs by hand.

## Required Fix

Four things. The first is what the round went red on.

1. **The repetition rule must be independent evidence.** Both runs are
   compared against the same recording run, so a file whose record was
   taken on a lucky run crosses on *every* subsequent run and "twice in
   a row" is guaranteed rather than improbable. Either compare the runs
   with each other as well as with the record, or hold a rolling
   per-file band (`UX-442` already keeps a carry file; it holds names,
   not numbers). Whichever is chosen, the three readings above —
   12.58 / 22.5 / 16.9, with 11.74 on a developer machine — are the
   population to argue it from, and the argument must say what a *real*
   tier change would look like against it, or the rule is just a wider
   gate. `UX-418` exists to catch that change; this must not blind it.
2. **`spread` and the gate must use one shift.** `spread()` should take
   its median over `shift_population()` rather than over everything, so
   the history accumulating in the document is a history of the
   quantity the gate divides by. A guard that moves `SHIFT_FLOOR_S` and
   expects `spread`'s shift to move with it is what holds this.
3. **A message that names the remedy that applies.** The current text
   tells the reader to re-record, which for an untouched file is asking
   them to launder someone else's noise into the baseline — and round
   73 did exactly that, appending 15.05s for a file whose next run said
   8.8s, then reverting. When the named file is untouched by the diff,
   say so, or say what else to look at. A message that cannot tell a
   regression from an excursion must not offer the same one-line remedy
   for both.
4. **Then the wholesale re-record**, from one green run's
   `tier-reference` job, retiring the hand-appends this round added
   (`test_emphasis_is_a_budget.py` 16.86,
   `test_the_shape_conclusions_have_a_negative_case.py` 0.07,
   `test_the_trace_census_reads_both_ends.py` 6.76,
   `test_a_generated_project_builds.py` 0.17,
   `test_a_candidate_is_confirmed_alone.py` 2.32). That run's spread is
   the second distinct one the document will ever have carried, and it
   is what item 1 is argued against next round.

## Out of Scope

- **Raising `CI_DRIFT_FACTOR`.** `UX-458` measured that this
  distribution has no separating value, and that finding stands. What
  it got wrong is what the two-run rule was doing, not where the factor
  sits. A factor wide enough to clear 1.78 would let a genuine tier
  change through — `UX-418`'s whole defect.
- **`IMAGE_BAND`.** 0.677 and 0.81 are both inside (0.6, 1.7), and that
  is arguably right: the runner really was faster, and the band's job
  is to catch a stale reference rather than a fast afternoon.
  Narrowing it to catch this would red the build on the wrong sentence.
- **The tier floors in `tests/tiers.py`.** CI never reads them
  (`UX-418`); `make test-tiers` is the developer-side check, and it is
  not what fired.
- **Making `test_emphasis_is_a_budget.py` faster.** It boots the real
  exported page on purpose (`UX-359`), and 11.7s of that is the
  measurement, not overhead.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py -q
```

green, with a new clause that feeds the tool two runs of one unchanged
file at the readings above (12.58 recorded, then 22.5 and 16.9) and
asserts it does **not** report — and that reddens when the change from
Required Fix item 1 is reverted. Plus:

```bash
python3 -c "import json;print(json.load(open('tests/ci_reference.json'))['spread'])"
```

showing a spread taken from the re-recording run, not `1.34`'s.

## Outcome

_Not started._

## Outcome (round 73, 2026-09-01) — 🟢 Done

Three of the four items. The fourth is `UX-488`, and the reason it is
a separate row is ordering rather than effort — see **Deviation**.

### Item 1: what the two-run rule was actually doing

Both runs are read against the **same** recording run. So a file whose
record was taken on a lucky run crosses on *every* subsequent run, and
"twice in a row" is guaranteed rather than improbable: two runs against
one record are not two pieces of evidence, they are one measurement
counted twice.

Confirming now needs evidence of a **different kind** — something in
the diff that could account for the cost. `explained_by` asks
`tools/dev_touching.select`, the same map `make test-touching` runs on,
and `repeated` returns three buckets instead of two:

- **confirmed** — agreed across the window *and* the diff names it;
- **unexplained** — agreed and the diff does not: printed with its
  readings, not failed on;
- **waiting** — did not agree across the window (unchanged).

Run against this row's own numbers — 12.58s recorded, then 22.5s on a
run whose shift was 1.006 and 16.9s on one whose shift was 0.81:

```text
=== run 1: test_emphasis_is_a_budget.py at 22.5s, runner x1.006 ===
1 file(s) over both gates on this run only, and 2 consecutive runs are
what reports (UX-442):
  tests/unit/test_emphasis_is_a_budget.py  22.5s  against 12.6s
      recorded, x1.78 after this run's x1.01 shift
exit 0

=== run 2: test_emphasis_is_a_budget.py at 16.9s, runner x0.81 ===
1 file(s) over both gates on 2 consecutive runs, with nothing in this
branch's diff that names them (UX-476):
  tests/unit/test_emphasis_is_a_budget.py  16.9s  against 12.6s
      recorded, x1.66 after this run's x0.81 shift   readings: x1.66, x1.78
exit 0
```

x1.78 and x1.66 — the two figures the row was filed on, reproduced —
and **exit 0** where the branch went red.

**What a real tier change looks like against it**, which the item asked
to be argued rather than assumed: a commit that makes a file slower
touches that file or a module it names, `dev_touching` selects it, the
row is *confirmed*, and the build is red. `UX-418`'s defect stays
caught. What this stops failing on is a file that really got slower
with nothing in the diff naming it — it is printed under `unexplained`
rather than being silent, and on the branch that opened this row that
population was three files and all three were false alarms.

### Item 2: `spread` and the gate now use one shift

`spread()` took its median over every file both documents named;
`shift_of` takes it over `shift_population` — files at or over
`SHIFT_FLOOR_S` in the reference. Measured sixteen minutes apart on one
reference, the same run read **0.677** one way and **0.81** the other.
So the quartiles accumulating in the document described a distribution
the gate never applied, and `UX-458` sized `CI_DRIFT_FACTOR` from them.

`spread` calls `shift_of` now, and reports `shift_files` beside
`files` so the two populations are both visible — `UX-423`'s floor
excludes 42% of a real suite and `files: 314` said nothing about that.

The guard needed a fixture that can tell the two medians apart:
`tiers.recorded()` is entirely at or over the floor, so on it they are
the same number and the first version of the clause **passed against
the mutation**. It adds 200 sub-floor files now and asserts the two
medians differ before asserting which one `spread` took.

### Item 3: the message names the remedy that applies

The old text told the reader to re-record, which for an untouched file
is asking them to launder someone else's noise into the baseline —
round 73 did exactly that, appended 15.05s for a file whose next run
said 8.8s, and reverted it. The `unexplained` block says what is true
instead: every run is read against the one recording run, so agreeing
runs are evidence the *reference entry* is unrepresentative as much as
evidence the file got slower; `git diff <base>` touches neither these
files nor anything they name; if the readings agree, refresh that
entry, and if they do not, the next run will say so. **Either way this
is not a failure.**

The readings are what makes that judgeable, so the carry file holds
them now — `{name: normalised}` rather than a bare name list. A carry
written in the old shape still restores as names with no readings, so
the run that lands this keeps its memory instead of going quiet for one
run.

### The trap under it, found by mutation

`dev_touching.changed_files` swallows git's error and returns an empty
diff, and an empty diff reads as "the branch explains nothing" — which
would downgrade every row to `unexplained` on a failed fetch and
silence the gate exactly when its evidence is missing. Measured:
`explained_by("nope/nothing")` returned `set()`. It resolves the base
with `git rev-parse --verify` first now and returns `None`, which falls
back to `UX-442`'s agreement rule — loud rather than silent.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| P1 | `repeated` confirms on agreement alone again | 1 of 81 — `test_the_untouched_file_is_not_confirmed` |
| P2 | `spread`'s median back over every shared file | 1 of 82 — `test_the_recorded_shift_is_the_gates_own` |
| P3 | an unresolvable base returns `set()` instead of `None` | 1 of 82 — `test_a_base_that_does_not_resolve_is_no_evidence_at_all` |
| P4 | the CI step drops `--base` | 1 of 82 — `test_the_drift_step_is_given_the_branchs_base` |

**Two of these passed on their first writing** and are the reason the
clauses are what they are: P2 against a fixture with no sub-floor files
(the two medians were both 1.0), and P3 against no clause at all. Both
are recorded here rather than quietly fixed.

### Deviation from the Required Fix

- **Item 1 is neither of the two shapes the item proposed.** It asked
  for "compare the runs with each other as well as with the record, or
  hold a rolling per-file band". Neither discriminates on this row's
  own data: the two readings 22.4 and 20.9 *agree with each other*, so
  a mutual-consistency rule would confirm exactly the false alarm the
  row is about. What separates a bad record from a real regression is
  whether anything in the diff can account for it, so that is the rule.
  The readings are carried and printed — the item's first shape, kept
  as evidence for the reader rather than as the verdict.
- **Item 4 is `UX-488`.** Item 2 changed what `--record` writes, so a
  candidate taken from a run predating it carries the old quantity —
  the proxy this row was filed about. The re-record has to come from a
  run that already has the fix, and the commit that lands the fix
  cannot contain that run's output.
- **The candidate is now in the log too**, inside a `::group::` block,
  which the item did not ask for. It is what makes `UX-488` doable from
  a terminal or an API client: this session could reach the artifact's
  redirect and not its blob host (`connect_rejected` by the egress
  proxy), and `UX-441`'s rule that the failure stays last in the log
  holds because the group is collapsed.

### The runs

```text
python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py -q
                     82 passed in 0.96s
make test-touching   537 passed in 14.41s
make test            5,661 passed, 27 skipped in 321.50s (0:05:21)
make lint            ruff + PyMarkdown, both clean
```
