# UX-165: ten help strings end mid-sentence

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-158 (the concision pass that cut them)

## Motivation

UX-158's cut worked at the line level and the guard proves it — but
"flag help cut to its first sentence" was applied by deleting
continuation *lines*, and ten strings lost their sentence's
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

The ten sites render complete sentences under `--help`; the
fragment check reddens when a continuation line is deleted from any
flag help (mutation on one site); every command still meets its
line cap.

## What was built

Ten flag helps got their sentences back — `--plane2` (twice),
`graph --by-kind`, `sweep --calibration-dir`, `correlate --cache-logs`,
`correlate native_report`, `cache-trend run_dirs`, `cache-trend
--format`, `compare --regression-threshold`, and `extract
--native-max-jobs` — rewritten to end where
they mean to rather than restored verbatim, since what UX-158 cut was
mostly design history and only incidentally the predicate.

The reason the cut could do this silently was that UX-158's guard
counted *lines*, so truncation scored as an improvement.
`tests/unit/test_help_is_short.py` now also asserts no help string ends
mid-sentence: every one must end in a terminator, and parens must
balance. That check is what makes the line-count guard safe to keep.

UX-158's own task file carries an annotation that its table of
before/after line counts predates this repair.

**Count corrected (`UX-176`, round 18).** This file said "seven" in
three places and listed nine; the commit repaired **ten** - nine in
`bga/cli.py` and one in `tools/`. One number now, and it is the one the
diff supports.

**And the guard was weaker than this file claimed.** The fragment check
was described here as "every one must end in a terminator", while its
pass-list accepted `,` `:` `)` `]` - a help string ending mid-clause
went through. `UX-176` narrowed the pass-list to real terminators and
scoped the check to blocks that carry prose rather than argparse's own
metavar renderings, which took sixteen further help strings to satisfy.
