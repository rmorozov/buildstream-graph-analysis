# UX-449: a skip reason is only checked where the skip happens

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 70, four red CI jobs on a suite that was green locally | **Serves:** the contributor whose new guard skips for a reason nobody declared, who finds out from CI rather than from `make test` | **Topic:** guards

## Motivation

The skip census (`tests/conftest.py`) is the instrument that stops a
guard file going quiet: it counts skips by reason and fails the session
on a reason `KNOWN_SKIP_REASONS` has never declared. It is a **runtime**
instrument, and that is its blind spot — it can only see a skip that
actually happened.

`UX-434` added two clauses gated on Perfetto's optional
`trace_processor_shell`, and coined its own wording for "the tool is
absent" instead of asking `tests/trace_processor.py`, which `UX-321`
built to be the one gate asked in one place. On the machine that wrote
them the binary is installed, so the clauses **ran**, the census never
saw the reason, and `make test` was green:

```text
5388 passed, 26 skipped, 1 warning in 266.97s
```

Every CI runner has no such binary, so the clauses skipped, and the
census failed all four interpreters — after every test had passed:

```text
5260 passed, 144 skipped in 334.53s (0:05:34)
================================= skip census ==================================
2 test(s) skipped for a reason this suite has never declared: 'no
trace_processor_shell (tools/dev_perfetto_queries.py --fetch)'. …
make: *** [Makefile:51: test] Error 1
```

This is the second time. `tests/conftest.py:116` records the first, in
round 50: `UX-330`'s two gzipped-raw-log clauses "invented their own
skip reason, so they skipped silently in CI and passed vacuously here,
where the capture happens to exist." Same shape, same direction, five
rounds apart — the census catches the coined reason only on a machine
that lacks the dependency, which is never the machine that writes it.

## Required Fix

A guard that reads the **declared** reason rather than waiting for it to
be exercised: scan the suite's `pytest.mark.skipif(..., reason="…")` and
`pytest.skip("…")` literals and assert every one is a key of
`KNOWN_SKIP_REASONS`. It fails in `make test-small` on the author's own
machine, whatever that machine happens to have installed.

Two things it must handle rather than ignore, because a scan that
silently drops them is a guard that passes for the wrong reason:

- a reason built at runtime (an f-string, a variable, a helper's
  `REASON`) has no literal to read — the guard must **count** what it
  could not resolve and assert that count against a measured baseline,
  so a new unresolvable reason is a change rather than a silence;
- `tests/unit/test_the_order_the_page_has.py` passes deliberately fake
  reasons (`"because I said so"`, `"x"`, `"gone"`) to
  `census_complaints` directly. Those are arguments to a function, not
  skips — the guard reads skip call sites, so they are already out of
  its population; confirm that rather than adding an exclusion list.

## Out of Scope

- Changing the census itself: the runtime count stays, and this is a
  second reading of the same fact, not a replacement.
- Making `trace_processor_shell` a dependency, or fetching it in CI
  (`UX-312` decided against both, for reasons recorded there).

## Acceptance Test

With the guard in place, coin a fresh reason in any test file and run
the small tier on a machine where that skip does **not** fire; the guard
names the file and the undeclared string. Paste both the reddened run
and the count of reasons the scan could not resolve statically.

## Outcome (round 71, 2026-08-31) — 🟢 Done

### What the scan found on its first run

Eighteen skip reasons written into the suite that `KNOWN_SKIP_REASONS`
had never heard of, on a tree where `make test` was green:

```text
resolved reasons: 41  call sites: 165
UNDECLARED      : 25
    'bst not on PATH'                       tests/unit/test_doctor.py:176
    'jq not installed'                      tests/unit/test_compare.py:185
    'no C compiler on PATH'                 tests/unit/test_process_spine.py:37
    'node is required'                      tests/unit/test_a_task_uid_is_not_a_label.py:42
    …
```

Seven of the twenty-five were a **second wording for a family already
declared** — three spellings of "bst is absent", three of "no C
compiler", two of "jq", two of "node". That is `UX-321`'s defect at
scale, and it is what splits one census family into several. Those were
unified into the canonical wording (18 call sites); the remaining
eighteen reasons were declared.

### The second blind spot, which this item did not know about

