# UX-669: a runbook is a shape — the next steps rendered once, as steps

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-429 (§1d, a command is one line), UX-285, UX-535 | **Serves:** R1, at the moment of deciding what to run | **Topic:** viewer | **Shape:** judgement

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

## Outcome

**The gap, measured.** The Motivation held. On `macro_micro`, booted
at 1440x900: `#decision` listed 3 `[data-step]`, and
`[data-section=next_steps]` held a `<table data-table="next_steps">`
with the same three reasons and the same three commands, its `From`
cells printing `critical_path_detail` and `plane2_coverage` - payload
keys, which is the defect §4b names.

**The close, measured.** One shape, declared:

```text
schemas.py         RUNBOOK = "bga:runbook"; next_steps gains RUNBOOK: True
section next_steps <p><a href="#decision">3 steps, in the decision panel</a></p>
                   tables 0 · [data-step] 0        (golden: "2 steps, ...")
panel  #decision   3 li[data-step], each: p.why + code.next-command + a.from
a.from             #critical_path_detail  "from: Which elements are on the
                                           chain that binds?"
                   #findings              "from: Where the time is: ..."
                   #plane2_coverage       "from: How much did Plane 2 see?"
export bytes       442,716 -> 444,220 · +1,504 on **both** fixtures
                   +1,483 source · +21 contract · +0 data
```

**The mutation table.** Ten, each reddening a named clause in
`test_a_runbook_is_not_a_table.py`.

| mutation | clause that reds |
|---|---|
| restore the table | `..._the_section_holds_no_table` |
| the hint is declared but `hintsOf` never reads it | `..._the_hint_survives_the_read` |
| the shape is not declared | `..._next_steps_carries_the_runbook_hint` |
| the citation prints the key | `..._the_citation_is_a_question_and_never_a_key` |
| a step cites twice | `..._one_in_page_link_that_resolves` |
| a finding's step anchors on the finding id | `..._one_in_page_link_that_resolves` |
| the link's count is off by one | `..._the_section_is_one_link_to_the_panel` |
| the section keeps a copy of the steps | `..._the_section_lists_no_step` |
| a step is a reason with no command | `..._each_step_carries_exactly_one_command` |
| every array of objects becomes a runbook | `..._the_other_reason_array_still_draws_a_table` |

**The tenth mutation found a vacuous clause of my own.** The control
first counted `critical_path_detail`, then any table on the page.
Neither reaches this branch - the chapter renderers draw them - so both
stayed green with *every* array turned into a runbook. `provenance`
is the array that goes through it.

**Four deviations.**

*The aliased import does not survive the export.* `followsFrom` wanted
`format.js`'s `heading` beside three local `heading` variables, and
`import { heading as headingOf }` rendered the whole decision panel as
`ReferenceError: headingOf is not defined`: `_inline_module` strips the
`import` line and concatenates the modules into one scope, where the
alias names nothing. No viewer module had ever aliased an import, so
nothing caught it. The three locals became `head`; the trap is filed as
`UX-721`.

*`.command` is `code.next-command`.* The Acceptance Test names a class
the page does not have; §1d's command node has carried this one since
`UX-429` and three sites build it through `commandLine`.

*A step that follows a finding links the findings list.* Findings have
no per-finding anchor, so the label is the finding's own title - long,
and the only published field it has. Its id is the alternative and that
is the raw key this item removes.

*Only the `golden` bound moved.* Both exports grew by the same 1,504 B;
`macro_micro` had 3,335 B of headroom left under its bound and
`golden` only 284.
The old note on that row said 438,826 - `UX-681` recorded it before its
last edit and nothing re-read it. Measured at HEAD before this change:
442,716.
