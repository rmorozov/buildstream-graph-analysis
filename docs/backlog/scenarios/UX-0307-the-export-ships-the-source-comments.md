# UX-307: the export ships the source commentary

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-195 (the export this weighs), UX-287 (the split that measures it) | **Serves:** R1 — whoever a report is sent to | **Topic:** viewer

## Motivation

`--export` inlines every viewer module verbatim, and this
repository's modules are commented by design — the argument for a
rule lives beside the rule. That commentary is right in the tree
and is dead weight in an attachment: **175 KB of the 196 KB page a
reader downloads is commented JavaScript**, and nobody opening a
report reads it.

Found by `UX-303` tripping the ratio `UX-287` set. Measured on the
1,000-element run at round 41:

```text
                  data       page     ratio
round 39       691,401     97,488      7.1x
round 41       765,103    196,340      3.90x
```

The page doubled while the data at that scale did not, so the guard
that says "the data is what an export weighs" fell from 7.1x to
3.90x and its 4x threshold had to be restated to 3.5x. The page
growth is real work — `UX-289`'s presets, `UX-302`'s dispatch and
toggle, `UX-303`'s drawings — and roughly two thirds of what each
of those adds is prose.

## Correction (`UX-320`, round 44): the premise above is wrong

The conformance pass measured the exported page and found that
`_inline_module` **already strips comments** — `_uncommented` in
`tools/bga_view.py` has dropped whole-line and block comments from the
inlined copy since `UX-205`, and its own docstring records the
79,180 → 52,870 B it bought. So "175 KB of the 196 KB page is commented
JavaScript" was never true of the *export*; it is true of the
repository, which is a different file.

Measured on the round-44 export of the 1,000-element run:

```text
page     223,276 B
  js     198,058 B   89%   trailing `//` on code lines ~114 B
  css     22,247 B   10%
  rest     2,971 B
data     764,900 B   3.43x
```

The page is **code**. What this item has left is those ~114 bytes and
whatever a real minifier would buy — and a minifier is the thing the
Required Fix below explicitly declines, for reasons that still hold.

**So the item stands, at a tenth of its stated size, and its motivation
is corrected rather than its status changed.** The ratio guard has now
been restated twice (4x → 3.5x → 3.3x) against a cause that was
misattributed both times: the real one is that the viewer grows
features while the synthetic run's data does not grow with it. A round
that wants the page smaller should start from the measurement above and
decide whether the ratio is the right instrument at all.

## Required Fix

`_inline_module` strips comments from the copy it inlines. The
repository keeps every one; the attachment carries none.

Not a minifier and not a build step: a comment stripper that
understands string and regex literals, in `tools/bga_view.py`, on
the order of thirty lines, with the property that the stripped
module still parses and still boots. **Served mode keeps the
comments**, because a served page is read from the tree by whoever
is working on it and `view-source:` is a debugging affordance
there.

## Out of Scope

- Minification, mangling, or bundling. `UX-193`'s standing rule is
  no build step, and stripping comments needs none.
- The stylesheet's comments, unless the same pass is free — the
  measurement above says they are 1.6 KB of 19.6 KB.
- Changing what any module says. This is about which copy carries
  it.

## Acceptance Test

The exported page boots and renders identically (booted section
order, section count and every drawing's `data-*` byte-identical
before and after); the page shrinks by a stated figure; a module
whose comment contains `*/` inside a string literal survives the
pass (mutation: a naive regex stripper corrupts it and the boot
guard reddens); the served page still carries its comments; the
`UX-287` ratio is restated upward with the new measurement.
