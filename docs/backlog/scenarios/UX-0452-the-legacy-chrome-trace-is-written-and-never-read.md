# UX-452: every capture writes a legacy Chrome trace that no reader opens

**Priority:** Low | **Status:** 🟢 Done | **Found by:** round 70, `UX-437`'s consumer census on its first run | **Serves:** the reader who tars a capture up for an issue, and pays for a file nobody reads | **Topic:** contracts

## Motivation

`UX-437` built a census that wraps `builtins.open` while every reader
runs over a complete capture and asks which of the capture's files were
opened. On its first run it found two unread. One was the item's own
subject. The other is this:

```text
readers asked: bga analyze, bga blast, bga correlate, bga timeline,
               bga view --export, bga view (payloads), the store
               listing, the store's settings
unread:        runs/<stamp>/run/chrome_trace.json
               runs/<stamp>/capture-context.txt   (declared: prose)
```

The capture layout's own row already half-admits it:

```text
bga/run_store.py:625
    (".../run/chrome_trace.json", CONDITIONAL, None,
     "the Plane 1 trace in the legacy Chrome JSON shape. Written by "
     "the extraction; `bga timeline` writes the Perfetto form instead "
     "and nothing on a read path requires this."),
```

"Nothing on a read path requires this" and "no reader opens it" are
close, but they are not the same sentence, and the second is now
measured rather than asserted. `bga timeline --format chrome` writes
the legacy shape **on demand, from `trace.json`** — so the copy sitting
in every capture is not what that command reads either.

This is the same shape as `UX-437` and a smaller instance of it: a file
written on every capture that no consumer has. It is filed rather than
fixed there because deleting a file from the capture layout is a
contract change with its own blast radius — `UX-381` names the path,
`test_the_capture_directory_is_a_contract.py` reads the layout, and a
capture written by an older `bga` will keep having one.

## Required Fix

- **Decide whether it is still written.** Either it has a consumer that
  the census cannot see — a person opening `chrome://tracing` on the
  file by hand is a real one, and if that is the answer the layout row
  should say so and the census should carry the declaration — or the
  extraction stops writing it.
- **If it stops**, the layout row becomes a note that older captures
  have one, and the census declaration `UX-437` left goes away rather
  than staying as a permanent exemption.
- **Measure what it costs first**, on the seeded scale run rather than
  on eleven elements: a decision to keep a file needs its size beside
  it.

## Out of Scope

- **`capture-context.txt`**: the other file the census found unread, and
  the layout says `Never parsed` about it deliberately — it is prose for
  a person (`UX-146`), which is a consumer the census structurally
  cannot observe.
- **`bga timeline --format chrome`**: the on-demand writer stays
  whatever this decides, because it renders from `trace.json` and does
  not read the file in question.

## Acceptance Test

```bash
bga gen-synthetic /tmp/scale --seed 1
bga analyze /tmp/scale --diagnostics
ls -l /tmp/scale/chrome_trace.json
make test
```

The census in
`tests/unit/test_every_captured_file_has_a_consumer.py` passes with
`NO_CONSUMER_DECLARED` one entry shorter, whichever way the decision
goes.

## Outcome (round 71, 2026-08-31) — 🟢 Done

### The decision: the extraction stops writing it

The item asked whether a consumer exists that the census cannot see.
One was **named, in the write site's own comment**:

> the same real, human-inspectable artifact the user's own existing
> personal workflow (visualizing a real build timeline in perfetto.dev)
> already relies on `tools/bst_log_to_chrome_trace.py` for

That reader is now served twice over, and better. `bga timeline` writes
the **Perfetto-native** form with both planes, the dependency flows and
the host counters in it, and `bga view`'s hand-off opens it in one
click. And the legacy shape itself has not gone anywhere: `bga timeline
--format chrome` renders it **on demand, from `trace.json`** - which is
what makes this a move rather than a capability dropped, and is the
second clause of the guard.

So the copy in every capture goes. Nothing is lost that was not already
one command away.

### What it cost

Measured on the two committed captures that have one:

```text
                                 chrome_trace   trace.json   snapshot
tests/fixtures/with_timeline          7,957 B      2,613 B     94,166 B   8.4%
examples/08-process-storm             2,369 B        797 B    111,772 B   2.1%
```

