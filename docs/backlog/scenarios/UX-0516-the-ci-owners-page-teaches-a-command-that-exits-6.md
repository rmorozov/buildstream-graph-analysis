# UX-516: the CI owner's page teaches a command that exits 6 on this repository's own refs

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-96` (which added the remedy) | **Found by:** review 11 | **Serves:** the CI owner who copies the block, meets exit 6, and has no next line to type | **Topic:** docs

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

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

The page's step 2, verbatim, against the live refs:

```text
$ bga baseline --glob 'captures/fdsdk/953683fb-incremental-b4j4-*' -n 3
  captures/fdsdk/953683fb-incremental-b4j4-33302016575
  captures/fdsdk/953683fb-incremental-b4j4-32615919649
  captures/fdsdk/953683fb-incremental-b4j4-32223468993
  NOT COMPARABLE: trace_spine differs across the set (false, true)
Refusing to compare against a set that is not internally comparable.
trace_spine is not in the ref name, so no --glob separates this set.
Drop the odd capture(s) with --exclude <run-id or ref glob>. Here that
is 32223468993.
EXIT=6
```

The refusal already names `--exclude`; the page did not, anywhere.

A second gap, found while covering it: the guard that reads this page's
commands **could not see step 2 at all**. `documented_invocations()`
read one physical line, `shlex.split` refuses a trailing `\`, and the
invocation was dropped — 203 invocations found where 220 exist, 17 of
them wrapped. Every flag below a wrap in every guide was unchecked.

### After

Step 2a carries `--exclude`; the same block, run whole, with a real
candidate run directory:

```text
$ bga baseline --glob 'captures/fdsdk/953683fb-incremental-b4j4-*' -n 3 \
      --exclude 32223468993 --candidate .../02-32223468993/run
--exclude dropped 1 capture(s) before the newest 3 were taken.
3 capture(s), newest first: 33302016575, 32615919649, 32177690506
Verdict: NO SIGNIFICANT CHANGE  (total duration -262.30s, -7.4%,
  3523.51s -> 3261.22s)
  Judged against a noise band from 3 baseline run(s): 3009.02s .. 4038.00s
EXIT=0
```

The scan now joins continuations: **221** invocations, 19 with a
continued first line, 0 offending flags.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M1 | `while False and command…endswith("\\")` — the join disabled | `test_a_wrapped_invocation_is_read_past_its_backslash`, `0 >= 8`; 1 failed, 7 deselected |
| M2 | the join drops the continuation's first token | same guard, `'$PROJ' … not in [...]` at `ci-comment.md:18`; 1 failed, 7 deselected |
| M3 | the page's `--exclude` renamed `--excludes` | `test_no_documented_flag_is_one_the_command_does_not_have`, ``ci-comment.md:26: `bga baseline --excludes` - no such flag``; 1 failed, 7 deselected |

No guard of this item's failed to discriminate. M1 and M2 redden
different clauses of the same guard on purpose: M1 the count, M2 the
per-invocation token check.

### Deviation from the Required Fix

The Required Fix offered step 2 **or** the sentence at :39; both landed,
because the block alone does not say when `--exclude` is needed and the
sentence alone is not runnable. Fixing the scan's backslash blindness
was not named in the item — without it the new flag is in the page and
in no guard, which the second bullet requires.

```text
$ make lint
All checks passed!
$ make test-touching
5 test file(s) name the 2 changed file(s); running them.
99 passed in 20.54s
```

Full `make test` is the orchestrator's; this track ran the touching set.
