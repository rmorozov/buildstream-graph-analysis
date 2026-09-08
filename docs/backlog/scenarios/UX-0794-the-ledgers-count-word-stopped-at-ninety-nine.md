# UX-794: the ledger's count word stopped at ninety-nine

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-666 (the derived count sentence), UX-752 (the guard reads the writer's own words) | **Found by:** round 109, appending the hundredth row | **Serves:** the round that appends a row and gets a traceback for a ledger sentence | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

```console
$ python3 tools/dev_track_cost.py --ledger <transcript> --round 109 ... --append
  File "tools/dev_track_cost.py", line 383, in count_word
    return _TENS[tens] + (f"-{_UNITS[unit]}" if unit else "")
IndexError: tuple index out of range
$ grep -c "^| " docs/audits/agent-runs.md
100
```

`count_word` built tens and units only; the guard's table
(`test_a_counted_figure_is_derived.py`) spanned `range(1, 100)` and the
sentence regex allowed no space, so nothing said where the word ended
until the row that needed it.

## Required Fix

`count_word` in `tools/dev_track_cost.py` builds hundreds (`one hundred
and three`), refuses 1000 and above by name; the count-sentence regex
admits the space; the guard's table spans `range(1, 1000)`.

## Out of Scope

- A thousandth row — `ValueError` names the stop; the ledger is at 103.

## Acceptance Test

`tests/unit/test_a_run_is_priced.py::test_the_word_is_built_not_tabled`
reds under the mutation `if n >= 100:` → `if False:`; `--append` on a
ledger of 99 rows writes `one hundred`.

## Outcome

**Gap measured.** The traceback above, on the hundredth row; two
appends lost before the cause was read.

**Close measured.** Four appends: `one hundred` … `one hundred and
three`; `test_a_run_is_priced.py -k word` → 1 passed;
`test_a_counted_figure_is_derived.py` reads the new sentence back.

| mutation | reddened |
|---|---|
| `if n >= 100:` → `if False:` | `test_the_word_is_built_not_tabled`: 1 failed |

**Deviation.** Found and fixed by the session mid-round; the guard's
table was a range the writer never crossed — `UX-752`'s "two tables
drift" held for a table and its own limit.
