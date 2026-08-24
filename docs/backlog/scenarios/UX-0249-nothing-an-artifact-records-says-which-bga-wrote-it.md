# UX-249: nothing an artifact records says which bga wrote it

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-248 (the set to stamp) | **Serves:** R1 and R7 — whose questions are answered by comparing against runs an older bga measured | **Topic:** contracts

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

## Outcome

**Status:** 🟢 Fixed & Verified

Every run directory and every published `analyze/v1` document now
carries a producer stamp — tool, version, and the contract set the
writing build had — added by `add_producer` beside `add_host_manifest`,
on the same path and under the same best-effort rule.

```text
$ bga gen-synthetic /tmp/s1 --seed 1 && cat /tmp/s1/run-context.json
"producer": {"tool": "bga", "version": "0.2.0", "contracts": [...9 ids...]}
```

**The whole contract set, not this artifact's dependencies.** A writer
that enumerates its own dependencies freezes the guess into every
artifact, where it cannot be corrected; the full set is nine short
strings and lets a *reader* compute whichever subset its question
needs. The policy then lives in one place (`UX-250`) instead of being
frozen into every writer.

**Recording only.** No refusal here, deliberately: the record has to
land before the policy that reads it, or the policy arrives with
nothing to read.

### The absence has a name

Every artifact in every store today predates this. `read` returns
`None`, `version_of` returns `unstamped`, and `describe` says *"written
before bga recorded its own version"* — never agreement. `None` (no
stamp) and `[]` (a stamp whose enumeration failed) stay distinct
answers, because collapsing them would let the second agree with
anything.

### Two places this touched that were not obvious

The synthetic generator writes a run directory too, so it is stamped —
which makes the reproducibility claim *exact* rather than approximately
true. `bga gen-synthetic --seed 1` still hashes identically across two
invocations; it is byte-identical **for a given version**, which is
what it always actually was.

`tests/test_golden.py` drops `producer` the way it drops `run_instance`:
committing it would make the golden file fail on the first release
rather than on the first regression, which is the opposite of what a
golden test is for. A dropped field with nothing else checking it is a
field that can stop being written unnoticed, so the drop itself is
guarded here.

### Two guards that fired for real

`analyze/v1` gaining a top-level key reddened `test_output_schemas.py`
and `test_the_viewer_renders_the_schema.py`, both naming the fix in
their failure message. The key is declared in `_ANALYZE_OPTIONAL`,
`ANALYZE_FULL_KEYS` and the view-hints — **an addition, so no version
bump**, which is `UX-190`'s rule working exactly as written.

**Mutations verified red and reverted (9, one rejected as never
landed):** the run-context writer stopping stamping (reddened two); the
published document stopping stamping; a missing stamp reading as a
match (two); absent and empty collapsing into one answer; a failed
stamp leaving debris; the golden harness no longer dropping it. The
rejected one was a shell-quoting failure that silently matched nothing
— caught by asserting the mutation landed, which is the step the
`falsify` skill exists to insist on.

**Deviation from the Required Fix:** none. The store's snapshot
metadata is covered transitively — a snapshot *is* a run directory —
rather than by a separate write.

Small tier: `2079 passed, 1142 deselected in 26.57s`.
Full suite: `3218 passed, 3 skipped in 360.71s`. `make lint`: clean.
