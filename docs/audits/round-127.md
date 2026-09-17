# Round 127 — the two operator surfaces for a custom-prefix shim

Run on 2026-09-17, after round 126 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

Round 126 shipped the `flto` compiler-LTO shim, but its reference shim
only reaches a GCC driver invoked by a bare name off `PATH`. The user's
real toolchains are built in-sandbox with **custom prefixes** and invoked
by absolute path (or wired in a `toolchain.cmake`), which PATH-shadowing
cannot reach — and they already maintain their own clang-shim. Two
surfaces close that gap, both filed round 126:

- **`--wrapper-dir`** (`UX-881`): the operator points bga at their own
  wrapper directory — a shim matching bga's published contract — so their
  custom-prefix compiler is covered by a shim *they* wire in.
- **the `public: bga.jobserver-auth` annotation** (`UX-882`): the
  per-element style, committed with the element instead of re-typed on
  every invocation.

A round-127 `researcher` read confirmed both are feasible against the
current tree: `%{public}` is already fetched and YAML-parsed by
`bst_show_to_graph.py` (an arbitrary sub-domain reads the same way the
`bst:` one does), and the `--wrapper-dir` env/mount plumbing mirrors the
UX-879/880 translate-to-env pattern. It also settled the one open call:
the annotation is advisory **input** bga reads (like the `kind`/`%{vars}`
reads), not a bga-published output — no `bga.contracts` `/vN` id, no
`specification.md` Part-32 edit.

## Plan

| wave | rows | why |
|---|---|---|
| build | `UX-881` | `bga capture run --wrapper-dir <path>` (augment, or `--replace`) → `BST_TRACE_WRAPPER_DIR`/`_MODE`; `_wrapper_mount` binds two dirs, operator first on PATH; a published `docs/guides/wrapper-contract.md` |
| build | `UX-882` | a second `bst show %{public}` read → `BST_TRACE_ELEMENT_AUTH_MAP`; `_jobserver_injection` resolves command-line override, then annotation, then auto; the four styles UX-879 already has, sourced from the project |

Two bounded `implementer` tracks on `sonnet`; their only shared file is
`bwrap_shim.py` (881 in `_wrapper_mount`, 882 in `_jobserver_injection` —
different regions, merge-additive). `keep` (auto-but-never-scrub), the
make/autotools LTO gap (`UX-884`) and the two process rows (`UX-885`,
`UX-886`) stay filed for a later round.

## What closed

_(filled at close)_

## The verifiers found

_(filled at close)_

## Agents

_(filled at close)_

## The gate

| run | head | result |
|---|---|---|
| 0 | the filing | red only on the round-open bootstrap guards; docs-only |

## Standing

_(filled at close)_
