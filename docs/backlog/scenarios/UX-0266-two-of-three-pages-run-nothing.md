# UX-266: two of the three served pages run nothing

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-263 | **Serves:** R1, and R2 through the timeline | **Topic:** viewer | **Area:** bga/viewer

## Motivation

Reported from a real run: *"i've found a problem on sql.html page — let's
check all views and fix the problem"*. Checked, in Chrome 141, against
the pages `bga view` actually serves:

```text
                   CSP violations   main children   body text
index.html                      0              26      11,056
sql.html                        1               0         508
perfetto.html                   1               4         398
```

`sql.html` rendered **nothing** — `main` had zero children and the
questions list never existed. `perfetto.html` is quieter and worse: the
page renders, the *"Open in Perfetto"* button is there, and nothing was
listening to it, so `bga view --perfetto` lands on a button that does
nothing at all.

The cause is one the repository already knows. The server sends
`default-src 'self'`, and that refuses inline **script** exactly as it
refuses inline style. Both pages carried
`<script type="module">…</script>` inline. `UX-263` fixed the style
half of this and checked `index.html` only, which is why the script
half survived it — the guard was as narrow as the fix.

## Required Fix

1. Every served page loads its script from a **file**, as `index.html`
   always has. The modules are added to `ASSETS`, or they 404 and the
   page is dead by a different route.
2. The guard sweeps **every** `.html` the viewer serves, for inline
   script and inline style, rather than one page for one of them.
3. And the other direction: each page names the module that drives it,
   because a page with no script at all would also pass a ban on
   inline ones.

## Out of Scope

- Relaxing the CSP. `UX-263` declined `'unsafe-inline'` on the record
  and the argument is unchanged: this page renders element names and
  paths out of a build.
- The report's own rendering. That is `UX-267`.

## Acceptance Test

Load every served page in a browser and count CSP violations: zero.
Then confirm each page rendered something — a violation count of zero
also describes a page that was deleted.

## Outcome

**Fixed.** `sql.js` and `perfetto_page.js` are files; the pages load
them with `src`; both are in `ASSETS`. Re-measured in Chrome 141:

```text
                   CSP violations   main children   body text
index.html                      0              26      11,056
sql.html                        0               1         778
perfetto.html                   0               4         398
```

`sql.html` renders its four questions again. The `main children` count
is the half that matters — zero violations alone would also describe a
page that renders nothing, which is exactly the state this was in.

**Three mutations, three reds:** restoring an inline `<script>`;
removing a page's script entirely; and dropping `sql.js` from `ASSETS`
so it 404s. The third is worth keeping — a module the server does not
list is the same dead page by a different route.

**A note on the index's console.** `index.html` logs three 404s
(`compare.json`, `store.json`, `store-aggregate.json`). Those are the
page probing for optional documents and correctly treating absence as
"no band to draw" — noise, not a defect, and recorded here so the next
reader does not chase it.
