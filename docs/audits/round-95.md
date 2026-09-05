# Round 95: the first batch under the pipeline — the gate widened, three tracks priced

Run on 2026-09-05, after round 94 merged. A feature round in batch
form (§6a, the `decompose` skill's §5). The user asked for the tasks
that unblock the most others or pay off at once for later sessions,
naming zero-tolerance quality gates. Five closed: `UX-693` by the
session, `UX-700`, `UX-707`, `UX-709`, `UX-710` by three `implementer`
tracks on `sonnet`, each read by a `verifier` on `sonnet` before its
merge. This is `UX-708`'s measurement: the first priced batch.

## The batch, chosen by fan-in

Transitive fan-in over the 48 open rows (`Depends on` fields):

```text
UX-693  unblocks 6   judgement   the rule set          → the session
UX-694  unblocks 3   bounded     the baseline          → next, on the widened set
UX-666  unblocks 2   judgement   ledger rows with friction
UX-687  unblocks 2   judgement   the impact tool
UX-709, UX-707+710, UX-700   bounded, no open dependency  → tracks
```

## What landed

`UX-693`: `select = ["F"]` → `F, I, UP, B, SIM, C4, RUF100`, by layer;
2,218 fixes over 370 files, 43 sites by hand, `ERA` declined (11 of 11
prose), `SIM115` to the baseline, `ruff==0.15.8`. Two gate mutations
red. `UX-700`: `tools/dev_symbols.py`, 0.7 s a query. `UX-709`: a
batch `--move`, which closed this round's four tracks in one call.
`UX-707`: `--session` prices a session's rebuilds — 36 over the whole
transcript, 78.7 %. `UX-710`: `--ledger` derives a run's row; the six
rows below are its output.

## The tracks, priced

| run | shape | tokens | tool calls | wall | the verifier found |
|---|---|---|---|---|---|
| track C, UX-700 | bounded | 216k | 101 | 25 m | a guard that could not fail; `__all__` listed dead; four precision limits |
| track A, UX-709 | bounded | 271k | 97 | 31 m | leaked module globals, hidden under `-n auto`; a repeated id closed twice; a false claim about lint |
| track B, UX-707+710 | bounded | 281k | 129 | 31.1 m | the first response never a rebuild; an untested guard; 139k vs 145k explained |
| verifiers | — | 45k · 46k · 63k | 48 · 29 · 44 | 5.6-9.8 m | six defects the tracks' own mutation tables did not |

Tokens are the fresh figure (`UX-710`), each track including its
resumed fix run. The three first runs alone were 103k, 128k, 135k by
the harness's line. A bounded track on `sonnet` costs 2-3× a
researcher run and lands; every one needed the verifier: **six
defects in three tracks, none caught by the track's own mutations**,
one of them a guard that passed whatever the code did. The advisory
holds as measured: `sonnet` for bounded shapes, never without the
verifier.

## Three losses, recorded

Three tracks were killed two minutes in when a declined permission
interrupted the orchestrator's turn; the `decompose` skill's §5 now
says the orchestrator edits nothing while tracks run. The verifiers'
`make test-touching` was a no-op inside a track whose commit is HEAD;
`verifier.md` now says `--base`. The orchestrator's tokens, measured
by the round's own tool: 36 rebuilds, 78.7 % of the session.

## Standing

`UX-694`, the baseline, is next on the widened set. Not done here:
`UX-666` and `UX-687` (judgement, two unblocks each). The round-93
grep found five unreferenced viewer exports; `dead --js` finds two;
`UX-699` decides.
