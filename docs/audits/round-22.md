# Audit round 22: the viewer learns what it is looking at

Run on 2026-08-21, same retained environment as rounds 10-21. Three
inputs: the sibling's landing of the entire viewer axis (UX-193..197
plus two packaging follow-ups), the user's four field observations
from running it, and an external review of the shipped viewer —
evaluated claim by claim rather than adopted on trust.

## The landing, verified — all five hold

The review re-ran six mutations (allowlist fall-through, hard-coded
dispatch list, origin-check deletion, ticker-to-stdout twice, the
trend filter) — all red; drove `--perfetto`'s exit 7 and the export
live from an installed venv; confirmed the page is 39,119 bytes to
the byte and the export inline-first discipline holds. The
"broken in every installed shape" commit's three defects (missing
package-data, ASSET_DIR walking the checkout layout, `from tools.`
imports) are fixed with guards — though the guards are checkout-side
proxies, which became a finding below. Suite: **2,465 passed, 0
failed**; lint clean; status table and markers agree.

What verification found that no log carries, filed as **UX-203
(High)**:

- **The band view is unreachable.** It renders only compare payloads;
  `bga view` serves exactly one payload — the analyze document — and
  no CLI path ever produces a compare document for the page. UX-196's
  headline view, the disputed region made one glance, has never been
  seen outside its test harness.
- **The trend plots snapshot size**, not the duration/verdict/hit-rate
  its filing promised — an undeclared narrowing beside a declared
  deviation.
- **CI never runs an installed `bga view`** — the packaging loop
  stops at `--help`, so the exact class 47a3f83 fixed is guarded by
  assertions about configuration rather than by the install-shape
  exercise that found it.

## The field, ground-truthed

- **Perfetto one-click broken in latest Chrome** → mechanism pinned:
  the `window.open` is never synchronous with the user's gesture.
  The `--perfetto` page auto-runs at script load — no activation
  exists, blocked every time (the code's own "Try again" button is
  the tell); the report button opens only after an async fetch,
  inside the activation window only for small fast traces. No
  `?url=` path exists and the server sends no CORS. **UX-198**: open
  first, fetch after; the deep link with a Perfetto-only ACAO header
  as fallback.
- **Minutes of silent analyze inside snapshot** → the analyze
  pipeline has zero progress instrumentation (nothing under
  analyzer/correlate/ingest imports `progress`), and stderr *is*
  still a TTY there — tickers would draw; there are none to draw.
  The hot phases are named, including UX-42's quadratic attribution.
  **UX-200**, with the missing `[all]` extra riding along.
- **Poor navigation** → inventoried: no section ids, no TOC, no
  collapse; one long scroll, Ctrl-F as the nav. **UX-199**, which
  also restores what the export loses (the SQL questions, stripped;
  a blast search box that ships but cannot work from `file://`).

## The external review, synthesized

Its six code claims were verified line by line — **all six
confirmed**, including the two live formatting wrongnesses
(`peak_rss_mb: 512` → "512 B"; a 0-100 `cpu_pct` → "4200.0%") that
prove the schema-vs-name-sniffing split is not theoretical. The
synthesis is Direction 7's second iteration:

- **Adopted**: recursive schema semantics with column objects, item
  shapes and the `verdict_kind` enum (**UX-201**); the BGA overview
  waterfall and the evidence header (**UX-202**); Perfetto as
  investigation with TraceContext as a module (**UX-204**); table
  filters and thresholds (**UX-205**); the two focused graphs and
  nothing DAG-shaped (**UX-206**) — where the review's restraint and
  Direction 7's deferral arrived at the same place independently;
  descriptions-as-popovers folded into UX-201, sourced from the
  schemas rather than viewer prose.
- **Adjusted**: the four-layer architecture is right in direction
  and over-built for a no-toolchain viewer — modules, not layers.
  The P3s (element inspector, comparison workspace) stay deferred.
- **Its blind spot, supplied by the field**: the handoff it rates
  "exactly right" is popup-blocked by construction — UX-198 must
  land before UX-204's context has a transport to ride.

## Standing

The MVP verdict stands. The viewer went from argument to landed axis
in two rounds, and its first field contact produced the same lesson
as every axis before it: the features hold, and the seams are where
the feature meets the world it was built for (a browser's popup
policy, a page's own length, a view no command serves). Priority for
the sibling: **UX-198 and UX-203 first** (the two the user hits
today — the blocked handoff and the unreachable views), then
**UX-199 and UX-200** (the field's remaining pair), then **UX-201**
(the contract wave everything later leans on), then UX-202, with
UX-204/205/206 following its shapes. The external review's verdict
on the foundation — "unusually well positioned; nothing needs to be
thrown away" — matched this audit's own, which is worth recording:
two independent reviewers, one conclusion, and the backlog above is
the difference between them made checkable.
