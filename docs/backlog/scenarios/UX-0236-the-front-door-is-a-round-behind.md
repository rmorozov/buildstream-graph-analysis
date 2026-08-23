# UX-236: the front door is a round behind

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-233 (the architecture half, done) | **Serves:** R1 and R8 first — the two who arrive without context | **Topic:** docs

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

## Outcome

**Status:** 🟢 Fixed & Verified

`tests/unit/test_the_front_door_is_current.py` run against the front
door as it stood, before a word was changed:

```text
subcommand(s) named in no front-door document:
  ['cache-trend', 'diagnostics', 'graph', 'replay', 'sweep', 'utilisation', 'whatif']
published schema(s) docs/README.md does not name:
  ['analyze/v1', 'blast/v1', 'compare/v1', 'correlate/v1', 'host/v1',
   'store-aggregate/v1', 'store/v1', 'whatif/v1']
docs/README.md lists the schema ids without saying how to print one
```

Seven of twelve subcommands and eight of eight schemas. That is the
gap, measured rather than argued, and it is what the guard now holds
shut.

### What changed at the door

`docs/README.md` gained a **What it emits** section — the eight ids,
what writes each, and `bga --schema <id>` as the way to read one — plus
a paragraph naming `bga whatif`, `bga analyze --explain` and
`bga snapshot --aggregate`, and saying what the six section-only
commands (`graph`, `floors`, `replay`, `sweep`, `utilisation`,
`diagnostics`) and `cache-trend` are, since a reader meeting them in
`--help` had nowhere to look.

`README.md` gained the three round-28 capabilities where a reader is
already asking for them: `bga whatif` beside the "and then what?"
question it answers, `--explain` beside the report whose claims it
justifies, and `--aggregate`/`--blend` inside the "one capture is not a
baseline" callout, which is exactly the argument the store aggregate
makes with runs you already have.

**The budget was the constraint, not the length.** The README is capped
at 250 measured lines (`UX-135`) and the additions took it to 252, so
two came back: the install paragraph and the `bga doctor` paragraph
were reflowed, and the seventh pointer to `real-project.md` — of eight
in one file — was deleted. It ends at 249.

### The exemption is not a hiding place

Ten `tools/` aliases stay off the front door (`capture`,
`checkout-cost`, three trace converters, `graph-from-show`,
`rebuild-set`, `run-context`, `timeline`, `cross-check`), each with its
reason in `NOT_ON_THE_FRONT_DOOR`. That list would be a loophole on its
own, so it costs something: every exempt alias must still be reachable
from `docs/guides/cli.md`, and an exemption naming an alias that no
longer exists fails on its own. "Deliberately absent" must not decay
into "undocumented", which is the failure this item is about.

### Two figures that were going to drift again

The Development block said "1,985 tests in 22s" and "3,112 tests"; the
fixing guide's tier table said 160 and 213 files. All four had moved
within one round of being written. The counts that change on every
commit are gone from the README — `make test` now says `5m11s,
measured`, which is the number a reader is deciding on — and the tier
table's file counts are refreshed to 164/217 from `tests/tiers.py`.

**Mutations verified red and reverted (4, plus 3 reddenings on the real
pre-change documents):** an exempt alias deleted from `cli.md`; an
exemption for an alias that does not exist; an alias with neither a
door mention nor an exemption; the index naming a schema nothing
publishes.

**Deviation from the Required Fix:** none. Clause 3 asked for the drift
guard to extend to the front door; it is a separate file rather than an
addition to `test_the_documents_keep_up_with_the_contracts.py`, because
the two ask different questions — that one asks whether a contract is
*specified*, this one whether it is *findable*.

Small tier: `2005 passed, 1130 deselected in 21.30s`.
Full suite: `3132 passed, 3 skipped in 310.51s`. `make lint`: clean.
