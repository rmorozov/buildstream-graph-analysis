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
