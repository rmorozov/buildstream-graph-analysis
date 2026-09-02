# UX-525: a track costs 81k-131k tokens, and nobody knows where

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-504 (the implementer whose runs these are), UX-500 (the measurement round it joins) | **Serves:** the maintainer's subscription | **Topic:** docs

## Motivation

Round 75 ran three implementer tracks and recorded, for the first
time, what one costs:

```text
track    wall      tokens
UX-490   943 s     81k
UX-492   996 s    123k
UX-493  1,174 s   131k
```

Three numbers and no split. The register (`UX-497`) cut what a
session *reads*; nothing says whether a track's tokens go to reading
the task file and its ranges, to pasted test output, to the Outcome,
or to retries — and the levers differ for each. Pytest output alone
is a suspect: a full `-q` run of a browser file prints hundreds of
lines the agent then quotes back.

## Required Fix

Instrument the next three tracks: the implementer's transcript
split into phases (orient/read, edit, test output, falsify, Outcome,
close) with tokens per phase, pasted in the round document beside
the wall clock. Then the one or two cheapest levers, named from the
split — the expected ones are a `make test-touching` that prints one
line unless red, and `-q --tb=short` as the agent's only pytest
shape — each landed with its before/after on a fourth track.

## Out of Scope

- Any model or context-window setting — the cost is what the agent
  reads and writes, and that is what is measured.
- The audit session's own tokens — a different shape of work; measure
  it separately if the track figures prove the method.

## Acceptance Test

Three tracks' phase splits pasted; one lever landed with its
before/after; the round-75 figures cited as the baseline.

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

Round 75 wrote `943s · 996s · 1,174s` and `81k · 123k · 131k` as two
unordered lists with no definition. The transcripts are on disk, so the
tool pairs them: 943 s / 78,583 is `UX-490`, 996 s / 119,062 `UX-493`,
1,174 s / 126,187 `UX-492`. The wall clocks match round 75 exactly; the
totals sit 3.1-3.8% under its.

### After

`tools/dev_track_cost.py` reads the transcript's per-response `usage`.
The quantity is `input_tokens + cache_creation_input_tokens` per API
response: summed it reproduces each track's final context to **0.2%**
(78,583 vs 78,455), so it is the whole track, not a sample. A response's
cost is charged to the *previous* response's phase — what entered the
context is that turn's tool results.

Three splits pasted in
[`docs/audits/data/round-75-track-cost.md`](../../audits/data/round-75-track-cost.md),
`UX-490` / `UX-493` / `UX-492`: **read 37.7 / 42.5 / 63.7%**, edit 41.4
/ 10.0 / 14.0, close 1.1 / 22.3 / 0.8, brief 11.0 / 7.5 / 7.0, falsify —
/ 9.0 / 7.8, test 5.8 / 5.0 / 2.5, outcome — / 2.9 / 4.2, other 3.0 /
0.8 / 0.1. Pytest output by command match is **10.0 / 15.7 / 10.2%** —
the filing's suspect, confirmed — but `make test-touching` is only 537 /
3,166 / 1,184 of it in 1-3 runs; the rest is 10-16 direct `pytest` runs.

### The lever landed, before and after

`dev_touching` prints one line on green, everything on red. Same
selection, same tree; `--loud` is the old behaviour:

```text
$ python3 tools/dev_touching.py --base babc6f0~1 --loud <3 deselects>
rc=0   14 lines, 792 chars
$ python3 tools/dev_touching.py --base babc6f0~1 <3 deselects>
rc=0    1 line,   43 chars:  7 file(s) selected · 255 passed in 36.74s
```

749 chars a green run, ~190 tokens; at 1-3 selector runs a track that is
**0.2-0.5%**, not the 10-16% the phase name suggests. Stated rather than
claimed — `UX-420`'s shape.

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| M1 | `responses()` keys by record, not `message.id` | 3 clauses of `TestOneResponseIsCountedOnce` |
| M2 | cost charged to the receiving turn | `..._charged_for_what_pytest_printed`, `0 == 9000` |
| M3 | `cache_read_input_tokens` added to the cost | `..._not_in_the_total`, `110300 == 300` |
| M4 | `PHASES` orders `read` above `test` | `..._charged_to_the_higher` |
| M5 | a `Write` to a task file is an ordinary edit | `..._is_the_outcome_not_an_edit` |
| M6 | green prints the whole run again | `test_green_is_one_line`, `7 == 1` |
| M7 | red is summarised too | `test_red_is_the_whole_run` |

**An instrument of this item's was wrong, and validating it against the
context high-water caught it.** The first version summed `usage` per
JSONL *record*, and the harness writes one record per content block each
repeating the same `usage`: it read `UX-490` as 107 turns and 140,700
tokens against 65 and 78,583, with `other` at 35-40%. M1 is that defect
as a standing guard. `output_tokens` is not summed either — this
transcript reports 8 for a response carrying two tool calls.

`make lint` clean; `make test-touching` on this diff → `3 file(s)
selected · 177 passed in 7.69s`, with the three status-drift clauses
deselected: they read the index row the orchestrator has yet to move.
The new guard file is 20 tests in 0.14s, so no tier row.

### Deviation from the Required Fix

Four, named. The three tracks are **round 75's**, not round 80's: they
are the three the filing quotes as its baseline, and round 80's other
two are still running. The splits are in `docs/audits/data/`, not the
round document — `docs/audits/round-80.md` does not exist and is the
orchestrator's. **One** lever landed, not two: the second edits the
agent's instructions, which another track may hold this round. And its
before/after is the command's own output, because a fourth track is not
something one track can run.
