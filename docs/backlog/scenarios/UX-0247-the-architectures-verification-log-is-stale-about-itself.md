# UX-247: the architecture's verification log is stale about itself

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the maintainers, and the next review | **Topic:** docs

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
