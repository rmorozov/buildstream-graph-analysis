# UX-1286: the review gate reads its band from the bundles CI kept, without a store on the runner

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-899, UX-900 | **Found by:** the 2026-10-02 state audit: `--band-from-class` needs a `project.conf` enclosing a `.bga` store (`bga/cli.py:1247-1257`), and a review runner is stateless | **Serves:** R4 | **Topic:** cli | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** test_the_gate_reads_kept_bundles_in_place.py

## Motivation

UX-900 lets CI keep bundles in a directory tree instead of a store,
and `bga snapshot --list|--aggregate|--capacity --bundles DIR` reads
that tree through a temporary store deleted on exit
(`tools/bga_snapshot.py:1644`). `bga compare --band-from-class` has no
such route: a fresh review runner must `bga bundle --load` the whole
tree into its workspace first, which costs 1.9x-5.6x the tree on disk
(UX-900's reading) and writes the history into a checkout that should
hold only the candidate.

## Decomposition

Input classes: `--bundles DIR` with enough same-class runs; with too
few (exit 8); with a corrupt bundle (refused by name, nothing judged);
`--bundles` without `--band-from-class` (usage error); the candidate's
own stamp also present in the tree (excluded, as the principals are
today). Journey: the pilot snippet's review step (UX-1288).

## Required Fix

`bga compare --band-from-class [N] --bundles DIR` selects members from
the tree through the same temporary-store route `snapshot --bundles`
uses, with UX-1285's host filter, and needs no `project.conf` around
the candidate. The comment names the tree as the band's source.

## Out of Scope

Reading members without materialising them; remote trees (URLs).

## Acceptance Test

A tree of five same-class bundles and a candidate outside any project:
the band is the five, exit 0 or 4 as the seconds say; the working tree
holds no `.bga` afterwards. A truncated bundle in the tree: refused by
name, exit 2.

## Outcome (2026-10-02)

**Premise:** held — the base had no route from a tree to a band.

### The gap, measured

`repro1286.py` (five same-class bundles exported by `bundle.export` into
`kept/100..104/`, baseline and candidate under `ci-job/`, no
`project.conf` anywhere, cwd an empty `work/`), base tree `1448af2c7`:

```text
$ bga compare ../ci-job/baseline ../ci-job/20260921T000000Z/run --band-from-class --bundles ../kept --fail-on-regression
bga: error: unrecognized arguments: --bundles ../kept
exit=1
$ bga compare … --band-from-class --fail-on-regression
Error: --band-from-class needs a run store to select from, and no BuildStream project (a directory holding project.conf) encloses …
exit=8
```

### The close, measured

The same tree, this branch:

```text
$ bga compare … --band-from-class --bundles ../kept --fail-on-regression --format ci-comment
exit=0
band from baseline 5 runs, widened to the fixed 1% rule: 99.0s .. 101.0s — from `20260905T000000Z`, … `20260901T000000Z` — read from the bundles under `../kept`
$ ls -A            # work/ afterwards: empty; /tmp holds 0 bga-bundles-*
$ bga compare … --bundles ../broken …     # kept/ with 102/ cut in half
Error: 1 bundle refused, so nothing was written:
  ../broken/102/20260903T000000Z.bga-bundle.tar.gz is not a readable archive: Compressed file ended before the end-of-stream marker was reached
exit=2
```

### Mutations verified red and reverted (8)

`test_the_gate_reads_kept_bundles_in_place.py`, 6 tests:

| # | mutation | reddened |
|---|---|---|
| N1 | the principals' stamps not excluded from the tree | the candidate's own stamp, 1 failed |
| N2 | the temporary store not removed | five, too few, truncated: 3 failed |
| N3 | the store found by `project.conf`, not the tree | 4 failed |
| N4 | `BundleError` not caught | the truncated bundle, 1 failed |
| N5 | `--bundles` accepted without `--band-from-class` | the usage error, 1 failed |
| N6 | the comment silent on the source | five, 1 failed |
| N7 | the refusal says "this store" | too few, 1 failed |
| N8 | the tree loaded under the cwd, then removed | five, 1 failed |

N8 survived the first draft, whose check was `work/.bga` after exit;
the guard now records where `load_tree` wrote and asserts the
temporary directory.
