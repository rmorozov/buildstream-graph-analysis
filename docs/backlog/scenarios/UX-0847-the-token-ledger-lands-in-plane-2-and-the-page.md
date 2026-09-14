# UX-847: the token ledger lands in Plane 2 and the page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-845, UX-846 | **Found by:** round 117, Direction 20 | **Serves:** R4 and R5 (was the pool or the graph the bound) | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

Every acquire and release under the mode is a timed event no plane
records: the server's pool moves (`UX-845`'s ledger), the wrappers'
holds (`UX-846`) and the sub-makes' reads are invisible to the
envelope, which sees busy cores but not why they were idle - tokens
nobody took, or tokens everybody waited for. `max_jobs_advice` has no
pinned-element rule and cannot say an element is joined.

## Required Fix

`bga/analyzer.py` and `bga/schemas.py`: a `jobserver` block under
`analyze/v6`, additive - `mode`, `pool_ceiling`, `tokens_idle_share`
(pool tokens unclaimed while an element waited on none), `tokens_starved_share`
(a client blocked on the FIFO while busy cores were below capacity),
per-element `tokens_held_p50`/`max` and `joined` (yes, pinned, held,
unknown kind); `bga/correlate.py`'s `max_jobs_advice` marks a pinned
element `refusal: pinned by the project` instead of a number; the
Perfetto trace gains a `jobserver` track from the ledger; the page
draws the block as one table with the two shares in the lead.

## Decomposition

Input classes: a run without the mode (the block absent, byte for
byte today's output), a run with every element joined, a run with a
pinned element and a held tool; the journey it extends is R4's "were
the cores busy" question in the answer key.

## Out of Scope

The scheduler's decisions (`UX-849`); the finding text's wording is
`UX-824`'s register.

## Acceptance Test

`tests/unit/test_the_token_ledger_has_two_shares.py` builds a
synthetic ledger and asserts the two shares and the per-element table;
mutation: count a held token as idle - red. The committed fixtures
refresh with no diff.
