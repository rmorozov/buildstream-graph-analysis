# UX-516: the CI owner's page teaches a command that exits 6 on this repository's own refs

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-96` (which added the remedy) | **Found by:** review 11 | **Serves:** the CI owner who copies the block, meets exit 6, and has no next line to type | **Topic:** docs

## Motivation

`docs/guides/ci-comment.md` is the CI owner's page (`UX-139`), and its
step 2 is:

```bash
bga baseline --glob "captures/$PROJ/<commit>-incremental-b4j4-*" -n 3 \
    --candidate runs/candidate
```

Run against this repository's own published refs, that exits **6**:

```text
NOT COMPARABLE: trace_spine differs across the set (false, true)
```

The page describes the refusal — line 39, "refuses when they are not
comparable (exit 6)" — and stops there. `UX-96` (round 76) added the
remedy the refusal now names, because the ref name carries four of the
seven homogeneous fields and no `--glob` separates a set differing on
`target`, `trace_spine` or `trace_opens`. The option is documented in
`docs/design/capture-workflow.md`, which is explicitly *not* the CI
owner's page — that document says so in its own header.

So the reader with the problem is on the page without the answer, and
the reader on the page with the answer is the one who did not need it.

## Required Fix

- `ci-comment.md`'s step 2 carries `--exclude`, or the sentence at :39
  names it, so exit 6 has a next line to type.
- Whichever it becomes, the guard that reads this page's commands
  (`test_the_documented_invocations_parse.py`) covers the new flag.

## Out of Scope

- `docs/design/capture-workflow.md`, which already has it (`UX-96`).
- The homogeneity rule itself. `UX-108` set it and `UX-114` split
  absence per field; this is about the page, not the check.

## Acceptance Test

The block in `ci-comment.md` run against
`captures/fdsdk/953683fb-incremental-b4j4-*` on the live refs, exiting 0
with the output pasted — which today needs one `--exclude`.

## Outcome

_Not started._
