# UX-1085: the residue scan misses non-ASCII identifiers

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1069 | **Found by:** the owner's #298 re-review at 156d7436, finding 2 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

`bundle._WORD = re.compile(r"[a-z0-9]+")`, so `_residue_hits()` cannot
match a recorded original such as `café` in a kept string - a
regression from the previous escaped-string alternation. A residue
scan that silently skips non-ASCII originals approves bundles it
should refuse.

## Required Fix

Replace `_WORD`'s matching/indexing with a Unicode-aware strategy in
`bga/bundle.py` (matching on word characters generally, not the ASCII
class) so a non-ASCII original is indexed and matched the same way an
ASCII one is, including at the streamed-chunk boundary UX-1069's
chunked residue read introduced.

## Out of Scope

The map's write ordering (UX-1086); the numeric-credential default
(UX-1084).

## Acceptance Test

`tests/unit/test_the_residue_scan_matches_non_ascii_identifiers.py`:
a recorded original such as `café` kept in a member (1) wholly within
one residue chunk and (2) split across a chunk boundary each trip
`_residue_hits()`. Mutation: revert `_WORD` to `[a-z0-9]+`, and both
cases pass through clean.

## Outcome

Gap measured: `_WORD = re.compile(r"[a-z0-9]+")` cannot match `café`
or `иванов`; `test_the_residue_scan_matches_non_ascii_identifiers.py`
reddened all four non-ASCII cases against the pre-fix code.

Close measured: `_WORD` now `re.compile(r"[^\W_]+", re.UNICODE)`
(word chars, `_` excluded so it stays a separator alongside `-`/`.`);
`_residue_index` and `residue()` fold through a shared `_fold()`
(`casefold` then `unicodedata.normalize("NFC", ...)`), applied to the
carry joined with the new decoded text before each `_residue_hits`
call, so a base character held from one chunk composes with a
combining mark starting the next; `reach` is measured on the already-
normalized `variants` keys. All 9 new cases pass, plus
`test_the_residue_scan_is_linear.py` (6 cases) and
`test_an_anonymized_bundle_trips_on_a_leftover_name.py`/
`test_the_anonymized_export_runs_in_bounded_memory.py` (43 cases)
unaffected. `dev_touching.py --base e5075375`: 1925 passed, 3 skipped.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| `_WORD` reverted to `[a-z0-9]+` | 4 non-ASCII cases (café/иванов, whole-chunk and split) | 4 failed / 9 |
| carry made byte-counted (`block.decode(...)` per chunk, no incremental decoder) | both split-boundary cases (café, иванов) | 2 failed / 9 |
| `_fold()` dropped NFC-normalization (casefold only) | 4 NFC/NFD cross-form cases | 4 failed / 9 |

Deviation: a name written with no separator (張偉李娜, CJK, no
whitespace) still does not trip - the same limitation as two ASCII
names concatenated with no separator, pre-existing and out of this
task's scope.

