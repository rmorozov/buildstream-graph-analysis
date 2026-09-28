# UX-1079: `bga capture report` on a gzipped raw log drops every opened path, silently

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R1, R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`load_and_summarize` opens the log through `_open_maybe_gzipped`
(`UX-330`) for the process pass, then re-opens it with plain `open`
for the opens pass (`tools/bst_native_build_tracer.py:6764`). On a
`plane2.log.gz` - the name every snapshot stores - the second pass
reads deflate bytes and finds nothing. The same 1,202-element log
([the audit](../../audits/perf-snapshot-view-2026-09-28.md)):

```text
m_p10.log     opens_captured: 1,202 elements   parse_open_lines: 1202
m_p10.log.gz  opens_captured: {}               parse_open_lines: 0
```

`declared_vs_used` is omitted with it, and nothing says so. The
two-plane recipe in project memory gunzips first, which hides it.

## Decomposition

Input classes: the same log plain and gzipped, with and without `OPENS` blocks. Journey: `bga capture report`.

## Required Fix

In `tools/bst_native_build_tracer.py`: The opens pass opens the log through `_open_maybe_gzipped` too.

## Out of Scope

The capture itself, which reads the uncompressed log.

## Acceptance Test

`tests/unit/test_opens_from_a_gzipped_log.py`: `capture report` on a gzipped copy of a log with `OPENS` blocks
returns the same `opens_captured` as on the plain file. Mutation:
restore the plain `open`, and it reds.

## Outcome

Gap: `load_and_summarize`'s opens pass re-opened
`raw_log_path` with plain `open`, after the process pass had already
gone through `_open_maybe_gzipped` (`UX-330`) two lines above it - the
audit's `m_p10.log.gz` read `opens_captured: {}` against the plain
file's 1,202 elements.

Close: the opens pass now opens through `_open_maybe_gzipped` too, one
`with` clause changed at `tools/bst_native_build_tracer.py:6764`.
`python3 -m pytest tests/unit/test_opens_from_a_gzipped_log.py -q`:
`1 passed in 0.49s`.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| restore the plain `open` on the opens pass | `test_opens_captured_is_the_same_plain_or_gzipped` | 1 failed (gz `opens_captured` `{}` vs plain's `{'a.bst': ...}`) |
