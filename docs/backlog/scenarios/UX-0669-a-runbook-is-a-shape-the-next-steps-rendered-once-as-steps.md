# UX-669: a runbook is a shape — the next steps rendered once, as steps

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-429 (§1d, a command is one line), UX-285, UX-535 | **Serves:** R1, at the moment of deciding what to run | **Topic:** viewer | **Shape:** judgement

## Motivation

The next steps render **twice** in chapter 1:

```text
(a) decision panel   ol.next-steps > li.next-step[data-step]: p.muted reason + §1d command line + Copy
(b) section next_steps   <table data-table="next_steps"> Why | Run | From — 5 rows, "5 rows · Copy 5 rows · as Markdown"
    Run cell   bga blast core.bst /tmp/r90/ex06/.bga/runs/20260905T085711Z/run   wrapped over 3 lines at 310 px
    From cell  critical_path_detail · run_instance.targets   — raw keys (§4b)
```

The user's instinct that a table suits this content badly is the
mapping being followed too literally: §1 sends "array of objects" to
a table, and this array is an *ordered reason + command + citation* —
a runbook. No other payload list has that kind (`constraints` under
`capacity_recommendation` and `findings[].evidence` are the only
other `{reason, …}` arrays, and neither is ordered or runnable). And
§5a's repeated-text budget is spent on a full duplicate.

## Required Fix

Styleguide **§1 row + §1e, "A runbook is a shape"**: *an array of
objects with a `bga:command` member and a `reason` renders as a
runbook, never a table* —

```html
<ol class="runbook"><li data-step>
  <p class="why">…</p>
  {command line, §1d}
  <a class="from" href="#follows_from">from: {section question}</a>
</li></ol>
```

Hint `bga:runbook` on `next_steps`; rendered once — the decision
panel keeps it, the `next_steps` section becomes a link to it (or
the reverse; one site). `follows_from` renders as an in-page link
labelled with the section's question, never its key.

## Out of Scope

- The steps' wording — the payload's; `UX-577` owns the advice that
  refuses.

## Acceptance Test

Guard: `#next_steps` contains no `<table>`; each `li[data-step]` has
one `.command` and one in-page link whose target exists; panel and
section never both list `[data-step]`. Mutation: restore the table —
red.
