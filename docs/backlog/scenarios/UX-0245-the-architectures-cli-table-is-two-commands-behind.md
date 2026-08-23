# UX-245: the architecture's CLI table is two commands behind

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R8 and anyone pricing a change against the document that describes the system | **Topic:** docs

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
