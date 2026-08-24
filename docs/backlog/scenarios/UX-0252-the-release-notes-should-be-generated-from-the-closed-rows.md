# UX-252: the release notes should be generated from the closed rows

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-251 (the ledger the notes live in) | **Serves:** R8, reading what landed; and the maintainers, who should not write it a third time | **Topic:** docs

## Motivation

Every closed backlog row already carries a one-line statement of what
was wrong and a summary of what shipped, with its measurement — 789
lines of them, written at the moment the work was verified, which is
the only moment anyone knows the detail.

Hand-writing release notes would make a **third** copy of those facts,
after the task file's Outcome and the closed row. This repository's
most-repeated defect, by a wide margin, is two hand-maintained copies
of one fact drifting; a third would be a choice to reproduce it
knowingly.

So the notes' body is generated from `closed.md` between two release
markers, and the only writing per release is the head: the theme, the
contract delta, and what a consumer has to do about it.

## Required Fix

1. A generator — a `tools/` program, aliased like the rest — that takes
   two closed-row markers and emits the rows between them, grouped by
   topic, each linking its task file.
2. The head is hand-written and stays hand-written: what this release
   is *about*, the contract delta in a sentence, and the upgrade note
   when there is one. A generated theme would be a summary of summaries
   and worth nothing.
3. A guard that the generated half is generated — regenerating it
   produces no diff, the way `tests/test_golden.py` holds the golden
   snapshot.

## Out of Scope

- Generating the head. Stated above and worth stating twice: the
  judgment half is the half that makes notes worth reading.
- Rewriting closed rows into release-note prose. They are history and
  `UX-232` keeps them verbatim.

## Acceptance Test

The generator run over release 0.2.0's marker range reproduces that
release's body byte-for-byte, and the guard reddens when a closed row
is added without regenerating.

## Outcome

**Status:** 🟢 Fixed & Verified

`bga release-notes --from N --to M` emits the closed rows between two
markers, grouped by the topic each task file declares:

```text
$ bga release-notes --from 238 --to 243   # link targets elided below
5 scenarios closed (closed-row markers 238 → 243).

**contracts**
- UX-248 — `schemas.names()` answers a narrower question than it looks…
- UX-249 — `bga` reads its own past output as input, and nothing an…
- UX-250 — `bga compare` refuses on host and on cache mode…

**docs**
- UX-251 — `bga --version` said `0.1.0`, unmoved across 29 rounds…
- UX-252 — Hand-writing release notes would make a third copy…
```

`contracts` and `cli` come before `docs` because a reader scanning for
*what changed for me* should not have to pass the process news first;
alphabetical would bury the half they came for.

**The head stays written.** Theme, contract delta, upgrade note, and
the findings this release carries. A generated theme would be a summary
of summaries and worth nothing, and the guard checks the head sits
outside the generated block rather than trusting it.

**Regeneration produces no diff**, the `test_golden.py` property
applied to release notes. The marker range travels in the block's own
comment (`<!-- generated: UX-252 238→243 -->`), so the guard needs
nothing but the file — a range kept elsewhere would be the second copy
this item exists to avoid.

Rows 1–238 are stated as predating recorded releases rather than
reprinted: they landed across twenty-nine rounds under a version that
never moved, which is the thing `0.2.0` fixes, and 238 rows here would
be a copy of `closed.md` rather than a changelog.

**Mutations verified red and reverted (4):** the committed body edited
by hand; the generator dropping rows inside its own count; an
impossible range returning silence instead of an error; an item with no
task file being folded into `docs` rather than surfaced as
`uncategorised`.

**Deviation from the Required Fix:** none.

Small tier: `2079 passed, 1142 deselected in 26.57s`.
Full suite: `3218 passed, 3 skipped in 360.71s`. `make lint`: clean.
