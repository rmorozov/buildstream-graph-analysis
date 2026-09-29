# UX-1084: a short numeric credential still exports verbatim

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1068 | **Found by:** the owner's #298 re-review at 156d7436, finding 1 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

**Guard:** none — named test_a_short_numeric_credential_pseudonymizes.py, absent from tests/

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

Gap measured: before the fix, `pytest tests/unit/test_a_short_numeric_credential_pseudonymizes.py`
failed 2/7 (`--otp=123456`, `--pin=1234` kept their value verbatim);
`_value`'s cap (`len(value) <= 6`) had no option context at all. A
first close keyed safety on flag name alone; the verifier found
`gcc -l1234` (a linker library) and `curl -O 12345` (an output
filename, via positional inheritance) both still kept verbatim -
`-l`/`-O` mean different things off `make`/`gcc`.

Close measured: `pytest tests/unit/test_a_short_numeric_credential_pseudonymizes.py
tests/unit/test_a_command_line_credential_is_dropped.py` - 25 passed.
`--otp=123456`/`--pin=1234` pseudonymize (absent from the rebuilt
command; present in the map's originals, since pseudonymizing is
reversible by design, unlike the credential-shaped drop path).
`-j8`, `--jobs=4`, `-DCMAKE_BUILD_PARALLEL_LEVEL=8`, space-form
`-j 8`/`-l 4` keep their value only when argv[0] is a make-like
binary (`_MAKE_LIKE_BINARIES`/`_MAKE_SAFE_FLAGS`); `-O2` keeps its
value only glued and only on a compiler driver (`_COMPILER_BINARIES`,
`_OPT_LEVEL`) - `gcc -l1234` and `curl -O 12345` now pseudonymize.
The safe set is re-keyed on (binary, option): make/gmake/ninja keep
`-j`/`--jobs`/`-l`/`--load-average`; a compiler driver keeps only a
glued `-O<digit>`; `JOBS`/`CMAKE_BUILD_PARALLEL_LEVEL` keep regardless
of binary. Verifier's leaks `gcc -l1234` and `curl -O 12345`/`wget -O
12345` pseudonymize (checked: `gcc -lf-9346`, `curl -O f-15243729`).
`python tools/dev_touching.py --base e5075375`: 44 files selected,
1877 passed, 3 skipped.

Mutation table:

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `_value`'s default-pseudonymize check | `_value` keeps every digit value unconditionally | both test files | 4 failed / 25 |
| `_flag_argument`'s binary key | drop `binary in _MAKE_LIKE_BINARIES` from `flag_safe`/`glued_safe` | `test_a_compilers_glued_library_count_is_not_a_load_average` | 1 failed / 10 |
