# UX-1291: one guide says how to keep, share, anonymise and reload a capture

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1286 | **Found by:** the docs audit (2026-10-02, finding 6): `bundle --load/--resolve/--key-fingerprint` and `snapshot --bundles` are documented only in `cli.md` and `architecture.md` | **Serves:** R4, R5 | **Topic:** docs | **Area:** unassigned | **Shape:** bounded | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Outcome
