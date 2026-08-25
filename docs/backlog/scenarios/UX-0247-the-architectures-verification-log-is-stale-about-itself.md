# UX-247: the architecture's verification log is stale about itself

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Serves:** the maintainers, and the next review | **Topic:** docs

## Motivation

Found by review 1 (`UX-241`), and it is the smallest finding with the
worst shape: a document's claim *about its own currency* that is false.

```text
docs/design/architecture.md, "## Verification Log":
  "Updated 2026-08-18 (after `UX-76`) ..."

git log -1 --date=short -- docs/design/architecture.md:
  7bb63cf 2026-08-23 UX-233: the architecture document meets the viewer axis
```

Five commits have touched the file since that line was written. A
reader who checks the log to decide whether to trust the document gets
a date five days and one whole axis out of date, and the log is the one
place that is *supposed* to answer that question — so it is worse than
no log, in the same way `UX-239`'s context map was worse than no map.

## Required Fix

1. The Verification Log states what is true: when the document was last
   re-grounded, against what, and by which item.
2. The mechanical half is guarded — the date the log claims is not
   older than the file's last commit that changed prose. Review 1
   found this by hand and the next one should not have to.

## Out of Scope

- Every other document's "last updated" line. Only `architecture.md`
  makes this claim; if the guard finds it cheap to generalise, that is
  a bonus rather than the task.
- Auto-stamping the date in a hook. A log entry that says *what* was
  re-grounded is the useful half, and a hook cannot write that.

## Acceptance Test

The guard reddens against the log as it stands (2026-08-18 against a
2026-08-23 commit) and is green after the correction; moving the date
back reddens it again.

## Outcome

🟢 **Done.** The log says what is true, and the mechanical half is held.

```text
before:  log claims 2026-08-18 (after UX-76)
         git log -1 -- docs/design/architecture.md: 2026-08-25
after:   log claims 2026-08-25 (after UX-286)
         git log -1 -- docs/design/architecture.md: 2026-08-25
```

**Item 1: re-grounded, not re-dated.** The document was actually read
against what this round changed, and it was one axis out: the viewer
section described the schema-driven page, the width rule and the presets
and said nothing about the chapters `UX-286` groups the document into.
That bullet is there now, with the measurement that decided the shape
(18.51 screens → 18.10, and the 31.3 screens of whitespace Direction 13
refused). The log's new entry names what it was re-grounded in —
`bga/viewer/`'s module list, the schema `bga analyze --schema` prints,
and `closed.md`'s round-38 and round-39 rows — and the older entries are
kept below it, because a log that overwrites its own history is a field.

**Item 2, the guard.** `test_the_verification_log_is_true.py` reads the
date the log claims and compares it with `git log -1 -- <the document>`.
Equal is the normal case: the commit that re-grounds the document is the
commit that moves the line. It also holds the half a hook cannot write —
that the entry says *what it was grounded in*, naming a file or a
command a reviewer can open — and that earlier entries survive.

Where a shallow clone has no commit touching the file, the guard skips
with a reason declared in the census (`tests/conftest.py`), so "we could
not check" cannot read as "checked and found nothing".

**Falsification.** The acceptance test names the reproduction, and it
runs two ways:

```text
R1  the date rolls back to 2026-08-18, as filed     the guard reddens
R2  the same comparison over the filed dates        asserted directly,
    (2026-08-18 against 2026-08-23)                 through the guard's
                                                    own function
```

R2 calls the guard's own `stale()` rather than restating the
comparison — a reproduction that re-implements what it is checking
passes while the guard uses something else.

**One thing this cost, recorded because it is the second time.** R1 was
applied to an *uncommitted* file, and `git checkout` of the mutation
took the item's real edits with it. They were rewritten from the script
that made them. Mutation testing runs against a committed tree; that
rule was adopted in `UX-293` and this is what it costs when it is not
followed.
