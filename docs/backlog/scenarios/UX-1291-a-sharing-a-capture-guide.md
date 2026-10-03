# UX-1291: one guide says how to keep, share, anonymise and reload a capture

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1286 | **Found by:** the docs audit (2026-10-02, finding 6): `bundle --load/--resolve/--key-fingerprint` and `snapshot --bundles` are documented only in `cli.md` and `architecture.md` | **Serves:** R4, R5 | **Topic:** docs | **Area:** unassigned | **Shape:** bounded | **Reading:** container

**Guard:** test_the_sharing_guide_runs.py, test_the_docs_index_is_a_router.py

## Motivation

A pilot keeps bundles on CI and may send one back for analysis. The
steps (export, anonymised export, `--load` a tree, read it in place,
`--resolve` a pseudonym locally) and what each discloses live in
`cli.md`, `architecture.md` and `design/anonymized-bundle.md`; no
guide walks them in order.

## Required Fix

`docs/guides/sharing-a-capture.md`: the five steps with one command
each, what a plain bundle contains (full paths, argv), what the
anonymised one hides and where the key lives (`.bga/anon/`, 0600),
and the disk cost of `--load` (UX-900: 1.9x-5.6x the tree).

## Out of Scope

Changing what anonymisation covers.

## Acceptance Test

Every command in the guide runs against the committed fixture
bundles in a guard; the guide is linked from the router (UX-1289).

## Outcome (2026-10-03)

**Premise:** held; `bga bundle --export --anonymize` (`UX-1295`) had
landed since filing and is step 2.

### The gap, measured

Base tree `b71d19ac8`:

```text
$ git cat-file -e HEAD:docs/guides/sharing-a-capture.md
fatal: path 'docs/guides/sharing-a-capture.md' exists on disk, but not in 'HEAD'
$ git show HEAD:docs/README.md | grep "share a capture"
| **share a capture** … | `guides/cli.md` (its `#carrying-a-capture-to-another-machine-ux-520` anchor) |
```

### The close, measured

`docs/guides/sharing-a-capture.md`, five steps, six lines in its `bash`
blocks (`mkdir -p ci/101`, `--export`, `--anonymize`, `--load ci`,
`snapshot --list --bundles ci`, `cat reply.txt | … --resolve`). The
guard reads those blocks and runs every line in order through
`bga.cli.main`: a runner project holding `same_build_twice_cold` and
`macro_micro` as two snapshots, the tree copied to a reading project.

```text
$ pytest tests/unit/test_the_sharing_guide_runs.py tests/unit/test_the_docs_index_is_a_router.py
7 passed
| **share a capture** … | `guides/sharing-a-capture.md` |
```

The guide's figures, measured on those fixtures (2026-10-03): the plain
bundle's `plane2.json` carries 18 distinct absolute paths and each
repeated operation's command line; `--load` turned an 11,031-byte tree
into a 59,479-byte store, 5.4x, inside `UX-900`'s 1.9x-5.6x. No bundle is
committed, so "the committed fixture bundles" are bundles the guard
exports from committed fixture runs. Found, not fixed: `--export -o
DIR/FILE` with a missing `DIR` is a `FileNotFoundError` traceback, so
step 1 carries a `mkdir -p`. The selector `max` in
`test_the_loop_stays_fast.py` 197 → 198: the new guard runs `bga.cli`.

### Mutations verified red and reverted (8)

`test_the_sharing_guide_runs.py` (4) and
`test_the_docs_index_is_a_router.py` (3):

| # | mutation | reddened |
|---|---|---|
| N1 | the guide's `--anonymize` misspelt `--anonymise` | 4 |
| N2 | the guide's `mkdir -p ci/101` removed | exits zero, steps: 2 |
| N3 | the resolve line's fingerprint a literal | exits zero, steps: 2 |
| N4 | step 4's command removed | each step, steps: 2 |
| N5 | the router's sharing row back to `cli.md` | one row per job: 1 |
| N6 | `bga`: a terminal's answer ignored | exits zero, key, steps: 3 |
| N7 | `bga`: the key written 0644 | key 0600, steps: 2 |
| N8 | `bga`: `--resolve` echoes its input | steps: 1 |

Restored: 7 passed. N2 first errored in the fixture rather than
failing; the guard now records a raised exception as that line's exit.
