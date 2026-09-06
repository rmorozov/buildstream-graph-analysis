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
baseline is empty; the first batch is `S607` (18 partial-path
executables → `shutil.which`).

## Out of Scope

- Judging a fix's design — the suite and the golden are the judge;
  a batch that needs judgement is a refactor track (`UX-695`).
- Blocking a merge on the baseline shrinking — the gate is
  zero-tolerance for new findings; the pace is a round's choice.

## Acceptance Test

After the first batch: `git grep -c S607 tests/quality_baseline.json`
→ 0, `make test` green, one ledger row; mutation: a batch that adds
one `# noqa: S607` — `--check` red on the suppression count, the
track fails.

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

