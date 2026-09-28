# UX-1088: an unrecognized numeric value is dropped, not mapped

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1084 | **Found by:** the owner's #298 re-review at 76f2179e, finding 1 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

UX-1084's tests assert `--otp=123456` and `--pin=1234` are absent from
the archive *but present in* `PseudonymMap`. `otp`/`pin` are not on
`_CREDENTIAL_NAME`, so they pseudonymize like an ordinary numeric
value instead of dropping like a credential - and pseudonymizing an
unrecognized secret still puts it in the reversible map, contradicting
class G's rule that a credential is dropped and never mapped.

## Required Fix

Add `otp`, `pin` (and `passcode`, `mfa`, `totp`) to `_CREDENTIAL_NAME`
in `bga/anonymize.py`, and change `_value`'s numeric default: a
digit-only value whose (binary, option) pair is not on the existing
safe set (`_MAKE_SAFE_FLAGS`+`_MAKE_LIKE_BINARIES`, `_OPT_LEVEL`+
`_COMPILER_BINARIES`, `_MACRO_SAFE_NAMES`) is dropped to `<dropped>`
and counted, same as a named credential - never pseudonymized, never
entering the map. A safe-listed pair is unaffected.

## Out of Scope

The glued `-j<digits>` shortcut, which bypasses the safe-set check
entirely rather than defaulting the wrong way (UX-1089); the residue
scan and the map's write path (UX-1085, UX-1086).

## Acceptance Test

`tests/unit/test_an_otp_or_pin_value_is_dropped_not_mapped.py` and
`tests/unit/test_a_command_line_credential_is_dropped.py`:
`--otp=123456`, `--otp 123456`, `--pin=1234`, `-DPORT=8080`,
`gcc -l1234`, `curl -O 12345` values absent from the rebuilt command
and from `PseudonymMap`'s originals (checked via its saved map file);
safe pairs (`make -j8`, `ninja --jobs=4`, `gcc -O2`,
`-DCMAKE_BUILD_PARALLEL_LEVEL=8`, `-DJOBS=4`) still keep their values.
Mutation: restore `_value`'s digit branch to unconditional
`pseudonymize_identifier`, and an unsafe numeric value re-enters the map.

## Outcome

Gap measured: reverting `_value`'s digit branch to unconditional
`pseudonymize_identifier` (the pre-fix shape) and dropping
`otp`/`pin`/`passcode`/`mfa`/`totp` from `_CREDENTIAL_NAME` -
`pytest tests/unit/test_an_otp_or_pin_value_is_dropped_not_mapped.py
tests/unit/test_a_command_line_credential_is_dropped.py` failed 4/25:
`--otp=123456`, `--pin=1234`, `gcc -l1234`, `curl -O 12345` and
`-DPORT=8080`/`-DBUILD=123456789` all pseudonymized into
`PseudonymMap` instead of dropping.

Close measured: `pytest
tests/unit/test_an_otp_or_pin_value_is_dropped_not_mapped.py
tests/unit/test_a_command_line_credential_is_dropped.py` - 25 passed.
`otp`/`pin` join `_CREDENTIAL_NAME`; `_value`'s digit branch drops
to `<dropped>` (counted in `counts["F credential"]`) unless `safe` is
true, keeping the (binary, option) safe set from UX-1084 unchanged.
`python tools/dev_touching.py --base 76f2179e`: 83 files selected,
2424 passed, 3 skipped.

Mutation table:

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `_value`'s default-drop numeric check | restore unconditional `pseudonymize_identifier` | both test files | 4 failed / 25 |
| `_CREDENTIAL_NAME`'s `otp`\|`pin`\|... addition | drop the new names from the regex | `test_a_non_numeric_otp_value_drops_on_its_name_not_its_shape` (a non-digit, non-high-entropy OTP the digit rule cannot catch) | 1 failed / 11 |

Live probe at `1a498516`: `curl --otp=123456` -> `--m-slbw=<dropped>`,
`x --pin=1234` -> `=<dropped>`, `cmake -DPORT=8080` -> `=<dropped>`,
`tool 42` -> `<dropped>`. After these four (plus the acceptance run
above), `PseudonymMap`'s originals are empty and its forward keys are
names only: `m-slbw`, `b-tn`, `m-wqlt`, `m-j_pc`, `b-qchp` - no dropped
value ever reaches the map.
