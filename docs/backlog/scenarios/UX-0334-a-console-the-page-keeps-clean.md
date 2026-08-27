# UX-334: a console the page keeps clean

**Priority:** High | **Status:** 🟢 Done Done | **Depends on:** UX-320 (the walks this joins), UX-193 (the CSP that is right to be strict) | **Serves:** R1 — and every developer who opens devtools | **Topic:** viewer

## Motivation

The user's field report: the Chrome console on `bga view` is full
of Content-Security-Policy violations (`default-src 'self'`).

Reproduced and counted (headless Chromium, CDP, violation
listener): **11 `style-src-attr` violations per macro-page boot**,
all from one path — `drawings.js:123`'s `setAttribute` receiving a
`style:` from the exhibit tick labels at `:155`. The server sends
`default-src 'self'` with no `style-src` (`tools/bga_view.py:1050`),
so style *attributes* are forbidden — and Chrome **enforces**, not
just reports: every tick label computes `left: 0px` and piles at
the exhibit's left edge on served pages, while all CSSOM-set
styles (`fill.style.width`, `setProperty("--w")`) survive because
the attr directive does not govern them. The export (no CSP) shows
the ticks where they belong — the served page is the broken one.
Three noise sources ride the same console: four 404s per boot
(favicon plus the optional compare/store/store-aggregate payload
probes), and ~200 DevTools accessibility Issues (table filter
inputs with neither ids nor labels).

The CSP itself is correct — a local report server should be
strict — the page just violates its own policy, and nothing in
the suite listens to the console, so the errors accumulated
invisibly across rounds. The user's ask is the guard as much as
the fix: invent something that keeps this whole error class out.

## Required Fix

The tick labels move to the CSSOM path every other drawing
already uses (a custom property, not a style attribute) — fixing
the real geometry loss, not just the noise; the optional-payload
probes stop 404ing the console (the run manifest already knows
which payloads exist — the page asks it, not the network); the
filter inputs get the ids/labels the Issues panel demands. Then the guard: the Chromium harness the
round-44 walks already boot captures **console messages and
security-policy-violation events** on both fixture pages, served
and exported, and fails on any error-severity message or CSP
report — TypeErrors included, which makes this the net for
`UX-335`'s class too. The clause joins the UX-320 conformance
family.

## Out of Scope

- Weakening frame-ancestors or the allowlist (the server's
  posture stands).

## Acceptance Test

