# UX-683: the foundation tier is declared, and the kind-based exemption misses it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-479, UX-681 | **Serves:** R2 who owns the toolchain and wants out of the noise; R3 reading the ranking | **Topic:** analysis

## Motivation

```text
bga/ingest/models.py:25   STRUCTURAL_ELEMENT_KINDS = {junction, import, filter, compose, stack}
bga/findings.py:1361-1372 blast-radius-structural: excluded from the ranking, "reaching most of the graph by design"
```

The exemption is by *kind*. A toolchain or a base image is an
`autotools`, `manual` or `cmake` element with a fan-out in the top
percentile *by design* — and it is not exempt, so it tops every
blast ranking as the largest thing to fix, which is the noise the
user described. A discovered tier (top p5 fan-out) moves with the
graph; the honest form is a declaration.

## Required Fix

A `foundation` declaration — an element list in the project's `bga`
config (or a `bga:foundation` annotation the extractor reads from
`project.conf`), validated against the graph — reported as its own
tier in every blast, fan-in and expected-cost ranking: present,
separated, never the top row. The discovery half proposes candidates
(top p5 fan-out among non-structural kinds) and says "declare or
dismiss".

## Out of Scope

- Deciding what is foundation for a project — the owner declares;
  the tool proposes.

## Acceptance Test

Example 06 with `toolchain.bst` declared: the blast ranking's top row
is core.bst, toolchain sits in the foundation tier with its fan-out;
undeclared, the discovery names it; mutation: drop the tier from the
ranking — the tier guard reds.
