# UX-705: the burn-down runs on the reporters' model — a batch a commit, never a suppression

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-694 (the baseline), UX-663 (the model advisory and the run ledger), UX-498 (the implementer's worktree) | **Serves:** R8, who wants the baseline to reach zero without the session's model reading 1,709 findings | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

A baseline (`UX-694`) is a list; the user's second half of the trick
is that a list is work a smaller model can do. `ruff --fix` takes the
auto-fixable shelf (`UX-693`); what remains is edited by hand: 87
bandit-class, 270 type errors, the `B904` raise-without-from, the
`SIM115` open-without-context, the viewer's 70. Round 90's advisory
puts reading and checking on `sonnet`; a burn-down is checking with
an edit attached, and the suite plus the baseline judge it, not the
model. Structural findings — `C901`, `PLR091x`, file length — are
not in this list: a 548-line function is a refactor track (`UX-695`).

## Required Fix

A burn-down track is one `implementer` run on the reporters' model,
in a worktree, on one rule family in one directory, at most 40
findings, with the batch pasted in the brief. It passes when:
`make test-touching` then `make test` are green; `dev_baseline.py
--shrink` removes exactly the batch and nothing else; no new finding
of any rule; no suppression added — `# noqa`, `# type: ignore`, a
per-file-ignore, an `eslint-disable` are each a finding in the
baseline's own count, so a suppression is a growth and red. One row
per batch in the run ledger: tokens, findings closed, reverts. A
round with two or more tracks gives one to the burn-down until the
baseline is empty; each batch is picked from the census, and `S607`
is not one of them — Batch 1 below measured why.

## Out of Scope

- Judging a fix's design — the suite and the golden are the judge;
  a batch that needs judgement is a refactor track (`UX-695`).
- Blocking a merge on the baseline shrinking — the gate is
  zero-tolerance for new findings; the pace is a round's choice.

## Acceptance Test

Per batch: `dev_baseline.py --shrink` removes exactly that batch's
findings and `--check` adds none of any rule, `make test` green, one
ledger row. Mutation: a batch that adds one `# noqa: S607` —
`--check` red on the suppression count, the track fails.

## Progress

**The rule that makes a burn-down safe to delegate did not exist.** The
Required Fix reads "a `# noqa`, `# type: ignore`, a per-file-ignore, an
`eslint-disable` are each a finding in the baseline's own count, so a
suppression is a growth and red". Measured: `dev_baseline.py` had no
notion of a suppression at all. So a track told to close 24 `S607`
findings could have closed all 24 by annotating them, and the number it
is judged by would have shrunk exactly as if it had fixed them.

Built and verified. `suppression_findings()` in `dev_baseline.py`
records them as `repo SUPPRESSION` entries, and the property holds:

```console
$ # a burn-down "closes" one by silencing it instead
$ python3 tools/dev_baseline.py --check
new: repo SUPPRESSION bga/blast.py (#1) import os # noqa: S607
```

The census scans the paths the baseline governs plus `pyproject.toml`,
whose per-file-ignores silence checks *in* those paths. Population
today: 2, both per-file-ignores. `tests/` is outside the baseline's
scope, which is why the three `noqa: F401` under it are absent.

**The first census read itself.** A text scan counted its own pattern
table (`re.compile(r"eslint-disable")`) and prose quoting a directive.
Python is now read with `tokenize`, so a string is not a comment, and a
directive on a comment-only line is left out because it suppresses
nothing - ruff reports an unused `noqa` there instead.

| mutation | reddened | of 9 |
|---|---|---|
| the census stops reading comment tokens | two `TestWhatCounts` clauses | 2 |
| the code-line requirement dropped | `_a_directive_in_prose_is_not_one` | 1 |
| the per-file-ignores table check dropped | `_the_same_shape_elsewhere_...` | 1 |

**What is left.** The first batch - `S607`, now **24 findings in 12
files**, not the 18 this row states - as one `implementer` run on the
reporters' model, and its ledger row. The row stays open for it; what
this adds is the check that would otherwise let that run pass by
annotating.

## Batch 1 outcome (`S607`, `tools/`, 23 findings in 11 files)

**Gap measured**: 23 `S607` findings, `shutil.which` resolution real
(not a rename) in every case. **Close measured**: `dev_baseline.py
--shrink` → `removed 7 stale entries`; `--check` → `clean: 300
finding(s)`; `make test-touching` → `1355 passed, 3 skipped`; `make
test` → `7558 passed, 126 skipped, 1 warning in 359.89s`.

**7 of 23 closed** (`bst_extract_run.py` ×5, `dev_commit_bodies.py`
×1, `dev_perf_ratchet.py` ×1) - each call already carried a variable
argument, so `S603` was already priced in and unaffected by the swap.

**16 left, not mechanical**: resolving the executable turns a literal
argv into one with a `Name` in it, which is exactly what `S603`
("subprocess call: check for execution of untrusted input") uses to
tell a trusted call from an unproven one - `bga_doctor.py`'s own
`shutil.which` sites already carry this tax, baselined. 8 gain a
*new* `S603` (`bst_baseline_set.py` archive/ls-tree/show×2,
`dev_baseline.py` ruff-version, `dev_close_task.py` diff-HEAD,
`dev_finding_coverage.py` ls-files, `dev_touching.py` ls-files
--others); 5 shift an *already-baselined* `S603`'s identity, same
count either way (`dev_baseline.py` show/top, `dev_close_task.py`
ls-files, `dev_plane_capability.py` nm, `dev_tier_drift.py`
rev-parse); 3 are baseline-clean but redden a test asserting a
literal argv (`bst_baseline_set.py` fetch/ls-remote,
`bst_native_build_tracer.py` bst-artifact) -
`tests/unit/test_baseline_set.py`, `tests/unit/test_the_contents_read_is_one_call.py`.

**Verified independently, and decided.** Reproduced on
`tools/dev_touching.py`: before, `S603@118 S607@122 S603@395`; after
resolving `git`, `S603@120 S603@123 S603@397` — the finding changed
label, it did not close. **The growth is not authorised**: a `--force`
that turns 8 `S607` into 8 `S603` moves the count sideways and costs
three tests their literal-argv assertion. So this row's original "first
batch is `S607`, → 0" was unachievable as a reduction, and 7 of 23 is
the whole of what that family had to give.

**The census after batch 1** — `dev_baseline.py --check`: `clean: 300
finding(s)`. 195 are structural and `UX-695`'s (`C901` 84, `PLR0912`
47, `PLR0913` 34, `PLR0915` 30); 105 are this row's. **Next batch is
`SIM115`** (11 findings, 4 files, all under `tools/`). Read before
briefing it: **8 are mechanical** — a `.read()` or a comprehension over
a fresh handle, which takes a `with` (`bga_view.py` 928/946/1321/1323,
`bst_native_build_tracer.py` ×3, `dev_trace_coverage.py`). **3 are the
rule's false positives** and stay baselined: `bga_view.py:1604` opens
outside the `with` only so the `except OSError` two lines up can answer
404, and `trackevent.py:265` is a handle whose lifetime is the writer's,
closed at `:295`. So the batch is 8, not 11, and the row's own "removes
exactly that batch's findings" is what says so.

