# UX-1089: a glued -j keeps its digits only on a make-like tool

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1084 | **Found by:** the owner's #298 re-review at 76f2179e, finding 2 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

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

