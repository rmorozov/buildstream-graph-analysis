# UX-1068: a credential in a command line is dropped, not kept

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1062 | **Found by:** the owner's implementation review on #298 (2026-09-28), finding 1 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

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

**Gap measured:** `_argument`/`_assigned`/`_value` in `bga/anonymize.py`
ran every `-D`, `--flag=`, `-flag=` and env-style `NAME=value` word
through the general grammar first; `_value` kept any digit-only value
verbatim (`value.isdigit()`), so `cmake -DAPI_TOKEN=12345678` exported
`12345678`, and any non-numeric value (`s3cr3t`) reached
`pseudonymize_identifier` and joined the local map - class G says
drop, not map. A leading env-style word (`PASSWORD=hunter2 make`) was
worse: `rebuild_command` treated it as `argv[0]`, so it never reached
argument handling at all.

**Close measured:** `_CREDENTIAL_NAME` (token/secret/password/passwd/
key/auth/credential/cookie/session, case-insensitive substring) is
checked before the grammar for all three grammars, plus a leading run
of `NAME=value` words ahead of `argv[0]`; a credential's name is still
pseudonymized, its value replaced by a fixed `<dropped>` marker,
numeric or text, and the raw value never reaches `pmap`. `counts["F
credential"]` increments once per drop, so `bundle.review_screen`'s
"values rewritten, per class" line reports it.
`pytest tests/unit/test_a_command_line_credential_is_dropped.py tests/unit/test_an_anonymized_bundle_trips_on_a_leftover_name.py -q`:
`32 passed in 0.79s` - all five acceptance cases drop cleanly, the
map holds no dropped value, and `-DJOBS=4` still keeps `4`.

**Verifier gap measured (7eb7e817):** four more leaks/a regression: (1)
`pat`/`bearer`/`apikey` etc. weren't on `_CREDENTIAL_NAME`, so
`-DGITHUB_PAT=ghp_x` mapped `ghp_x` verbatim - a word list fails open;
(2) `--api-key 12345678` (space form, no `=`) never reached any
credential check, and any digit-only value of any length was kept
verbatim; (3) `_NAMED_FLAG`'s name capture is lowercase-only, so
`--Authorization=Bearer` fell to the opaque whole-word fallback and
mapped `Authorization=Bearer` as one blob; (4) the leading-env loop's
`[A-Za-z_]...=` regex ate a lowercase `a=b`'s `argv[0]`, misreading
`a=b --flag x` as `argv[0]=--flag`.

**Verifier close measured:** added `_credential_shaped` (known token
prefixes, an auth-scheme marker, or 20+-char mixed letter/digit runs) -
a value-shape backstop independent of name, checked in `_value`;
`_CREDENTIAL_NAME` gained `pat`/`bearer`/`apikey`/`private_key`/
`signing`; digit-only values only stay verbatim up to 6 digits
(`_DIGIT_CAP`), longer ones pseudonymize; the credential check on a
flag's name (`_argument`) now runs case-insensitively on the raw
`flag` string, not `_NAMED_FLAG`'s lowercase-only capture;
`_space_credential` drops a bare credential flag's following word;
`_continues_scheme` drops a further word after a `Bearer`/`Basic`
marker; `_LEADING_ENV` is now uppercase-only and never consumes the
last word. `pytest tests/unit/test_a_command_line_credential_is_dropped.py
tests/unit/test_an_anonymized_bundle_trips_on_a_leftover_name.py
tests/unit/test_analysis_commutes_with_anonymization.py -q`: `53 passed
in 2.48s`. `--sessions=2` over-drops on purpose (`session` is on the
name list); accepted per the verifier's own call.

**Judgement (the digit-only pass-through elsewhere):** now closed by
the digit cap above - a long numeric value pseudonymizes regardless of
name, so a 16-digit card-number shape is no longer a special case.

**Mutation table:**

| Mutation | Reddened | Count |
|---|---|---|
| Original: `_CREDENTIAL_NAME` -> `(?!)` (never matches) | 6 of 7 cases, e.g. `"12345678" not in rebuilt` fails | 6 failed, 1 passed |
| `_CREDENTIAL_NAME` list reverted (drop `pat`/`bearer`/`apikey`/`private_key`/`signing`) | `test_the_signing_name_alone_...`: `-DSIGNINGNONCE=1234` kept `=1234`, not `=<dropped>` | 1 failed, 14 passed |
| `_credential_shaped` -> `False` | `test_a_shaped_value_drops_even_off_the_name_list`: `ghp_...` mapped as `f-...` | 1 failed, 14 passed |
| `_DIGIT_CAP` -> `999` | `test_a_long_digit_only_value_is_pseudonymized_not_kept`: `123456789` kept verbatim | 1 failed, 14 passed |
| `_space_credential` -> always `False` | `test_a_space_separated_credential_flag_drops_the_next_word`: `12345678` kept, no `<dropped>` | 1 failed, 14 passed |
| `_argument`'s flag credential check gated on `flag.islower()` | `test_a_mixed_case_flag_name_and_its_continuation_both_drop`: 1 `<dropped>` not 2, `Authorization=Bearer` folded into one opaque token | 1 failed, 14 passed |
| `_LEADING_ENV` reverted to `[A-Za-z_]...=` | `test_a_lowercase_leading_word_is_the_binary_not_an_env_prefix`: `--flag` becomes a dash-less `b-` binary pseudonym | 1 failed, 14 passed |

Each reverted from a copy of `bga/anonymize.py` saved before mutating,
not `git checkout --`, since the mutation and this task's uncommitted
work share the file; `__pycache__` cleared between runs.
