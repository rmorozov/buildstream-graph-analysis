# UX-900: a store is a directory, but CI will keep bundles in versioned directories

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-520 (the bundle), UX-234 (the aggregate) | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 1) — CI will preserve `bga` bundles in directories named by build number | **Serves:** R5 and R7 (an aggregate over what CI actually kept), R8 (the health view that reads the same store) | **Topic:** store | **Area:** bga | **Shape:** mechanical

**Guard:** `tests/unit/test_a_tree_of_bundles_is_a_store.py`

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

## Decision

```text
Route:     `bundle.load_tree(root, project)` walks the tree for `*bga-bundle.tar.gz`, sorted, and runs read_manifest, check_readable and _safe_members on every bundle before writing anything, then the existing `load()` for each (`_differs` already makes it idempotent). Two entry points: `bga bundle --load DIR` materialises the runs into the project's store; `bga snapshot --list|--aggregate|--capacity --bundles DIR` is the in-place reader: it loads into a temporary project, runs the same `_list`/`_aggregate`/`_capacity`, and deletes the copy on exit.
Rejected:  skipping a bad bundle and loading the rest (the refusal names every bad bundle and writes nothing) · true in-place reading of tar members (store code opens files by path in dozens of places) · a new `bga store` command · cache-trend (takes run directories; out of scope).
Files:     bga/bundle.py (load_tree; a TarError from getmembers on a truncated archive becomes a BundleError naming the file), bga/cli.py (_bundle_load directory branch; usage/help), tools/bga_snapshot.py (`--bundles DIR`; main skips why_the_project_is_not_one when given), tests/unit/test_a_tree_of_bundles_is_a_store.py
Guard:     two bundles in nested build-number directories: `--list` shows 2 runs, `--aggregate --format json` equals the aggregate of the same two run directories with paths masked; a truncated bundle is refused by name and nothing is written; a stray non-bundle file is ignored; loading the tree twice leaves the same store.
Mutation:  drop check_readable/_safe_members from the pre-pass (truncated bundle joins); replace `_differs` with a fresh stamp per load (second pass doubles the runs).
Class:     product. The Outcome records measured disk for both routes on the committed fixture: tree bytes, materialised store bytes, peak scratch of --bundles.
```

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

**Gap measured.** At `b8072cd7`, on the two `same_build_twice_*`
fixture runs exported into `ci/100/` and `ci/101/`:

```text
$ bga bundle --load ../ci
IsADirectoryError: [Errno 21] Is a directory: '../ci'      (a traceback)
$ bga snapshot --list --bundles ci
bga snapshot: error: unrecognized arguments: --bundles
```

**Close measured.** `python3 -m pytest -q
tests/unit/test_a_tree_of_bundles_is_a_store.py`: `9 passed in 1.35s`.
The same tree, a stray `console.log` beside the bundles:

```text
$ bga snapshot --list --bundles ci       -> 2 snapshots in ci: (exit 0)
$ bga bundle --load ../ci                -> Loaded 2 bundles ... (twice, same store)
$ bga snapshot --aggregate --bundles ci  (a 300-byte cut added as ci/102)
Error: 1 bundle refused, so nothing was written:
  ci/102/20260903T100000Z.bga-bundle.tar.gz is not a readable archive: ...   (exit 2)
```

Disk for both routes (`scratchpad measure.py`, sums of file sizes):

| fixture | tree | `--load` store | `--bundles` peak scratch |
|---|---|---|---|
| `same_build_twice_cold` + `_incremental` | 1,824 B | 3,466 B | 3,629 B |
| `macro_micro` x2 (with `plane2.json`) | 20,380 B | 115,118 B | 115,281 B |

The scratch is the store plus its `.gitignore`, held only while the
command runs; `--load` keeps it. Materialising costs 1.9x-5.6x the tree.

**Mutation table.** From a saved copy of `bga/bundle.py`, with
`PYTHONDONTWRITEBYTECODE=1`; reverted and 9 passed after.

| mutation | reddened | count |
|---|---|---|
| `_check` without `check_readable` | `test_a_bad_bundle_is_named_and_nothing_is_written[newer]` | 1 of 9 |
| `_check` without `_members_of` (`_safe_members`) | `...[short]` | 1 of 9 |
| no pre-pass (`load_tree` loads each directly) | `...[newer]`, `[short]`, `[truncated]` | 3 of 9 |
| `load` stamps with `+ os.urandom(3).hex()` | aggregate-equals, loading-twice, `bundle --load DIR` | 3 of 9 |

The Decision's first mutation was split in three: `read_manifest`
resolves `bundle.json` by name, which makes tarfile scan every member,
so a truncated bundle is refused there and never reaches
`_safe_members`. A `newer` (schema) and a `short` (manifest names a
member the archive lacks) bundle make each pre-pass check reddenable.
