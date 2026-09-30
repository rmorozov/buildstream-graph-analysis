# UX-1172: text residue after UX-1166

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer, bga/structural, bga/cli.py | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

`bga/structural/serialization_points.py:89` writes " - variables: notparallel: True - " into the macro_micro `#serialization_point_risks` Hint (a raw YAML key and two spaced hyphens; the same shape sits in `bga/utilisation/envelope.py:183` and `bga/cache_effectiveness.py:387`). `bga/findings.py:1622` starts the "Work them in this order" detail with four spaces and "- the last of those leaves 68.8% ..." (the guard's regex wants a word before the hyphen). Copy finding buttons carry "->" in aria-label and title ("... 2.1 min -> 54.5 s"). `#document_shape` says "with [] for a list step" and no [] is on the page. The Perfetto question prose shows raw `**flows**` asterisks. `cli.py:168` prints "{x:.2f}s" with no space. Markdown copy carries unit-less microseconds ("| layer07/mod000.bst | 279000 |" where the table shows 279 ms). `#critical-path-drawn` chain names break inside the token ("layer03/mod" / "009.bst", `.path-name` `overflow-wrap: anywhere`).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

No spaced hyphen dash, raw YAML key, leading bullet, ASCII arrow or raw asterisk in reader text; names carry the arrow glyph; the "[]" clause is dropped; the CLI prints a spaced unit; Markdown copy carries a unit; a chain name breaks at its separators, not inside a token.

## Out of Scope

The schema descriptions `UX-1159` fixed; the JSON copy's field names.

## Acceptance Test

At 1440 and 390 on the three pages no reader text or accessible name holds a spaced hyphen, a leading "- ", "->", "**" or a bare key path, and `bga` prints "1.50 s". Guard: `test_a_reader_sees_labels_not_keys.py` extended to names and bullets. Mutation: restore one string, and the guard reds.

## Outcome

Open.
