# UX-250: comparison refuses on host and mode, but not on contract movement

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-249 (the stamp it reads) | **Serves:** R4 — whose gate must not report a definition change as a regression | **Topic:** contracts

## Motivation

With `UX-249`'s stamp recorded, the policy question becomes answerable,
and it is the one Direction 10 was really about: when are two runs
measured by different builds of `bga` *not* comparable?

The wrong answer is "when the package versions differ". It would refuse
every comparison across every upgrade, including the twenty-eight
rounds that changed no contract at all, and a refusal that fires
constantly gets switched off — which is how this repository lost, and
then rebuilt, several guards.

The right answer falls out of the stamp: **refuse when a contract the
comparison depends on moved between the two producers, and report
otherwise.** Two runs from `0.1.0` and `0.9.0` still compare when every
contract they touch is unchanged; two runs one patch apart refuse when
one is not.

Today neither happens, because there is nothing to read.

## Required Fix

1. `bga compare` gains contract movement as a refusal reason, reusing
   `EXIT_CODE_MISMATCHED_RUNS` (6) and the existing refusal wording —
   this is one more dimension of an existing answer, not a new one.
2. The store's aggregate and the trend, which mix many runs rather than
   two, report the contract sets present and exclude the minority the
   way `store-aggregate` already excludes a host class — a distribution
   over two definitions is not a distribution.
3. A missing stamp is **not** a refusal. Every artifact written before
   `UX-249` lacks one, and refusing them would make the feature's
   arrival delete everyone's history. It is named, and counted.

## Out of Scope

- Migration or translation between contract versions. If `analyze/v2`
  arrives, converting `v1` runs is its own decision with its own
  evidence; this item refuses honestly rather than guessing.
- Refusing on the package version. Argued out in Direction 10: it
  would refuse every comparison across every upgrade, including the
  twenty-eight rounds that moved no contract at all.

## Acceptance Test

Two synthetic runs whose stamps differ only in package version compare
normally; two whose stamps differ in a contract the comparison reads
refuse with exit 6 and name the contract; a run with no stamp compares
with the absence named. The first two cases need a fabricated `v2`
stamp, since no contract has yet moved — and that is the point of
building this before the first bump rather than after.

## Outcome

**Status:** 🟢 Fixed & Verified

`bga compare` gains contract movement as a refusal reason, reusing
`EXIT_CODE_MISMATCHED_RUNS` (6) and the existing refusal grammar. Run
against two real run directories:

```text
$ bga compare /tmp/cmp_a /tmp/cmp_b          # candidate rewritten to analyze/v2
Refusing to compare these runs (producer_contracts):
  - the two runs were measured against different published contracts
    (analyze/v1 → analyze/v2), so their numbers do not mean the same thing
Pass --allow-mismatch to compare anyway
exit=6
```

**The refusal is on contract movement, never on the version.** The
policy behaves as Direction 10 argued, measured on fabricated stamps
because no contract has yet moved:

```text
0.1.0 vs 0.9.0, identical contracts   -> compares (a note, no refusal)
0.2.0 vs 0.2.1, analyze/v1 → v2       -> refuses
0.2.0 vs 0.3.0, whatif/v1 → v2        -> compares (a comparison never reads it)
unstamped vs 0.2.0                    -> compares, absence named
```

`COMPARISON_CONTRACTS` names what a comparison actually reads. Refusing
on every contract would make `whatif/v1` moving refuse two durations,
and a refusal that fires constantly gets switched off — which is worth
less than none.

**A missing stamp is named, not refused.** Every artifact predating
`UX-249` lacks one; refusing them would make the stamp's arrival delete
the history it was built to protect. It renders as a caveat beside the
numbers, in `comparability_warning` rather than `mismatches`, which is
where `UX-186` put the cross-host caveat for the same reason.

`--allow-mismatch` still opts back in, because a new refusal with no
way past it is a new way to be stuck.

**Mutations verified red and reverted (6):** the policy comparing
versions instead of contracts (reddened two); the read set becoming
every contract (reddened two); an unstamped run being refused; `compare`
no longer acting on the movement.

**Deviation from the Required Fix:** clause 2 — the store's aggregate
and the trend reporting contract sets across many runs — is **not
implemented**. `compare` is the two-run case and is done; the
many-run case needs a decision about what "the minority" means when
three contract sets are present, and guessing it here would ship a
rule nobody argued. Filed as `UX-253` rather than left as a comment,
per `§3.11`.

Small tier: `2079 passed, 1142 deselected in 26.57s`.
Full suite: `3218 passed, 3 skipped in 360.71s`. `make lint`: clean.
