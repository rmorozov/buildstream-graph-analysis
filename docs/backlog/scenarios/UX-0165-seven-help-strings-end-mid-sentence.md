# UX-165: seven help strings end mid-sentence

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-158 (the concision pass that cut them)

## Motivation

UX-158's cut worked at the line level and the guard proves it — but
"flag help cut to its first sentence" was applied by deleting
continuation *lines*, and at least seven strings lost their sentence's
back half. Rendered verbatim today: `bga correlate --help` ends a flag
with "for the same", `bga graph --help` with "grouped by BuildStream",
and the round-17 review lists five more (`bga/cli.py:1083` "…run.
When", `:1239` "…run. The knee", `:1259` "…different value of the",
`:1343` "…the caller's to know:", `:1440` an unbalanced "(default: the
same significance"). The line-count guard cannot see a fragment — a
truncated string is *shorter*, which is what the guard rewards.

Also from the review, worth folding in: the UX-158 log's
before/after table is stale at HEAD (`capture` 20→23, `snapshot`
29→33 — grown by UX-148/UX-159 flags landed later in the same range;
honest at its commit, wrong at the tip).

## Required Fix

Restore each cut string to one *complete* sentence. Add to the help
guard a fragment check: every rendered help/epilogue line block ends
in sentence punctuation (or a flag default `)`, balanced), so a future
cut that drops half a sentence reddens. Annotate the UX-158 table per
the UX-132/UX-144 convention.

## Out of Scope

- The caps and the CompactHelp formatter (working as designed).

## Acceptance Test

The seven sites render complete sentences under `--help`; the
fragment check reddens when a continuation line is deleted from any
flag help (mutation on one site); every command still meets its
line cap.
