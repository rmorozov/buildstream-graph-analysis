# UX-630: two environment variables no inventory sees

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-326 (the tool's sentences are contracts) | **Found by:** architecture review 15 | **Serves:** anyone trying to find out what changes bga's output | **Topic:** docs

## Motivation

Two environment variables landed this window, both input surfaces:

```text
BGA_RATE            bga/report/rate.py:30             changes what `bga analyze` and `bga whatif` print
BGA_REQUESTED_AT    tools/_run_context_common.py:258  changes what a capture publishes
```

Of the eight `BGA_*` names in `bga/` and `tools/`, **six** appear in
no document outside `docs/backlog/` and `docs/audits/`. Only
`BGA_NO_PROGRESS` and `BGA_INTERRUPT_GRACE_SECONDS` do.

`rate.py:24` chose an environment variable on the grounds that it
*"costs no help line"* — which is the same reason `bga --help`, the
inventory the architecture review's own checklist item 4 uses, cannot
report it. The choice and the blind spot are one decision.

### Re-measured before implementing (round 86)

Three of the four premises hold as written. Two corrections, marked
above; the original text is kept at the foot of this file.

- **`BGA_RATE` is narrower in the filing than in the code.** It reaches
  the "In Your Units" block in `bga/report/text.py:286` as well as
  `bga/whatif.py:172`, so it changes `bga analyze` and not only
  `bga whatif`.
- **The justification is at `rate.py:24`, not `:22`.** The quoted
  phrase is exact; line 22 opens the paragraph.
- **The eight are not one kind of thing.** `BGA_STRICT_HINTS` is a page
  global (`globalThis`, `bga/viewer/format.js:513`) and not a process
  environment variable; `BGA_TIER_ANY` is *written* into a child
  environment by `tools/dev_touching.py:281` and read by nothing in
  this tree, at either commit that added it. An inventory that demands
  a documented home for every grep match has to say which is which.

## Required Fix

An environment-variable surface a reader can find, and an inventory
that reads the tree rather than `--help`, so a variable added without
a flag still appears.

## Out of Scope

- Whether these two should be flags instead — a separate argument.

## Acceptance Test

A new `BGA_*` name in `bga/` or `tools/` with no documented home,
reddening a guard.

## Outcome (round 86, 2026-09-04) — 🔴 Open

**Premise:** held, with two narrowings — `BGA_RATE` changes `bga
analyze` as well as `bga whatif`, and the quote is at `rate.py:24`.
The count and the six/two split are exact.

### The gap, measured

```text
$ grep -rho 'BGA_[A-Z0-9_]*' bga/ tools/ | sort -u | wc -l
8
$ per name: which .md outside docs/backlog/ and docs/audits/ names it
BGA_NO_PROGRESS                ./docs/guides/cli.md
BGA_FORCE_PROGRESS             (none)
BGA_RATE                       (none)
BGA_STRICT_HINTS               (none)
BGA_INTERRUPT_GRACE_SECONDS    ./docs/guides/real-project.md
BGA_TIER_ANY                   (none)
BGA_TRACE_PROCESSOR            (none)
BGA_REQUESTED_AT               (none)
```

Both variables are real input surfaces, read rather than inferred:
`BGA_RATE=90 USD/machine-hour` adds seven lines to `bga analyze
tests/fixtures/macro_micro/run` and two to `bga whatif … --element
core.bst`; `requested_at({'BGA_REQUESTED_AT': …})` returns
`(1788516000000000, 'env:BGA_REQUESTED_AT')` and `add_queue_seam`
publishes it as `requested_at_us`/`requested_at_source`.

### After

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
      tests/unit/test_the_environment_surface_is_an_inventory.py -q
....                                                              [100%]
4 passed in 0.13s
```

`docs/guides/cli.md` gains one section, two tables, eight rows — five a
reader may set, three in the namespace that are not switches, each with
what it changes and a file that carries the name. The population is the
tracked files under `bga/` and `tools/` and a `BGA_[A-Z0-9_]+` scan of
them, so a variable added with no flag beside it is in it.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | `os.environ.get("BGA_QUIET_PHASES")` added to `bga/progress.py` — the Acceptance Test | every-name-has-a-row, 1 of 4, naming the file |
| A2 | a row for `BGA_DOM_SHIM`, a name outside the roots, cited to `tests/conftest.py` | every-row-names-something, 1 of 4 |
| A3 | the scan skips `.css` — a suffix carrying no name, so only the vacuity clause can see it | the-scan-reads-every-tracked-file, 1 of 4 |
| A4 | `BGA_RATE`'s row cites `bga/report/text.py` — a file that exists and does not name it | each-row-cites-a-file-that-carries-it, 1 of 4 |
| A5 | with A1 applied, the new name added to the section's **prose** | every-name-has-a-row, still red; adding the row turned it green |

A3 and A5 are the two shapes this repository keeps finding. A3: the
vacuity clause is "every tracked file under the roots was read", not
"the scan found something" — a narrowing that drops a file with no name
in it is invisible to every other clause. A4: the clause asks whether
the cited file *carries the name*, not whether it exists; an
`is_file()` check alone passes on `text.py`, which is `rate`'s caller
and names no variable. No guard of mine failed to discriminate.

### Deviation from the Required Fix

- **No helper under `tools/`.** `test_the_context_map_is_the_tree.py`
  requires every `tools/*.py` to have a row in fixing guide §6, and
  this track may not touch that file — so the inventory is the guard,
  which reads the tree and prints the offending names.
- **`BGA_FORCE_PROGRESS` is documented against its own comment.**
  `bga/progress.py:66` says "Deliberately not documented as a
  user-facing switch"; it is now in the second table, named as not a
  switch and carrying that reason. The alternative was an exclusion
  list, which is the thing that goes stale.
- **Two findings, filed nowhere.** `BGA_TIER_ANY` is written by
  `tools/dev_touching.py` and the pre-commit selector and read by
  nothing, at either commit that added it. And the capture pipeline
  reads a whole `BST_TRACE_*` family
  (`tools/native_trace/bwrap_shim.py`) that no `BGA_*` scan sees.

---

## The Motivation as filed (kept for the record)

```text
BGA_RATE            bga/report/rate.py:30           changes what whatif prints
BGA_REQUESTED_AT    tools/_run_context_common.py:258  changes what a capture publishes
```

`rate.py:22` chose an environment variable on the grounds that it
*"costs no help line"*.
