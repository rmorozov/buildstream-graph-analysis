# UX-1250: next-step commands carry a 100-character absolute run path

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding M5 | **Serves:** R1 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** test_a_next_step_names_the_run_by_its_snapshot.py

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §M5).

"What should I run next?" hands over `bga blast layer24/mod011.bst /tmp/.../big/.bga/runs/20260303T091500Z/run`: scroll width 1,246 px in a 288 px box at 390, so the reader sees "bga blast layer24/mod011.bst /tm". Three of five commands carry the path; the fifth already uses the alias grammar (`bga compare @prev @last`). On an exported page the path is the capturing machine's, so it cannot run elsewhere either.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     one helper in bga/findings.py turns a store run_dir into `@<stamp>`; every argv in compute_next_steps goes through it; measure-again drops --project (bga_snapshot defaults to project_root()). A run outside a store keeps its path.
Rejected:  @last (changes meaning with the next snapshot; needs a filesystem read in a pure function); --project "when not the cwd" (an exported page cannot know the reader's cwd).
Files:     bga/findings.py, tests/unit/test_a_next_step_names_the_run_by_its_snapshot.py, tests/unit/test_the_printed_sentences_are_contracts.py (retire the parsed.project clause)
Guard:     a two-run store page: every argv <= 60 chars, no /.bga/runs/; blast, sweep, correlate via main() from the project dir resolve to the same run_dir.
Mutation:  argv back to the raw run_dir.
Class:     product
Split:     one track; lands before 1244/1256 steps use it.
```

## Required Fix

A next-step command names the run by its snapshot id (or `@last` when it is the newest) and the project with `--project` only when it is not the working directory, as `bga compare` already does.

## Out of Scope

The command shape (§1d).

## Acceptance Test

On this page every next-step command is at most 60 characters and none contains `/.bga/runs/`; pasted in the store's project directory each resolves the same run. Mutation: restore the absolute path, and the guard reds.

## Outcome (2026-10-01)

### The gap, measured

`tests/fixtures/macro_micro/run` copied into a store at
`<scratchpad>/demo/.bga/runs/20260303T091500Z/run`, `bga analyze --format json`,
each `next_steps[].argv` joined with its length, base `92a48946`:

```text
153 bga blast core.bst /tmp/claude-0/.../demo/.bga/runs/20260303T091500Z/run
153 bga blast core.bst /tmp/claude-0/.../demo/.bga/runs/20260303T091500Z/run
147 bga snapshot --project /tmp/claude-0/.../demo -- bst build all.bst
23 bga compare @prev @last
```

### The close, measured

```text
36 bga blast core.bst @20260303T091500Z
36 bga blast core.bst @20260303T091500Z
33 bga snapshot -- bst build all.bst
23 bga compare @prev @last
```

`run_token()` in `bga/findings.py` returns `@<stamp>` for a store run
whose stamp is in the alias grammar, the path otherwise; `measure-again`'s
reason names the project to run it in, as `compare`'s already did.
`docs/guides/cli.md`'s quoted block follows (its guard compares it to the tool).

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| M1 | `run = run_dir` (argv back to the raw path) | argv clause, 1 failed (195 chars) |
| M2 | `token = '@last'` | resolves-the-same-run clause, 1 failed |
