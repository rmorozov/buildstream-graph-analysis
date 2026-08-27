# UX-334: a console the page keeps clean

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-320 (the walks this joins), UX-193 (the CSP that is right to be strict) | **Serves:** R1 — and every developer who opens devtools | **Topic:** viewer

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
