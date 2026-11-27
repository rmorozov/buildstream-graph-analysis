# UX-1393: the examples README says only Ubuntu 24.04 stages without a warning

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** review 40 (2026-11-27) | **Serves:** R8 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_examples_readme_names_each_declared_host_release.py`

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

## Outcome

**Gap measured** (`sed -n 180p examples/README.md`, base `7e7b5db3`): "outside
Ubuntu 24.04, expect that warning"; `HOST_RELEASES` keys are 24.04 and 26.04;
the pasted table and "host-staged 2.39" carried no release. No existing guard
read the README's release names.

**Close measured**: the warning names 24.04 or 26.04, the table is labelled
"read on Ubuntu 24.04" (26.04's glibc 2.43, uutils 0.10.0 stated), "2.39 (24.04)".
`pytest tests/unit/test_the_examples_readme_names_each_declared_host_release.py`:
2 passed.

| Mutation | Result |
|---|---|
| README warning: drop ` or 26.04` | 1 failed, 1 passed |
| README: drop `read on Ubuntu` label | 1 failed, 1 passed |
| `HOST_RELEASES`: add `28.04` | 1 failed, 1 passed |

Review rework (2026-11-27): the label was checked only against `HOST_RELEASES` keys, so relabelling the table "read on Ubuntu 26.04" passed. A third test now requires the pasted glibc/coreutils figures to equal `HOST_RELEASES[label]`. Mutations: label 24.04 -> 26.04 -> 1 failed, 2 passed; glibc 2.39 -> 2.38 -> 1 failed, 2 passed.
