# UX-245: the architecture's CLI table is two commands behind

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** R8 and anyone pricing a change against the document that describes the system | **Topic:** docs

## Motivation

Found by review 1 (`UX-241`,
[`docs/audits/architecture-review.md`](../../audits/architecture-review.md)),
which is the point: `UX-233` fixed the document's *contract inventory*
and guarded it, and the chapter a reader actually starts from went on
drifting because nothing measured it.

Checked against `cli.create_parser()`:

```text
subcommands in `bga --help`, absent from "## Real current CLI surface":
  blast    shipped round 19 (UX-172)
  whatif   shipped round 28 (UX-230)
```

`--explain` (`UX-229`) appears nowhere in `architecture.md` either,
although the provenance mechanism it prints is described in the
contracts chapter. So the document describes the machinery and not the
way anyone reaches it.

`blast` is the sharper half: it has been shipped for ten rounds, it is
on the front door and in `cli.md`, and the chapter titled *"Real
current CLI surface"* does not have it.

## Required Fix

1. The CLI-surface table gains `bga blast` and `bga whatif`, in the
   register the other rows use — what it reports, and the `UX-` id that
   introduced it.
2. `--explain` is named where the provenance chain is described, since
   a mechanism with no visible entry point reads as internal.
3. A guard, of the same shape as `test_the_front_door_is_current.py`:
   every subcommand `bga --help` lists appears in that table, and the
   table names none that does not exist.

## Out of Scope

- The "Real package structure (Plane 1)" chapter's 16 unlisted
  top-level modules. That chapter is explicitly about Plane 1's
  pipeline packages, and the whole-tree map is the fixing guide's §6
  (`UX-239`), which is guarded.
- Rewriting the chapter. The fix is two table rows and one
  sentence, and a review that turns into a rewrite stops being a
  review (`UX-241`).

## Acceptance Test

The guard reddens against the table as it stands (both `blast` and
`whatif` reported), and is green after; deleting a row reddens it;
adding a row for a command that does not exist reddens it.

## Outcome — 🟢 Fixed & Verified

The table gained the two rows, `--explain` gained the sentence that
says how the provenance chain is reached, and the drift is now
measured rather than reviewed.

**Before**, `bga --help` against the chapter titled *"Real current CLI
surface"*:

```text
$ python -m pytest tests/unit/test_the_architecture_names_the_commands.py -q
FAILED ...::test_every_subcommand_is_in_the_table
E   AssertionError: subcommand(s) `bga --help` lists and the architecture's
E   CLI-surface table does not: ['blast', 'whatif'].
```

**After**: 5 passed. `bga blast TARGET [RUN]` and
`bga whatif [RUN] --element UID …` are rows in the register the other
sixteen use — what it reports, and the `UX-` id that introduced it —
and each carries the one clause that makes its answer safe to quote:
blast's answer *says which reading of `TARGET` it used*, and whatif's
is *one longest-path recompute, never a sum* (`UX-244`'s convention,
one sentence of it, at the point a reader meets the command).

`--explain` is stated where the provenance chain is described, not in
a list of flags:

```text
**`bga analyze --explain`** is how the provenance chain below is
reached from the command line: under each claim it prints the evidence
fields it was drawn from, the rule that fired, and the trace query that
deepens it (`UX-229`). The mechanism is published in `analyze/v1`
either way; the flag is what makes it visible to a reader who has a
terminal and not a payload.
```

**The guard** — `tests/unit/test_the_architecture_names_the_commands.py`,
5 tests — reads the table's **first column only**. Not the chapter, and
not the whole row: every row's second cell is prose about what the
command reports, and prose about `bga blast` contains the words
`bga blast`, so a guard reading it would be satisfied by a command
being *discussed* rather than listed. That is the same self-matching
failure this repository has now recorded twelve times, avoided by
construction rather than by noticing.

Falsified, five mutations, each on the test it should hit:

```text
M1  delete the `bga blast` row      -> test_every_subcommand_is_in_the_table
M2  delete the `bga whatif` row     -> test_every_subcommand_is_in_the_table
M3  add a row for `bga frobnicate`  -> test_the_table_names_nothing_that_does_not_exist
M4  remove the --explain sentence   -> test_explain_is_named
                                     + test_the_flag_is_named_beside_the_provenance_it_prints
M5  name --explain 600+ chars from  -> test_the_flag_is_named_beside_the_provenance_it_prints
    any provenance prose               (test_explain_is_named still green — the pair
                                        discriminates on placement, not presence)
```

M3 is the direction the item's Out of Scope did not ask for and the
review did: a row for a retired command is worse than a missing row,
because it is an instruction to type something that fails — the shape
`UX-122` measured on ref globs.

**Deviation from the Required Fix:** clause 3 asked for a guard "of the
same shape as `test_the_front_door_is_current.py`". It is the same
shape and not the same file: the front-door guard's `_mentions()` is
deliberately loose (a command counts as named if it appears as
`` `bga x` `` *anywhere* in a README, which is right for a document
that is prose), and reusing it here would have accepted the drift this
item is about. The two checks now differ in exactly that one way, and
the docstring says so.
