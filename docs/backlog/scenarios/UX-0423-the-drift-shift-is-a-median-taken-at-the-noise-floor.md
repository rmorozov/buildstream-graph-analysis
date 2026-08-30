# UX-423: the drift shift is a median taken at the noise floor

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 67, a red `test (3.11)` on PR #185 that a re-run turned green | **Serves:** every contributor, at the point CI tells them something is wrong | **Topic:** guards

## Motivation

`UX-420` armed `tools/dev_tier_drift.py --check` in CI. Its first
independent run reported one file, on a diff that cannot reach it:

```text
369 file(s) measured against ci_reference.json, this run x1.36
1 file(s) slower than CI's own record of them:
  tests/unit/test_the_page_has_a_reader.py  15.3s  against 7.1s recorded,
    x1.58 after this run's x1.36 shift
```

Both gates tripped by their own rule — ×1.58 over `CI_DRIFT_FACTOR`
(1.5) and +5.6s over `CI_DRIFT_SECONDS` (5.0). Nothing in that PR
touched `bga/`, the viewer or any fixture; the file runs 8.47s on the
branch locally, single-process. The same commit `b33ced6` was
re-run on a different runner and went green with no change, which is
the confirmation: the file did not get slower.

**The shift is the defect.** `against()` divides out the median ratio
so that a uniformly slower runner is not read as drift. That is the
right idea, and the population it takes the median over cannot support
it:

```text
reference files                     367
  median seconds                    0.1
  under 0.1s                        181
  under 0.5s                        230
  at or over 5s                     50
  browser-driven                    36
  median, browser-driven            11.97
  median, everything else           0.05  (n = 331)
```

*(`python3 -c` over `tests/ci_reference.json`, tokenising each file and
matching `test_the_tiers_are_a_partition.py`'s `BOOTS_A_BROWSER`;
the script is pasted in the Acceptance Test below.)*

The median member of that population costs **0.1s**, and 181 files cost
under 0.1s. A ratio of two tenth-of-a-second numbers is a ratio at the
timer's noise floor — the quantity `UX-420` and `UX-422` were both
filed about. That noise-floor ratio is then the single correction
applied to a 7.13s file to decide whether it drifted by five seconds.

Two things follow, and they are separable:

1. **The estimator is drawn from the wrong quantities.** Whatever the
   true run-to-run shift is, files at 0.05s are where it is measured
   worst. 50 files carry five seconds or more; those are the ones whose
   ratio means something, and they are 14% of the sample.
2. **The population is not one class.** 36 files boot a real Chrome and
   have a median of 11.97s against 0.05s for the other 331. Chrome
   startup, rendering and CDP round-trips do not scale with a Python
   import under contention, so a single median under-corrects for
   exactly the files most sensitive to it. This is the mechanism the PR
   comment named, and it rests on **one** sample.

Claim 1 is measured above and holds regardless of claim 2. Claim 2 has
a mechanism and one observation.

This is one more instance of a shape the repository has hit far more
often than it realised. A sweep of the backlog, `tests/`, `tools/`,
`bga/` and the design documents (round 67; 22 phrase greps, ~35 files
opened, `git log --all --grep=proxy` over 663 commits) found **about
thirty sightings across about twenty-six items** of *an instrument
reading a proxy rather than the thing*, in four sub-shapes: a text scan
that cannot tell code from data (`UX-340`, `UX-307`, `UX-401`,
`UX-327`); a ratio at the noise floor (`UX-420`, `UX-422`, `UX-112`,
`UX-342`); a comparison across machines (`UX-418`, `UX-421`, `UX-235`,
`UX-334`); and the wrong artifact or population (`UX-359`, `UX-415`,
`UX-287`, `UX-296`, `UX-264`, and others).

The count is a lower bound and the sweep says so: each new grep
phrasing turned up items the previous ones had missed, which is
evidence it had not converged. `UX-425` is the row for the fact that
this class is named in four places and none of them is a rule document.

## Required Fix

Make the shift an estimate of the quantity it stands for:

- **Take the median over files with something to measure.** A floor —
  `MEDIUM_FLOOR_S` is already imported by this module — restricts the
  ratio to files where a ratio is meaningful. On this reference that is
  roughly the 137 files at or over 0.5s rather than all 367. Smallest
  change, and it is the fix claim 1 argues for on its own.
- **And/or shift a class by its own class median.** `BOOTS_A_BROWSER`
  already exists in `tests/unit/test_the_tiers_are_a_partition.py` and
  would have to move somewhere both readers can import. This is the fix
  for claim 2 and needs the second sample first.

Whichever is chosen, `IMAGE_BAND` and the "stale" verdict have to be
re-read against the new estimator: a median over fewer files is a
noisier median, and the band that decides "the whole reference has
moved" was sized against the old population.

A file the check reports must still be a file that got slower. The
seconds gate stays — it is doing its job and is not what failed here.

## Out of Scope

- **Re-recording `tests/ci_reference.json`.** 15.3s is contention, not
  work; baking it in raises the floor for every later run. The tool
  offers `--record` for when a file is meant to cost more, and this is
  not that.
- **Sizing anything on the single sample.** One reading is not a
  baseline — `UX-420` paid three red CI rounds for that lesson and
  `tools/dev_process_bands.py` says so in its own output.
- **Relaxing `CI_DRIFT_FACTOR` or `CI_DRIFT_SECONDS`.** Both fired
  correctly by their own definition. Moving them would quarantine the
  check rather than fix the estimator underneath it.

## Acceptance Test

The census above, reproduced:

```bash
python3 - <<'PY'
import json, statistics, pathlib, re, io, tokenize
ref = json.load(open('tests/ci_reference.json'))['files']
PAT = re.compile(r"from tests\.browser import|from browser import|find_chrome\(")
def code(p):
    src = pathlib.Path(p).read_text(encoding='utf-8')
    try:
        return "".join(t.string for t in tokenize.generate_tokens(
            io.StringIO(src).readline)
            if t.type not in (tokenize.STRING, tokenize.COMMENT))
    except Exception:
        return src
browser = {n for n in ref if pathlib.Path(n).exists() and PAT.search(code(n))}
v = sorted(ref.values())
print(statistics.median(v), sum(1 for s in v if s < 0.5), len(browser))
PY
```

And, in `tests/unit/test_a_slow_file_says_which_file.py`:

- A synthetic run where every file is ×1.36 and one 7s file is ×1.58
  reports **nothing**, because that file's own class also moved ×1.58.
  This is the case that fired on PR #185 and it must go quiet.
- A synthetic run where every file is ×1.36 and one 7s file is ×1.58
  **while its class moved ×1.36** still reports it. Without this clause
  the fix is indistinguishable from switching the check off.
- The estimator ignores a hundred files at 0.02s whose ratios are
  scattered ×0.5–×2.0, and the reported shift is unchanged by them.

Each of the three must be shown red under a mutation that removes the
clause it tests, per the `falsify` skill.
