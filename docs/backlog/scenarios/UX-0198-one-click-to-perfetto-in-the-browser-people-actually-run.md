# UX-198: one click to Perfetto, in the browser people actually run

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-194 (the handoff this repairs)

## Motivation

Field report: *"transition to perfetto works bad in latest chrome, I
was not able to open my traces in one click."* Round 22 pinned the
mechanism — the `window.open` is **never synchronous with the user's
gesture**:

- The `--perfetto` landing page auto-runs `go()` at script load
  (`perfetto.html:43`) — no user activation exists, so
  default-settings Chrome blocks the popup **every time**; the "Try
  again" button in the code is the tell.
- The report page's button `await`s `handOff(traceUrl())` — a fetch
  plus `arrayBuffer` — and only then opens the tab
  (`app.js:306-314`, `perfetto.js:49`). Inside Chrome's transient
  activation window for a 25 KB local trace; blocked for a multi-MB
  trace, a slow disk, or the export's base64 decode.

The server sends no CORS headers and no `?url=` path exists, so the
documented deep-link alternative is currently impossible too.

## Required Fix

1. **Open first, fetch after**: the click handler calls
   `window.open` synchronously, then fetches, then posts when the
   PONG and the bytes are both in hand. The `--perfetto` page stops
   auto-running: it renders one large button and the same
   synchronous-open handler (auto-attempt may remain as best-effort
   after the first user gesture, never instead of it).
2. **The `?url=` belt to the braces**: the server sends
   `Access-Control-Allow-Origin: https://ui.perfetto.dev` on the
   trace blob only, and the page offers
   `ui.perfetto.dev/#!/?url=http://127.0.0.1:<port>/…` as the
   fallback link — a plain `<a>`, immune to popup policy. Not for
   the export (no server there; postMessage stays its path).
3. A visible "nothing opened? click here" line under the button in
   both modes, because popup policy will change again.

## Out of Scope

- The investigation-context payloads (UX-204 — they ride on this
  transport once it works).

## Acceptance Test

The Node harness gains a gesture model (activation flag consumed by
async gaps): the handler's `window.open` fires while activation
holds, with the fetch resolved after — mutation: restoring
open-after-await reddens it. The `--perfetto` page performs no
`window.open` before a click event (asserted). The trace endpoint
answers an `Origin: https://ui.perfetto.dev` request with the ACAO
header and refuses others (both asserted); the fallback link renders
in served mode and is absent from the export.
