# UX-1063: analysis commutes with anonymization

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1062 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), sections 6.4 and 6.10; the owner's review on #298, finding 5, and its follow-up at `8c3bead1`, finding 2: a release criterion for UX-1062's export | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** guards | **Area:** bga | **Shape:** judgement

## Motivation

An outside reader diagnoses the anonymized analysis; if it differs from
the real one beyond names, the diagnosis is of a different build. Any
output sorted or tie-broken by name reorders under HMAC pseudonyms.

## Required Fix

On the golden fixtures, `analyze(anon(capture))` and
`anon(analyze(capture))` agree on every invariant measurement exactly;
where a choice is tied, they agree on the set of equally valid choices,
not the representative; display order is not compared. Name-dependent
tie-breaks found in `bga/` are replaced where a name-independent order
exists; findings with no such order are listed by name in the guard.

## Out of Scope

Order-preserving pseudonyms: rejected, they break when an element is
added.

## Acceptance Test

`tests/unit/test_analysis_commutes_with_anonymization.py` over every
golden fixture. Mutation: reintroduce a sort by uid on the critical
path's tie-break, and it reds.

## Outcome
