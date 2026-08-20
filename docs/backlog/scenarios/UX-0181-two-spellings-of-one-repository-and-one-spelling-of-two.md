# UX-181: two spellings of one repository, and one spelling of two

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-171 (`normalize_url` and the identity model)

## Motivation

`normalize_url` exists so a blast is not halved by two spellings of
one repository. The round-19 review found both failure directions
live:

1. **Mangling (two identities for one repo)**: `git+https://host/org/
   repo.git` → `git+https///host/org/repo` (the scp-colon rewrite
   fires on the unlisted scheme's own colon); `HTTPS://Host/Org/Repo`
   → `https///Host/Org/Repo` (schemes matched case-sensitively, host
   lowering then hits the wrong segment). Garbage identities in the
   report, and the halved blast the function exists to prevent.
2. **Over-grouping (one identity for many resources)**: pip sources
   key on the **index url**, so several pip elements against one index
   report as a single shared ref-keyed resource — and "any commit to
   this rebuilds all of them" is the wrong sentence about a package
   index. Pip identity should be the package (or pip excluded from
   repository phrasing).

Three one-line nits from the same files, to close while in them:
`split_by_kind` double-iterates its argument (a generator yields a
negative assembling count); `runs_outside_band` is recomputed from the
two band edges only after widening (max 2 — misnamed, boolean
correct); `drain_until_exit` can lose a tail written in the gap
between a select timeout and `poll()` (one post-poll read closes it).

## Required Fix

Scheme handling: case-insensitive, unknown schemes passed through
un-rewritten (the scp heuristic applies only to scheme-less
`user@host:path` forms); per-kind identity: pip keys on package name
with an "index" clause, and the keying sentence comes from the kind.
Then the three one-liners.

## Out of Scope

- The scp-vs-port conservative trade (documented, fine).
- Round-trip resolution (UX-178).

## Acceptance Test

Property-style table: each spelling pair that must collapse
(`git@host:org/repo.git` / `https://host/org/repo/` /
`HTTPS://HOST/org/repo`) collapses; each pair that must not
(`git+https` unlisted-scheme passthrough vs the plain form; two pip
packages on one index) stays distinct; the pip row renders the
index-appropriate sentence. A generator into `split_by_kind` equals
the list answer. Mutations: re-adding the case-sensitive match and the
scp rewrite on schemes each redden.