## Batch 2 outcome (`SIM115`, `tools/`, 8 findings in 3 files)

**Gap measured**: 8 `SIM115` findings across `bga_view.py` (4),
`bst_native_build_tracer.py` (3), `dev_trace_coverage.py` (1) — each a
`.read()` or a comprehension over a handle opened without a `with`.
The 3 findings named as false positives (`bga_view.py:1604`,
`trackevent.py:265` ×2) were left untouched and verified still
present in the baseline after `--shrink`.

**Close measured**: `dev_baseline.py --shrink` → `removed 8 stale
entries`; `git diff tests/quality_baseline.json` removes exactly the
8 `SIM115` lines named in the brief, none other; `--check` → `clean:
292 finding(s)`; `make test-touching` → `3487 passed, 76 skipped in
254.42s`; `make test` → `7558 passed, 126 skipped, 1 warning in
432.99s`; `make lint` → `All checks passed!` then `clean: 292
finding(s)`.

**8 of 8 closed**, each wrapped in a `with` around the single read
site: two nested-function reads in `bga_view.py` (`_module_order`'s
`walk`, `_inline_module`), the export's `index.html`/`style.css`
pair (two separate opens, two separate `with`s), `/proc/uptime` in
`_process_start_age`, two `json.loads(...) for line in open(...)`
comprehensions in `load_and_summarize`, and the gzip/plain branch in
`dev_trace_coverage.decode`.

| mutation | reddened | of |
|---|---|---|
| add `# noqa: S607` to a closed site (`bga_view.py:928`) | `dev_baseline.py --check` (`new: repo SUPPRESSION`) | 1 of 1 |

No new guard was written this batch — the suppression census
(`suppression_findings()`) already exists from the Progress section
above; the mutation confirms it still discriminates against this
batch's sites, not that it is new.

