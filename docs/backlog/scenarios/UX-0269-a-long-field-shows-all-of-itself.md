# UX-269: a long field shows all of itself, always

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-267 | **Serves:** R1 | **Topic:** viewer

## Motivation

Requested: *"analysis of the length of contents of every field and
proper measures to show truncated output by default with the
possibility to look at the full content"*. Measured, per field, on a
44-element run:

```text
678 chars   findings[].copy_text
572 chars   floors.capacity_model_note
393 chars   findings[].copy_text
354 chars   findings[].copy_text
334 chars   findings[].copy_text
299 chars   findings[].copy_text
293 chars   attribution_hints.resource_wait_us
```

Two families, and they want opposite treatment:

- **`copy_text`** is a paragraph *meant* to be copied whole
  (`UX-224`). Truncating it in the cell is right; truncating what the
  copy button yields would break the feature.
- **`capacity_model_note`** and the `attribution_hints` strings are
  explanations. They are long because they are careful, and hiding
  them by default is how a reader stops seeing the caveat on a number.

So a flat character cap is the wrong instrument, and that is the point
worth recording: the rule has to distinguish *a value that is long* from
*a sentence that is long*.

## Required Fix

1. A cap on **values**, with the full text one click away and the
   truncation visible (`…`), never silent.
2. **Sentences the schema declares as explanation** are exempt, or the
   report starts hiding its own caveats.
3. The cap is a named constant with the measurement above beside it,
   as `TABLE_OPENS_BOUNDED_ABOVE` is.

## Out of Scope

- `copy_text`'s payload. What the button copies is unbounded by design.
- Wrapping and ellipsis as a purely visual effect: a reader who cannot
  select the full text has not been given it.

## Acceptance Test

A 678-character cell renders truncated with its full content reachable;
a declared explanation of the same length does not; and the copy button
still yields the whole thing.

## Outcome

**Fixed**, with the split the measurement demanded rather than a flat
cap.

`CELL_TEXT_CAP = 160`. A longer **value** renders as a `<details>` whose
summary is the first whole words plus `…` and the character count, with
the full text inside and carried on `data-raw` so it stays selectable
and copyable. A longer **explanation** renders untouched.

```text
copy_text (400 chars)            -> details, 400 chars kept
capacity_model_note (400 chars)  -> span, untouched
resource_wait_us (400 chars)     -> span, untouched
anything_note (400 chars)        -> span, untouched
"fine"                           -> span
```

`EXPLANATIONS` names the fields that are prose, each with its reason,
and any `*_note` or `*_sentence` is exempt by construction — a
convention rather than a list to maintain. The exemptions are guarded
for having reasons, because an exemption with no argument is how the
list grows until the cap means nothing.

**Four mutations, four reds:** truncating explanations too; truncating
nothing; dropping the cap constant; and an exemption with no reason.

**Not done:** `attribution_hints` members other than `resource_wait_us`
are not exempt by name and rely on the `*_note`/`*_sentence`
convention. If one of them is long prose under a different name it will
truncate, and the fix is to name it — stated here so the next reader
knows where to look.
