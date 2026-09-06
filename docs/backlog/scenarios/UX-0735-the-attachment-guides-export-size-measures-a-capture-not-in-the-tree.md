# UX-735: the attachment guide's export size measures a capture not in the tree

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-511 (which set the dated-label shape), UX-195, UX-529 (which bounded the export's data half) | **Serves:** the CI author deciding whether to upload the artifact | **Topic:** docs | **Shape:** bounded | **Area:** tools

## Motivation

Architecture review 18, checklist item 4. `docs/guides/ci-comment.md`
tells a CI author what the attached report costs:

```console
$ sed -n '275,277p' docs/guides/ci-comment.md
it from the run's artifacts and opens it; nothing has to be deployed for
a viewer to exist. Measured on a real 46 s capture with both planes:
**82 KiB**.
```

Two problems, and the second is the one that matters. The figure is
undated, so nothing says which round it was true in. And the capture
it names — "a real 46 s capture with both planes" — is not in the
tree, so no reader and no guard can reproduce it. Six guards cite
this document (`grep -rln ci-comment tests/unit/*.py`); none reads
this sentence.

The only export the repository can measure today is six times it:

```console
$ python3 -c "
from tools.bga_view import export
import pathlib, tempfile
out = pathlib.Path(tempfile.mkdtemp())/'r.html'
export('tests/fixtures/macro_micro/run', str(out))
n = out.stat().st_size
print(f'export bytes {n} = {round(n/1024)} KiB')"
export bytes 499911 = 488 KiB
```

That is a different population — `macro_micro/run` is the repository's
fixture, not the guide's 46 s capture — and it is the point: the
guide's number cannot be checked against anything, and the one number
that can be measured is not close to it. `UX-529` bounded the export's
data half after this sentence was written, and `UX-307`, `UX-342` and
the inlined Perfetto trace all moved what an export carries; a reader
sizing an artifact upload against **82 KiB** is sizing against a tool
that no longer exists.

## Required Fix

Either shape works and the Outcome says which:

- **Date it**, `UX-511`'s shape: keep the 46 s capture's number,
  label it with the round and date it was taken, and say the capture
  is not in the tree. Costs nothing and stays honest; a reader still
  cannot check it.
- **Re-measure on a fixture and derive it**, `UX-549`'s shape: state
  the figure for `tests/fixtures/macro_micro/run`, name the fixture in
  the sentence, and let a guard run `export` and compare. Costs a
  second or two per run and cannot drift.

**The decision, taken here: the second.** The export is cheap on that
fixture and a guard can afford to run it:

```console
$ time python3 -c "… export('tests/fixtures/macro_micro/run', out) …"
499911
real    0m0.382s
```

0.38 s, no browser and no subprocess, so it sits in a small-tier file.
The first route keeps a number nobody can check, which is what the row
is about. Restate the sentence for `tests/fixtures/macro_micro/run`,
name the fixture in it, and derive it. A byte-exact equality will
red on any content change, so bound it — an order of magnitude, or a
band the Outcome argues for — and say what the bound is for.

## Out of Scope

- The export's size itself. Whether 488 KiB is too much for a CI
  artifact is `UX-529`'s axis, not this row's.
- The other figures in `ci-comment.md`. Review 18 read this one
  because it is a measurement; the rest are shapes.

## Acceptance Test

The sentence is either dated with its round or derived from a fixture
a guard measures. Mutation, for the second shape: make `export` write
a materially larger page — the clause reds naming both figures.

## Outcome

**Gap measured**: the guide's sentence named "a real 46 s capture with
both planes" — not in the tree, so no guard could check it — while
`export('tests/fixtures/macro_micro/run', …)` (the tree's own fixture)
measured 499,911 B = 488.19 KiB in 0.382 s, six times the guide's
82 KiB. Re-derived here rather than trusted: same figure, 499,911 B.

**Close measured**: `UX-549`'s shape, the decision the task already
took. `docs/guides/ci-comment.md:276-277` now names
`tests/fixtures/macro_micro/run` and states **488 KiB**, with the old
46 s capture's **82 KiB** kept as a dated aside (`UX-511`'s shape,
2026-08-21, `UX-195` — the commit that wrote it) rather than dropped.
A new guard, `TestTheCiWiring::test_the_export_size_the_guide_states_is_still_true`
in `tests/unit/test_the_report_you_can_attach.py`, parses the stated
KiB out of the doc, runs `export` on the fixture, and asserts the
measured KiB sits within ±20% of the stated figure — a band, not a
byte-exact equality: wide enough to absorb the few hundred bytes an
unrelated comment, contract field, or the embedded run path moves
without forcing a doc edit every round (the neighbouring
`test_each_committed_run_exports_within_its_stated_bound` bound for
this same fixture already carries ~700 B of comment-driven drift per
change); tight enough that a materially larger or smaller page still
reds.

**Mutation table**:

| mutation | reddened | measured |
|---|---|---|
| `export` appends 700,000 bytes to the written page (Acceptance Test's own) | `test_the_export_size_the_guide_states_is_still_true` | "states 488 KiB … measures 1199953 B = 1171.8 KiB, outside the ±20% band" |
| `export` writes only the first half of the page (tests the band's low side, not just growth) | same | "states 488 KiB … measures 249953 B = 244.1 KiB, outside the ±20% band" |

Both mutations applied to a scratch copy (`tools/bga_view.py`, copied
to the scratchpad before editing) and reverted from that copy;
`git diff --stat tools/bga_view.py` empty after each revert, guard
green again both times.

**Deviation**: none from the declared shape. The file's own
`--durations=0` shows the new test at 0.11 s (not the standalone
0.382 s — the process and imports are already warm inside the file's
run); the file's total went from ~2.2 s to ~2.3–6.4 s depending on
harness overhead, still far under `LARGE_FLOOR_S` (15.0 s) and above
`MEDIUM_FLOOR_S` (1.0 s), so the file's tier is unchanged (medium).
