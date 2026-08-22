# UX-224: copy a finding as something you can paste

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-217 (the evidence it carries), UX-115 (the CI comment renderer)

## Motivation

The report ends its life in a pull request, a chat message or a ticket,
and getting it there is manual: select the finding, lose the evidence,
retype the numbers, re-find the element name.

`UX-115` already renders a CI comment from a payload, and `UX-208`
already ships a clipboard helper with a `✓ copied` acknowledgment. A
Copy on each finding is those two things meeting.

```text
BGA finding: build is chain-bound
  critical path 3610s, 94% of wall-clock
  scheduling wait <1%
Top opportunity: core.bst — 12.05s recoverable, 18.6% of path
Suggested action: reduce the work on the chain, not the builder count.
Run: 20260821T170127Z
```

The last line matters as much as the first: a pasted finding without
the run identity is an assertion nobody can check, and `UX-178`
established that the identity must round-trip.

## Required Fix

1. A Copy button per finding, emitting plain text: title, evidence in
   its declared units, the elements named, the published next step from
   `UX-218`, and the run identity.
2. The same text, from the same function, as `--format ci-comment`
   already uses where the shapes overlap — one renderer, so the pasted
   finding and the CI comment cannot word the same conclusion
   differently.
3. Markdown when the platform will take it, plain text otherwise; the
   copy affordance says which.

## Out of Scope

- Posting anywhere. No network from the page.
- A new finding format, or changing `--format ci-comment`'s output.
- Copying the whole report (the export is that).

## Acceptance Test

The copied text for `time-concentration` on `examples/06` contains its
published `path_us` in the same unit the page shows, the element it
names, and the run stamp — asserted against the payload, not against a
golden string. The renderer is shared: asserted by reading the source,
not by the two happening to agree today (`UX-214`'s lesson).

Mutations, each asserted red: drop the run identity → the round-trip
guard fails; give the copy its own wording of the conclusion → the
one-renderer guard fails.
