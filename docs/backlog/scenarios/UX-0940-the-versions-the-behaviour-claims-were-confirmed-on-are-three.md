# UX-940: the repository's BuildStream behaviour claims are pinned to three versions and nothing says which were re-confirmed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-571 | **Blocks:** — | **Found by:** round 136 — reading the durable version claims while filing `UX-939`, after CI's binary moved to 2.8.1 | **Serves:** whoever reads a BuildStream behaviour claim in this codebase and has to decide whether it still holds | **Topic:** guards | **Area:** bga | **Shape:** judgement

## Motivation

`UX-939` argues that the durable form of a version claim is what a
version *publishes*, because that is checkable by anyone against any
binary of that version. The repository has such claims, and they name
two different versions:

```text
$ grep -rn "BuildStream 2\.[0-9]\.[0-9]" bga/ tests/unit/ --include=*.py
bga/artifact_weight.py:5          BuildStream 2.8.0 publishes no such number
bga/cache_capacity.py:7           the cheapest exact source BuildStream 2.8.0 has
bga/cache_effectiveness.py:226    BuildStream 2.8.0 publishes ...
bga/schemas.py:2928               BuildStream 2.8.0 has no artifact size
tests/unit/test_an_artifact_has_a_weight.py:4   2.8.0 publishes no per-element figure
bga/structural/serialization_points.py:10   re-checked against a real BuildStream 2.7.0 install
bga/ingest/models.py:16           get_unique_key() returns a constant - confirmed via BuildStream 2.7.0
```

The two 2.7.0 lines are load-bearing behaviour claims, not history.
`serialization_points.py` asserts that `max-jobs` is a protected
project-wide base variable an element may not redefine and that
BuildStream never reads `max-jobs` from `public:` — the whole module
exists because of what that rules out. `models.py` asserts that a
`stack` element's `get_unique_key()` returns a constant, which is why
`stack` is in the closed list of kinds the analysis flags.

Both were confirmed on 2.7.0, and `UX-939` re-read both in 2.8.1's own
wheel before moving the pins:

```text
buildstream/plugins/elements/stack.py   def get_unique_key: return 1
                                        BST_ELEMENT_HAS_ARTIFACT = False
buildstream/element.py:3103             for var in ("project-name",
                                          "element-name", "max-jobs"):
                                        "invalid redefinition of
                                        protected variable"
grep max-jobs, whole wheel           no read of it from `public:`
```

**They hold.** The row is not that the claims are wrong; it is that
nothing in the tree records that anyone checked. The same two sentences
read identically whether they were re-confirmed today or never since
round 31, and nothing will notice on 2.8.2.

`UX-939` met the cost of that directly. The natural place for the
record is beside each claim, and `bga/structural/serialization_points.py`'s
module docstring is already 36 lines against the register's 25, which
older files may only shrink — so the re-read went into a task file's
Outcome instead, which is the one place a later round will not think
to look. `bga/ingest/models.py` had room and now names both versions.
A record with no cheap home is the argument for giving it one.

That the claims are *stated with* their version is right, and better
than the exercised line `UX-939` is about, because a reader can check
them. What is missing is any record of which have been re-checked
since, so today the answer is "read the git log and guess".

## Required Fix

Say, once and in one place, which BuildStream version each behaviour
claim was last confirmed against, in a form a guard can read, and what
happens when the runner's version moves past it — a warning that names
the unre-checked claims is enough; a red that nobody can clear is what
`UX-939` is filed against.

`UX-939` has already done the re-checking once, by hand, for two
claims. What is missing is the place to put it and the thing that asks
again.

## Out of Scope

`UX-939`'s exercised line and its guard, which is the other half of
this and has to be decided first: this row's "in one place" should be
whatever that decision leaves. Re-checking every fact in
`docs/spec/ingestion-pipeline.md`.

## Acceptance Test

A reading, pasted with its command, of each behaviour claim against the
BuildStream version CI runs, with a stated verdict per claim; and a
guard that reddens when a claim's recorded version is older than the
binary the tier ran on, with a mutation that ages a claim reddening it.

## Outcome
