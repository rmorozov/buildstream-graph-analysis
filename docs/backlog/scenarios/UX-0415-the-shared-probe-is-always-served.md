# UX-415: the shared node probe says `file:` and always measures `http:`

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** UX-402's journey guard | **Serves:** every guard that boots the page in node | **Topic:** guards

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
