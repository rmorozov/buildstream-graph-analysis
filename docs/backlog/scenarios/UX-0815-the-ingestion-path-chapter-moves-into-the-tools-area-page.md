# UX-815: the ingestion-path chapter moves into the tools area page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-689 (the rule), UX-810 (the tools page it joins) | **Found by:** round 114, `UX-810`'s Out of Scope | **Serves:** the reader pricing a change to the capture path; the session finishing `UX-689` | **Topic:** docs | **Area:** tools | **Shape:** mechanical

## Motivation

The largest chapter left in `docs/design/architecture.md` is the
capture path's own — how the tracer, the shim and the spine measure
themselves (`UX-105`–`UX-110`) — 217 lines of `tools/` mechanism. The
tools area's page (`UX-810`) holds one section; this is its second.
The log guard's anchor rule makes it its own item.

```console
$ grep -n "^## " docs/design/architecture.md | sed -n 7p
187:## The ingestion path now measures itself (`UX-105`–`UX-110`)
$ sed -n 187,403p docs/design/architecture.md | wc -l
217
```

## Required Fix

The chapter at `docs/design/architecture.md:187-403` moves into
`docs/design/areas/tools.md` as its second `##` section, after the
Plane 3 one, prose verbatim, links re-based; `architecture.md` keeps
the heading and a one-paragraph pointer, plus any line a guard reads
from inside the chapter (find them: `grep -ln "architecture.md"
tests/unit/*.py`, then each guard's landmarks inside lines 187-403 —
blank the chapter and re-run the files, as `UX-810` did). A new
Verification Log entry crediting `UX-815` rides the same commit.

## Out of Scope

- The chapters left after this one — `UX-816` takes the `bga` area's
  five (joining the planes, the two round-history chapters, the core
  invariants, the real extensions) into `docs/design/areas/bga.md`,
  landed after this one.
- The chapter's claims — moved verbatim, not re-measured.

## Acceptance Test

`python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q`
the same count before and after; every sentence of the 217 lines in
the new section or the kept pointer (a diff of the removed prose
against the section's body, empty); `test_docs_links_and_commands.py`
green; mutation: one moved sentence deleted from a scratch copy — the
diff names it.