The Motivation names one: a gate for a tool the author happens to have.
There is another, and it is larger. The census hook counts
`report.when == "setup"`, and a `pytest.skip()` raised in a **test
body** reports at `call`. Measured on a two-test probe where both tests
skipped:

```text
CENSUS SAW: {'a setup-phase reason': 1}
```

So the census has never counted an in-body skip, on any machine, ever.
Of the eighteen undeclared reasons, **sixteen** were that shape. The
suite has 42 such call sites against 123 marker sites.

This is why the static scan is not a duplicate of the census but a
reading of something the census structurally cannot see, and
`test_the_census_cannot_see_an_in_body_skip` asserts it so that the
argument stops being true loudly rather than quietly.

### The acceptance test, run

Coin a fresh reason where the skip does **not** fire — `node` is
installed on this machine:

```console
$ sed -i 's|reason="node is not installed")|reason="node, which this machine happens to have")|' \
      tests/unit/test_the_graph_shape_query_answers.py

$ python3 -m pytest tests/unit/test_the_graph_shape_query_answers.py -q
5 passed, 2 skipped in 0.27s          # the census: silent

$ python3 -m pytest tests/unit/test_every_skip_reason_is_declared.py -q
E  'node, which this machine happens to have' first at
   tests/unit/test_the_graph_shape_query_answers.py:52
1 failed, 5 passed
```

The two halves of that are the item in one screen: the runtime
instrument passes, the static one names the file and the string.

### Coverage, and what is left unread

| | before the item | after |
|---|---|---|
| call sites read | — | 195 |
| reasons resolved | 41 | 38 (fewer, because seven families merged) |
| unresolvable | 85 | 55 |

The drop from 85 came from following two things the first cut did not:
module-level constants, and one hop of `from <repo module> import
NAME`. Both matter more than the count suggests — the shared gate
(`NO_BROWSER` in `tests/browser.py`) is the pattern `UX-321`
*recommends*, so a scan that could not follow it would have been blind
exactly where the repository tells people to write. Resolving constants
found two more undeclared reasons on its own, both duplicate families.

The remaining 55 are asserted as a **ceiling**: f-strings (17), a
constant this scan will not chase further (33), an attribute (4), a
computed concatenation (1).

### A hole the mutations found in the guard itself

`N4` was written as `import pytest as _p`, and the scan did not see it:
`_dotted` produced `("_p", "mark", "skip")`. An aliased import silenced
the whole file — the same class of defect one level up from the one
this item exists to catch. Found only because the mutation's debris was
left in the tree and the next full run tripped the *census* on it.
`_aliases()` resolves the import now, and `N6` is that case.

The first cut of `test_the_scan_knows_the_forms_the_suite_uses` also
searched the text and matched the `pytest.mark.skip(` in **its own
docstring** — fixing guide §5, committed inside the guard written to
enforce §5. Recorded rather than tidied away, and the clause parses now.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| N1 | coin a fresh reason where the skip does not fire (this item's own acceptance) | **`test_every_declared_skip_reason_is_known`** — the census stays green |
| N2 | scan by regular expression instead of by parse | **`test_the_scan_reads_calls_and_not_text`** (+ the known-reason clause, on the decoys it picks up) |
| N3 | stop following `from ... import` constants | **`test_the_unreadable_reasons_are_counted_not_ignored`** |
| N4 | a `pytest.mark.skip` appears in the suite | **`test_the_scan_knows_the_forms_the_suite_uses`** |
| N5 | census counts every phase, not just `setup` | **`test_the_census_cannot_see_an_in_body_skip`** |
| N6 | a skip behind `import pytest as _p` | **`test_the_scan_knows_the_forms_the_suite_uses`** |

### Deviation from the Required Fix

One, widening. The bullet asks for a guard; making its assertion true
needed the twenty-five reasons reconciled — seven unified into existing
families, eighteen declared at 0. All eighteen are 0 because none fired
in `make test` here or in round 70's CI (144 skips, every one declared);
a count that turns out wrong in CI is the census doing its job and is a
measurement to correct, not a reason to leave them undeclared.

Both Out of Scope bullets held: the runtime census is unchanged, and
`trace_processor_shell` is still neither a dependency nor fetched.

### The suite

```console
$ make lint
All checks passed!

$ make test
5451 passed, 28 skipped, 1 warning in 266.84s (0:04:26)
```

New file 3.2s, medium by measurement (`tests/tiers.py` updated).
