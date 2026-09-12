# UX-810: the Plane 3 chapter moves into the tools area page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-689 (the rule and the first area), UX-807 (the third, and the one-id-per-chapter rule) | **Found by:** round 113, `UX-807`'s Out of Scope | **Serves:** the reader pricing a change to the persisted-log reader; the session restructuring without losing a sentence | **Topic:** docs | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-807` named the next chapter: Plane 3, BuildStream's own persisted
logs, read by `tools/bst_cache_logs.py` — the `tools` area, whose
hand-written page does not exist yet. The log guard's anchor rule
(`tests/unit/test_the_verification_log_is_true.py`, `closing_commit`
takes the oldest commit naming an id) makes each chapter its own item,
its own entry, landed after the last.

```console
$ grep -n "^## " docs/design/architecture.md | sed -n 5p
163:## Plane 3: BuildStream's own persisted logs (`UX-91`)
$ sed -n 163,208p docs/design/architecture.md | wc -l
46
```

## Required Fix

The chapter at `docs/design/architecture.md:163-208` moves into a new
hand-written `docs/design/areas/tools.md`, the same shape as
`docs/design/areas/bga-replay.md`: a heading, the "Moved from" pointer
paragraph, the prose verbatim, links re-based; the page is the tools
area's, so its heading names the area and the chapter is its first
section — later chapters on the tools join it. `architecture.md` keeps
the heading and a one-paragraph pointer, plus any line a guard reads
(find them: `grep -ln "architecture.md" tests/unit/*.py`, then each
guard's landmarks inside lines 163-208). `docs/README.md`'s design
index names the new page; the generated `docs/backlog/areas/tools.md`
carries the derived `Mechanism:` line after `dev_close_task.py --check
--write`. A new Verification Log entry crediting `UX-810` rides the
same commit (the guard's rule), saying what was re-grounded and against
what.

## Out of Scope

- The other chapters — one item each, filed as the tracks land; the
  next is "Joining the planes" (`architecture.md:209`, `bga/correlate.py`,
  the `bga` area).
- The chapter's claims — moved verbatim, not re-measured; a figure
  found stale is a filing, not an edit here.

## Acceptance Test

`python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q`
the same count before and after; every sentence of the 46 lines in the
new page or the kept pointer (a diff of the removed prose against the
new page's body, empty); `test_docs_links_and_commands.py` green;
`dev_close_task.py --check --write` a no-op after the commit; mutation:
one moved sentence deleted from a scratch copy — the diff names it.
