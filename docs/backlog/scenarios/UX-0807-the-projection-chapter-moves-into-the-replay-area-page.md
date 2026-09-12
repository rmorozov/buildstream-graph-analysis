# UX-807: the projection chapter moves into the replay area page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-689 (the rule and the first area), UX-806 (the second, and the one-id-per-chapter rule) | **Found by:** round 112, `UX-806`'s Out of Scope | **Serves:** the reader pricing a change to a projection; the session restructuring without losing a sentence | **Topic:** docs | **Area:** bga-replay | **Shape:** mechanical

## Motivation

`UX-806` named the next chapter: the projection one. The log guard's
anchor rule (`tests/unit/test_the_verification_log_is_true.py`,
`closing_commit` takes the oldest commit naming an id) makes each
chapter its own item, its own entry, landed after the last.

```console
$ grep -n "^## " docs/design/architecture.md | sed -n 13p
545:## What a projection is, and why it is a bound (`UX-230`, `UX-74`)
$ sed -n 545,601p docs/design/architecture.md | wc -l
57
```

## Required Fix

The chapter at `docs/design/architecture.md:545-601` moves into a new
hand-written `docs/design/areas/bga-replay.md`, the same shape as
`docs/design/areas/tools-native_trace.md`: a heading, the "Moved from"
pointer paragraph, the prose verbatim, links re-based. `architecture.md`
keeps the heading and a one-paragraph pointer, plus any line a guard
reads (find them: `grep -ln "architecture.md" tests/unit/*.py`, then
each guard's landmarks inside lines 545-601). `docs/README.md`'s design
index names the new page; the generated `docs/backlog/areas/bga-replay.md`
carries the derived `Mechanism:` line after `dev_close_task.py --check
--write`. A new Verification Log entry crediting `UX-807` rides the same
commit (the guard's rule), saying what was re-grounded and against what.

## Out of Scope

- The other chapters — one item each, filed as the tracks land; the
  next is Plane 3 (`architecture.md:163`), its area page named when
  filed.
- The chapter's claims — moved verbatim, not re-measured; a figure
  found stale is a filing, not an edit here.

## Acceptance Test

`python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q`
the same count before and after; every sentence of the 57 lines in the
new page or the kept pointer (a diff of the removed prose against the
new page's body, empty); `test_docs_links_and_commands.py` green;
`dev_close_task.py --check --write` a no-op after the commit; mutation:
one moved sentence deleted from a scratch copy — the diff names it.
