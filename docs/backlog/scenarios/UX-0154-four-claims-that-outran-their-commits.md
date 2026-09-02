# UX-154: four claims that outran their commits

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-136, UX-138, UX-141 (the logs this corrects) | **Topic:** docs

## Motivation

The round-15 review diffed round 14's landings against what their logs
claim, and four claims describe work the commits do not contain — the
same class as UX-131's status drift, but in prose rather than a table,
where no guard test can catch it:

1. **UX-136 item 1** says `real-project.md` now teaches `bga baseline`
   — `grep -c "bga baseline" docs/guides/real-project.md` is **0**,
   and `real-project.md:667-683` still teaches the exact superseded
   three-`--baseline-run` assembly the item was filed against. README
   and `ci-comment.md` were fixed; the guide named in the claim was
   not.
2. **UX-138's `toll` sweep** stopped one file short: `bga correlate`
   still alternates inside one sentence ("…sandbox **tax** … X.Xs of
   **toll**", `bga/correlate.py:1189`) and prints "sandbox toll" twice
   more (`:1212-1215`, pinned by `tests/unit/test_granularity.py:120`)
   — while the claimed no-`toll` guard
   (`tests/unit/test_cache_logs.py:408`) is scoped to the cache-logs
   report only.
3. **UX-135's log** says README went 430 → 245; the old README is
   **420** lines (`git show 0acaff5:README.md | wc -l`).
4. **UX-141's Out of Scope** attributes the group-stop detach to
   "UX-142"; that finding is UX-143.

## Required Fix

Teach `bga baseline` in `real-project.md`'s comparison section
(replacing the three-flag assembly, one command plus one sentence);
finish the `toll` sweep in `bga/correlate.py` and widen the no-`toll`
guard to every user-facing renderer (update the granularity test's
pin); correct the two figures/cross-references and annotate each log
per the UX-132/UX-144 convention.

## Out of Scope

- Every other UX-135..UX-139 claim — verified exactly as filed
  (corpus 3,128 → 2,203 confirmed to the line; the relocations,
  glossary, journey-B page and duplicate-cluster cuts all hold).

## Acceptance Test

`grep -rn "toll" bga/ --include="*.py"` finds no user-facing string
(comments citing UX-99's history are fine); the docs-commands test
covers `real-project.md`'s new `bga baseline` block; both corrected
logs carry their annotations. `make lint-docs` and the full docs
enforcement suite stay green.


---

## What was built

All four, and each log annotated per the `UX-132`/`UX-144` convention.

1. **`real-project.md` teaches `bga baseline`** — the one-command form
   leading, the three-flag assembly kept as what it composes. A
   docs-commands guard now asserts it, because a prose claim about prose
   is exactly what nothing else catches.
2. **The `toll` sweep finished.** `bga correlate` was alternating
   "sandbox tax" and "toll" inside one sentence and printing "sandbox
   toll" twice more, pinned by a test. The new guard **parses** every
   module in `bga/` and `tools/` and checks string literals the code can
   print — docstrings and comments recording `UX-99`'s history are where
   the word belongs, and the `toll_*` JSON keys stay, because they are a
   published contract (`UX-75`) and renaming a field to tidy prose would
   break every consumer keyed on it.
3. **430 → 420.** The README reduction is 175 lines, not 185.
4. **UX-141's cross-reference** said UX-142 (doctor's hardcoded target)
   where it meant UX-143 (the group-stop detach).

Worth naming: three of these four are claims *I* wrote, in logs
describing my own commits, and none of them was catchable by a test at
the time. The guard added for (1) is the only one of the four that
mechanically cannot recur.
