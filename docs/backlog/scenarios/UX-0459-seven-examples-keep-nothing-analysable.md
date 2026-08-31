# UX-459: seven of nine examples keep nothing a reader or a guard can analyse

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 72, building the findings-to-captures census | **Serves:** the reader who opens `examples/` to see what a real finding looks like, and the guard that cannot check a finding no fixture produces | **Topic:** guards

## Motivation

`examples/` holds nine projects, each built to plant a distinct
pathology — contention, a deep mixed-kind chain, a git-sourced identity,
a critical path with two independent opportunities, a real C++
toolchain, the macro/micro pair, declared-vs-used, a process storm,
fine-grained siblings. Two of them keep a capture:

```console
$ for d in examples/0*/; do
    [ -d "$d/.bga/runs" ] && echo "HAS  ${d%/}" || echo "none ${d%/}"; done
none examples/01-resource-contention
none examples/02-deep-chain-mixed-kinds
none examples/03-project-refs-identity
none examples/04-critical-path-optimization
none examples/05-cmake-cpp-toolchain
HAS  examples/06-macro-micro-optimization
none examples/07-declared-vs-used-dependencies
HAS  examples/08-process-storm
none examples/09-fine-grained-siblings
```

`bst-examples` builds 01-06 on every CI run and throws the result away.
So the pathology each project was written to demonstrate is
demonstrated **nowhere a reader or a test can look** — the projects are
build inputs, not evidence.

What that costs, measured by running `analyze` over every committed
capture and collecting the finding ids:

```text
21 findings in FINDING_READERS | 7 produced by no committed capture

  cache-transfer-cost   certified-headroom   shared-source-blast
  criticality           execution-bound      build-failed
  failed-task-time
```

A probe says the repair is cheap and real. Building `02` here and
analysing it took one command and produced **`certified-headroom`**,
one of the seven, for **152 KB** on disk:

```console
$ bga snapshot -- bst build all.bst      # examples/02, isolated cache
This snapshot: 90.9K.
$ bga analyze <run> --format json | jq '[.findings[].id]|sort|unique'
blast-radius-ranking, blast-radius-structural, cache-hit-ratio,
certified-headroom, confidence, efficiency-score, wait-category
```

Everything the harder ones need is on this machine — `bst` 2.7.0,
`bwrap`, `buildstream-plugins`, `cmake`, `make`, `gcc`, `git`,
`busybox` — so the toolchain is not what has been stopping this.

## Required Fix

- **Commit one capture per example** for 01, 02, 03, 04, 05, 07 and 09,
  each built the way `bst-examples` builds it and captured with
  `bga snapshot` into an isolated cache.
- **Each capture says what it is for.** The example's README section
  gains the finding ids that capture actually produces, read off
  `analyze` rather than asserted — so a later round can see when a
  project stops demonstrating what it was written for.
- **Watch the store's weight.** `UX-300` measured what a big snapshot
  does to a store; state the total the repository gains and check it
  against `UX-189`'s rule that a clone should not ship a capture
  archive.

## Out of Scope

- **A new example holding every defect at once**: possible later, and
  premature now — seven projects that already plant distinct
  pathologies are being thrown away, and using them is cheaper than
  authoring a tenth. Revisit once the census below says what is still
  uncovered.
- **`build-failed` and `failed-task-time`**: a capture of a *successful*
  build cannot produce them by construction. They belong in `UX-460`'s
  declared-unreachable list, not in a capture.
- **Re-running the examples in CI to refresh these captures**: they are
  fixtures, and a fixture that regenerates is not a fixture.

## Acceptance Test

```bash
python3 tools/dev_finding_coverage.py
```

names every committed capture and the findings it produces, and the
count of findings with no capture has fallen — with the before and
after pasted, and each example's README section naming its own.

## Outcome

_Not started._
