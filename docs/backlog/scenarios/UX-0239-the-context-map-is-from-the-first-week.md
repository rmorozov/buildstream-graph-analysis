# UX-239: the context map is from the first week

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** every session, human or LLM, in its first minute | **Topic:** docs

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

## Outcome

**Status:** 🟢 Fixed & Verified

The map was regenerated from the tree and grouped by what a session is
actually looking for — the pipeline, what it concludes and publishes,
the commands that are not `analyze`, the viewer, capture and tools,
tests and docs. `tests/unit/test_the_context_map_is_the_tree.py` holds
it there in both directions: every top-level module and package under
`bga/` and `tools/` appears, and every `bga/`-, `tools/`-, `tests/`- or
`docs/`-shaped path the map names exists.

Measured before the regeneration, 16 of the map's subjects were absent
and one was a claim about a repository with a single test file.
Measured after: 0 absent, 0 stale, and `tests/unit/`'s 218 files named
as 218 alongside the four harnesses beside them.

### The guard matched its own explanation

The first draft of `_map_text()` read everything between `## 6.` and
`## 7.` — which includes the paragraph explaining *why* the section was
regenerated, and that paragraph quotes the old map (`tests/test_e2e.py
only existing test file`) as its evidence. Two guards passed the moment
they were written and would have passed with the map deleted, because
the prose that describes the bug also contains the bug's text.

It now reads only the fenced blocks. This is the **third** instance of
this failure mode in the round — `UX-231`'s "names its reader" check
matched the sentence saying directions must name their reader, and
`UX-233`'s spec check matched anywhere in a 9,000-line file. All three
share one shape: a guard that greps a document for a phrase will find
the phrase in the sentence that argues for the phrase. The rule that
falls out is narrow enough to be useful — **when a guard reads prose,
first say which part of the document is the subject and which part is
the argument**, and read only the subject.

`.bga/runs` caught the same class of under-fitting in the other
direction: `\b(bga|tools|tests|docs)/…` matched the `bga/runs` inside
it and reported a directory a build creates as a path that does not
exist. The pattern now refuses a preceding path character.

### The streams

`§6a` names six — design, audit, feature, fix, documentation,
refactor — as a four-column table (`starts from · produces · done
when`), checked against what the 27 round documents in `docs/audits/`
and this backlog actually contain. Two rules cut across all of them,
and the second is the one worth stating: **the verification discipline
(§3) does not vary by stream.** An audit's measurements are pasted like
a feature's acceptance test.

`§1` now branches before it picks: only *feature* and *fix* start from
a backlog row, and an audit session was previously being told to find
the highest-priority 🔴 — an instruction it cannot follow, because the
rows it will produce do not exist yet. A guard checks that the first
numbered step names `§6a` and that picking a row is not step one.

**Mutations verified red and reverted (7):** a module added without
touching the map; a map row for a path that does not exist; `only
existing test file` restored; a stream with no row; a stream row with
an empty cell; the shared-discipline sentence moved to a later section
(after the guard was scoped to `§6a`, since the first version would
have accepted it anywhere below); the stream step demoted below the
row-picking step.

**Deviation from the Required Fix:** none.

Small tier: `1992 passed, 1130 deselected in 21.65s`.
Full suite: `3118 passed, 3 skipped in 311.44s`.
