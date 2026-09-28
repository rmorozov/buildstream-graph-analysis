# UX-1084: a short numeric credential still exports verbatim

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1068 | **Found by:** the owner's #298 re-review at 156d7436, finding 1 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

`_value()` keeps every digit-only value of at most six characters
(`_DIGIT_CAP`). `--otp=123456` and `--pin=1234` are not on
`_CREDENTIAL_NAME`'s list, so their flag names pseudonymize but the
numeric values ride through into the rebuilt command; six digits is a
normal OTP length, so the cap itself is the leak, not just the name
list's coverage.

## Required Fix

Invert the default in `bga/anonymize.py`: a numeric value
pseudonymizes unless its option is on a small, explicitly named safe
list (jobs, optimization level, and similar counts/levels where the
number is not a secret); a credential-shaped or credential-named
option keeps dropping its value as UX-1068 already does. The safe list
is named in the module, not inferred from a length or shape.

## Out of Scope

Non-numeric credential values (UX-1068's `<dropped>` marker already
covers them); the residue scan and the map's write path (UX-1085,
UX-1086).

## Acceptance Test

`tests/unit/test_a_short_numeric_credential_pseudonymizes.py`:
`--otp=123456` and `--pin=1234` each export with no trace of the
value in the decoded archive and no trace in the map; `-DJOBS=4` and
`-O2` (or the repo's equivalent named-safe options) still keep their
values. Mutation: drop the default-pseudonymize numeric check, and
`123456`/`1234` travel verbatim.

## Outcome
