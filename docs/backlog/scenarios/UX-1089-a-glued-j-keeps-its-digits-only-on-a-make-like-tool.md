# UX-1089: a glued -j keeps its digits only on a make-like tool

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1084 | **Found by:** the owner's #298 re-review at 76f2179e, finding 2 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

`_KEPT_FLAG = ... j\d* ...` accepts a glued `-j<digits>` on any
`argv[0]`, and `_argument()` returns it before the make-like binary
check UX-1084 already keys the space-separated and assigned forms on.
`curl -j123456` or a private tool with that argument keeps six digits
verbatim, even though every other numeric form is correctly keyed by
tool.

## Required Fix

Restrict the glued `-j<digits>` shortcut in `bga/anonymize.py` to
`_MAKE_LIKE_BINARIES`; off one, it falls to the same default-drop
`_value` path UX-1088 gives every other unsafe numeric. Audit every
other digit-carrying glued shortcut in `_KEPT_FLAG`/`PUBLIC_FLAGS`
(`-O\d`, `-l`, and the rest) for the same gap; `-O` and `-l` are
already keyed by tool (UX-1084), `g[0-3]?` is a bounded 4-way enum,
not a captured value, and needs no key.

## Out of Scope

The credential name list and the numeric default itself (UX-1088);
any glued shortcut found safe by this audit needs no change.

## Acceptance Test

`tests/unit/test_a_glued_j_keeps_its_digits_only_on_a_make_like_tool.py`:
`curl -j123456` and a private tool (`acme-gen -j123456`) drop their
digits; `make -j8`/`ninja -j12` still keep them; `gcc -O2` stays kept;
`curl -O2` drops (curl is not a compiler driver, so its digit is
unsafe like any other). Mutation: drop the make-like binary check in
the glued `-j` branch, and `curl -j123456` keeps `123456` again.

## Outcome

Gap measured: reverting the glued `-j` branch's safety argument from
`binary in _MAKE_LIKE_BINARIES` to unconditionally `True` (the pre-fix
shape, matching `_KEPT_FLAG`'s old unconditional `j\d*`) -
`pytest tests/unit/test_a_glued_j_keeps_its_digits_only_on_a_make_like_tool.py`
failed 2/6: `curl -j123456` and `acme-gen -j123456` both kept
`123456` verbatim.

Close measured: same file - 6 passed. `_KEPT_FLAG` no longer matches a
digit-carrying `-j`; `_GLUED_JOBS` routes it through `_value` keyed on
`binary in _MAKE_LIKE_BINARIES`, same as the space-separated and
assigned forms. Audited `-O\d` (already keyed to `_COMPILER_BINARIES`,
UX-1084) and `-l` (already keyed to `_MAKE_LIKE_BINARIES` via
`_flag_argument`'s `glued_safe`); `g[0-3]?` stays unkeyed - a bounded
4-way enum, not a captured value. `curl -O2` drops (not a compiler),
`gcc -O2` stays kept. `python tools/dev_touching.py --base 76f2179e`:
83 files selected, 2424 passed, 3 skipped.

Mutation table:

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| glued `-j`'s make-like binary check | drop `binary in _MAKE_LIKE_BINARIES`, always `True` | `test_a_glued_j_keeps_its_digits_only_on_a_make_like_tool.py` | 2 failed / 6 |
| `_flag_argument`'s `if equals:` split | drop the branch, fall through to the plain-glued fallback | `test_a_single_dash_flag_glued_to_equals_goes_through_the_numeric_rule.py` | 2 failed / 4 |

Live probe at `1a498516`: `curl -j123456` and `acme-gen -j123456` ->
`-j<dropped>`; `make -j8`, `ninja -j12`, `make -j 8`, `make -l 4`,
`gcc -O2`, `gcc -g3` keep their values; `curl -O2` -> `-O<dropped>`
(curl is not a compiler driver).

Deviation: verifier on `1a498516` found a fourth glued form the audit
missed - `-X=value` (`-j=123456`), too narrow for `_NAMED_FLAG`'s
lookahead, fell to the plain-glued fallback whose `_value` call got
the literal `=value` and mapped it unsplit. `_flag_argument` now
splits at the first `=` for any short flag before that fallback,
closing UX-1089's audit gap here.
