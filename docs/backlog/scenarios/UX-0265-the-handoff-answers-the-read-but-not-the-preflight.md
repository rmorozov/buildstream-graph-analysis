# UX-265: the hand-off answers the read but not the pre-flight

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** R1, whenever a timeline is worth opening | **Topic:** viewer

## Motivation

Reported from a real project: *"perfetto handover doesn't work in
latest chrome. on the perfetto side console says about something is
blocked by cors policy no access control allow origin header is present
on the requested resource"*.

`UX-198` built the `?url=` deep link and gave the trace blob a CORS
grant: `Access-Control-Allow-Origin` for Perfetto's origin, on that one
path, and nowhere else. That grant was right and is unchanged. What was
missing is that it only ever answered the **read**:

```text
$ curl -sI -H "Origin: https://ui.perfetto.dev" .../timeline.json.gz
HTTP/1.0 200 OK
Access-Control-Allow-Origin: https://ui.perfetto.dev      <- correct

$ curl -X OPTIONS -H "Origin: https://ui.perfetto.dev" \
       -H "Access-Control-Request-Method: GET" .../timeline.json.gz
HTTP/1.0 501 Unsupported method ('OPTIONS')               <- nothing
```

`BaseHTTPRequestHandler` answers an unimplemented method with `501`,
and a `501` carries no allow header. A browser reports that as the
header being absent from the resource — which is the reported sentence,
word for word.

Nothing about `bga` changed. A **simple** cross-origin `GET` is not
pre-flighted, so for as long as Perfetto's fetch stayed simple the
missing `OPTIONS` never showed. The moment anything makes the read
pre-flight, the hand-off stops. Chrome's Private Network Access is the
documented reason a *public* origin reading a *local* address begins to
pre-flight — `ui.perfetto.dev` is public, this server is `127.0.0.1` —
and it needs no change on either side to start.

## Required Fix

1. Answer the pre-flight, scoped exactly as narrowly as the `GET`
   grant: the trace blob only, Perfetto's origin only, `GET`/`HEAD`
   only. A pre-flight against the report, the schemas or the blast
   endpoint stays refused, and so does one from any other origin.
2. Include `Access-Control-Allow-Private-Network: true`, which is the
   header the public→local transition is granted by name.
3. Echo `Access-Control-Request-Headers` rather than naming a fixed
   list. A fixed list breaks the hand-off again the first time the
   other side attaches a header, which is how this broke.
4. `Vary: Origin` on both responses, so a cache cannot hand Perfetto's
   grant to a page that was refused one.

## Out of Scope

- The `postMessage` path (`UX-194`). It is tab-to-tab and involves no
  fetch, so no CORS, and it is unaffected.
- Widening the grant. The trace is the only thing Perfetto needs; the
  report and the blast endpoint carry this project's element names and
  paths and stay unreadable cross-origin.

## Acceptance Test

A pre-flight from Perfetto's origin against the trace answers `204`
with the allow headers; the same pre-flight from any other origin, and
against any other path, is refused; and a cross-origin read that
pre-flights succeeds in a real browser where it previously failed with
the reported message.

## Outcome

**Fixed.** `do_OPTIONS` answers the pre-flight and refuses everything
outside the one grant.

The end-to-end hand-off could **not** be run here: this sandbox's
network policy denies `ui.perfetto.dev` (`CONNECT tunnel failed,
response 403`), so the real Perfetto page never loaded. What was
measured instead is Chrome's own CORS engine, with the allowed origin
stood in by a second local origin, against two servers differing in
`do_OPTIONS` and nothing else:

```text
                   simple GET              pre-flighted GET
before (501)       ok 200, 415 bytes       FAILED: TypeError: Failed to fetch
after  (204)       ok 200, 415 bytes       ok 200, 415 bytes
```

and the console line Chrome 141 printed against the unfixed server:

```text
Access to fetch at 'http://127.0.0.1:8512/timeline.json.gz' from origin
'http://127.0.0.1:8500' has been blocked by CORS policy: Response to
preflight request doesn't pass access control check: No
'Access-Control-Allow-Origin' header is present on the requested
resource.
```

That is the reported sentence, reproduced. The first column is the
other half of the finding: a simple cross-origin `GET` works in both,
so the read was never the broken part — only the pre-flight was.

**What is measured and what is inferred.** Measured: the server
answered no pre-flight; any pre-flighted read fails with exactly the
reported message; the fix makes both shapes work; the grant stays
scoped. Inferred, and not verifiable from here: that the specific
trigger on the reporter's machine is Private Network Access. Both
origins in the reproduction are local, so no public→local transition
occurs and PNA cannot be exercised. The fix does not depend on which
trigger it is — it answers the pre-flight, grants the private-network
transition, and echoes whatever headers are asked for.

**A gap the reproduction found in the first fix.** The probe attached
its own header and Chrome refused with *"Request header field
x-bga-probe is not allowed by Access-Control-Allow-Headers"* — the
first version of `do_OPTIONS` named no allowed headers at all. A
pre-flight answer that grants no headers is a fix that works only for
the exact request you imagined. Echoing `Access-Control-Request-
Headers` closed it; the origin and path are still the whole grant.

**Six mutations, six reds:** removing `do_OPTIONS`; dropping the
private-network header; dropping the header echo; granting the
pre-flight to any origin; granting it on any path; and dropping `Vary`.
