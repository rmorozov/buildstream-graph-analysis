# Round 111 — the round-110 filings and the round-sized rows, in parallel tracks

Run on 2026-09-08.

Round 110 left eight filings and five round-sized rows. This round
took all of them the same way — every track an `implementer` on
`sonnet` in a worktree, every merge behind a `verifier`, every hold
fixed on the track's branch before the merge — plus the two filings
its own gates produced, and one area of `UX-689`.

## What closed

- `UX-796`, `UX-801`, `UX-802`, `UX-798`, `UX-799`, `UX-800`, `UX-803`, `UX-782`, `UX-797` — round 110's filings: the host sampler's window, `bst show`'s CAS in its own home, pyright four times not sixteen, the directions counts derived, the map row's two producers, the rail landing's settle, the drift gate's base carry, the register's derived rounds, the spread clauses' measured tolerance.
- `UX-804` — filed on the first gate (load 18) and closed: the diagnostics performance guard counts `bga`'s own call events (3,627,224 against 5,400,000), not ten seconds of wall clock.
- `UX-695` — three renderers split behind a walked list each: `format_text` 570 → 254, `build_document` 365 → 107, `create_parser` 417 → 214 lines, golden output and every `--help` byte-identical. `format_compare_text` (254) is the ledger's next top row.
- `UX-678` — memory joins the sweep: the replay's own concurrent set against host RAM on `sweep/v1` and the recommendation. The queue-model half is on the record as narrowed: `store/v1` has no per-element RSS or host RAM.
- `UX-805` — filed on the third gate and closed: the doctor's chain probe ran under a throwaway HOME with no BuildStream config, so bst's default reserve (5 % of the volume's total, 13.53 GB) met 13.54 GB free and every chain build read "Cache too full". The probe carries the user's config now.
- `UX-684` — the cached-build verdict: the share of recorded changes at or under the graph's own p50 weighted blast, the dominant elements by duration-weighted expected cost, height and weight stated separately with the two advices.
- `UX-680` — remote execution priced two ways, never summed: unbounded builders (the sweep's own row) and compiler offload (per-element, on the critical path), each a stated bound.
- Direction 19 marked landed once `UX-695` closed.

Filed: `UX-804`, `UX-805`, `UX-806`.

## In progress

`UX-689`'s first area: the viewer chapter into
`docs/design/areas/bga-viewer.md`, 56 of 56 sentence units, the generated
area page carrying a derived `Mechanism:` link. The verification-log
guard anchors on the oldest `UX-NNN` commit, so each further chapter is
its own item, landed serially — `UX-806` filed and closed for the
Plane 2 chapter; the rest are the next round's tracks.

## What the verifiers found

Nineteen verifier runs; eleven returned a HOLD and two a PASS with a
finding (`UX-695`'s CLI order, `UX-805`'s hint), each landed on the
track's branch before the merge:

```text
UX-801   test_doctor.py wrote the ambient CAS; a variable-bound bst
UX-802   the PATH strip, a decline off the record, walls with load
UX-798   hyphenated count words did not parse
UX-799   TOOLS could drift from the row
UX-797   the CPU spread implied by the per-element bound; the wall half unguarded
UX-782   an unguarded tuple
UX-804   the count was cold/warm-dependent, the tracer cleared not restored
UX-695   the section order unguarded (twice: text and CLI); stale baseline rows
UX-678   bga sweep --plane2 crashed in both formats; no CLI-path guard
UX-689   the pasted 435 was 434 — no log entry credited the commit
UX-684   the pasted log tree had no command; the advice branch unguarded
UX-680   a global clamp read 0.0 s where the per-element bound leaves 5.25 s; the guard saturated; a 10-line body
```

Two of them are the shape CLAUDE.md names last: a guard whose fixture
already excludes the defect — `UX-680`'s offload guard could not tell
the critical path from every element while the clamp saturated, and
`UX-684`'s advice guard needed a synthetic chain because `macro_micro`
is one straight chain.

## Standing

The suite's shape, derived by `dev_shape_budget.py` and printed by
`dev_close_task.py --check` (`UX-690`):

```text
shape         files   CI seconds    share
unit            450       814.5s    47.9%
sweep             1         2.1s     0.1%
journey           2         0.1s     0.0%
browser          53       845.2s    49.7%
enormous         20        39.3s     2.3%
total           526      1701.3s
```

Browser reads 49.7 % (re-adopted from 49.0 % after the round's four new
test files) against the 40 % the row was filed with; journey is 2 files
against 25 published contracts.

## Process, measured

- The full gate reddened three times on this box on findings nobody's diff touched: `test_diagnostics_performance.py` at load 18 (`UX-804`), the doctor's chain probe at 13.54 GB free (`UX-805`), and Direction 19's `partial` status once its last filing closed. All three fixed in the round.
- PR #219's first CI run reddened the drift gate on `test_a_rail_click_lands_on_its_section.py`, 58.2 s against 34.6 s recorded: `UX-800`'s two tall fixtures walk every link twice more. The row refreshed from that reading (round 110's rule; `UX-803`'s lag).
- The size ledger re-adopted after every merge batch; `UX-695`'s merges conflicted on the task file's Outcome blocks (union) and `UX-684`'s on the CLI guide's derived key count (261, re-derived).
- The container restarted once, cutting four agents; all resumed from their transcripts on intact worktrees. One session-side `pkill` of a gate also caught the tracks' pytest runs; each was told, and re-ran.
- Three tracks committed with `BGA_SKIP_SELECTOR=1` on the Direction 19 red, stated in the body; the red was the round's own.
- The `derive` shape held: no track edited the spec.

## Agents

38 runs — 19 `implementer`, 19 `verifier`, all on `sonnet`. Ten tracks
were judgement-shaped; the session took the judgement in the brief and
the track the work.

| | |
|---|---|
| implementer | 19 tracks, every one merged behind a verifier; median 282k tokens, 46 m |
| verifier | 19 runs; median 49k tokens, 8 m; 11 of 19 returned a HOLD |
