# UX-1063: analysis commutes with anonymization

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1062 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 6.4 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** guards | **Area:** bga | **Shape:** judgement

## Motivation

An outside reader diagnoses the anonymized analysis; if it differs from
the real one beyond names, the diagnosis is of a different build. Any
output sorted or tie-broken by name reorders under HMAC pseudonyms.

## Required Fix

`analyze(anon(capture)) == anon(analyze(capture))` on the golden
fixtures; the name-dependent tie-breaks it finds in `bga/` are replaced
by name-independent ones.

## Out of Scope

Order-preserving pseudonyms: rejected, they break when an element is
added.

## Acceptance Test

`tests/unit/test_analysis_commutes_with_anonymization.py` over every
golden fixture. Mutation: reintroduce a sort by uid on the critical
path's tie-break, and it reds.

## Outcome
