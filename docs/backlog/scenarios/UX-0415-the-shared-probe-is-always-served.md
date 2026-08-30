# UX-415: the shared node probe says `file:` and always measures `http:`

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** UX-402's journey guard | **Serves:** every guard that boots the page in node | **Topic:** guards

## Motivation

`tests/unit/test_a_report_you_can_navigate.py::_PROBE` is the boot
every navigation, chapter and census guard reuses. It takes a
`PROTOCOL` environment variable so a guard can say which shape it is
measuring — an export at `file:` or a served page at `http:` — and it
sets the protocol from it:

```js
globalThis.location = { protocol: protocol.startsWith("http") ? "http:" : "file:",
                        href: "http://127.0.0.1:8000/index.html" };
```

`href` does not follow. Every consumer that reads a *URL* rather than
the protocol therefore measures the served shape whatever `PROTOCOL`
said, and `wireTheHandoff` is exactly such a consumer:

```js
const absolute = new URL(traceUrl(), location.href);
const served = absolute.protocol === "http:" || absolute.protocol === "https:";
```

The gap is invisible on the two committed fixtures, because both
inline their trace as a `data:` URL and `new URL("data:...", href)`
keeps the `data:` protocol whatever the base is. It is not invisible
on a real capture: a trace too large to inline is written as a
*relative path*, `new URL("timeline.json.gz", "http://…")` resolves to
`http:`, and the export takes a branch it can never take in a browser.
Measured on `UX-402`'s journey capture:

```text
Could not load this run
TypeError: Cannot set properties of null (setting 'hidden')
    at wireTheHandoff (…:6034:35)
    at boot (…:6212:27)
```

Line 6034 is `download.parentElement.hidden = false`, on an element the
probe synthesises with no parent. A real browser has a parent there
and never runs that line from an export at all, so **the page is
fine** — the instrument is wrong, in the direction that hides a whole
class of export behaviour from every guard that uses it.

This is `UX-264`'s rule for `dom_shim.mjs` ("every behaviour here is
what a real browser does, measured rather than assumed") applied to the
other half of the harness, which never got it.

## Required Fix

- `href` follows `PROTOCOL`: `file:///…/report.html` when the probe is
  told it is measuring an export, the served URL otherwise.
- Re-run every guard that passes `PROTOCOL="file:"`; any clause that
  moves was measuring the served path under an export's name and is
  the second half of this finding.
- A clause in the probe's own guard asserting the two agree, so they
  cannot drift apart again.

## Out of Scope

- `dom_shim.mjs` itself — its fidelity rule is already written down and
  guarded; this is the probe that wraps it.

## Acceptance Test

- With `PROTOCOL="file:"`, `location.href` starts with `file:`.
- `UX-402`'s empty-population clause runs green through the probe
  rather than needing a browser, and the browser reading agrees.

## Outcome (round 65, 2026-08-30) — 🟢 Done

### The gap, measured

The probe set one of the two halves of a URL from `PROTOCOL` and left
the other on a constant:

```js
globalThis.location = { protocol: protocol.startsWith("http") ? "http:" : "file:",
                        href: "http://127.0.0.1:8000/index.html" };
```

Measured through the new clause, with the old line restored:

```text
AssertionError: a relative trace resolves to
'http://127.0.0.1:8000/timeline.json.gz' under 'file:' - the branch a
reader's browser takes and this harness cannot see
2 failed, 16 passed in 13.70s
```

And on a run whose trace really is a path — `UX-402`'s journey capture,
booted through the probe rather than through Chrome:

```text
AssertionError: Could not load this run
1 passed, 12 deselected, 2 errors in 45.70s
```

### After

```text
tests/unit/test_a_report_you_can_navigate.py  18 passed in 13.40s
tests/unit/test_the_journey_has_an_answer_key.py -k Incremental
                                               3 passed in 45.96s
```

### One boolean, read twice

`protocol` and `href` are now derived from a single `served`, so they
cannot drift:

```js
const served = protocol.startsWith("http");
globalThis.location = {
  protocol: served ? "http:" : "file:",
  href: served ? "http://127.0.0.1:8000/index.html"
               : pathToFileURL(process.env.PAGE).href,
};
```

The clause that keeps them honest is in two parts, because the string
and the resolution are different claims: one reads `location.href`'s
prefix, the other runs `wireTheHandoff`'s own computation
(`new URL(traceUrl(), location.href)`) over the probe's base. Only the
second is what a consumer does, and only the second would have caught
this — an `href` of `http://…` under a `file:` protocol is wrong in a
way a prefix check finds, but the reason it *matters* is the join.

### The second half of the finding is empty, and that is a measurement

The filing asks: re-run every guard that passes `PROTOCOL="file:"`, and
any clause that moves was measuring the served path under an export's
name. Eleven files, 222 clauses:

```text
222 passed in 37.19s
```

**Nothing moved.** Not because the defect was harmless, but because
every one of those guards renders a *committed fixture*, and both
fixtures inline their trace as a `data:` URL — which `new URL()` keeps
whatever the base is. The only reading that could move is one over a
capture too large to inline, and there was exactly one such guard:
`UX-402`'s, which is why it is the one that found this.

### `UX-402` reads the page through the probe now

The filing's acceptance test, delivered: the empty-population clause
boots the shared probe instead of Chrome, and a second clause asserts a
real browser reads the same page identically. The agreement is a guard
rather than a one-off check, because a shim that drifts from the
browser is this same defect one layer down.

### A second site, found on the way

`tests/unit/test_the_shape_before_the_rows.py` carries its own probe
with the same inconsistency (`href: "http://x/"` under any `PROTOCOL`).
No consumer there resolves a URL today — it calls render functions
directly and its `getElementById` returns `null`, so `wireTheHandoff`
exits early — which is precisely why it would have been the next one to
bite. Fixed in the same commit and recorded rather than left.

### Mutations verified red and reverted (2)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| A1 | `href` back to the served constant | `test_the_url_agrees_with_the_protocol[file:]` and `test_a_relative_trace_resolves_to_that_protocol[file:]`; 2 failed, 16 passed |
| A2 | the same, against a real path-shaped trace | `UX-402`'s `exported` fixture, on `Could not load this run`; 1 passed, 2 errors |

A2 is the one that matters: A1 proves the strings agree, A2 proves the
page boots. The mutation is the same edit both times and the two
failures are different, which is the distinction this item is about.

### Deviation from the Required Fix

- **None** on the three bullets. The second — "any clause that moves
  was measuring the served path under an export's name" — returned an
  empty set, and the reason is written above rather than reported as a
  clean bill of health.
