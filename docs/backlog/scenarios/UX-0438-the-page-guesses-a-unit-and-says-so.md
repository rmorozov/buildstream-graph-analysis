# UX-438: the page guesses a unit on a real capture, and says so on the console

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 69, strand (b) — pressing all 468 controls on a real capture | **Serves:** every reader, and the next round that trusts a clean console | **Topic:** contracts

## Motivation

Booting the export of a real capture of `examples/06` and pressing every
control produced exactly one console message:

```text
bga: transfer_share has no bga:quantity; guessed share
```

The page is name-sniffing. §1a's rule is the one being broken:

> **A hint is a declaration, never a guess**: the page reads what the
> schema says a value is and falls back to name-sniffing only where the
> schema says nothing, which is a schema gap rather than a feature
> (`UX-201`).

And the quantity is not missing from the repository — it is declared:

```text
bga/schemas.py:1413
    "transfer_share": ("share",
        "Artifact transfer as a share of wall-clock."),
```

So the table knows the unit and the value still arrives without it.
The likely reason is the path it travels: `transfer_share` is written
into a **finding's `evidence`** —

```text
bga/findings.py:451
    evidence={'transfer_share': share, 'transfer_us': transfer},
```

— and an evidence map is a free-form object, so the property carries no
hint even though the name is in the quantity table. That is a
hypothesis the item must confirm; it is not established here.

**Why nothing caught it.** `UX-334` gave the page a clean-console
guard, and the console is clean on the committed fixtures. This warning
needs a capture with artifact transfer in it, which the fixtures do not
have — the same shape as the rest of this round: **a real capture says
things the fixtures cannot.**

`transfer_us` sits beside it in the same map and is presumably in the
same position; the sweep saw only one warning because only one value
was rendered.

## Required Fix

- **Establish the path**, then close it where it actually breaks:
  either evidence maps carry hints for the keys the quantity table
  already names, or the value is published somewhere schema'd and the
  evidence map references it.
- **Check the whole map, not the one key that warned.** A warning per
  rendered value means the count of warnings measures what was drawn,
  not what is undeclared.
- **The clean-console guard runs against a capture that has transfer
  data.** A guard whose fixture cannot produce the finding is one whose
  setup excludes what it tests, which this repository has now seen nine
  times.

## Out of Scope

- **The name-sniffing fallback itself**: it exists deliberately so a
  gap degrades rather than crashes (`UX-201`), and this item fills a gap
  rather than removing the net.
- **The other 467 controls**: all pressed, none threw, none raised a
  window error — recorded in the round's notes and needing no item.
- **`UX-334`'s guard rewrite** beyond giving it a capture that can
  produce this warning.

## Acceptance Test

```bash
cd examples/06-macro-micro-optimization
bga snapshot -- bst build all.bst
bga view @last --export /tmp/report.html
```

Boot it, press every control, and the console stays empty. A mutation
removing `transfer_share`'s quantity declaration must redden the guard.

## Outcome

**Round 70, 2026-08-31.** The gap was real and it was not where this
item guessed.

### The hypothesis, tested and wrong

This file proposed that `transfer_share` arrives without a hint because
it rides a finding's `evidence`, "a free-form object". Reading it
settled it the other way — `findings[].evidence` declares
`properties: EVIDENCE_QUANTITIES`, and both keys have been in it since
`UX-217`:

```console
$ PYTHONPATH=. python3 -c "from bga import schemas; import json; \
    s = schemas.schema('analyze/v4')['properties']['findings']['items']\
['properties']['evidence']['properties']; \
    print(json.dumps({k: s[k] for k in ('transfer_share', 'transfer_us')}, indent=2))"
{
  "transfer_share": {
    "bga:quantity": "share",
    "description": "Artifact transfer as a share of wall-clock."
  },
  "transfer_us": {
    "bga:quantity": "duration_us",
    "description": "Wall-clock spent moving artifacts rather than building them."
  }
}
```

