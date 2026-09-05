# UX-429: a command is rendered as a list of its words

**Priority:** High | **Status:** 🟢 Done | **Found by:** round 69, an outside walk of `bga snapshot` → `bga view` → Perfetto | **Serves:** every reader who is handed a command and expected to run it | **Topic:** viewer | **Area:** bga/viewer

## Motivation

The page's "What should I run next?" control is a three-row table whose
middle column is headed `Run`. Probed in the booted export of a
1,202-element run, at 1440x900:

```text
  row 1
    mono=False code=False btn=False  bga, blast, layer08/mod073.bst, /tmp/…
    mono=False code=False btn=False  critical_path_detail
```

The cell is not monospace, holds no `code` element, and carries no copy
control. The payload behind it:

```json
"argv": ["bga", "blast", "layer08/mod073.bst", "/tmp/…/run"]
```

**The same field is rendered correctly in two other places.** Three
sites read `next_steps[].argv`:

| site | renders it as | result |
|---|---|---|
| `bga/viewer/decision.js:737` | `argv.join(" ")`, `data-argv`, copy button | a command |
| `bga/viewer/views.js:500` | `argv.join(" ")`, copy button | a command |
| `bga/schemas.py:3134` — `{"key": "argv", "title": "Run"}` | the generic array path | `a, b, c` |

The two sites that know it is a command join it with the shell's
separator. The third does not know, and **the visual contract is why**:
`["bga", "blast", …]` is a *short scalar array*, whose control in
`docs/design/styleguide.md` §1 is the inline `code` list — a
comma-separated list of values. The mapping is being followed
correctly. The mapping has no row for a command.

So this is not a rendering slip to patch at the third site. It is a
missing shape, and §1's own rule says what that means: "a shape *not*
in this table is a design task, not an improvisation: it lands here
first, with its control, then in the code."

A pasted `bga, blast, layer08/mod073.bst, /tmp/…` does not run. This is
`§4d`'s failure in a different clothing — the handoff is present, looks
complete, and does not work.

## Required Fix

- **Declare the shape.** A `bga:command` hint on `next_steps[].argv`
  (and any other argv the schemas publish), saying that a scalar array
  is one command line rather than a list of values.
- **Add the row to §1's mapping table** and the hint to §1a's
  vocabulary. These land together or not at all:
  `tests/unit/test_the_contract_names_its_vocabulary.py` holds §1a and
  `bga/schemas.py` equal in both directions, so a documented hint
  nothing emits reddens exactly as an undocumented one does.
- **One control, read by every site.** `classify()` in
  `bga/viewer/shapes.js` returns the command control, and the table
  path, `decision.js` and `views.js` all render through it — the
  present state, where two sites hand-join and a third does not, is the
  drift the shape-dispatch exists to prevent.
- The control is a single monospace line with the copy affordance §4c
  requires, and it survives the export (no server, no hover).

## Out of Scope

- **Changing what the command *is*** — `UX-218` settled that the next
  step is a runnable command and this item does not reopen which
  command it should be.
- **The other commands on the page**: the `decision` section's
  "Copy command" controls already render correctly and this item does
  not restyle them (it makes them read the shared control, which is a
  refactor of the same behaviour, not a change to it).
- **`bga:command` on the query library's SQL**: a query is not a shell
  command and `perfetto_page.js` already gives it its own control.

## Acceptance Test

```bash
bga gen-synthetic /tmp/scale --seed 1
bga view /tmp/scale --export /tmp/report.html
```

Boot `/tmp/report.html` and assert, over every rendered node: no text
node matches an argv joined by `", "` where the payload holds that same
array, and every control rendering a `bga:command` value is monospace
and carries a copy control. A mutation that reverts the table column to
the generic array path must redden it.

## Outcome

**Round 70, 2026-08-31.** All four bullets, and the shape landed in §1
before it landed in the code.

### The gap, through the page's own resolution

Measured on `macro_micro`, driving `renderStructured` under the DOM
shim with the schema node as it was:

