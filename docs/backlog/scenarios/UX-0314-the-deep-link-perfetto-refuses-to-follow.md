# UX-314: the deep link Perfetto refuses to follow

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-198 (the link), UX-299 (what made it load-bearing) | **Serves:** R1 | **Topic:** viewer

## Motivation

Reported from a real local run of the previous round's `bga`:
*"i am again see this problem in ui.perfetto.dev console and no
capture handed over to it"*, naming `connect-src`.

The cause is not this server's headers. A `?url=` deep link makes
**ui.perfetto.dev fetch the trace itself**, so the request is
governed by ui.perfetto.dev's own Content-Security-Policy. Our
`Access-Control-Allow-Origin` grant (`UX-198`, `UX-265`) is
necessary and *not sufficient*: when `connect-src` refuses, the
request never leaves the browser and there is nothing for CORS to
answer.

Read from Perfetto's source rather than guessed — the procedure
`UX-298` established for a fact that lives in someone else's
repository — `ui/src/frontend/index.ts`,
`setupContentSecurityPolicy()`:

```text
'connect-src': ['self', 'ws://127.0.0.1:8037',
                'http://localhost:8080', 'https:', 'blob:', 'data:']
  .concat(['http://127.0.0.1:9001', 'ws://127.0.0.1:9001',
           'ws://127.0.0.1:9167'])
```

Over plain `http:` exactly **two** origins are fetchable. `bga
view` binds `127.0.0.1` on an **ephemeral** port, which is never
one of them — so the deep link has never worked in served mode.
Below `UX-299`'s 4 MiB threshold the button still works, because
`postMessage` is governed by no CSP; above it the deep link is the
*only* transport, so a big trace failed silently. That is the
reported symptom exactly.

`127.0.0.1:8080` is refused where `localhost:8080` is allowed —
CSP matches the host **name**, not the address it resolves to — so
even `--port 8080` failed, because the server names itself by
address.

Two guards were green throughout. `UX-198`'s asserted "a server is
behind it, therefore show the link", which is the rule that
produced the bug; `UX-299`'s pinned `location` to
`127.0.0.1:8000` and required the over-threshold path to navigate
to the deep link anyway. Both were written from this side of the
boundary, and neither could see the policy on the other side.

## Required Fix

Perfetto's rule becomes code with its provenance attached, and
nothing offers a transport that rule refuses: the deep link is
shown only where it can be followed, and over the threshold on a
refused origin the page says so and names the ways out instead of
navigating a tab onto a refusal. `bga view --port 8080` spells its
own URL the way the policy requires, so there is a working
one-click handoff at any size, and a default run says at startup
that it is not one. The trace is downloadable from the page for
Perfetto's own drag-and-drop, which no policy refuses.

## Out of Scope

- The `rpc_port` escape hatch. `cspAllowAnyWebsocketPort` is
  `defaultValue: false`, so a link built on it fails for every
  reader who has not gone and turned it on. Named in the code,
  relied on nowhere.
- Serving over `https:`. That would make any port fetchable, and it
  buys a certificate to trust, a key to store and a warning
  interstitial to explain — for a viewer whose whole premise is that
  it is a local process you stop with Ctrl-C.
- `127.0.0.1:9001` as a recommendation: fetchable, but it is
  `trace_processor_shell --httpd`'s port and Perfetto probes it at
  startup expecting an RPC endpoint.

## Acceptance Test

The deep link appears for `localhost:8080`, `127.0.0.1:9001` and
any `https:` origin, and not for `127.0.0.1:8080`, `127.0.0.1:8000`,
an ephemeral port, or an export; over the threshold on a refused
origin nothing is navigated, no trace is posted or fetched, the tab
is closed and the status names both ways out; `landing_url(8080)`
is spelled `localhost` and the Python and JavaScript halves agree
about every port; a default run warns at startup. Mutation:
restoring "served, therefore shown" reddens.

## Outcome

🟢 **Done.** The rule that decides the handoff now lives in the
code that depends on it, quoted from the file it came from.

**Falsification.** Eight mutations against the committed tree:

```text
P1  served implies fetchable (the bug as it shipped)   3 guards red
P2  the host spelling is ignored                       1 red
P3  8080 is named by address again                     3 red
P4  navigate to a link CSP will refuse                 1 red
P5  the save-it-yourself route disappears              1 red
P6  the server stops saying the handoff is limited     1 red
P7  the rule stops saying where it was read from       1 red
P8  the message stops naming the way out               1 red
```

P4 is the one worth naming. It passed on the first run — the
over-threshold branch was the whole bug and nothing covered it,
because `UX-299`'s guard was standing on a refused origin while
asserting the navigation happened. Parametrizing that harness by
origin is what made P4 discriminate, and the clause it added is
the field failure written down.

**Not verified against the live site.** `ui.perfetto.dev` and
`get.perfetto.dev` are both refused by this environment's network
policy, so the fix is argued from Perfetto's source and guarded
against it, not confirmed in a browser against the real page. The
reporter's own run is the only end-to-end evidence either way, and
it is evidence for the diagnosis rather than for the repair.
