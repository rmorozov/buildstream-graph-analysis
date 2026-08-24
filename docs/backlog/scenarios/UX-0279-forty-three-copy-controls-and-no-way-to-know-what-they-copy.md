# UX-279: forty-three copy controls, and no way to know what they copy

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-224 | **Serves:** R8 — who pastes a finding into a ticket | **Topic:** viewer

## Motivation

Reported: *"in sections there is button copy - its context generally
unclear - what will it copy - the query, the text above query and so
on."*

Measured on the served report — 43 copy controls, three vocabularies,
and no hover text on any of them:

```text
"Copy link to this view"    1   (clear: the url)
"Copy"                     14   (decision ×3, findings ×11)
"Copy shown rows"          28   (one per table)

controls carrying a `title`        0 of 43
controls carrying an `aria-label`  0 of 43
```

Two distinct problems, and the bare **`Copy`** is the sharper one. In
`findings` it copies that finding's pasteable form (`UX-224`); in
`decision` it copies the next command. A reader cannot tell those apart,
and cannot tell either from `Copy shown rows` two sections down — the
same word for three different payloads.

`Copy shown rows` is honest about *scope* and silent about *shape*: it
copies the rows currently passing the filter, as the `data-raw` values,
which is the right choice and is written down nowhere the reader can
see.

The cost is not a mis-click; it is that the affordance goes unused. A
button whose result you cannot predict is one you do not press when you
are in a hurry, which is precisely when `UX-224` was meant to help.

## Required Fix

1. Every copy control says what it copies, in the control or on hover —
   the noun, not the verb. `Copy finding`, `Copy command`,
   `Copy 12 shown rows`.
2. The row-copy control names the count it will copy, from the live
   filter, so "shown" is a number rather than a promise.
3. One vocabulary. If two controls copy different things they read
   differently, and a guard asserts no two copy controls on one page
   share a label while carrying different payloads.

## Out of Scope

- What the payloads *are*. `UX-224` settled the finding's pasteable
  form and `UX-218` the command; this is about saying which is which.
- A copy-format menu. Offering Markdown as well is `UX-280`.

## Acceptance Test

No two copy controls with different payloads share a label. Every one
has a title naming its object. The row-copy label carries the live
count, and changing the filter changes the label.
