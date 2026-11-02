# Round 175 - the freedesktop-sdk field test's rows, closed and held

Run on 2026-10-30: a blind expert analysis of the freedesktop-sdk cold
capture (`captures/fdsdk-cold-latest`, run 36850726112) against cold bga
filed ten gaps (`UX-1357`..`UX-1366`). Seven closed here; three are
implemented and held for a re-capture. The write-up is
`/mnt/project-files/fdsdk-field-test-2026-10-30/fdsdk-field-test.md`.

```text
closed   UX-1357 UX-1359 UX-1362 UX-1363 UX-1364 UX-1365 UX-1366
in progress  UX-1358 UX-1360 UX-1361 (implemented; field reading waits on a re-capture)
index    dev_close_task.py --counts: 1311 scenarios, 8 open, 1303 closed
```

Round 174 was already used (`UX-1352`, `UX-1354`, `UX-1355`, closed as
"round 174, 2026-10-12"), so this round takes 175.

## What closed

- `UX-1357`: an edge what-if prices removing a dependency. fdsdk
  doxygen to libxml2 3.75 to 2.87 h, 126 to 99 elements.
- `UX-1359`: a chain element under half its granted width gets a line.
  openssl 1.49 of 4 cores, 10.0 min; it is in What to do next.
- `UX-1362`: one element's saving is the same number in every section.
  The candidate cap went 8 to 64; the gcc "1.0 s" now reads 30.6 min.
- `UX-1363`: the builders line reads this run's own sweep (3, not 1).
- `UX-1364`: the run context carries physical cores; both denominators print.
- `UX-1365`: analyze names the Plane 2 report beside a published capture.
- `UX-1366`: a build tool's reach is expected; a flag on every element is
  said once.

## Still open

- `UX-1358` serial stretches, `UX-1360` never-read edges, `UX-1361` the
  weekly capture: all 🟡 In Progress. Their field reading waits on a
  re-capture; `UX-1361`'s re-pin is verified only by a dispatched run.

## Agents

| role | model | effort | task | outcome | cost |
|---|---|---|---|---|---|
| implementer | opus-5-5 | high | T2 UX-1357 | complete; page-budget guards red at +844 B (55 B headroom) | $8.52 |
| implementer | opus-5-5 | high | T1 UX-1358, UX-1360 | complete; both rows, mutations red; fdsdk rerun not possible | $9.98 |
| implementer | opus-5-5 | high | T3 UX-1362, UX-1359, UX-1363 | complete; builders line reads this run's sweep; 2 budget reds | $21.81 |
| implementer | sonnet-5-5 | medium | T4 UX-1365, UX-1364, UX-1366 | complete; 1366 premise fixed in apply_resolved_widths; 3 browser tests need tiers | $11.90 |
| integrator | opus-5-5 | high | merge of the ten rows | complete; 4 budgets held for owner, 2 pre-existing red | $5.88 |
| walker | sonnet-5-5 | medium | fdsdk edge what-if page after merge | complete; 2 defects (print, a11y); no repo edits | $1.00 |

Shared friction: the worktree shell guard refused compound commands and
shell variables; the page budget (`PAGE_BUDGET_B`, 166,750 B) left
55-60 B of headroom. The integrator's six environmental reds came from a
shallow clone. The walker found that plain `bga view` serves the stale
stored analysis without `--reanalyse` (`UX-1367`).

Held for the owner, not raised here: the page budget (about 167,600 B
needed), the exports data-half budget, the macro_micro volume-words
budget and the xl_both DOM budget (8,295 against 8,085).

## Owner call

Ruslan chose "Raise all four, ~2% headroom" (2026-10-31): `PAGE_BUDGET_B` 166,750 -> 170,000 B (read 167,576), the macro_micro data half 100,000 -> 105,000 B (read 103,389), macro_micro words 13,700 -> 14,200 (read 13,922), xl_both DOM nodes 8,085 -> 8,450 (read 8,295).
