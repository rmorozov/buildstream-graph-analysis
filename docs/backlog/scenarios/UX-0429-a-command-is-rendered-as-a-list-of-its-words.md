# UX-429: a command is rendered as a list of its words

**Priority:** High | **Status:** 🔴 Not Started | **Found by:** round 69, an outside walk of `bga snapshot` → `bga view` → Perfetto | **Serves:** every reader who is handed a command and expected to run it | **Topic:** viewer

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

_Not started._
