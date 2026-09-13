# UX-819: the export's Perfetto handoff fetches a quoted data: URI

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-299 (the handoff carries the trace), UX-314 (the fetchable rule) | **Found by:** round 114, walk seed 3 | **Serves:** R1 opening the timeline from an export | **Topic:** viewer | **Area:** bga-viewer | **Shape:** judgement

## Motivation

The export inlines the trace as a JSON string —
`<script type="application/json" id="bga-trace">"data:application/gzip;base64,…"</script>`
(`tools/bga_view.py:1348`) — and `traceUrl()` (`bga/viewer/sections.js:611`)
returns the node's text without parsing it, quotes included. Driven
in real Chrome on seed 3's export, "Open timeline in Perfetto" fetched:

```text
Access to fetch at 'file:///…/%22data:application/gzip;base64,H4sICJo6pW…==%22'
… blocked by CORS policy: Cross origin requests are only supported for
protocol schemes: chrome, chrome-extension, chrome-untrusted, data, http, https
```

`%22` is the JSON quote. `new URL('"data:…"', location.href)` resolves
to a `file:` path, so `UX-314`'s served test says "not served" and the
data: URI is never seen as one.

## Required Fix

`traceUrl()` parses the node's JSON when the node exists, so an export
yields a bare `data:` URI and the handoff's own rule decides what to do
with it. Guard on the export: the shared node probe reads `traceUrl()`
and asserts it starts with `data:`; mutation: drop the parse — red.

## Decomposition

Input classes the guard covers: an export (the node holds a data: URI),
a served page (no node, the `timeline.json.gz` default), and an export
of a run with no trace; the journey it extends is the Perfetto handoff
in `test_the_journey_has_an_answer_key.py` — export → open timeline —
with the URL's shape as its first step.

## Out of Scope

- Whether Perfetto can open a data: URI from a file: page — `UX-314`'s
  rule decides that once the URL is one.

## Acceptance Test

On seed 3's export, `traceUrl()` returns a string starting `data:`;
the guard green; the mutation red.

## Outcome

**Gap measured.** Walk seed 3, real Chrome, "Open timeline in Perfetto"
on the export (`docs/audits/walk-seed-3.md`):

```text
Access to fetch at 'file:///…/%22data:application/gzip;base64,H4sICJo6pW…==%22'
… blocked by CORS policy
$ sed -n 621,624p bga/viewer/sections.js          # before
export function traceUrl() {
  const node = document.getElementById("bga-trace");
  return node ? node.textContent.trim() : "timeline.json.gz";
```

**Close measured.** `traceUrl()` parses the node's JSON when it is
JSON and passes a bare path through; the guard is a node harness over
the three input classes:

```text
$ python3 -m pytest -q -p no:xdist tests/unit/test_the_perfetto_handoff.py -k TheExportsTraceIsABareUri
3 passed, 62 deselected in 0.42s
  export node  '"data:application/gzip;base64,H4sIAAAAAAAAA"' → 'data:application/gzip;base64,H4sIAAAAAAAAA'
  bare path    'trace/timeline.json.gz' → unchanged
  no node      → 'timeline.json.gz'
$ npx --yes --package eslint@9 --package globals@17 -- eslint bga/viewer
(clean)
```

| mutation | result |
|---|---|
| the parse dropped (`JSON.parse(text)` with its value discarded) | 1 failed, 2 passed — `'"data:applic…"' == 'data:applica…'` |

**Deviation.** The click path was not driven in Chrome: the handoff
fetches whatever `traceUrl()` returns, and the harness reads that
return; the CORS line above is the walk's reading of the same call
before the fix.
