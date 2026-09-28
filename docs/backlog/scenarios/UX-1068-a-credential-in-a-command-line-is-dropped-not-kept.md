# UX-1068: a credential in a command line is dropped, not kept

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1062 | **Found by:** the owner's implementation review on #298 (2026-09-28), finding 1 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

`rebuild_command()` sends `-D...` assignments through `_assigned()` and
`_value()`, which keeps every digit-only value, so `cmake
-DAPI_TOKEN=12345678` exports `12345678`; a text secret goes into the
local map, though class G says drop. A residue scan cannot catch a
credential its dictionary never held.

## Required Fix

Classify a sensitive assignment before the general argument grammar in
`bga/anonymize.py`: a `-D` macro, a `--flag=`, or an environment-style
`NAME=value` whose name reads as a credential (token, secret, password,
passwd, key, auth, credential, cookie, session; any case, any
separator) keeps its pseudonymized name and loses its value (a fixed
`<dropped>` marker), numeric or text alike; the value never reaches the
map. The review screen counts the drops.

## Out of Scope

Secrets outside command lines (UX-1062's class G paths already drop);
raw logs (UX-1066).

## Acceptance Test

`tests/unit/test_a_command_line_credential_is_dropped.py`: `-DAPI_TOKEN=12345678`,
`-DAPI_TOKEN=s3cr3t`, `--token=12345678`, `--auth-key=abc`, and
`PASSWORD=hunter2 make` each export with no value in the decoded
archive and no value in the map; a non-credential `-DJOBS=4` keeps `4`.
Mutation: drop the credential check, and the numeric token travels.

## Outcome
