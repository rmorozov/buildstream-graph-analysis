# UX-521: the Perfetto handoff goes quiet, and cannot tell working from refused

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-299` (the size threshold and the deep link), `UX-314` (the fetchability check), `UX-282` (the fallback beside the button) | **Found by:** round 77, field report — *"bga view definitely misses some progress when open timeline in perfetto is clicked on big captures — I waited several minutes before it opened"* | **Serves:** the reader of a big capture, staring at two tabs that both say nothing | **Topic:** viewer

## Motivation

`bga view` copies a trace through the page up to a published threshold
and hands the URL to Perfetto above it:

```text
tools/bga_view.py:635   TRACE_BUDGET_B = 4 * 1024 * 1024
```

A big capture is over 4 MiB, so it takes the deep-link path. That path
announces once, in `bga/viewer/app.js`, and returns:

```javascript
tab.location = deepLink(absolute.href);
announceHandoff(status,
  `${(size / 1048576).toFixed(1)} MiB — over the ` +
  `${(inlineMax / 1048576).toFixed(0)} MiB this page will copy, ` +
  `so Perfetto is fetching it from here directly.`);
return;
```

After that sentence the page is finished. Perfetto then fetches the
trace from this server and parses it, and on a big capture that is
minutes — during which the `bga view` tab's last word is a sentence
written at t=0 and the Perfetto tab is blank. The field report is
exactly that wait.

**The sharper half is that the page cannot tell two different situations
apart.** "Perfetto is fetching and parsing, wait" and "Perfetto never
fetched anything" produce the identical screen — one sentence and a
blank tab — and they need opposite actions from the reader. `UX-314`
already checks *whether Perfetto is allowed* to fetch the origin before
taking this path, so the refusal it can predict is handled; what is not
handled is the fetch that was allowed and did not happen, or happened
and is still parsing.

**The server has the fact the page is missing.** The trace is served by
`bga view`'s own handler (`tools/bga_view.py:do_GET`, `TRACE_NAME`), so
this process sees Perfetto's `GET` arrive and complete. Nothing in the
page asks it.

For completeness, the under-threshold path has a different silence with
the same cause: `await handOff(url, …)` fetches the whole trace into the
page before `postTrace` runs, and the status line still reads *"opening
ui.perfetto.dev — sent tab to tab, not uploaded…"* for the whole fetch.
Its `postMessage` handshake is bounded (`TIMEOUT_MS = 20000`); the fetch
before it is not.

## Required Fix

- The deep-link path says what is about to happen before it happens, in
  the units the reader has: the trace's size is already in hand from the
  `HEAD`, so the sentence can carry it and say that a trace this size
  takes minutes to open and the tab stays blank until it does.
- The page distinguishes *fetched* from *not fetched*, from the server's
  own view of the request rather than from a timer. A wait that is
  progressing and a wait that will never end are different sentences.
- Whatever it becomes, it obeys `UX-334`: no console noise, and no
  polling left running after the answer arrives or the reader leaves.

## Out of Scope

- Perfetto's own parse time, which this repository does not control and
  must not pretend to predict. Saying "still fetching" and "fetched,
  Perfetto is parsing" is honest; a percentage of the parse is not.
- Raising `TRACE_BUDGET_B`. `UX-299` set it against a measurement and
  copying more bytes through the page is the opposite of this fix.
- The refusal path `UX-314` already handles, which prints its own
  sentence and closes the tab.

## Acceptance Test

A served capture over the threshold, opened with the timeline button,
with the `bga view` tab's status line captured at t=0 and after the
server has finished serving the trace — two different sentences, both
pasted. Mutation: make the server's view of the fetch always report
"not yet" — the second sentence must not appear.

## Outcome (round 78, 2026-09-02) — 🟢 Done

### The gap, measured

```text
$ git show HEAD:tools/bga_view.py | grep -c 'trace-status'   ->  0
$ git show HEAD:bga/viewer/app.js | grep -c 'watchTheFetch'  ->  0
$ git show HEAD:bga/viewer/app.js | sed -n '/deepLink/,/return/p'
            tab.location = deepLink(absolute.href);
            announceHandoff(status, `... MiB — over the ... this page will ` +
              `copy, so Perfetto is fetching it from here directly.`);
            return;
```

Nothing asks and nothing answers. That `return` is the page's last
word, the same whether Perfetto is parsing gigabytes or never asked.

### After

Through the real `wireTheHandoff` against a real `bga view` (port 8080
for `UX-314`'s CSP, `TRACE_BUDGET_B` lowered to 0 so a fixture-sized
trace takes the deep-link path — `UX-451`'s technique), Node making
Perfetto's own `GET`:

```text
t=0            0.0 MiB — over the 0 MiB this page will copy, so Perfetto is
               fetching it from here directly. A trace this size takes
               minutes, and its tab stays blank until it has.
status         {"fetches": 0, "bytes": 0}
Perfetto GET   785 bytes
after the GET  0.0 MiB — Perfetto has fetched the whole trace from here. It
               is parsing now; the tab fills in when it finishes.
```

Two sentences, the second the server's own view of the request rather
than a timer. `0.0 MiB` is the 785-byte fixture through `UX-299`'s
formatter. With the Acceptance Test's own mutation — the server always
answering `fetches: 0` — the second never appears. The export grew
**+1,065 B, all page** (293,783 → 294,848 B, both fixtures' embedded
data byte-identical); `macro_micro`'s bound is restated with that
measurement in `test_the_report_you_can_attach.py`.

### Mutations verified red and reverted (16)

| # | mutation | red |
|---|---|---|
| M1 | a `HEAD` counts as a fetch | 1 |
| M2 | the server always says not-yet | 3 |
| M3 | `bytes` accumulates instead of naming the trace | 1 |
| M4 | the count is one process-wide global | 3 |
| M5 | the answer declares a `schema` | 5 |
| M6 | the page never asks | 7 |
| M7 | it asks on every over-threshold transport | 5 |
| M8 | it keeps asking after the answer | 2 |
| M9 | the asking has no ceiling | 1 |
| M10 | a dead server is retried forever | 1 |
| M11 | it asks at a rate of its own | 1 |
| M12 | the t=0 sentence drops the wait | 1 |
| M13 | it predicts Perfetto's parse (`40% done`) | 1 |
| M14 | it asks whichever transport wins | 6 |
| M15 | it says fetched without reading the answer | 3 |
| M16 | the two route-name constants drift | 7 |

All 18 clauses are reddened by at least one. M7 was written for
`..copied_trace_never_asks` and did not discriminate it — it sits
inside the over-threshold branch, which that class never reaches. M14
does; M7 stays because it discriminates the refused-origin clause.

### Deviation from the Required Fix

None. The under-threshold silence the Motivation notes "for
completeness" is left alone: bounded by `TRACE_BUDGET_B` and
`TIMEOUT_MS`, it is not the minutes-long blank filed here.
`trace-status.json` declares no schema and is undocumented in
`docs/guides/cli.md` on purpose — a liveness fact, not a contract.

```text
=========== 5902 passed, 27 skipped, 1 warning in 442.92s (0:07:22) ============
ruff check bga/ tools/ tests/ .claude/hooks/   ->  All checks passed!
```
