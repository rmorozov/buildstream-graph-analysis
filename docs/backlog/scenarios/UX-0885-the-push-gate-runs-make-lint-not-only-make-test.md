# UX-885: the push gate runs `make lint`, not only `make test`

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** round 125 (PR #235's test matrix went red on a `make lint` PyMarkdown finding the local push gate had passed — the gate covers `make test`, which writes `.gate-covered`, but not `make lint`, so a lint-clean-locally-but-not-in-CI blob still pushed) | **Serves:** the pipeline (a push that CI will fail on lint is caught before the push, not after) | **Topic:** guards | **Area:** tools-dev | **Shape:** judgement

## Motivation

The push hook blocks a sha whose `make test` gate did not run
(`.gate-covered`), but `make lint` (ruff + PyMarkdown) is **not** part of
the gate. Round 125 pushed a round-doc blob that a local `make lint` had
(anomalously) passed at exit 0, and CI's pinned `pymarkdown 0.9.40`
reddened it (MD032 on a wrapped `+ ` line) — the test matrix runs
`make check-clean` → `make lint` → pytest, so the lint failure *skipped
pytest entirely* across the whole 3.9–3.12 matrix. A cheap local lint in
the gate would have caught it before the push and the CI round-trip.

## Required Fix

Fold `make lint` into the push gate beside `make test` (or a
`make gate` target that runs both and writes `.gate-covered` only when
both are clean). Must use the **same pinned** `pymarkdown`/`ruff`
versions CI uses, or the local pass/CI fail gap reopens. Weigh the added
gate wall-clock (lint is seconds, not the multi-minute suite) against the
CI round-trips it saves.

Surfaces: the push hook / gate script under `tools/` or `.git/hooks`
wiring, the `Makefile` (a `gate` target if introduced),
`docs/contributing/fixing-guide.md` (the gate's definition).

## Decomposition

surfaces: gate/push-hook script · `Makefile` · `docs/contributing/fixing-guide.md`
guards: `test_the_push_gate_includes_lint.py` (new): a blob that fails `make lint` does not produce a covered sha / is blocked by the gate
gap: version pinning drift between local and CI is the root cause behind the round-125 incident and must be asserted, not assumed
track: bounded `implementer`
gate: a later round (filed this round, not built)

## Out of Scope

Fixing any specific lint finding. Changing CI's own order.

## Acceptance Test

A staged change with a known PyMarkdown/ruff violation: the gate refuses
to mark it covered (or the push hook blocks it). Mutation: gate on
`make test` only — the lint-violation blob passes the gate, reddening the
guard.

## Outcome

**The gap.** The push gate reads `.gate-covered`, which only `make test`
wrote (on a green suite). `make lint` was not in that path, so round 125
pushed a round-doc blob a local `make lint` passed and CI's pinned
PyMarkdown reddened (MD032) — and because CI runs `check-clean → lint →
pytest`, the lint failure skipped pytest across the whole 3.9–3.12 matrix.

**The close.** `lint` is now a prerequisite of `test` (`Makefile`:
`test: lint`). `make` builds the prerequisite first, so the recipe runs
`lint-docs` (PyMarkdown) → `ruff check` → `dev_baseline.py --check` →
pytest → the `.gate-covered` write, and aborts on any failure — a
lint-red tree never reaches the write. The lint recipe is unchanged, so
it uses the same tools CI does; the pins live in `requirements.lock` /
`.pymarkdown.json`, and UX-887's `dev_env_check.py` catches a local PATH
that shadows the pinned `ruff`. `docs/contributing/fixing-guide.md` rule
14 now records the lint prerequisite.

**Guard.** `test_the_push_gate_includes_lint.py` (4 tests) reads the
gate's own recipe through `make -n test` (dry-run, no suite): `ruff`,
`pymarkdown` and `dev_baseline.py` each appear, and before `pytest`,
which is before the `.gate-covered` write. Mutation: drop the `lint`
prerequisite → `make -n test` shows only pytest + the write → all 4
redden; reverted, 4 green.

**Deviation.** CI's own `lint` step is untouched (Out of Scope). The
matrix legs now re-run lint via `make test` — a redundant few seconds
per leg — accepted: CI order is Out of Scope, and the redundancy never
changes an outcome (a lint failure already fails CI at its own lint step
before any leg's `make test` runs).
