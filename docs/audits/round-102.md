# Round 102: five ledger rows, a mid-round gate, and two red spine clauses

Run on 2026-09-06. No commit reads "round 102: take ... judgements";
the only commit naming the round is a mid-round checkpoint, `af56022`
(2026-09-06 18:08), "Round 102 gate: three guards `UX-667` moved and
did not visit". The round's identity is the ledger's, not a marker
commit's: `agent-runs.md` rows 51-55 all read `102` in their first
column, for `UX-667`, `UX-691`, `UX-702`, `UX-712` and `UX-703`.

## What closed

`UX-667` + `UX-691` (`ecdd659`): the rail becomes a source list —
chapters disclose, the mark stays in its own rect (`UX-667`); a flake
ledger counts an excursion before it is a flake (`UX-691`).

`af56022` (the gate, mid-round): three guards `UX-667`'s track moved
and did not visit — the rail's chapter rows became a disclosure list,
so `toc-rail` had to follow `nav.toc`'s children; a golden export bound
moved 449,000 -> 453,000, attributed by diffing the two exports; and a
browser guard the track reported red on its own base passes on
`origin/main`.

`UX-702` + `UX-712` (`a4eecb0`): the gate reddened two spine clauses at
load 16 that CI passes quiet — "the tree is not at fault and the
tolerances are not the fix" — filed as `UX-741`; the size ledger for
what has no finding identity lands alongside it.

`UX-703` (`3805321`): a weekly mutation run over the modules a diff
touched, and "the round's five ledger rows" derived by
`dev_track_cost.py --ledger`, "not typed" — the same commit that names
round 101's four lost transcripts (`round-101.md`, Agents).

## Agents

`agent-runs.md`, rows 51-55:

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 102 | implementer | sonnet | `UX-667` the rail is a source list (judgement, decided in the brief) | 319k | 243 | 59.6 m | merged | reverse-engineering which prose in a judgement Required Fix was load-bearing DOM and which was already true; reported a base failure as pre-existing that `origin/main` passes |
| 102 | implementer | sonnet | `UX-691` a flake ledger (bounded) | 146k | 105 | 21.1 m | merged | the derived cost row and the context map both red from adding two test files, and neither is in the task file or `rules.md` |
| 102 | implementer | sonnet | `UX-702` a performance ratchet at the gate (bounded) | 259k | 230 | 52.6 m | merged | issued early reads against the shared checkout instead of its worktree; left `dev_perf_ratchet.py` off the §6 context map |
| 102 | implementer | sonnet | `UX-712` the size ledger (bounded) | 416k | 227 | 59.2 m | merged | stalled twice waiting on a background notification that never arrives; found pylint attributes every duplicate-code hit to one arbitrary module |
| 102 | implementer | sonnet | `UX-703` a weekly mutation run (bounded) | 226k | 207 | 76.6 m | merged | stalled on a backgrounded mutmut run; mutmut copies the tree one directory deeper, so every `parents[N]` root in this repo resolves wrong inside a mutant |

Five implementer runs, 1,366k, zero verifier runs — the same shape
`round-100.md` records, and the same absence `round-103.md` names:
"no round since 95" dispatched a verifier before merging. `UX-667`'s
and `UX-691`'s commits (`312483c` 17:15, `299e839` 17:29) both land
before the `af56022` gate (18:08); `UX-702`'s, `UX-712`'s and
`UX-703`'s (`a7f5552` 18:00 onward) land after it. The gate is a
checkpoint inside the round the ledger names, not its boundary.
