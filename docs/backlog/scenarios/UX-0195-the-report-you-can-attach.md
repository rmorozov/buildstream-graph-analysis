# UX-195: the report you can attach

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-193 (the page this exports), UX-115 (the CI journey this joins) | **Topic:** viewer

## Motivation

Direction 7's second delivery mode: the same page, as a file.
`bga view --export report.html` inlines the run's JSON into the
static page and writes one self-contained artifact — no port, no
server, no network. Three scenarios earn it:

- **CI**: the pipeline that posts the UX-115 comment also attaches
  the full visual report as an artifact — the comment is the
  headline, the export is the detail, and neither needs a viewer
  deployment.
- **Remote debugging**: "send me your report" becomes one file — the
  same motion the diagnosability rounds built for failure evidence,
  now for analysis.
- **The archive**: a snapshot pruned later still has its rendered
  report if the export was kept — cheap institutional memory.

## Required Fix

1. `--export PATH` on `bga view`: same page code, payloads inlined
   (a `<script type="application/json">` block per payload; the page
   reads inline-first, fetch-second — one code path decides). The
   Perfetto button still works from `file://` (the handshake is
   opener-based, no server involved); when the trace would bloat the
   file past a stated budget, it is left out with the button saying
   what to run instead — recorded, not silent.
2. Size discipline: the export's budget stated (page + payloads;
   measure on the golden run and the 1,202-element synthetic — the
   JSON dwarfs the page or the page has failed Direction 7).
3. CI wiring: `ci-comment.md` gains the artifact step beside the
   comment step, marked optional; the workflow uploads it when the
   compare ran.

## Out of Scope

- Hosting exports anywhere (they are files; where they go is the
  pipeline's business).
- Multi-run bundles (one run, one file; compare's export carries its
  pair inline like the compare JSON does).

## Acceptance Test

`bga view --export r.html @last` writes a file that opens with zero
network access (asserted: no external fetches in the page source, all
payload script blocks present) and renders the same data the served
mode does (the UX-193 parse harness, pointed at the file). The
export of the synthetic run stays under the stated budget or the
budget note explains. The CI docs lines pass the docs-commands test.

---

## What was built

**`bga view --export PATH`** writes one self-contained file: the same
`index.html`, the CSS inlined, `perfetto.js` and `app.js` concatenated
into a single inline module, and each payload in its own
`<script type="application/json" id="bga-…">` block. The timeline
travels as a `data:` URL, so the Perfetto button works from `file://` —
`fetch` handles `data:` and the handshake never needed a server.

**Inline first, fetch second, decided in one place.** `load(name)`
looks for the inline block and falls through to `fetch` — so the
exported file and the served page run the identical renderer, and there
is no second code path to drift.

**Measured, on the two runs the item names:**

```text
                          report.json     export     page is
1,202-element synthetic     816,573 B    653,379 B      6.0%
real examples/06 capture                  84,107 B     46.5%
the page itself (7 files)    39,119 B
```

(The export is smaller than `report.json` because `--format json`
indents and the inline block does not. Re-measured after `UX-196` added
`views.js`; at `UX-195` the page was 6 files and 26,387 B.) At 1,202
elements the payload is **17x the page** — Direction 7's own test of
whether the viewer stayed thin, passed with room. Budgets: 8 MiB for the file, 4 MiB for
the timeline alone. Both are *reported*, never enforced — a report that
large is still the user's report, and a timeline dropped for size says
why in the output.

**CI wiring**: `ci-comment.md` gains the artifact step beside the
comment step, with `if: always()` because the report is most wanted
when the gate failed.

Tests: 16 (`tests/unit/test_the_report_you_can_attach.py`), the
exported file parsed and rendered by the same Node harness `UX-193`
uses on the served payload, with `fetch` wired to throw so anything not
answered inline fails loudly. Eight mutations, each red.

### Three defects, and one of them was in the guard

1. **The inline blocks were keyed by url, not by name.** `payloads()`
   returns `{"report.json": …}`, so the block came out as
   `id="bga-report.json"` while the loader looks for `bga-report`. It
   is silent: the block is never found, the page falls through to
   `fetch`, and that *works when served* — so the export looks correct
   everywhere except the one place it is used.
2. **A guard that could not fail, found by falsifying it three times.**
   The render harness called `render(inlined("report"), …)` directly,
   never touching `load` — so deleting the inline-first branch outright
   left every render guard green. Two attempts to fix it silently
   no-op'd because the replacement string did not match the file's
   escaping, and the guard kept passing, which looked like the mutation
   being harmless. It now goes through `load`, and the mutation fails
   with the harness's own `the export fetched something`.
3. **A test that injected through a computed field.** The
   `</script>`-escaping guard set `run_id` in `run-context.json` — but
   `run_id` is *computed*, so the string never reached the payload and
   the guard exercised nothing. Injected at the `payloads` seam
   instead.

The through-line, again: **a guard is not a guard until a mutation has
made it fail.** Three of the eight mutations here found a guard rather
than a defect.

**Deviation from the Required Fix:** none.

