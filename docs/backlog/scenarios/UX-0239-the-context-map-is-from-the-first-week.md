# UX-239: the context map is from the first week

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** every session, human or LLM, in its first minute | **Topic:** docs

## Motivation

`docs/contributing/fixing-guide.md` section 6 is titled *"Where things
live (context map — don't re-derive this)"*. Measured against the tree
it describes:

```text
the map says:  "tests/test_e2e.py   only existing test file"
reality:        220 test files, 3105 tests

modules the map does not mention:
  bga/schemas.py  bga/compare.py  bga/blast.py  bga/correlate.py
  bga/provenance.py  bga/whatif.py  bga/store_aggregate.py
  bga/hostinfo.py  bga/run_store.py  bga/cache_trend.py
  bga/suspend.py  bga/sources.py  bga/progress.py
  bga/report/  bga/viewer/  tools/
```

A map that tells a low-context session **not to re-derive it** and then
describes a tree from the first week is worse than no map: it is
confidently wrong exactly where confidence was requested.

The second half is the user's observation about *streams*. Work here
arrives as several distinct kinds — architecture and design, audit of
landed work or of external feedback, a new feature, a bug fix,
documentation, refactoring — and the guide has one entry ritual for all
of them. "Pick the highest-priority 🔴 row" is right for a feature and
wrong for an audit round, which has no row until it has been done.

## Required Fix

1. **The context map is regenerated from the tree**, and a guard keeps
   it that way: every top-level module and package under `bga/` and
   `tools/` appears, and nothing appears that does not exist.
2. **The streams are named**, with what each one's entry and exit look
   like: design (argues a direction, produces filings), audit
   (measures what landed, produces filings), feature and fix (consume
   filings), documentation (its own stream, per `UX-237`), refactoring
   (needs a stated before/after measurement, not a taste argument).
   Each says which guides apply and what "done" is.
3. The picking rule (§1) branches on the stream rather than assuming
   every session starts from a backlog row.

## Out of Scope

- Rewriting the verification discipline (§3). It is the part that
  works, it is why this repository's claims hold up, and it is
  unchanged.
- A process framework. This is two pages, and the guard is on the map.

## Acceptance Test

The guard reddens on the map as it stands today (proving the gap), and
is green after the regeneration; adding a module without touching the
map reddens it; deleting one and leaving the row reddens it. The
streams section names every stream this repository has actually run in
28 rounds, checked against the round documents in `docs/audits/`.