The undeclared copy is in the **population**, not the quotation:
`cache`, where `compute_cache_accounting` adds `transfer_us` and
`transfer_share` for a run that moved artifacts. That block declared
five keys and neither of these.

### Why no fixture could produce it

Each committed run has half of what the block needs:

| fixture | Pipeline Summary | transfer span |
|---|---|---|
| `golden` | no | yes — one `DOWNLOAD` |
| `macro_micro` | yes | no |

`compute_cache_accounting` returns `{}` without a summary and adds
nothing without a span, so the fields have been undeclared for as long
as they have existed with every guard green.

### The gap, measured through the page's own resolution

`tests/pages.py`'s new `transfer_run` injects `TRANSFER_SPANS` into a
copy of `macro_micro`, and the document goes through the same node
census `test_every_number_says_what_it_is.py` uses — the page's own
`hintsOf`/`guessQuantity`, not a Python re-implementation:

```text
before   declared 863   guessed ['cache.transfer_share']
                        neither ['cache.transfer_us.DOWNLOAD',
                                 'cache.transfer_us.UPLOAD',
                                 'provenance.[].rule.threshold',
                                 'provenance.[].rule.threshold.[]']

after    declared 866   guessed []
                        neither ['provenance.[].rule.threshold',
                                 'provenance.[].rule.threshold.[]']
```

`cache.transfer_share` is the console message this item is named for.
The map beside it was **worse than guessed** — no unit at all, and
silent, because a value with nothing to sniff raises no complaint.
The two `provenance` entries are `UNDECLARABLE`'s existing entries.

### The whole map, not the one key that warned

Walking keys rather than numbers found a third: `target_closure.targets`,
a list of element names emitted since the closure was and described by
nothing. A list carries no quantity to guess wrong, so no console
message ever named it — which is the argument for the second bullet.
Declared here.

### The guards

`tests/unit/test_the_cache_block_declares_what_it_emits.py`, four
clauses, 0.41s (small tier by measurement, so `tests/tiers.py` is
unchanged): the fixture really produces the block; every key it emits
is described; no number in it renders from a guess; and the walk
reached the three transfer paths by name rather than by a count.

`test_the_console_stays_clean.py` gained the third run as its fifth and
sixth boots — the item's third bullet. It needs a browser and so is
skipped where there is none (a declared census reason), which is why
the unit half above exists: it reads the same gap under Node, so CI
can see it.

### Falsification

| # | mutation | result |
|---|---|---|
| C1 | drop `transfer_share`'s `bga:quantity` (this item's own acceptance mutation) | **red** — `test_no_number_in_it_renders_from_a_guess`, `test_the_walk_reached_the_transfer_block` |
| C2 | drop `transfer_us`'s `additionalProperties` | **red** — all three of the above plus `test_every_key_it_emits_is_declared` |
| C3 | drop `target_closure.targets`' declaration | **red** — `test_every_key_it_emits_is_declared` only |
| C4 | `TRANSFER_SPANS = ()`, so the fixture stops producing the block | **red** — `test_the_fixture_produces_the_block_that_was_never_tested`, `test_the_walk_reached_the_transfer_block` |

C3 is the one that matters most: it reddens *only* the key clause, which
is the evidence that the unit census structurally cannot see a key with
no unit, and that the second clause is not a restatement of the first.
C1 leaves `test_every_key_it_emits_is_declared` green for the same
reason in reverse — the description survives — which is the separation
being asserted rather than a hole.

### Deviation from the Required Fix

None on the three bullets. One correction to the Motivation: its stated
hypothesis about evidence maps is wrong, and the section above records
it rather than quietly fixing the file, because a later round reading
this item would otherwise go looking in the wrong module.

### The suite

```console
$ make lint
All checks passed!

$ make test
5390 passed, 28 skipped, 1 warning in 266.00s (0:04:26)
```
