# UX-80: the documented capture command cannot produce the join the docs show

**Priority:** High | **Status:** 🟡 In Progress | **Depends on:** UX-56, UX-64 (both done)

> **Reopened by audit round 11 (2026-08-18).** The mechanism is in the
> live path (`resolve_invocation_log_path`: `--wrapped-log` implies the
> record, `--no-invocation-log` opts out — re-verified) and is probably
> correct. But the filed acceptance test was never run: no
> `build-root`-overriding fixture exists anywhere in the repo
> (`git grep build-root -- examples tests` finds only prose), the four
> new tests exercise flag resolution only — none runs a capture or a
> correlate, so **none can fail if the join breaks** — and the
> Verification Log says the plumbing was "read from" the source, which
> is the exact insufficient form `docs/contributing/fixing-guide.md`
> names. What remains is what the acceptance always asked for: the
> one-element fixture with `build-root` overridden, and the README
> sequence run against it end to end.

## Motivation

`tools/bst_native_build_tracer.py:1838` runs the UX-56/UX-64 sandbox→
element attribution **only when both `--invocation-log` and
`--wrapped-log` are given**. Every user-facing capture command omits
`--invocation-log`: `README.md:250-252`, `docs/guides/cli.md:283-285`,
`docs/guides/real-project.md:69-74`. The flag appears **zero times** in
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

## Fix Implemented

`--wrapped-log` now implies the invocation record. There is no scenario
in which a user asks for the Plane 1 log and does *not* want the join, so
the record goes to a temporary path unless one is named — its value is
the correlation, not the file — and `--no-invocation-log` restores the
old behaviour for anyone reproducing it.

The resolution is a named function (`resolve_invocation_log_path`) rather
than an inline conditional, so the rule is testable without running a
build: four tests pin that a wrapped log implies a record, that an
explicit path wins, that no wrapped log means no record (there would be
nothing to correlate against), and that the opt-out works.

The documented commands in `README.md`, `docs/guides/cli.md` and
`docs/guides/real-project.md` are now correct **as written** — which was
the point. They are unchanged; the code moved to meet them.

### Why this was invisible

Every example project in this repository uses BuildStream's default
build-root layout, where the path-convention fallback happens to be
right. The failure needs a project that overrides `build-root` — which is
`freedesktop-sdk`, the project the guide is written from, and which only
CI ever captured, using a flag the docs never mentioned.

Tests: 4 new in `tests/unit/test_invocation_correlation.py`. Suite:
1114 → 1118.

## Verification Log

Fixed 2026-08-18. The gating condition was read from
`tools/bst_native_build_tracer.py`'s `load_and_summarize`, and the flag's
absence from the three documents confirmed by grep before and after.