Booting both pages served and exported: zero console errors, zero
CSP violation events (the measured violation classes each named
in the guard's docstring as regression cases); mutation: reintroduce
one inline-style site → the guard reds naming the directive; the
visual geometry is unchanged after the fix (the existing geometry
walks stay green).

## Outcome (round 47, 2026-08-27) — 🟢 Done

### The gap, measured

The instrument had to be built before the gap could be counted: no
guard in this repository had ever read what the browser said about the
page. `tests/cdp.mjs --observe` now collects three channels — console
messages (including the browser's own log lines, which is where a 404
on a subresource is reported and nowhere else), `securitypolicyviolation`
events, and Audits-panel issues. On the golden fixture, headless
Chromium, at `413d13a`:

```text
                      exported            served
console errors        6                   7
csp violations        0                   3   style-src-attr
issues                144                 83
  form control        138 + 6 label       70 + 10 label
```

and the served page's exhibit ticks, which is the part that was not
noise:

```text
[name, node.style.left, rendered x at 1440x900]
exported: [['first', '0%', 695], ['peak', '0%', 674], ['last', '100%', 868]]
served  : [['first', '(none)', 695], ['peak', '(none)', 674], ['last', '(none)', 628]]
```

The `last` tick was 240px left of where the export drew it, because
Chrome **enforced** `style-src-attr` and refused the attribute
outright. The two shapes of the same report disagreed about geometry,
and the geometry walks only ever booted the export — so the broken one
was the one nothing looked at.

### After

```text
                      exported            served
console errors        0                   0
csp violations        0                   0
issues                0                   0

exported: [['first', '0%', 695], ['peak', '0%', 674], ['last', '100%', 868]]
served  : [['first', '0%', 695], ['peak', '0%', 674], ['last', '100%', 868]]
```

Full suite after the fix: 4,172 passed, 18 skipped, 0 failed, 200s
at `-n auto`. Lint clean.

### Why each fix has the shape it has

**The ticks go through the CSSOM.** `node.style.left = …` is a property
assignment, not an inline style, and the attr directive does not govern
it — which is why `fill.style.width` and `setProperty("--w")` had
survived in the same file all along. `UX-263` learned this once in
`views.js:566`; this is the same lesson, one module over.

**The optional payloads ask the manifest.** `bga view` already knows
which documents it built: `_offered()` derives the list from the
document table itself, so a payload added later joins the manifest with
no edit and a payload that failed to build is absent from both at once.
`optional(run, name)` consults it. A run document with no `payloads`
key — an export written by an older `bga view` — falls back to probing,
so the old page still renders in the new one.

**The favicon gets a 204.** A browser asks for `/favicon.ico` on every
navigation whether the document links one or not. `<link rel="icon"
href="data:,">` was tried first and **measured**: this server's own
`default-src 'self'` refuses a `data:` image, so it traded a 404 for a
CSP violation. The 204 is answered by the server, and `file://` pages
never ask.

**Controls get a `name` and an `id`, labels get a `for`.** An
`aria-label` answers neither complaint — six were already on these very
controls. The browser is asking for the identity a *form control* has,
not for its accessible name. `controls.js` imports nothing, which is
what lets `views.js` use it without the cycle back through `app.js`
that its own header note forbids.

**The guard is the deliverable.** Four boots — two fixture runs, served
and exported — failing on any error-severity console message, any CSP
violation, or either form issue. A `TypeError` during boot lands in the
same net, which is why `UX-335`'s class needs no second instrument.

### Mutations verified red and reverted (8)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | `drawings.js` passes `style:` to `box()` again — the filed defect, reintroduced | 3: `no_page_logs_an_error`, `no_page_violates_its_own_policy`, `the_style_attribute_path_stays_shut` |
| M2 | the **served** run document publishes no `payloads` | 2: `no_page_logs_an_error`, `no_payload_is_discovered_by_failing_to_fetch_it` |
| M3 | the **exported** run document publishes no `payloads` | 2: the same two, on `file://` CORS refusals instead of 404s |
| M4 | the table filter box loses `identify()` | 1: `every_form_control_has_an_identity` |
| M5 | the what-if label loses `labelFor()` | 1: `every_form_control_has_an_identity`, on `FormLabelHasNeitherForNorNestedInput` |
| M6 | the `favicon.ico` 204 route goes away | 2: `no_page_logs_an_error`, `no_payload_is_discovered_by_failing_to_fetch_it` |
| M7 | the harness never opens its recording gate | 1: `it_reports_a_console_error_that_is_there` — and *only* that one, which is the positive control doing its job |
| M8 | `Log.enable` dropped from the harness **and** M6 reintroduced | 1: `it_reports_a_browser_log_line_that_is_there` |

Two of these changed the work rather than confirming it.

**M2 was the round's most useful finding.** On its first run it
reddened one clause, not two: the clause *named* for the payload probes
read `entry["text"]` only, and a served 404 says `Failed to load
resource: … 404` with the path in a separate field. It was blind to
exactly half the regression it exists for — the general clause was
carrying it. Fixed to read text and url together, and M2 now reddens
both.

**M8 did not exist until M7 exposed the shape of the gap.** Dropping
`Log.enable` from the harness and reintroducing the favicon 404 left
**all seven clauses green**: the whole browser-log channel — every 404,
every network error — could have been switched off and no test would
have said so. `it_reports_a_browser_log_line_that_is_there` was added
for that, fetching a payload that does not exist on the served page and
asserting the harness reports it. M8 reddens it now. A net with three
channels needs three positive controls; it had two.

### Two repairs to `dev_close_task.py` this closure turned up

`UX-336`'s helper wrote `🟢 Done — 🟢 Done — …` for this row: the note
was drafted with its verdict and `--move` adds one. It strips a leading
verdict now. And `--scenarios` pointed at a directory outside the
repository — which is the whole point of that flag, `UX-336` added it so
a mutation could run against a `tmp_path` copy — crashed on
`relative_to` in the advisory line *after* the row was written, so the
move succeeded and the command still exited on a traceback. Both were
found the way the helper's own printed instruction says to find them:
by reading the row it just wrote.

### Deviation from the Required Fix

- The tick fix uses `label.style.left`, a CSSOM **property assignment**,
  rather than the custom property the Required Fix names. A custom
  property set with `setProperty` would work identically as far as the
  CSP is concerned, but `left` is the property being set and there is no
  second reader for it — a `--at` variable plus a `left: var(--at)` rule
  is one indirection for no gain. `--w` exists in this file because the
  *bar* has a width its container also reads.
- The Required Fix names "the filter inputs"; the Issues panel named 138
  controls, not the four in `interrogable`. Every control the page
  builds is identified, in `app.js` and `views.js` both.
