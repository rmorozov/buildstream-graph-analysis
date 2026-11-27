# UX-1393: the examples README says only Ubuntu 24.04 stages without a warning

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 40 (2026-11-27) | **Serves:** R8 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`examples/README.md:180`: "If you stage on a host outside Ubuntu 24.04, expect
that warning". `UX-1386` and `UX-1387` declare both releases:
`tools/sysroot_manifest.py` `HOST_RELEASES` holds 24.04 (glibc 2.39, coreutils
9.4) and 26.04 (2.43, uutils 0.10.0), and `ci.yml` runs `bst-tests` on both. The
same README's pasted table (`:137-138`) and `:149` "host-staged 2.39" are
24.04's figures with no release label.

## Required Fix

The README names both declared releases, and labels its pasted figures with the
release they were read on.

## Out of Scope

Declaring a third release.

## Acceptance Test

A guard reads the README's release names against `HOST_RELEASES`' keys; a
release added to one and not the other reddens it.
