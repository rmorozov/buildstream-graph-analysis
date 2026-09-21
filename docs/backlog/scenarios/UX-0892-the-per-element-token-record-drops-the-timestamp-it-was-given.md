# UX-892: the per-element token record drops the timestamp it was given

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-847, UX-846 | **Found by:** round 131, [`docs/design/in-step-parallelism.md`](../../design/in-step-parallelism.md) §6 item 2 — reading the ledger to file it showed the timestamp is already on disk, which the document did not know | **Serves:** R2 (the recipe author asking how wide their element actually ran, and when) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

The jobserver publishes one width series for the whole pool
(`jobserver_pool_series`, `tools/bga_timeline.py:596-614` — only
`PoolController.tick` rows), and per element two scalars. The wrapper
writes a timestamp on every grant and the reducer throws it away:

```text
$ sed -n '50,52p' tools/native_trace/wrappers/_common.sh
    printf '{"event":"%s","tool":"%s","pid":%s,"tokens":%s,"t":%s}\n' \
        "$1" "$bga_tool" "$$" "$bga_held" "$(date +%s.%N)" \
        >>"$BST_TRACE_JOBSERVER_LEDGER" 2>/dev/null || :

$ sed -n '1113p' tools/bst_native_build_tracer.py
        pid, tokens = row.get("pid"), row.get("tokens")

$ python3 - <<'PY'
import re, pathlib
src = pathlib.Path("bga/schemas.py").read_text()
i = src.index('"per_element": {\n            "description": "Every element Plane 1 saw')
print(sorted(set(re.findall(r'^\s{20}"(\w+)": \{', src[i:i + 2200], re.M))))
PY
['joined', 'tokens_held_max', 'tokens_held_p50']
```

`tokens_by_element` reads `pid` and `tokens` and never `t`
(`tools/bst_native_build_tracer.py:1098-1119`), so p50 and max are all
that survive. "Four tokens for two seconds of a ninety-second element"
and "four tokens throughout" reduce to the same pair.

## Required Fix

Keep `t` through the join and publish a bounded per-element width
series beside the global pool track — `(element, t_us, tokens_held)`,
from the `acquire` and `release` rows that already carry all three.
`release` closes an interval rather than opening one, so the series is
a step function, not a sample.

The wrapper stamps `date +%s.%N` (epoch seconds) while
`PoolController.tick` stamps `t_us`; one of the two converts at read
time, and the ledger's own row shape does not change.

**State the coverage, do not paper over it.** Only wrapped tools write
these rows. A real `make` that reads the jobserver pipe itself holds
tokens nobody logs, so the series covers the wrapped share and must
publish that share as a number the way `UX-891` publishes
`lb_cpu_coverage` — never a series that reads as the whole element.

The reader is `tokens_by_element` and its caller
(`tools/bst_native_build_tracer.py:1098-1135`); the published shape is
declared in `bga/schemas.py` beside `tokens_held_p50`.

Bound it like every other series in the report: a per-element cap, and
the raw rows stay in the ledger (`UX-297` is why intervals do not go
back into the report).

## Decomposition

surfaces: `tools/bst_native_build_tracer.py` (`tokens_by_element`, `summarize_jobserver_tokens_by_element`), `bga/schemas.py` (the per-element series and its coverage), `tools/bga_timeline.py` (the per-element track beside the global pool)
guards: `test_a_per_element_width_series_keeps_its_clock.py` (new), reusing UX-846's fifo/fake-tool harness for the ledger fixture
gap: unwrapped tools hold tokens nobody logs; this publishes the wrapped share as a number rather than closing the gap
track: independent of UX-891, UX-893 and UX-894
gate: not yet scheduled

