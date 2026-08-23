# UX-241: architecture review has no cycle

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-233 (the drift guard), UX-237 (the filing rule) | **Serves:** R8, and the maintainers pricing the next big change | **Topic:** docs

## Motivation

The user's last observation: *regarding keeping documentation updated
and architecture flexible we need regular cycles of architecture and
documentation state review to place new tasks.*

`UX-233` fixed the drift once and guarded the mechanical half — every
published schema id must appear in the spec and the architecture
inventory. What it cannot catch is the half that matters most: a
*chapter* that describes a mechanism the code no longer has. The
architecture document went a whole axis out of date (rounds 21-26,
about 250 commits) before anyone noticed, and nothing in the process
would have noticed it sooner.

Feature audits happen here on a cadence — twenty-eight rounds of them.
Architecture and documentation review does not, and the asymmetry is
why one drifts and the other does not.

## Required Fix

1. **A review is a round type**, described where the streams are
   (`UX-239`): its input is the diff since the last review, its output
   is filings, and it produces no code.
2. **A checklist with teeth**: for each architecture chapter and each
   guide, does the code still do what it says; does every published
   contract have a home; is any figure invalidated; what shipped since
   the last review with no document naming it.
3. **The trigger is measured, not remembered.** A guard reports the
   distance since the last recorded review — commits, and rounds — and
   reddens past a stated bound, the same way the store's size warning
   works. The bound is a decision to argue for, not a number to guess:
   round 28's evidence says one axis is too long.
4. The review's output goes in `docs/audits/` like every other round,
   so the next one can measure against it.

## Out of Scope

- Reviewing the spec's Part text. It is ground truth and the fixing
  guide forbids editing it; a review that finds it wrong files against
  it instead.
- Automating the judgment. The guard measures *distance since*, never
  whether a chapter is true.

## Acceptance Test

The review round type is described with its input, output and
checklist; the distance guard reports a real number on this tree and
reddens past the bound (verified by moving the recorded marker back);
the first review is run and its filings land.
