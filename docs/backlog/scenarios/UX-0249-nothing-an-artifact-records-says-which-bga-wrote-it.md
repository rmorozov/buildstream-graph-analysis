# UX-249: nothing an artifact records says which bga wrote it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-248 (the set to stamp) | **Serves:** R1 and R7 — whose questions are answered by comparing against runs an older bga measured | **Topic:** contracts

## Motivation

`bga` reads its own past output as input: `@last`/`@prev`, the baseline
set, `cache-trend`, `store-aggregate`. On a project six months old,
those artifacts were written by a different build of the tool.

```text
grep -rn __version__ bga/ tools/ --include=*.py
  bga/__init__.py:15   __version__ = "0.1.0"
  bga/cli.py:28        from . import __version__, schemas
  bga/cli.py:1463      version=f'%(prog)s {__version__}'
```

Two uses, both the `--version` string. It is written into no artifact.
A `run-context.json` from round 3 and one from round 29 are
indistinguishable to the tool reading them both.

This is a missing *comparability dimension*, and this repository is
already strict about those: `bga compare` refuses two runs from
different hosts (`UX-186`) and refuses a caches-off run against a
caches-on one, with an exit code of its own, because "not comparable"
and "comparable and equal" must not look alike. Producer identity is
the same kind of axis with nothing watching it.

## Required Fix

1. A **producer stamp** written into every artifact that is persisted
   and later re-read — at minimum `run-context.json`, the store's
   snapshot metadata, and the published documents: the tool name, its
   version, and **the versions of the contracts that artifact
   depends on** (`UX-248`'s inventory is what makes that enumerable).
2. Absent on an artifact written before this lands, which is most of
   them — so the readers treat "no stamp" as a known state with a name,
   never as a match.
3. It is written, and reported; **this item makes no refusal**. What to
   refuse on is `UX-250`, deliberately separated so the recording lands
   before the policy that reads it.

## Out of Scope

- Rewriting existing artifacts to add a stamp. They are evidence; a
  backfilled stamp would be a guess about which build wrote them, which
  is worse than the absence.
- Comparing package versions to decide compatibility. Direction 10
  argues that one out: the package version in an artifact is
  provenance, and compatibility is per contract.

## Acceptance Test

A freshly written run directory carries the stamp with the real version
and the real contract set; a run directory with no stamp reads back as
an explicit unknown rather than as a match; the golden fixture's
comparison is unaffected, since the stamp is recorded and not yet
judged.