3.05x and 2.97x `trace.json`, which is 296-331 B per event at 2.18-2.67
events per Plane 1 span. At `gen-synthetic --seed 1`'s **1,202 spans**
that projects to **776 KB - 1.06 MB**, against a whole snapshot of
760,076 B:

```console
$ bga gen-synthetic /tmp/scale --seed 1
  builders:     16
  horizon:      355.13s
  total work:   5536.77s
$ du -sb /tmp/scale
760076  /tmp/scale
```

The convenience copy would outweigh the capture it sits in. That is a
projection from two measured rates rather than a measurement - stated
as one, because this environment has no `bst` to extract a real build
of that size, and the item asked for the figure to be beside the
decision.

### The acceptance test is wrong, and this is the correction

```bash
bga gen-synthetic /tmp/scale --seed 1
ls -l /tmp/scale/chrome_trace.json
```

`gen-synthetic` writes `graph.json`, `run-context.json` and
`trace.json` and nothing else - it produces a run directly and never
runs the extraction, so the file the `ls` names has never existed on
that path. The two committed captures above are where the file actually
is, and they are what the cost was measured on.

### Where the row went

`derived`, not deleted. The capture layout already has the three-way
presence `UX-381` argued for, and `derived` means exactly this: "absent
means nothing. It is a cache or a convenience and is rebuilt on
demand." A capture taken before this item has one and still satisfies
the contract; a capture taken now does not, and also satisfies it. No
new presence word was needed.

`NO_CONSUMER_DECLARED` is one entry shorter, as the Acceptance Test
asks, and the entry moved to `NOT_IN_THE_FIXTURE` rather than being
dropped: **a file with no consumer became a file with no writer**, which
is the only way that list gets shorter without the census being
weakened. The census fixture deletes the copied file, because its
population is "what a capture written by this `bga` holds".

### The instrument, and why it is not `bst`-gated

The end-to-end extraction tests need BuildStream on `PATH` and skip
everywhere it is absent - and a guard for this claim that only ran
where `bst` is installed is exactly the shape `UX-449` was filed on.

`_extracted()` runs the **real** `extract_run` against the committed
`tests/fixtures/with_timeline/build.log`, with only the `bst show`
subprocess replaced - by that fixture's own `graph.json` rendered back
into `bst show`'s field format, so the extraction parses what it would
have parsed. Everything it does with the log, the graph and the output
directory is the shipping code:

```console
$ python3 -m pytest tests/unit/test_bst_extract_run.py -q
22 passed in 5.91s

summary: {'targets': ['all.bst'], 'elements': 11, 'spans': 11}
wrote:   ['graph.json', 'run-context.json', 'sources.json', 'trace.json']
```

The clause asserts the **set** of four, not one absence, so a file
added back is as visible as one dropped.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| C1 | the extraction writes `chrome_trace.json` again | `test_one_extraction_writes_exactly_four_files` (1 failed, 21 passed) |
| C2 | `--format chrome` stops producing the legacy shape | `test_the_legacy_shape_is_still_one_command_away` — `unknown timeline format 'chrome'` (1 failed, 21 passed) |
| C3 | the census fixture keeps the copied legacy file | `test_nothing_in_the_capture_is_written_and_never_read` (1 failed, 12 passed) |

C2's first form renamed the `fmt == "chrome"` comparison and found no
such string - the branch is on `FORMAT_CHROME`, a constant. Retargeted
at the constant, it discriminates. A mutation that cannot find its site
is not a mutation, and it is recorded rather than quietly retried.

### Documents

`docs/spec/specification.md` 32.6's row and `bga/run_store.py`'s row
are the same sentence in two places and both moved, which is what
`test_the_presence_and_the_contract_match_row_for_row` holds. The
module docstring of `tools/bga_timeline.py` said "every extraction
writes `run/chrome_trace.json`" in its round-20 history paragraph and
now says what happened to it - fixing guide §3.10, a document this
change made wrong.

### Deviation from the Required Fix

- **None on the three bullets.** The decision was made and the
  extraction stops writing it; the layout row is a note that older
  captures have one; the cost was measured first.
- The **Acceptance Test's first two lines could not be run as written**,
  for the reason above: `gen-synthetic` never writes the file. Its
  fourth line (`make test`) was, and the clause it names -
  `NO_CONSUMER_DECLARED` one entry shorter - is met.

### The suite

```console
$ make lint
All checks passed!

$ make test
5479 passed, 28 skipped, 1 warning in 280.79s (0:04:40)
```
