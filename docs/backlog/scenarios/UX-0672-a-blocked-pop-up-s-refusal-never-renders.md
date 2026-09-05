# UX-672: a blocked pop-up's refusal never renders

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-451 (the refusal leaves the column), UX-198 | **Serves:** anyone whose browser blocks the Perfetto tab | **Topic:** viewer | **Shape:** judgement

## Motivation

```text
Open timeline in Perfetto, pop-up blocked
  rail after 6 s     "opening ui.perfetto.dev — sent tab to tab, not uploaded…"
  the error's "direct link below"   a[href="#"], hidden
  "did not open"     absent from body.innerText
  console            uncaught at app.js:455 → perfetto.js:143
```

The handoff has a refusal sentence and a direct link for exactly this
case, and neither reaches the page; the reader sees "opening" forever
and the console sees an exception — the class `UX-334`'s guard holds
for the served page, on a path the guard's fixtures never take.

## Required Fix

The blocked case renders its sentence and a real `href` to the
trace, the exception is caught where the pop-up is opened, and the
console guard's fixture includes a blocked `window.open`.

## Out of Scope

- The handoff's happy path — verified working.

## Acceptance Test

With `window.open` stubbed to return `null`: the refusal sentence and
a non-`#` link render, zero console errors. Mutation: rethrow — red.

## Outcome

**The gap, measured.**
`const tab = served ? openTab({}) : null;` sat before the `try {` at
`app.js:456`. `openTab` (`perfetto.js:139-149`) throws synchronously
when `window.open` returns `null`, so a blocked pop-up threw past the
click handler's only `catch` (`app.js:505-511`) — the sentence set at
line 448 ("opening ui.perfetto.dev…") was the handler's last write.
`tests/unit/test_the_handoff_says_whether_perfetto_fetched.py`'s
harness (`_HARNESS`) always stubbed `window.open` to return a tab; no
fixture ever exercised the `null` branch.

**The close, measured.** `let tab = null;` now precedes the `try`, and
the assignment moved to the first line inside it. `_click` gained an
`open_returns` kwarg (default `True`, unchanged callers); with it
`False`, `TestABlockedPopUpAnnouncesRatherThanCrashing` (3 clauses)
passes:

```text
tests/unit/test_the_handoff_says_whether_perfetto_fetched.py::TestABlockedPopUpAnnouncesRatherThanCrashing
  test_the_refusal_sentence_renders PASSED
  test_a_real_link_still_renders_beside_the_refusal PASSED
  test_it_never_asks_the_server PASSED
21 passed in 5.59s (whole file)
```

The fallback link's `href`/`hidden` are set at `wireTheHandoff` time,
independent of the click, so "a real href" was already true once the
handler stopped crashing before reaching it.

**Mutations.**

| mutation | reddened | count |
|---|---|---|
| move `tab = served ? openTab({}) : null;` back outside the `try` | all 3 `TestABlockedPopUpAnnouncesRatherThanCrashing` clauses, via `_click`'s own `returncode == 0` assert on the now-uncaught `perfetto.js:143` throw | 3 failed, 18 passed |

**Deviation.** None from the Required Fix. Export bytes for
`tests/fixtures/golden/mixed_task_kinds`: 428,054 → 428,070 (+16,
the moved comment). `tests/unit/test_the_report_you_can_attach.py`
was left untouched per instruction; run unmodified, it still passed
(31/31) — its byte assertions are not keyed to this exact fixture, so
the +16 did not need reconciling here.
