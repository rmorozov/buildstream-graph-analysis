# UX-176: three guards that assert less than their logs say, round three

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-163, UX-164, UX-165, UX-169, UX-170 (the logs these correct)

## Motivation

The round-18 review's target-class summary was clean — every measured
number reproduced exactly — and what remains is the UX-143/UX-131
class one size smaller: guards weaker than their prose, and prose
slips. All verified against the code:

1. **UX-164's paste-and-go claim is untested prose.** "The hint is
   byte-identical to what the snapshot command itself ran" has no test
   that pastes it; and `test_one_skipped_snapshot_reads_singular` is
   vacuous — it greps the *source* for both wordings, so it passes
   with the conditional inverted.
2. **UX-165's guard claim overstates the test.** The log says "every
   one must end in a terminator"; the test skips any block ending in
   `. ) ] : ! ? ,` (a comma counts as fine) and otherwise only rejects
   a ~38-word dangling-word list — a truncation ending on an unlisted
   noun passes. The test's own docstring is honest about being a shape
   check; the task file's summary is not. Also: the file's headline
   says seven strings, its list has nine, the annotation says ten.
3. **UX-163's "every phase converts" guard is source inspection**
   (`source.count("except KeyboardInterrupt:") >= 2`), not behavior —
   the live behavior held this round, but the guard would hold with
   both handlers broken.
4. Prose slips, one each: UX-169's Motivation keeps its
   19/246/517/917 table and "materialised three times" story
   uncorrected while its own fix disproves the third copy
   (`report["processes"]` *is* the records list — same objects);
   `real-project.md:785` says the "slowest" run falls below the band —
   2712.39s is the *fastest* (the UX-170 backlog file gets it right).

## Required Fix

A test pastes the walk-back hint verbatim and asserts the same pair
compares; the singular/plural test renders both store shapes; the
help fragment check either matches its description (terminator
required, comma removed from the pass-list) or the log's claim narrows
to what the check does; the phase-conversion guard SIGINTs each phase
through a seam instead of grepping source; the two prose slips
annotated per the UX-132/UX-144 convention, and UX-165's count made
one number.

## Out of Scope

- The features themselves (all verified working live this round).

## Acceptance Test

Each strengthened guard reddens on its natural mutation (hint built
from the wrong pair; conditional inverted; a help string truncated to
end on a noun; one handler removed); the annotations are in place;
`grep -n "slowest" docs/guides/real-project.md` finds no band
sentence.
