# UX-299: a handoff that does not carry the trace in its hands

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-198 (the transport it re-thresholds), UX-298 (the artifact), UX-195 (the export rule it amends) | **Serves:** R1 | **Topic:** viewer

## Motivation

The tab-to-tab handoff fetches the whole trace into the report
page's memory, posts it to Perfetto's window, and was measured
right at 25 KB — and it is the same design at 1.5 GB, where the
browser tab meets the same OOM the server did. The `?url=` deep
link already exists as the fallback (`UX-198`); at scale the roles
invert: Perfetto fetching the trace itself — streaming, no copy
through the page — is the only transport that works. The export
has the same cliff: a `data:` URL inlining gigabytes is not an
attachment anyone can open.

Measured shape today: the server gzips the merged timeline **in
RAM** and holds the blob for its whole lifetime
(`tools/bga_view.py:325-326`, `:747`); no handler reads a `Range`
header; and the handoff (`bga/viewer/perfetto.js:153-174`) fetches
the whole trace into an `ArrayBuffer`, `postMessage`s it (a
structured-clone copy), and Perfetto decompresses it — three-plus
copies of the trace in browser memory before the first pixel.

## Required Fix

A size threshold (argued in the code, from the postMessage copy
cost) above which the deep link is the primary control and the
tab-to-tab post is not offered; below it, today's behavior stands.
The server serves the trace with the headers streaming needs
(length, gzip encoding as `UX-194` established). Above the same
threshold `--export` stops inlining the trace: the exported page
says the trace's size, and carries the `bga view --perfetto`
command and the deep-link recipe instead — the blast-box honesty
pattern. Both thresholds are one constant with one explanation.

## Out of Scope

- Range/partial-content support unless Perfetto's fetch is shown
  to need it (record the check either way).
- Any change below the threshold — the UX-198 behavior is verified
  and right at small sizes; this item is the large-size inversion
  only.

## Acceptance Test

With a generated trace above the threshold: the report page offers
the deep link, no fetch of the trace occurs from the page's own
JS (asserted via the DOM-shim fetch audit), and the export
contains no `data:` trace but does contain the command; below the
threshold both behave exactly as the UX-198 guards already assert
(those guards unchanged and green). Mutation: posting the
over-threshold trace tab-to-tab reddens.

## Outcome

🟢 **Done.** One threshold, published once, deciding both transports.

**The threshold and its argument.** `TRACE_BUDGET_B` in
`tools/bga_view.py` was already the export's ceiling; it is now the one
constant with one explanation, because the two questions it answers are
the same question. Above it a trace stops being something to *carry*:
the export stops inlining it, and the served page stops posting it tab
to tab. 4 MiB compressed is where that lands - measured compression on
real traces runs 4.2x (`UX-298`'s 40,000-process fixture) to 11x
(`UX-198`'s capture of `examples/06`), so 4 MiB is 17-45 MiB
decompressed and ~25-55 MiB across the two tabs at the conservative
end. It is also what a mail client will still take, which is the export
half of the same number.

**Why the page asks at click time and not at load.** The size is not
knowable when the page loads: finding it means rendering the trace,
which `UX-296` deliberately moved off the startup path. So the page
sends a `HEAD` - reading no trace bytes - at the moment the reader asks
for the timeline, and picks the transport from `Content-Length`. The
render happens once server-side and is reused by whichever transport
wins. An unknown size is treated as small, because refusing a transport
that works for every capture that fits is worse than using it.

**What each side does now.**

```text
                    below 4 MiB              above 4 MiB
served page      fetch, postMessage       HEAD only; the opened tab is
                 (UX-198, unchanged)      navigated to the ?url= deep
                                          link and Perfetto fetches it
                                          from this server itself
--export         inlined as a data:       no trace; the page says its
                 URL (UX-195)             size and carries the
                                          `bga view <snapshot> --perfetto`
                                          command and what it does
```

**A defect the guard found in its own first implementation.** The small
path opened a tab, closed it, and let `handOff` open a second one -
*after* an `await`, which is precisely the pop-up a browser blocks and
precisely what `UX-198` was filed for. `handOff` now accepts an
already-open tab, and the page opens exactly one, on both paths. The
clause that caught it asserts `window.open` was called once per click,
for both sizes.

**The Range check, recorded either way** (the item's own out-of-scope
line). The server has no `Range` handler: measured, a request carrying
`Range: bytes=0-9` gets `200` with the whole 17,576-byte body and no
`Accept-Ranges`. Perfetto's `?url=` fetch is a plain `GET` and this
repository's served-mode guards exercise it as one, so nothing has been
shown to need partial content. **Not implemented**, and the reason is
that no consumer asked for it rather than that nobody looked.

**Falsification.** Four mutations against the committed tree:

```text
N1  the over-threshold trace is posted anyway        1 guard red
N2  the page keeps a second copy of the number       1 red
N3  the size probe is a GET rather than a HEAD       2 red
N4  the export inlines whatever the size             1 red
```

N3 is the one worth naming: it reddens *both* size clauses, because a
probe that reads the body has already done the thing the item exists to
stop - and the small path's assertion that exactly one `HEAD` and one
`GET` are made is what notices.
