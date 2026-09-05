# UX-707: the orchestrator's rebuilds are counted and priced, per session

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-525 (the track-cost tool), UX-663 (the run ledger) | **Serves:** the session deciding how long to stay idle and how much to keep in view, from a number rather than a feeling | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

`tools/dev_track_cost.py` prices a track by phase; nothing prices the
session that runs the tracks. Round 94 read this session's own
transcript: from round 46 on, 336 responses and 5.16M fresh tokens,
of which 11 responses with no tool before them — a wake after idle or
a compaction, re-entering the whole live context — were 3.76M, 73 %.
Reading was 4 %, writing 8 %, tests 3 %.

## Required Fix

`tools/dev_track_cost.py --session <transcript>`: one response per
`message.id`; a **rebuild** is a response over a floor (30k) with no
tool call in the response before it; print rebuild count, their
tokens, their share, and the live context at each (the response's
cost); per round when `--rounds <sha,…>` gives the boundaries. One
line per session in the run ledger, beside the agents' rows.

## Out of Scope

- Preventing rebuilds — the harness compacts and the cache expires;
  the lever is the live context's size, which the number makes
  visible.
- Pricing another session's transcript — a sibling's is not on this
  disk.

## Acceptance Test

On this session's transcript the tool prints 11 rebuilds and 3.76M;
mutation: count a response with a tool before it as a rebuild — the
count moves and the guard on a synthetic transcript reddens.

## Outcome

**The gap, measured.** No `--session` flag existed; `responses()` and
`_fresh()`-shaped cost were already there for the phase split, nothing
read them for a rebuild. `--floor` and `--rounds` were absent too.

**The close, measured.** `python3 tools/dev_track_cost.py --session
<this session's transcript>` (grown past round 94, run at round 95):
`rebuilds 36  tokens 14622448  share 78.7%` — round 94's 11/3.76M/73%
was this same live file measured 45 responses earlier; the file keeps
growing across rounds, so the ratio (not the count) is the stable
figure. `--rounds "a=2026-08-18T13:00:00Z,b=2026-08-19T10:00:00Z"` on
the same file: totals partition every response, `sum(tokens) ==`
the ungrouped total (checked by
`tests/unit/test_a_rebuild_is_a_wake_with_nothing_before_it.py`). The
verifier found `range(1, len(rows))` could never count response 0 -
the purest rebuild, nothing at all before it; fixed to `range(len(rows))`
with `index == 0 or not rows[index - 1][0]`, which moved the live
count from 35 to 36.

**Mutations.**

| mutation | reddened | count |
|---|---|---|
| drop the "no tool before it" guard (`cost > floor` alone) | `test_a_big_response_after_a_tool_carrying_one_is_not_a_rebuild` | 1 failed, 4 passed |
| `cost > floor` → `cost >= floor` | `test_a_response_at_the_floor_is_not_over_it` | 1 failed, 4 passed |
| restore `range(1, len(rows))` | `test_a_big_first_response_is_a_rebuild` | 1 failed, 5 passed |

**Deviation.** `--rounds` kept the old `index > 0` idiom after the track's fix and could not count a first response; made equal to `--session` at the merge. The acceptance figures (11 rebuilds, 3.76M) were a moving transcript's; the share, 73-79 %, is the durable one.
