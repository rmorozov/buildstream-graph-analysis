# UX-176: three guards that assert less than their logs say, round three

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-163, UX-164, UX-165, UX-169, UX-170 (the logs these correct)

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

## What was built

Five guards that described more than they checked, made to check what
they describe.

1. **The walk-back hint is pasted.** The tests asserted on the *string*
   `_compare_refs` returns; one now resolves both refs through the same
   store lookup a user's paste goes through and asserts they land on
   the two run directories that were compared. Reverting
   `_compare_refs` to `@prev @last` reddens it. Found while writing it:
   the fixture used `01`/`02` as snapshot names, which are not valid
   `@<stamp-prefix>` aliases at all - the paste property is only
   testable against real stamps, so the test uses them.
2. **Both store shapes render.** The singular/plural check asserted
   that both wordings appeared in `main`'s source, which holds whichever
   branch is reachable. The sentence moved into `_walkback_notice` and
   the test renders it for one skip and for two. Making the singular
   branch unreachable reddens it.
3. **The fragment check matches its description.** It was documented as
   "every one must end in a terminator" while its pass-list accepted
   `,` `:` `)` `]`. The pass-list is now real terminators only, scoped
   to blocks that carry prose rather than argparse's own metavar
   renderings - which took **sixteen** further help strings to satisfy,
   every one of them a real unpunctuated sentence.
4. **The phase-conversion guard uses a seam.** It compared two
   `source.index()` positions, which holds for any file where one
   string precedes another - it would have passed with the handler
   deleted and the words left in a comment. It now raises
   `KeyboardInterrupt` from inside the analysis phase and asserts on
   exit 130 and what the user sees on stderr.
5. **Two prose slips annotated**, per the `UX-132`/`UX-144` convention:
   `real-project.md` called the band's escapee the "slowest" run when
   2712.39s is the *fastest*, and `UX-169`'s Motivation called the
   report row a third copy when `report["processes"]` *is* the records
   list. Both corrected in place with the correction marked.

**And UX-165's count is one number.** That file said "seven" in three
places and listed nine; the commit repaired **ten** - nine in
`bga/cli.py`, one in `tools/`. Counted from the diff, not from memory.