```text
classify without the hint: inline code list
cell tag: span class: ""
cell text: "bga, blast, core.bst, tests/fixtures/macro_micro/run"
```

and after:

```text
hint on argv: "shell"
classify says: command line + copy
cell tag: code class: next-command
cell text: "bga blast core.bst tests/fixtures/macro_micro/run"
data-argv: "bga blast core.bst tests/fixtures/macro_micro/run"
```

### What was built

- **`bga:command`** on `next_steps[].argv`, valued `"shell"` — declared,
  never guessed, because `["cmake", "ninja"]` is the same measured shape
  and genuinely is a list.
- **§1 gained the row and §1a the hint**, sixteen hints to seventeen.
  They had to land together: `test_the_contract_names_its_vocabulary.py`
  holds the emitted and documented sets equal in both directions, and it
  went red on the first run naming `bga:command` — the guard doing
  exactly what `UX-306` built it for.
- **`controls.js:commandLine`**, the one control. `classify` returns
  `CONTROLS.COMMAND` for it; `structured.js`, `decision.js` and
  `views.js` all call it. The two hand-rolled copy buttons are gone.
- It returns **nodes rather than a wrapper**, so the DOM every existing
  guard reads for `.next-command` and `.copy-step` is unchanged.

### Where it lives, and why

`controls.js` inlines third; `questions.js`, which holds the query
library's own `copyButton`, inlines after `decision.js`. A command
control living there could not be imported by `decision.js` without
reordering the export, which `test_the_viewer_splits_along_its_seams.py`
would have caught. `test_the_control_lives_where_every_site_can_reach_it`
pins that.

### The guard

`tests/unit/test_a_command_renders_as_a_command.py`, sixteen clauses,
1.30s (small by measurement): the hint is declared and only on arrays;
the table cell is a monospace command; no argv is ever drawn
comma-separated, read against the payload's own join so an empty cell
cannot pass it; all four sites draw the identical element; both sections
keep their copy button; and the export still gets the line.

### A clause of mine that did not discriminate

The first cut of "one control, not three" scanned the three modules'
**source** for `next-command` and `copy-step`. It failed — on a
*comment* in `structured.js` mentioning `copy-step` by name. That is
fixing guide §5's own example, a text scan that cannot tell code from
data, written into this item's own guard. Replaced by
`test_all_three_sites_draw_the_same_element`, which renders
`renderBlastOffline` and `renderDecision` for real and compares the
elements they build. An earlier cut scanning for `argv.join(" ")` was
wrong for a different reason: two joins survive and both are right —
the decision panel's pasteable text block, and `views.js` asking
whether a step exists at all.

### Falsification

| # | mutation | result |
|---|---|---|
| M1 | drop `bga:command` from `argv` (the item's own acceptance mutation) | **red** — 7 clauses |
| M2 | the table path stops consulting the hint | **red** — 6 |
| M3 | `decision.js` hand-rolls a comma-joined span again | **red** — 5, including the same-element clause |
| M4 | `commandLine` drops the copy button | **red** — 4 |

### Deviation from the Required Fix

One, stated: **the table cell gets the line without a copy button of
its own.** Inside a table §4c's affordance is the table's — double-click
a cell, or Copy rows — and a fourth copy control per row is the clutter
`UX-284` measured rather than a fix. The two sections that had a button
keep it, and a clause holds them to it.

### What this cost, and what it surfaced

`structured.js` was at **exactly** 1,500 lines, `UX-337`'s ceiling. The
four lines this needed had to be paid for by folding two `classify`
options onto one line and deleting the dispatch branch's comment, which
is now in `controls.js` instead. `app.js` is also at exactly 1,500.
Two modules pinned on the ceiling, each paying in comments, is filed as
**`UX-450`** rather than absorbed silently again.

### The suite

```console
$ make lint
All checks passed!

$ make test
5415 passed, 28 skipped, 1 warning in 270.04s (0:04:30)
```
