# Architecture and documentation review

A round type, and its log. Feature audits happen here on a cadence —
twenty-eight rounds of them — and documentation review did not, which
is why one drifted a whole axis and the other did not (`UX-241`).

## What a review is

| | |
|---|---|
| **input** | everything that landed since the last row in the log below |
| **output** | filings, in `docs/backlog/scenarios/` — and this document's next row |
| **produces no code** | a review that fixes what it finds is a fix session wearing a review's name, and stops being able to see the next thing |
| **done when** | every item on the checklist has been answered with a measurement or a filing |

The stream table in
[`../contributing/fixing-guide.md`](../contributing/fixing-guide.md)
§6a carries it beside the other six.

## The checklist

Per architecture chapter, per guide:

1. **Does the code still do what it says?** Not "is it plausible" —
   open the module the chapter names and check the mechanism.
2. **Does every published contract have a home?**
   `test_the_documents_keep_up_with_the_contracts.py` guards the
   mechanical half (`UX-233`); the review asks whether the *prose*
   around each one is still true.
3. **Is any figure invalidated?** `git grep` the number. A figure a
   later round moved and an earlier document still quotes is the defect
   `UX-132` named.
4. **What shipped since the last review that no document names?** The
   inventories are `bga --help`, `schemas.names()`, and the closed rows
   added since the last log entry.
5. **Does each document's own "last updated" claim match reality?**
   `git log -1 --date=short -- <file>` against what the file says.

The spec's Part text is out of scope: it is ground truth, and a review
that finds it wrong files against it rather than editing it.

## The cadence, and why it is measured in closed rows

The trigger is a number, not a memory:
`tests/unit/test_the_review_has_a_cadence.py` reddens when more than
**25 scenarios** have closed since the last row below.

Closed rows rather than commits, because a commit is not a unit of
change here — one round is anywhere from one to nine of them — and
because the count is in the tree, so the guard needs no git and gives
the same answer on every machine. 25 is chosen against the drift that
was actually missed: the viewer axis ran from `UX-193` to `UX-226`, 34
closed rows, with nothing in the process to notice. A bound below that
would have caught it; a bound at it would only just have.

## The log

| review | date | closed rows at review | commit | findings |
|---|---|---|---|---|
| 1 | 2026-08-23 | 237 | `2818a06` | `UX-245`, `UX-246`, `UX-247` |

### Review 1 — 2026-08-23

The first one, run against `docs/design/architecture.md` and the three
live guides. Three findings, each measured:

**The architecture's CLI table is two subcommands behind.** Checked
against `cli.create_parser()`:

```text
subcommands in `bga --help`, absent from "## Real current CLI surface":
  blast    (shipped round 19, UX-172)
  whatif   (shipped round 28, UX-230)
```

`--explain` (`UX-229`) appears nowhere in the document either, although
the provenance mechanism it prints is described. Filed as `UX-245`.

**The end-to-end guide never reaches the command for its own last
step.** `docs/guides/real-project.md` walks capture → read → go inside
→ join → act → gate, and `bga whatif` — which prices the act step — is
named nowhere in it. Filed as `UX-246`.

**The architecture's own Verification Log is stale about itself.** It
says *"Updated 2026-08-18 (after `UX-76`)"*; `git log` says the file
was last written on 2026-08-23, with five commits touching it since
that line was written. A log that does not move when the document does
is worse than no log, because it is read as a claim. Filed as `UX-247`.

**What was checked and found current:** every published schema id
appears in spec Part 32.5 and the architecture inventory (guarded since
`UX-233`); the three planes' chapters match the modules they name; the
33% five-capture noise figure and the band derived from it are the ones
the round-9 audit measured; `docs/guides/cli.md` names every subcommand
and every `tools/` alias. `optimization-walkthrough.md` names almost no
command, which is correct — it is a tombstone pointing at
`real-project.md` (`UX-139`), not a guide.
