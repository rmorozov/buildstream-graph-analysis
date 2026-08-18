# UX-80: the documented capture command cannot produce the join the docs show

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-56, UX-64 (both done)

## Motivation

`tools/bst_native_build_tracer.py:1838` runs the UX-56/UX-64 sandbox→
element attribution **only when both `--invocation-log` and
`--wrapped-log` are given**. Every user-facing capture command omits
`--invocation-log`: `README.md:250-252`, `docs/cli.md:283-285`,
`docs/real-project-guide.md:69-74`. The flag appears **zero times** in
all three documents. The CI workflow that produced every number those
documents quote *does* pass it
(`.github/workflows/real-project-capture.yml:300`).

Consequence: a user following the guide on a project that overrides
`build-root` — which includes `freedesktop-sdk`, the exact project the
guide is written from — gets the UX-56 collapse the docs present as
solved: 99.4% of processes attributed to one `buildstream-build` bucket,
and a `bga correlate` join with nothing to join. The gap between "works
in our CI" and "works from our README" is precisely the flag the README
does not mention.

(Found while auditing why this round's local captures joined cleanly:
`examples/06` uses the default build-root layout, so the fallback
tagging works there and the omission is invisible on every example
project in this repository — the same fixture-shape trap as UX-52.)

## Required Fix

`bga capture run` should record the invocation log **by default**
whenever `--wrapped-log` is given (the two artifacts come from the same
wrapped invocation; there is no scenario where a user wants the join and
not the log). An explicit opt-out can exist if there is a real cost to
record. Docs updated so the copy-paste path produces a joinable capture
on a non-default build-root project.

## Out of Scope

- The attribution mechanism itself (UX-56/UX-64, shipped and verified).
- Raising attribution coverage past 86.1% (separate, known ceiling).

## Acceptance Test

On a project with `build-root` overridden in `project.conf` (add a
one-element fixture variant), run **exactly** the README's capture +
correlate command sequence, unmodified. `bga correlate` must join the
traced element by UID rather than reporting an unresolved-bucket
collapse. Grep the three docs for the final shipped command and confirm
what they show is what was run.
