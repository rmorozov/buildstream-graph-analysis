# UX-1071: the residue scan reads a large member in linear time

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1069 | **Found by:** the architect shaping UX-1069 (2026-09-28) | **Serves:** anyone sharing a large private capture | **Topic:** store | **Area:** bga | **Shape:** judgement

## Motivation

On a 5,000-record plane2 profile, `residue` took 1.8 s of a 2.8 s
export in `re.findall` over an alternation of about 800 variants,
about 0.4 MB/s: a GB-scale member would take on the order of an hour
before the review screen appears.

## Required Fix

Scan by tokenizing the decoded text at word boundaries and looking
each token (and its normalized variants) up in a set, instead of one
regex alternation; keep the same hits, the same carry-over between
chunks, and the same refusal message.

## Out of Scope

Pseudonymization speed.

## Acceptance Test

`tests/unit/test_the_residue_scan_is_linear.py`: the scan's hits equal
the regex scan's on the existing residue fixtures, and scan time over
N and 4N bytes grows at most 5x. Mutation: restore the alternation,
and the growth bound or the throughput floor reds.

## Outcome
