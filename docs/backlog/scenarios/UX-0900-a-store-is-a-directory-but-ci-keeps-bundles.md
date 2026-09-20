# UX-900: a store is a directory, but CI will keep bundles in versioned directories

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-520 (the bundle), UX-234 (the aggregate) | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 1) — CI will preserve `bga` bundles in directories named by build number | **Serves:** R5 and R7 (an aggregate over what CI actually kept), R8 (the health view that reads the same store) | **Topic:** store | **Area:** bga | **Shape:** judgement

## Motivation

`bga bundle --export` packs a whole capture into one file with a
manifest that refuses a partial load — the right unit for CI to keep,
and the one the rollout will keep. But every command that speaks for
more than one run (`snapshot --list`, `snapshot --aggregate`,
`snapshot --capacity`, `cache-trend`) reads a **store directory** of
run directories. So the artifacts CI will hold are in the one shape the
across-build half of the tool cannot read, and the manager view and the
sizing work both sit behind that mismatch.

Nothing about this is deep — it is a question of where the seam goes
before a nightly job writes a thousand bundles into a layout that then
cannot move.

## Required Fix

**Both**, which the owner asked for on 2026-09-20 and which is the right
answer for different call sites: a command that **materialises** a store
from a directory tree of bundles (idempotent, so a nightly can run it
over a growing tree, and `run_store`'s invariants hold unchanged), and a
reader that takes the **bundles in place** for the one-shot case where a
second copy of every capture is not worth its disk. The two share one
loader and one refusal: a bundle that fails its manifest check is named
and refused rather than skipped in silence.

Which one a caller wants is a disk-versus-repetition trade, so the task
states the measured cost of both on the committed fixture rather than
asserting a default.

## Decomposition

surfaces: `bga/bundle.py`, `bga/run_store.py`, and whichever of `tools/bga_snapshot.py`'s subcommands grows the entry point
guards: a tree of two valid bundles (a store of two runs), one with a bundle whose manifest is short (refused, named), one with a non-bundle file among them (ignored), and idempotence — the same tree twice gives the same store
gap: disk. Materialising doubles what CI keeps; the task states the measured size of both options on the committed fixture before choosing
track: `implementer`
gate: its own

## Out of Scope

Retention and pruning policy for CI's own directories — that is the
pipeline's. Any network fetch of bundles; this reads a local tree.

## Acceptance Test

`bga` reads a directory tree holding two exported bundles as a store:
`--list` shows two runs, `--aggregate` produces the same document it
produces from the equivalent run directories (byte-identical but for
paths), and a truncated bundle is refused by name. Run twice, the
result is identical. Mutations: skip the manifest check (the truncated
bundle must not silently join), drop the idempotence (a second run must
not double the runs).

## Outcome
