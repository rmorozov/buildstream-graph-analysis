# UX-307: the export ships the source commentary

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-195 (the export this weighs), UX-287 (the split that measures it) | **Serves:** R1 — whoever a report is sent to | **Topic:** viewer

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

## Outcome (round 45, 2026-08-26) — 🟢 Done

**Read the Correction above first.** This item shipped at a hundredth
of the size its Motivation claimed, and what it actually bought is not
bytes.

### What was left, measured

The exported golden page, split into its parts and read for surviving
commentary:

```text
page    223,227 B
  js    198,009 B   88%      5,034 lines
 css     22,247 B    9%
whole-line // survivors           0
lines with a // somewhere else    8
lines mentioning /* or */         1
```

Nine lines. Four are the trailing comments a stripper could take:

```text
line  1531    38 B   ? touch(entry[idKey]) : null;   // the join follows…
line  3501    39 B   if (isScalar(value)) return UNMAPPED;   // scalars…
line  3521    34 B   if (!entries.length) return UNMAPPED;   // "none"…
line  4499    42 B   return null;   // scalars belong in the summary…
total        153 B   of a 223,227 B page (0.069%)
```

Round 44 estimated ~114 B. The measured figure is **153 B**.

The other five are why this took a scanner rather than a regex:

```text
const PERFETTO_ORIGIN = "https://ui.perfetto.dev";
const PERFETTO_FRIENDLY_URL = "http://localhost:8080/";
const SVG_NS = "http://www.w3.org/2000/svg";
const SVG = "http://www.w3.org/2000/svg";
.replace(/\|/g, "\\|").replace(/\s*\n\s*/g, " ");
```

Cut at the first `//` and the four constants become unterminated
strings — the page does not boot, it does not parse. The fifth is the
block form: `/\s*\n\s*/g` contains `*/`, so a `/\*.*?\*/` pass over
the whole text can pair it with a `/*` anywhere above and delete
everything between them.

**That is the finding.** The rule this replaced could only reach a
comment that *begins a line*, which is safe by construction and is
also a ceiling: it could not be widened to take the four, because four
others in the same bundle are indistinguishable from them by any rule
that does not know a string from code.

### What landed

`_uncomment_js` and `_comment_spans` in `tools/bga_view.py`: one pass
tracking the states in which a `//` or a `/*` is not a comment — both
quoted string forms, a template literal (whose `${ }` is code again,
recursively), and a regex literal. It removes comments and the run of
whitespace that led into them, and nothing else. Still not a minifier:
code is left exactly as written, so a stack trace from an exported
page still quotes the source.

```text
                    before      after     delta
modules            202,499    202,346      -153
golden page        223,227    223,074      -153
golden html        321,770    321,617      -153
golden data         98,374     98,374        +0
macro_micro html   361,086    360,932      -154
```

### It renders the same thing

Both committed fixtures, booted through the same harness the served
payload goes through:

```text
classes      identical  (45)
sections     identical  (16, in order)
severities   identical  (3)
text         identical  (17,430 characters)

golden       1 drawing,  11 data-* attributes   byte-identical
macro_micro  3 drawings, 39 data-* attributes   byte-identical
sha256 (macro_micro drawings) ac759eaa8762aecf78f8d77811653bdc9a548050
```

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| T1 | blind the string scanner | 4 clauses of the literal family |
| T2 | blind the template-literal scanner | the template clause alone |
| T3 | blind the regex scanner | **nothing at first — see below** |
| T4 | only take comments that begin a line (the old ceiling) | the double-slash census, naming the regression |
| T5 | run every block span one char past its `*/` | **nothing at first — see below** |
| T6 | a CSS string carrying `/*` | the stylesheet clause |
| T7 | strip the tree instead of the copy | the served-page clause |

### Two guards of mine that did not discriminate

Both worth more written down than quietly fixed.

**T3 — the regex state was unexercised by the corpus.** Blinding
`_close_regex` entirely left all sixteen modules byte-identical and
all 41 clauses green. The reason is that no regex checked in today
contains a `//` or a `/*`: the state is real and defensive, and
nothing in the tree can tell it is there. `SURVIVING_STARSLASH` looked
like it covered this and does not — it guards against a *whole-text*
`/\*.*?\*/` pass, which is a different mechanism. Fixed by a clause
that exercises the state on a module built for it,
`const url = /^https:\/\//;   // strip the scheme`, whose trailing
`\/\/` a blind scanner reads as a line comment and swallows the rest
of the file behind. T3 reddens exactly that one clause now.

**T5 — "the spans tile the source" was vacuous.** It cut the source at
the scanner's own indices and glued it back, which reconstructs the
input for *any* indices whatever. It passed against a mutation that
ran every block span one character past its `*/`. Replaced with a
clause that reads each span: it must open `//` or `/*`, a block span
must *end* at its `*/`, a line span must not cross a newline, and
spans must not overlap. T5 now reddens 14 of them.

A third, smaller: the first draft of the naive-stripper clause used
`/* opener */` as its unpaired opener. A block comment that closes
itself never reaches the regex below it, so the clause proved nothing;
it uses a `/*` inside a string literal now, which is what an unpaired
opener actually looks like in the wild.

### Deviations from the Required Fix

- **"on the order of thirty lines"** — it is about 110 with its
  docstrings, across six small functions. A scanner that understands
  template interpolation (which is code, recursively) and regex
  literals does not fit in thirty; the alternative was a shorter pass
  that handles fewer cases, which is the thing that was already there.
- **"the `UX-287` ratio is restated upward with the new measurement"
  — declined, with its reason.** That clause was written when this
  item was believed to be worth 175 KB. Measured on the fixture the
  ratio guard uses: **3.4266x → 3.4289x**, the fourth decimal place.
  Tightening a threshold on 153 B would manufacture a significance the
  measurement does not have, and would leave the next round to trip
  that guard inheriting a number nobody could account for. The
  threshold stays at 3.3x and the refusal is written into the guard's
  own docstring rather than left in this file.
- **The stylesheet was in scope only "if the same pass is free".** It
  is not — CSS would need its own scanner — so `_uncommented_css` is
  unchanged. What did land is a guard for the hazard its own docstring
  names and says "a guard would catch": no guard did. A `/*` inside a
  `content:` string would be mispaired by that whole-text regex, and a
  clause now asserts no CSS string carries a comment delimiter.
