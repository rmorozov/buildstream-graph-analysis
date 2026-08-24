# UX-263: the page's own policy refuses its drawings

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** R1, on every run opened in a browser | **Topic:** viewer

## Motivation

Reported from a real project: *"lots of errors from latest Chrome about
applying inline style violates the following content security policy
default-src, pointing to views.js"*.

Reproduced on the golden run, served by `bga view` itself, in
Chrome 141 — the server's own header is the one that refuses:

```text
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'

Refused to apply inline style because it violates the following Content
Security Policy directive: "default-src 'self'". ... Note that hashes do
not apply to event handlers, style attributes and javascript:
navigations unless the 'unsafe-hashes' keyword is present. Note also
that 'style-src' was not explicitly set, so 'default-src' is used as a
fallback.
```

A **style attribute is inline style**, so
`element.setAttribute("style", ...)` is refused. `views.js` used it in
four places, and every one of them is a visual encoding:

| site | what it draws |
|---|---|
| `views.js:516` | the waterfall bar's width |
| `views.js:802` | the critical-path box's share of the path |
| `views.js:869` | the blast tree's indentation, which is depth |
| `views.js:2111` | the optimization horizon's bar |

Console noise was the symptom. The defect is that **four drawings were
dead**: the attribute was set on the element and the declaration never
applied. Measured on the 7-element golden run at 1440x900:

```text
                       violations   wf-fill widths   path-box grow   horizon --w
before                         15   1 distinct       1 distinct      1 distinct
```

Every waterfall bar the same width, every path box the same size, every
horizon bar empty — on a page whose whole argument is that the numbers
make themselves self-evident (`UX-196`). Fifteen violations on seven
elements is why a 1,202-element run produces "lots".

Nothing caught it because the harness is a hand-rolled DOM shim with no
CSS engine, and it carried `style: {}` — a plain object that swallowed
every write and reported success. Third instrument defect in three
rounds (`UX-235`, `UX-262`).

## Required Fix

1. The viewer sets style through CSSOM — `el.style.width = ...`, and
   `el.style.setProperty("--w", ...)` for a custom property, which has
   no CSSOM alias. CSSOM is not inline style and is not subject to the
   policy.
2. The CSP is **not** relaxed. `'unsafe-inline'` would silence it in
   one line and is the wrong direction for a document that renders
   element names and paths out of a build and gets attached to tickets.
3. The shim reflects `.style` writes into the `style` attribute and
   serialises them the way a browser does — measured, not assumed.
4. A guard bans the style attribute in the viewer, and a second one
   pins that the policy stayed strict.

## Out of Scope

- Any other CSP directive. `script-src`, the Perfetto CORS grant
  (`UX-198`) and `frame-ancestors` are unchanged and unquestioned here.
- The 25 copies of the DOM shim, which is what made this a 25-place
  fix rather than a one-place one. That is `UX-264`.

## Acceptance Test

Serve a run with `bga view`, load it in Chrome, and count
`Refused to apply inline style` in the console: zero. Then read the
four encodings back out of the rendered page and confirm they differ
per element — a page that stopped drawing would also produce zero
violations.

## Outcome

**Fixed.** Both halves measured in Chrome 141 against the golden run
served by `bga view`, each in a **fresh browser profile** — the first
attempt reported 15 violations after the fix, which turned out to be
Chrome replaying the previous page's log buffer on `Log.enable`, not
new violations. Measuring twice in one browser would have recorded the
fix as having done nothing.

```text
                       violations   wf-fill widths   path-box grow   horizon --w
before                         15   1 distinct       1 distinct      1 distinct
after                           0   4 distinct       3 distinct      5 distinct
```

The `distinct` columns are the half that matters: zero violations alone
would also describe a page that draws nothing.

**The style attribute is still on the element.** `setAttribute` set it
and CSP refused to *apply* it, so the DOM read correct while the render
was wrong — which is exactly why a shim that inspects attributes could
never have seen this. The shim now reflects `.style` writes into the
attribute and serialises them as Chrome does, measured first:

```text
el.style.width = "50%"                 -> style="width: 50%;"
el.style.flexGrow = "428.571"          -> style="flex-grow: 428.571;"
el.style.setProperty("--w", "18.75%")  -> style="--w: 18.75%;"
two declarations                       -> style="width: 50%; padding-left: 1rem;"
nothing set                            -> no attribute at all
```

Three guards read a declaration out of that string; they used to
`.replace("flex-grow: ", "")` and would have broken on the real form,
so they now parse it properly through one shared `_decl` helper.

**The policy was not relaxed.** `'unsafe-inline'` was the one-line
alternative and is declined on the record, with a guard that fails if
it ever appears in `tools/bga_view.py`.

**Five mutations, five reds:** restoring one `setAttribute("style",
...)`; relaxing the CSP; reverting one shim to `style: {}`; dropping
the semicolon from the shim's serialisation; and deleting the horizon's
width entirely — that last one is the guard that stops the ban being
satisfiable by not drawing.

The new guard file shipped with the **self-matching bug it warns
about**: `"style: {}" not in source` matched the comment inside
`_styleFor` that explains why the literal is gone. Eighth instance of
`UX-239`'s pattern, first one written by the guard that names it.
