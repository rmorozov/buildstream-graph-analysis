# UX-251: a release is a contract state, not a date

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-248 (the contract set a release records), UX-241 (the review it consumes) | **Serves:** R4 and R8 — who pin something and need to know when it moved | **Topic:** docs

## Motivation

Direction 10's argument, made operational. Measured today:

```text
bga --version   0.1.0     unmoved across 29 rounds and 247 scenarios
git tag         0
CHANGELOG       none
```

Nothing answers *"what changed between the `bga` I installed and the
one I have now"*. The material exists — 3,549 lines of audit rounds,
789 lines of closed rows, 39 Outcome sections — and none of it is that
document, because all of it is organised by *when the work happened*
rather than by *what a consumer sees*.

The version number is the second half. `0.1.0` is not wrong so much as
meaningless: it has never moved, so it cannot signal that anything did.

## Required Fix

1. **`CHANGELOG.md`** at the repository root — the ledger and the
   notes, in the shape `docs/audits/architecture-review.md` uses for
   reviews: a table of releases, each with its version, date, the
   closed-row marker, the commit, and the contract set that shipped.
2. **The version is derived, not chosen.** Comparing the contract set
   at the previous release row with the set now:
   - any published contract's version bumped, or a subcommand or flag
     removed or renamed → a **breaking** release;
   - a new contract, subcommand or flag → an **extending** release;
   - neither → a **patch** release.
   Pre-1.0 that is `0.MINOR.PATCH` with breaking and extending both
   moving MINOR — and the release row records *which* it was, because
   the number cannot say it while the major is pinned at 0.
3. **A guard on the derivation**: the increment between the last two
   release rows must match the contract delta between them. A version
   somebody picked by feel is a number with no meaning.
4. **A release consumes `UX-241`'s review; it does not add a second
   one.** A release may only be cut when a review row exists at or
   after the previous release's marker — guarded — and that review's
   findings are the release's documentation work. Two mechanisms
   racing for one job is the drift this backlog fixes most often.
5. A `docs/contributing/release-guide.md` for the procedure, pointed at
   from the fixing guide, and a `release` row in `§6a`'s stream table.

## Out of Scope

- A time-based cadence. There are no external consumers yet and nothing
  to deploy; a monthly release would be ceremony generating no
  information. The trigger is contract movement plus a current review,
  both already measurable.
- Publishing to PyPI. That is a distribution decision, and this item is
  about the tool being able to say what it is.
- Making the package version the compatibility signal. Direction 10
  argues it out, and `UX-250` implements the alternative.

## Acceptance Test

The guard reddens on a release row whose version increment disagrees
with its contract delta, and on a release with no review row at or
after the previous marker; `CHANGELOG.md` carries release `0.2.0` with
its real contract set; `bga --version` and the newest release row agree.
