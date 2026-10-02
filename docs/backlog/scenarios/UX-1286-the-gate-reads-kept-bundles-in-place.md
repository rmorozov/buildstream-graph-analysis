# UX-1286: the review gate reads its band from the bundles CI kept, without a store on the runner

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-899, UX-900 | **Found by:** the 2026-10-02 state audit: `--band-from-class` needs a `project.conf` enclosing a `.bga` store (`bga/cli.py:1247-1257`), and a review runner is stateless | **Serves:** R4 | **Topic:** cli | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Outcome
