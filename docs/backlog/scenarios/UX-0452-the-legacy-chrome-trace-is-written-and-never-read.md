# UX-452: every capture writes a legacy Chrome trace that no reader opens

**Priority:** Low | **Status:** 🔴 Not Started | **Found by:** round 70, `UX-437`'s consumer census on its first run | **Serves:** the reader who tars a capture up for an issue, and pays for a file nobody reads | **Topic:** contracts

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

## Outcome

_Not started._
