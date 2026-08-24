# UX-251: a release is a contract state, not a date

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-248 (the contract set a release records), UX-241 (the review it consumes) | **Serves:** R4 and R8 — who pin something and need to know when it moved | **Topic:** docs

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

## Outcome

**Status:** 🟢 Fixed & Verified

`CHANGELOG.md` is the ledger, and `0.2.0` — *the build that says what
it is* — is the first recorded release. Each row carries the date, the
closed-row marker, the commit and the **kind**; each release section
carries a fenced `state` block with the contract set and the command
surface, which is what the derivation reads.

```text
| release | date       | closed rows | commit    | kind    |
| 0.2.0   | 2026-08-24 | 243         | fac9618   | initial |
```

`bga/__init__.py`, `pyproject.toml` and the newest row are three copies
of one number — exactly the shape this repository has watched drift
five times — so a guard compares all three.

### The version is derived, and the derivation is exercised

The rule is pure and lives in the guard: a bumped contract or a removed
command is `breaking`, a new one is `extending`, neither is `patch`;
pre-1.0 both of the first two move MINOR, which is why the row records
the kind — the number cannot say it while the major is pinned at 0.

With one release row there is no pair to derive from, so **seven
synthetic pairs exercise the rule** — an unchanged state, a bumped
contract, a removed contract, a removed command, a new contract, a new
command, and a release that both adds and breaks (breaking wins, for
the reader who upgrades for the new thing). A derivation first run on
the day a contract breaks is a derivation nobody has seen work.

The ledger-reading half was then falsified by *planting a second
release*, since a check that zips over pairs is silent with one row:

```text
planted 0.3.0 patch  with analyze/v2  -> "records patch, its state delta says breaking"
planted 0.2.1 extending              -> "0.2.1 is extending and did not move MINOR"
planted 0.2.1 with the review moved back
                                     -> "was cut with no review at or after marker 238"
```

### The argument that was about *not* building something

A release **consumes** `UX-241`'s review rather than adding a second
documentation-sweep trigger, and the guard enforces it: a release with
no review row at or after the previous release's marker fails. Two
mechanisms racing for one job is the drift this backlog fixes more
often than anything else, and the release is cheaper for referring
rather than repeating.

The head names the three findings review 1 filed and left open
(`UX-245`..`UX-247`), so "we knew" is on the record rather than in
someone's memory — also guarded.

**Mutations verified red and reverted (12):** a bumped contract
recorded as a patch; an extending release that did not move MINOR; a
release cut with no review at or after the previous marker; the package
version disagreeing with the newest row; a recorded state that is not
this tree's; the oldest release no longer `initial`; a row with no
state block; the guide no longer saying it consumes the review; a
carried finding going unnamed — plus the seven derivation cases, which
are the rule's own exercise rather than mutations of it.

**Deviation from the Required Fix:** none. No tag was pushed — a tag on
an unmerged branch would name a commit that may be rebased, so it is
the last step of the merge rather than of this commit, and the release
guide says so.

Small tier: `2079 passed, 1142 deselected in 26.57s`.
Full suite: `3218 passed, 3 skipped in 360.71s`. `make lint`: clean.
