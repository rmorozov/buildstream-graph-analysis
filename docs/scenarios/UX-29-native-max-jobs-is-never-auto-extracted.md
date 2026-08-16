# UX-29: `native_max_jobs` is never auto-extracted, so the whole capacity-guard chain is inert on runs produced by the documented pipeline

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-12, UX-18 (both done)

## Motivation

`bga`'s capacity guards - `UX-12`'s oversubscription check, `UX-16`'s `max-jobs=0` sentinel resolution, `UX-17`'s `UtilizationAnalyzer` delegation, `UX-21`'s memory guard - all key off `run_context.native_max_jobs`. That field is populated only when the operator passes `--native-max-jobs N` to `tools/bst_extract_run.py` (or `tools/bst_run_context.py`) by hand; `tools/_run_context_common.py` documents it as "purely operator-supplied".

Follow the repo's own documented ingestion recipe (`README.md` → "Use it on your real project") and you get:

```
$ python3 -m tools.bst_run_wrapped examples/05-cmake-cpp-toolchain /tmp/build.log \
    -- bst --builders 4 --max-jobs 4 build all.bst
$ python3 -m tools.bst_extract_run --format wrapped examples/05-cmake-cpp-toolchain /tmp/build.log /tmp/run
$ cat /tmp/run/run-context.json
  ...
  "scheduler": {
    "builders": 4,
    "fetchers": 10,
    "pushers": 4,
    "native_max_jobs": null      <-- the run was --max-jobs 4
  }
```

and therefore, from `bga analyze -f json`, `violations: []` - the guards return early on `if native_max_jobs is None`. Every capacity feature built across `UX-12`/`UX-15`/`UX-16`/`UX-17`/`UX-21` is off by default on real runs, silently, and nothing in the report says so.

The value is not merely available - it is **already in the file the extractor just parsed**. Line 1 of every `tools/bst_run_wrapped.py` log is:

```
[wrapper][2026-08-16 18:22:59,383] INFO: Executing command: bst --builders 4 --max-jobs 4 build all.bst
```

and `tools/bst_log_to_chrome_trace.py` already has an `EXEC_CMD_RE = re.compile(r"^Executing command:\s+(.*)$")` matching that exact line. `builders`/`fetchers`/`pushers` are recovered from BuildStream's own `Maximum Build Tasks:` header lines in the same parser. `--max-jobs` is the one scheduler input sitting in plain text that nothing reads.

`docs/scenarios/README.md`'s own filing-history note records that a prior external review raised "`native_max_jobs` isn't auto-extracted from `bst show`/the log" and it was triaged as *not worth a dedicated task*. That triage was about `bst show`, where the value genuinely is not exposed per-element. The wrapped log is a different source and it does carry it, and the evidenced consequence - five shipped features inert on the documented happy path - is what changes the call. Filing it now with that evidence rather than re-litigating the earlier note.

## Required Fix

1. In the wrapped-log parser, capture `--max-jobs N` / `--max-jobs=N` from the `Executing command:` line, alongside the existing `builders`/`fetchers`/`pushers` capture, and thread it into `run_context.native_max_jobs`.
2. Keep an explicit `--native-max-jobs` override, and keep the two distinguishable: record where the value came from (`"parsed_from_invocation"` vs `"operator_declared"` vs absent) so the guards can say what they are certifying against. This mirrors `UX-17`'s own `effective_cpus_source` provenance field.
3. Raw-format (`--format raw`) logs have no wrapper line and legitimately cannot supply this - keep `None` there, and consider saying so once in the report rather than silently degrading (`UX-25`'s pattern).
4. When `native_max_jobs` is unavailable *and* a capacity guard therefore did not run, say that in the report. A user should not have to read `bga/analyzer.py` to learn that a check they think is on has never executed.

## Out of Scope

- `UX-28`'s threshold semantics. Fixing extraction makes the check *run*; `UX-28` is why it still would not fire. Both are needed.
- Auto-detecting a per-element parallelism override - that is `UX-31`, and it is a different mechanism entirely.
- `host_cpu_count`/`cpu_budget`, which are already handled correctly (auto-detected and operator-declared respectively, per `UX-15`).

## Acceptance Test

1. `tools/bst_extract_run.py --format wrapped` against a log whose first line records `--max-jobs 4` produces `native_max_jobs: 4` with no extra flag.
2. An explicit `--native-max-jobs` still overrides, and the provenance field distinguishes the two.
3. `--format raw` still yields `None` and the report says the capacity guards did not run.
4. `tools/bst_run_context.py` behaves identically (the `UX-18` parity requirement). Full suite green.

## Verification Log

Filed 2026-08-16 from a real session. The `run-context.json` excerpt is a real file produced by the exact command sequence in `README.md`, against a real `bst --builders 4 --max-jobs 4` build of `examples/05-cmake-cpp-toolchain` on a 4-core host; the wrapper log line is quoted verbatim from that run's own log. `EXEC_CMD_RE`'s existence was confirmed by reading `tools/bst_log_to_chrome_trace.py` directly.

Real end-to-end re-verification, re-extracting the exact real capture from this doc's Motivation with **no new flags** (`python3 -m tools.bst_extract_run --format wrapped ...`, against a real `bst --builders 4 --max-jobs 4 build all.bst` log):

```
native_max_jobs = 4
native_max_jobs_source = parsed_from_invocation
host_cpu_count = 4
scheduler = {'builders': 4, 'fetchers': 10, 'pushers': 4, 'native_max_jobs': 4}
```

and the two sides of item 4, from real `bga analyze -d` runs on the new and the old extraction of the same build:

```
# newly extracted - guards ran, note stays clean
  Note: LB/Efficiency Score certify against this run's recorded resource capacities ... (see UX-09/UX-15).

# previously extracted, native_max_jobs null - guards inert, and it now says so
  Note: ... (see UX-09/UX-15). Capacity checks (over/under-subscription, memory) did not run
  for this run - missing: native_max_jobs. They are inert here, not passing; a wrapped log
  records --max-jobs on its own first line (UX-29), or declare the missing value explicitly
  at extraction time.
```

Acceptance Test items 1-4 all confirmed with real data. Note what this fix does **not** do, deliberately: the guards now *run* on this real 4-builders x 4-max-jobs run on a 4-core host and still report no violation, because the threshold compares against BuildStream's own already-oversubscribed defaults - that is `UX-28`, filed separately for exactly this reason. Full suite green (678 passed, up from 668), `make lint` clean.
