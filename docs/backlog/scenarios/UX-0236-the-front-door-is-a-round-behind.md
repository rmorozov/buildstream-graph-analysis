# UX-236: the front door is a round behind

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-233 (the architecture half, done) | **Serves:** R1 and R8 first — the two who arrive without context | **Topic:** docs

## Motivation

`UX-233` fixed the architecture document and the spec's contract table.
The *front door* — `README.md` and `docs/README.md` — was not in its
scope and is now the stale half: three commands and a flag shipped in
round 28 and neither document mentions any of them.

Measured against `bga --help` and `schemas.names()`:

```text
in the tool, in no front-door document:
  bga whatif              (UX-230)
  bga snapshot --aggregate / --blend   (UX-234)
  bga analyze --explain   (UX-229)
  store-aggregate/v1, whatif/v1        (two of eight published schemas)
```

The README is 250 lines and reads well; the problem is not length, it
is that a reader who arrives today is told about a tool one round old.
The same drift the user named about architecture, at the door.

## Required Fix

1. `README.md` and `docs/README.md` state what the tool does *now*:
   the provenance chain, the store aggregate, and what-if selection,
   each in the register those documents already use — one line where a
   line does, not a section each.
2. A pass for consistency and concision across both, and for the
   guides that quote them: no figure that a later round invalidated, no
   command that does not exist, no promise the tool no longer makes.
3. The drift guard extends to the front door: `UX-233` asserts every
   published schema is named in the spec and the architecture
   inventory; the same set should be reachable from the docs index,
   which is where a reader looking for "what can this thing emit"
   actually starts.

## Out of Scope

- Restructuring either document. The README's shape — four questions,
  three planes, then the paths — survived four audit rounds of reader
  feedback, and the fix is currency, not a rewrite.
- The guides' own narratives (`real-project.md`, `cli.md`): they are
  long by design and already carry the new commands.

## Acceptance Test

Every subcommand `bga --help` lists is either named in a front-door
document or is deliberately absent with the reason recorded (guard);
every published schema id is reachable from `docs/README.md` (guard);
the existing link, command and table guards stay green; the README's
measured line budget is not exceeded.
