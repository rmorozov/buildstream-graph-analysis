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

| row | what landed |
|---|---|
| `UX-881` | `bga capture run --wrapper-dir <path>` (augment by default, `--wrapper-dir-mode replace` for a fully custom set) → `BST_TRACE_WRAPPER_DIR_OVERRIDE`/`BST_TRACE_WRAPPER_MODE`, mirroring the UX-879/880 translate-to-env pattern; `_wrapper_mount` binds the operator dir ahead of the shipped one on PATH (augment) or in its place (replace, no shipped `flto/`). A published `docs/guides/wrapper-contract.md` states what an operator's shim must satisfy — so a custom-prefix compiler PATH-shadowing can't reach is covered by a shim they wire in |
| `UX-882` | a `public: { bga: { jobserver-auth: fd\|fifo\|off\|flto } }` element annotation, read via a **separate** `bst show %{public}` (RS/US-delimited, YAML-parsed, the `off`→bool-`False` gotcha handled) → `BST_TRACE_ELEMENT_AUTH_MAP`, resolved in `_jobserver_injection` as command-line override **wins**, then annotation, then auto. The per-element style committed with the element; advisory input, no contract version bump |

## The verifiers found

- `UX-881`: **PASS** (first pass). Augment emits two `--ro-bind` mounts with
  the operator dir first on PATH; replace binds only the operator dir and
  never adds the shipped `flto/` subdir; the mutation (`_wrapper_mount`
  ignores the override) reddened 4 of 10; the contract doc mirrors the real
  `_common.sh` entry points. It confirmed a `bst_cache_logs.py` pyright
  `new:` finding pre-existed on the base — a local pyright-version artifact
  that is clean under the pinned toolchain.
- `UX-882`: **PASS** (first pass). Annotation `off` scrubs where auto fifos;
  a command-line override beats it; unmatched falls to auto. The `%{public}`
  read is a separate call, never raises, and the YAML `off`→`False` gotcha
  is handled. The one `quality_baseline.json` change is a single authorised
  S603 entry (the new `subprocess.run`) plus the `ruff_version` corrected to
  the 0.16.7 pin — not a rewrite.

## Agents

Two `implementer` tracks and two `verifier` reads, all on `sonnet`; **both
rows passed on the first verify** — no HOLD this round. A `researcher` read
(the de-risk: `%{public}` feasibility and the `--wrapper-dir` plumbing) ran
before the tracks — the session's own context, not a priced track.

| role | runs | tokens | calls | minutes |
|---|---|---|---|---|
| implementer | 2 | 326k | 257 | 42 m |
| verifier | 2 | 142k | 91 | 19 m |

## The gate

| run | head | result |
|---|---|---|
| 0 | `f5bd0af` (the filing) | red only on the round-open bootstrap guards (`test_a_run_is_priced`); docs-only |
| 1 | the close | the run this commit is pushed under; the pull request carries the figure |

## Standing

The custom-prefix shim story is complete: round 126 shipped the `flto`
shim and reference GCC-driver wrappers; round 127 gives the two surfaces
that reach a real in-sandbox toolchain — `--wrapper-dir` (the operator's
own shim, against a published contract) and the `public: bga.jobserver-auth`
annotation (the per-element style, committed). An operator can now cover a
custom-prefix compiler and pin an LTO element's style from the project.

An environment hazard surfaced and is filed (`UX-887`): the implementer
brief's `pip install -e '.[dev]'` fallback repoints the shared editable
`bga` install at a worktree (the round-109 mode) and a stale
`/root/.local/bin/ruff` shadows the pinned one — both tracks caught and
restored, and the merge gate ran with the editable install repointed at
the main checkout and the pinned `ruff 0.16.7`/`pyright 1.1.414`. Left
standing for a later round: `keep` (auto-but-never-scrub), the
make/autotools LTO gap (`UX-884`), and the process rows (`UX-885`,
`UX-886`, `UX-887`).
