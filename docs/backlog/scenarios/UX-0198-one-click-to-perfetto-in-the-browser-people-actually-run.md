# UX-198: one click to Perfetto, in the browser people actually run

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-194 (the handoff this repairs) | **Topic:** viewer | **Area:** bga/viewer

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

---

## What was built

Both halves of the mechanism the filing pinned, confirmed by reading
the code before touching it.

**1. The tab opens before the first `await`.** `handOff` fetched the
trace and awaited `arrayBuffer()` and *then* called `window.open` —
two async gaps after the click that authorised it. A browser grants
transient activation on a gesture and revokes it at the first `await`,
so the open was unauthorised by the time it ran; it survived a 25 KB
file on a warm cache, which is why it shipped.

`openInPerfetto` is split into `openTab` (synchronous) and
`postTrace` (the ping/PONG handshake). `handOff` now opens, then
fetches, then posts when both the bytes and the PONG are in hand, and
closes the tab if the fetch fails rather than leaving an empty
Perfetto open. `handOff` is still `async`, which is fine: everything
before its own first `await` runs synchronously inside the caller's
click handler.

**The `--perfetto` page stops auto-running.** It called `go()` at
script load, so *no* activation had ever existed and the pop-up was
blocked every time — the "Try again" button under it was the tell. It
renders one button now.

**2. The `?url=` belt.** `deepLink()` builds
`ui.perfetto.dev/#!/?url=…`, a plain `<a href>` immune to pop-up
policy, and the server answers `Access-Control-Allow-Origin:
https://ui.perfetto.dev` — **on the trace blob only, and only when the
request's `Origin` is Perfetto's**. Measured across every endpoint:

```text
trace   Origin=perfetto : 200  ACAO=https://ui.perfetto.dev
trace   Origin=evil     : 200  ACAO=None
trace   no Origin       : 200  ACAO=None
report  Origin=perfetto : 200  ACAO=None
schemas Origin=perfetto : 200  ACAO=None
blast   Origin=perfetto : 200  ACAO=None
```

Never `*`, and never on the report or the blast endpoint, which carry
a project's element names and paths. The link is rendered in served
mode and hidden in an export, where the trace is a `data:` URL with no
server behind it.

**3. "Nothing opened?"** on both pages, because pop-up policy will
change again.

Tests: 12 new. The centrepiece is a **gesture model** — an activation
flag that a real browser drops at the first async gap, so `open()`
returns `null` the way a blocked pop-up does. Restoring the old
ordering reddens it; the old harness, where `open` always succeeded,
could not tell the two orderings apart, which is precisely why the bug
shipped green.

Eight mutations, each red — including two over-fixing directions
(never showing the fallback link; a wildcard ACAO).

**A guard of mine that guarded nothing, found by falsifying it.** The
first version of the export check read the exported *file* for the
deep-link string. The href is set by script at runtime, so the static
file never contains it either way — deleting the `served` check left
the guard green. Rewritten to drive the real `wireTheHandoff` under a
DOM shim and assert whether the link is *revealed*, parameterised over
a served URL and a `data:` URL; it now reddens in both directions.

**A pre-existing guard caught a regression in the fix.** Rewording the
blocked-pop-up error dropped `ui.perfetto.dev`, and
`test_a_blocked_popup_is_an_explained_failure` asserts the message
names the manual route out. The message names the direct link *and*
the manual route now, and `openInPerfetto` still returns a rejected
promise rather than throwing, which the same test pinned.

