# UX-537: forty-eight hand-built documents, and the shared shim they were to become

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-264` (the shared shim), `UX-219` and `UX-254` (two defects this shape has already produced), `UX-523` (found it again) | **Serves:** the next round that adds a standard DOM call to the viewer | **Topic:** guards

## Motivation

`UX-264` replaced twenty-five hand-built `document` objects with one
shared shim. There are forty-eight now:

```text
$ grep -rln "globalThis.document = {" tests/unit/*.py | wc -l
48
$ for f in $(grep -rln "globalThis.document = {" tests/unit/*.py); do
    grep -q documentElement "$f" || echo "$f"; done | wc -l
48
```

None models `documentElement`, though `tests/dom_shim.mjs` - the shared
one - has had it since `UX-264`. So a viewer that reads a standard DOM
property the shims do not carry fails in **ten guards at once**, in
`boot()`'s catch-all, with a message about the harness rather than the
page. That is the third time this exact shape has cost a round:

| | what the model was missing | how it surfaced |
|---|---|---|
| `UX-219` | `createTextNode` | the exported page threw inside `boot()` and rendered the banner |
| `UX-254` | `querySelector` | twelve order guards reported "Could not load this run" |
| `UX-523` | `documentElement` | ten setup errors; the page now guards the write |

Each was fixed by *widening the model rather than avoiding the method*,
and each fix landed in one file. The other forty-seven kept the trap.

## Required Fix

- Count what the forty-eight shims actually differ in, measured rather
  than assumed: which of them need their own `getElementById` policy
  (the reason `installDocument` takes overrides), and which are copies.
- Move the copies onto `installDocument`, one commit, no behaviour
  change - the diff is deletions plus an import.
- A guard that a new hand-built `globalThis.document = {` in
  `tests/unit/` fails, naming `installDocument` and the three defects
  above. That is the part that makes this the last time.
- Then drop `boot()`'s `documentElement?.dataset` guard, whose one line
  of why points here.

## Out of Scope

- The shim's fidelity as a DOM. It is a model on purpose; this is about
  there being **one** of it.
- The browser-tier guards, declined: they drive a real Chromium and
  have no shim to consolidate.

## Acceptance Test

`grep -c "globalThis.document = {" tests/unit/*.py` before and after,
both pasted, and the whole suite green. Mutation: add a fresh
hand-built document to one guard file - the new guard must redden and
name `installDocument`.

## Outcome

_Not started._
