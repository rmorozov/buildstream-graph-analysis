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

Both were confirmed on 2.7.0. CI now runs **2.8.1**. Nothing in the
tree re-checked either on 2.8.0, and nothing will notice on 2.8.2: a
behaviour claim carries the version it was confirmed on and no
expiry, so the same sentence reads identically whether it was
re-confirmed yesterday or never since round 31.

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

Then re-check the two 2.7.0 claims on the version CI actually runs and
record the result, whichever way it goes. `max-jobs` being a protected
base variable and `stack`'s constant unique key are both cheap to read
out of the installed source.

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
