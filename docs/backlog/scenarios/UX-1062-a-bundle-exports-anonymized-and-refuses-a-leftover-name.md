# UX-1062: a bundle exports anonymized, and refuses a leftover name

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1060, UX-1061, UX-1067 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), sections 1, 6 and 7; the owner's review on #298, findings 3 and 4 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

A capture of a private project cannot leave the company today: every
member names elements, paths and the host.

## Required Fix

`bga/bundle.py` gains an anonymized export that walks every
`CAPTURE_LAYOUT` row by the treatment the design's section 7 table
states (keep, transform or drop) and refuses on a row with none. A
transformed member is rewritten by its UX-1060 policy: identifiers
pseudonymized, hashes re-keyed, time shifted to epoch 0, secrets
dropped; a class F field is rebuilt from its grammar or dropped, never
scanned and forwarded. The residue scan runs over the decoded final
archive as a tripwire; nothing is written until the owner approves the
review screen.

## Out of Scope

Raw logs (UX-1066); public names (UX-1065).

## Acceptance Test

`tests/unit/test_an_anonymized_bundle_trips_on_a_leftover_name.py` on the
golden fixtures: no fixture uid, hostname, source path or target name is
found in the decoded archive, and the bundle loads. Mutations: plant a
uid in a kept string, and the residue scan refuses; add a row to
`CAPTURE_LAYOUT` with no treatment, and the export refuses.

## Outcome
