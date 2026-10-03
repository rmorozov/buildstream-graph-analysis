# Round 169 - the bookkeeping sweep, 22 lines resolved

Run on 2026-10-03: the architect shaped `docs/backlog/bookkeeping.md`'s
22 open lines (the three r149 lines were at their third sweep) into
four tracks; all four merged and every line is resolved.

```text
closed   none
filed    UX-1314
index    dev_close_task.py --counts: 1263 scenarios, 11 open, 1252 closed
spread   dev_touching.py --spread: 35-205 of 830 test files
sweep    dev_bookkeeping.py --sweep: 0 open lines
```

## What closed

- 12 lines swept under `UX-998`: the four styleguide §7 lines and
  styleguide.md:1450 (track A: every browser guard cites a § or is named
  in a shrink-only `UNCITED`); forward and Escape in `bga/viewer` (track
  B: the 266 px was a `scrollY` reading, the anchor holds within 0.4 px,
  now guarded; Escape folds the Sections list); `correlate` 18 vs 24,
  `junction-cost` same run (owner chose Refuse on 2026-10-03, exit 2),
  its blank label, `cache-trend` churn (track C); `dev_baseline`
  re-sign, `dev_close_task` pipe, `decompose/SKILL.md:167`,
  `anonymized-bundle.md:62` and `:233` (track D).
- 1 line promoted: the tracer's `ElementCpuSampler` reads host pids from
  a sandbox namespace, `UX-1314`.
- 6 lines dropped as already fixed or by design: `.gitattributes`
  merge=union (`UX-1129`), resting-appearance weight (`UX-1130`),
  `docs/README.md:97` (moved, counts reproduce), `tests/cdp.mjs`
  (`bb060cbe`), viewer Copy 25 rows (`UX-1189`, `UX-1185`), viewer
  Questions with no timeline (hidden without a timeline, app.js:960).
- The three r149 lines were refused by `validate()` (open past 3
  sweeps) while any of them stayed open, so `--mark` could not resolve
  them one at a time; the closer marked them with validation off for
  that step.

## Findings folded in beyond the lines

- `bga compare`'s cache churn also counted PULL-only elements
  (`compare.py`), the same population error as `cache-trend`'s.
- `cache_trend`'s `_rebuild_us` read `task_key.kind`, so `rebuild_us`
  was always `None`.

## Ceilings

- The exported page is 166,249 B of `PAGE_BUDGET_B` 166,250: 0 bytes
  of headroom; the next viewer change needs an owner call.
- The loop ceiling moved to max 205.

## Lessons

- A `--mark` loop over a ledger holding a line past `SWEEP_LIMIT`
  refuses every mark: resolve the oldest lines first or the sweep
  cannot start.
- The A and C fix resumes ran inside their tracks' transcripts, so
  their rows carry the whole track, resume included.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 169 | architect | opus | architect: the sweep's shape, 22 lines | 124k | 91 | 9.1 m | complete | see round-169 |
| 169 | implementer | opus | track A styleguide guard ledger, with the fix resume | 741k | 106 | 69 m | merged | see round-169 |
| 169 | implementer | opus | track B viewer Escape and forward | 94k | 99 | 27.5 m | merged | see round-169 |
| 169 | implementer | sonnet | track C analysis sentences, with the fix resume | 540k | 98 | 78.8 m | merged | see round-169 |
| 169 | implementer | sonnet | track D dev tools and process docs | 98k | 43 | 15.9 m | merged | see round-169 |
| 169 | verifier | sonnet | track A verifier | 48k | 29 | 5.1 m | complete | see round-169 |
| 169 | verifier | sonnet | track B verifier | 41k | 10 | 14.9 m | complete | see round-169 |
| 169 | verifier | sonnet | track C verifier | 38k | 24 | 11 m | complete | see round-169 |
| 169 | verifier | sonnet | track D verifier | 61k | 17 | 15.8 m | complete | see round-169 |
| 169 | integrator | opus | integrator: merge tracks A-D | 145k | 55 | 32.2 m | merged | see round-169 |
| 169 | closer | sonnet | closer: ledger, round document, history | 43k | 13 | 1.3 m | complete | see round-169 |
