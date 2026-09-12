# UX-812: the impact guard needs an open analysis row to be green

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-687 (the impact tool and its guard) | **Found by:** round 113, the round gate, red on it a second time | **Serves:** the session closing a round; a guard that reads the tool, not the backlog | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

`test_the_impact_set_is_derived.py`'s
`test_an_open_filing_on_the_same_topic_is_named` asserts
`dev_impact.report("bga/correlate.py")["filings"]` is non-empty — that
some open row sits on the analysis topic. Twice now the round's gate
reddened on it the moment the round closed the last analysis row:

```text
$ make test        # round 112, after UX-739 and UX-808 closed; round 113, after UX-809
FAILED tests/unit/test_the_impact_set_is_derived.py::TestTheSetNamesWhatTheChangeReaches::test_an_open_filing_on_the_same_topic_is_named
E   AssertionError: no open row on the module's topic
```

Round 112 filed `UX-809` (owed anyway) to turn it green; round 113 had
no analysis row to owe. The guard reads the backlog's state, not the
tool's derivation: an empty backlog on a topic is not a defect in
`filings_of`.

## Required Fix

The guard reads the tool: on a synthetic index (two open rows, one
analysis, one docs, written to a temp file and `INDEX` pointed at it)
`filings_of("bga/correlate.py")` returns exactly the analysis row; on
the real index, the derived list equals the rows an independent parse
finds on the module's topic — empty when the backlog has none.
Mutations: return every open row regardless of topic (the synthetic
test reds, and the real one whenever another topic has an open row);
return `[]` always (the synthetic test reds).

## Out of Scope

- The tool's topic map (`_topic_of`) — `UX-688`'s area column replaces it.

## Acceptance Test

`python3 -m pytest tests/unit/test_the_impact_set_is_derived.py -q`
green on a backlog with no open analysis row (this round's); the two
mutations red; the gate green without a filing made to feed it.

## Outcome

**Gap measured.** Two gates red on the guard, rounds 112 and 113
(pasted above); the fix in round 112 was a filing, not a guard.

**Close measured.** Two tests replace the one:

```text
$ python3 -m pytest tests/unit/test_the_impact_set_is_derived.py -q
8 passed        # 7 before, the one replaced by two
```

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| `filings_of` returns every open row regardless of topic | `..._the_open_rows_on_the_module_s_topic`, `..._agrees_with_an_independent_parse` (UX-689, docs, is open) | 2 of 8 |
| `filings_of` returns `[]` | `..._the_open_rows_on_the_module_s_topic` | 1 of 8 |

Both reverted; green after each.

**Deviation.** None. Session-side, one commit.
