# UX-715: fifteen viewer modules, in a passage with no date

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-294 (the acceptance the passage narrates), UX-511 (dated or derived), UX-340 (the module graph instrument) | **Found by:** architecture review 17, checklist item 3 | **Serves:** a reader of the architecture's viewer chapter, counting modules | **Topic:** docs | **Area:** bga/viewer | **Shape:** judgement

## Motivation

`docs/design/architecture.md:1465`:

> `UX-294`'s acceptance (*named in at least one document under
> `docs/`*) had become true of all **fifteen** viewer modules by
> attrition, while the architecture — the document a reader of
> `bga/viewer/` opens — named eight

```console
$ ls bga/viewer/*.js | wc -l
22
```

The passage is past tense and narrates a decision, so it is close to a
record — but it carries no date and no id anchoring *when* fifteen was
true, and "all fifteen viewer modules" reads as a statement about the
directory. A reader counting modules against it is out by seven.

This is the smallest instance of the shape the last four reviews have
each found once: a figure in prose, correct when written, that no guard
reads and no date pins.

## Required Fix

`UX-511`'s remedy, which is dating rather than deleting: the sentence
says *fifteen at `UX-294` (2026-08-…)*, or names the id whose tree had
fifteen, so the number is anchored to a moment rather than to the
directory. The passage's argument does not change.

## Out of Scope

- The live viewer module map elsewhere in the chapter, which `UX-340`'s
  instrument derives and a guard reads — it is correct at 22.
- A sweep of every historical figure in the architecture document. The
  population has not been measured and a sweep wants deriving rather
  than grepping, which `UX-660` already noted is a different row.

## Acceptance Test

No bare count of viewer modules in the architecture document reads as
current. Mutation: add a module under `bga/viewer/` — no sentence
becomes false that a guard does not already catch.

## Outcome

**The gap, measured.**

```console
$ sed -n '1465,1467p' docs/design/architecture.md
had become true of all fifteen viewer modules by attrition, while the
architecture — the document a reader of `bga/viewer/` opens — named
eight; so the guard went on the map instead.
$ ls bga/viewer/*.js | wc -l
22
```

Fifteen, undated, against a live 22.

**The close, measured.**

```console
$ sed -n '1464,1467p' docs/design/architecture.md
`UX-294`'s acceptance (*named in at least one document under `docs/`*)
had become true of all fifteen viewer modules at `UX-294` (2026-08-26)
by attrition, while the architecture — the document a reader of
`bga/viewer/` opens — named eight; so the guard went on the map
```

`UX-294`'s own close commit (`3e2c9c1`, `git log --follow` on its task
file) is dated 2026-08-26, matching the date used. The argument (a
guard that was green for asking the maintainer's question) is
unchanged.

**Mutation, and why no new guard.** Ran the Acceptance Test's own
mutation: added `bga/viewer/zzz_mutation_test.js`, ran
`test_the_viewer_modules_have_a_home.py` — two failures, both from
`UX-294`'s existing map guard (`test_every_module_has_an_entry`,
`test_each_module_is_named_somewhere_in_the_docs_tree`), zero new
ones. No sentence in the dated passage became false; reverted (`rm`,
confirmed `git status` clean, 27 passed).

No guard is added for the "fifteen" sentence itself. Once dated to
`UX-294`, it is the shape `CLAUDE.md`'s own bare-count guard already
carves out: *"a figure frozen to a closed item... cannot go stale,
which is why that sentence spells its number and \[that guard\] reads
digits"* (`test_no_line_carries_a_count_that_a_close_makes_wrong`,
citing the `UX-420` example). A clause asserting "fifteen" stays next
to "UX-294" would only redden if someone deleted the date this row
just added — testing the edit against itself, not the tree.

**Deviation.** `test_the_verification_log_is_true.py` requires the
commit crediting an item to be the one that re-grounds the log
(oldest-match-wins on the subject), so a Verification Log entry had to
land in this same commit. Re-grounding it against `bga.contracts` and
`bga/schemas.py` found two figures the entry below had not tracked —
**56 → 60** `analyze/v6` top-level properties, **22 → 23** viewer
modules — moved by items this row did not audit; recorded in the new
entry rather than attributed. Ids, superseded and printable counts
were unchanged (25/10/9/16/3).