Input classes: `acquire` with `t` and a mapped pid → a series point;
`acquire` with an unmapped pid → `unmapped`, as today; `release`
without a paired `acquire` → skipped, not a negative interval; a
wrapper killed before its trap (UX-852's leak) → the interval is left
open at the element's span end, and the coverage says so; no wrapped
tool in the element → series absent, not empty; the mode off → nothing
published at all.

## Out of Scope

Making unwrapped tools report — that is the capture change this filing
declines, and the reason coverage is published instead. Changing the
pool controller, the auth style, or any grant decision. The global pool
track, which stays as it is.

## Acceptance Test

`tests/unit/test_a_per_element_width_series_keeps_its_clock.py`: on a
ledger holding one element's `acquire` at t0 with 4 tokens and its
`release` at t0+2s, with the element's span 90s, the published series
is two points and the element's mean width over its span is not 4.
The wrapped-share coverage is published and is less than 1.0 when the
fixture also holds an unwrapped `make`.

**Mutations** (`falsify`):

1. Drop `t` from the `acquire` row. The series is absent for that
   element; p50 and max are unchanged. Catches a series reconstructed
   from the scalars.
2. Move the `release` row 80s later. The mean width over the span
   changes; the peak does not. Catches an interval read as a sample.
3. Mark the fixture's only tool unwrapped. Coverage falls to 0 and the
   series is absent rather than empty. Catches an absent series
   published as zero width.

## Outcome (round 132, 2026-09-20) — 🟢 Done

**Premise:** held. The wrapper stamps `date +%s.%N` on every ledger row
and `tokens_by_element` read `pid` and `tokens` and never `t`.

### The gap, measured

```text
$ sed -n '50,52p' tools/native_trace/wrappers/_common.sh
    printf '{"event":"%s","tool":"%s","pid":%s,"tokens":%s,"t":%s}\n' \
        "$1" "$bga_tool" "$$" "$bga_held" "$(date +%s.%N)" \
        >>"$BST_TRACE_JOBSERVER_LEDGER" 2>/dev/null || :

$ python3 -c '<the per_element properties of the jobserver block>'
['joined', 'tokens_held_p50', 'tokens_held_max']
```

Four tokens for two seconds of a ninety-second element and four tokens
throughout reduce to the same pair.

### After

```text
acquire 4 tokens at t0, release at t0+2s, element span 90s:
  tokens_held_p50 4   tokens_held_max 4
  tokens_held_series [[1700000000000000, 4], [1700000002000000, 0]]
  mean width over the span 0.0889, not 4
  tokens_series_coverage 0.5   (an unwrapped make in the same element)
```

The series is a step function, not a sample: an `acquire` opens an
interval and a `release` closes one, so a point is the element's total
holding after that event. Only wrapped tools write these rows, so the
wrapped share is published as a number the way `UX-891` publishes
`lb_cpu_coverage` — never a series that reads as the whole element. A
wrapper killed before its trap (`UX-852`) has its interval closed at
the element's span end and counted in `tokens_series_open`. The series
is capped at 200 points per element; the raw rows stay in the ledger.
`bga timeline` draws one counter track per element beside the global
pool track.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| C1 | a row with no clock reconstructed anyway | `test_a_row_with_no_timestamp_leaves_the_scalars_and_drops_the_series` (1) |
| C2 | a release read as a sample, not an interval close | `test_two_seconds_of_four_tokens_is_not_four_tokens_throughout` (1) |
| C3 | the wrapped share published as 1.0 | `test_the_series_covers_the_wrapped_share_and_says_so` (1) |
| C4 | an unpaired release driving the sum | `test_a_release_without_its_acquire_is_skipped_not_negative` (1) |
| C5 | a leaked interval left running | `test_a_wrapper_killed_before_its_trap_leaves_the_interval_open` (1) |
| C6 | the series unbounded | `test_the_series_is_bounded_and_says_when_it_was_cut` (1) |

### Deviation from the Required Fix

The ledger fixture is a synthetic row list rather than `UX-846`'s
fifo/fake-tool harness: the claim under test is the reducer's, and the
rows the harness produces are the rows the guard writes. The wrapped
share's denominator is the element's `make`/`gmake`/`ninja` pids read
from the raw log, which needed one more streaming pass — folded into
the pass that also reads each element's span end, not a third.

```text
make test: 8955 passed, 174 skipped, 1 warning in 329.80s (0:05:29)
make lint: All checks passed! / clean: 567 finding(s) match tests/quality_baseline.json
```
