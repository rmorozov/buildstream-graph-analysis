# UX-449: a skip reason is only checked where the skip happens

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 70, four red CI jobs on a suite that was green locally | **Serves:** the contributor whose new guard skips for a reason nobody declared, who finds out from CI rather than from `make test` | **Topic:** guards

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
