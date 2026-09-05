# UX-707: the orchestrator's rebuilds are counted and priced, per session

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-525 (the track-cost tool), UX-663 (the run ledger) | **Serves:** the session deciding how long to stay idle and how much to keep in view, from a number rather than a feeling | **Topic:** guards | **Shape:** bounded

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
