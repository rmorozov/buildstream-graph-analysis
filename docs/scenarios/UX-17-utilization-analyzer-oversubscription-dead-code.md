# UX-17: `UtilizationAnalyzer`'s own oversubscription check (Part 30.3) is dead code, and would use the wrong field if fixed naively

**Priority:** High | **Status:** 🔴 Not Started - scope decided | **Depends on:** `UX-12`, `UX-15`

## Motivation

An external review of `UX-12`'s builders/`native_max_jobs` split raised a general architectural concern: `RunContext.max_jobs` is a spec-defined field that actually means `builders` (confirmed - see `UX-12`'s own docstring citations), a naming trap that's "easy to misunderstand" and could cause a future bug where code reads `max_jobs` expecting it to mean the native `--max-jobs` concept. Checking whether this had *already* happened anywhere in the existing codebase (not just a hypothetical risk) turned up a real, concrete instance - a genuine bug independent of anything the review directly cited.

`bga/utilisation/__init__.py`'s `UtilizationAnalyzer` implements Part 30.3's own oversubscription detection, whose docstring names three real evidence sources:

```text
1. Configuration: builders x max_jobs > effective_cpus
2. Observed: high CPU utilization
3. Duration degradation with concurrency
```

Evidence source 1 is implemented as:

```python
if self.builders is not None and self.max_jobs is not None:
    if self.builders * self.max_jobs > self.effective_cpus:
        config_oversubscription = True
        self.potential_oversubscription = True
```

But `bga/analyzer.py`'s only real call site (`_initialize_engines`, where `UtilizationAnalyzer` is actually constructed for every real `bga analyze` run) is:

```python
self.utilization_analyzer = UtilizationAnalyzer(
    cpu_accounting=cpu_accounting,
    wall_clock_us=wall_clock_us,
    max_jobs=max_jobs,
)
```

`builders` is never passed - confirmed by the call site's own adjacent comment, `# builders would come from run_context if available`, left unfinished. `UtilizationAnalyzer.__init__`'s default for `builders` is `None`, so `self.builders is not None` is **always** `False` for every real run, and evidence source 1 can never fire, regardless of any real input data.

Reproduced directly: constructing `UtilizationAnalyzer` with real CPU accounting data and `builders=100, max_jobs=8` explicitly passed correctly sets `potential_oversubscription = True`; replaying the exact real call pattern from `bga/analyzer.py` (`builders` omitted) with the identical accounting data leaves `potential_oversubscription = False` - the config-oversubscription evidence path is unreachable from any real `bga analyze` invocation today.

**A second, independent problem compounds this**: even if the wiring were fixed to pass `builders=`, `self.max_jobs` here is `run_context.max_jobs` - which, per the schema semantics `UX-12` established, means `builders` again, not the native `--max-jobs` concept. Fixing only the wiring bug would make the check compute `builders x builders`, not `builders x native_max_jobs` - a nonsensical comparison that happens to look plausible. This is the exact failure mode the review's naming-trap concern predicted, caught in the wild rather than only in the abstract.

**A third problem, found while sequencing this backlog against already-closed work**: even both of the above fixed, the check would *still* be practically unreachable in real usage. `P1-33` (already done, 🟢) deliberately gates `UtilizationAnalyzer._analyze_oversubscription`'s entire body on `cpu_accounting_available`, true only when `effective_cpus` came from a real measurement source - and `tools/bst_extract_run.py`/`tools/bst_run_context.py` deliberately never populate `cpu_accounting` at all since `P1-33` (no real CPU-measurement source exists in this pipeline). So `cpu_accounting_available` is `False` for essentially every real run today, for reasons entirely independent of this task's own wiring bug.

## Decision (resolved)

Presented to the user as three options - resolved in favor of the most thorough one: **wire `UtilizationAnalyzer.effective_cpus` from `host_cpu_count`/`cpu_budget`, and have this check delegate to `_check_process_oversubscription`'s (`UX-12`) own already-correct, already-tested logic rather than maintaining a second, independently-derived formula.**

Rationale: `host_cpu_count` (`UX-12`, a real, independently-*measured* value via `os.sched_getaffinity`) and `cpu_budget` (`UX-15`, a real, independently-*declared* value - the same legitimate category of input as `builders`/`fetchers` themselves) are **not** the thing `P1-33` banned (`effective_cpus` derived *from* `builders`) - wiring from them respects `P1-33`'s rule and makes this evidence source alive in real practice today, without needing new CPU-measurement infrastructure. And once both checks would be comparing essentially the same real inputs (`builders`, `native_max_jobs`, `host_cpu_count`/`cpu_budget`), keeping two independently-derived threshold formulas (`UX-12`'s `4 x min(cores, 8)` BuildStream-default-aware threshold vs. Part 30.3's raw `builders x max_jobs > effective_cpus`, which flags *any* excess) risks two divergent verdicts for the same real condition - a genuine correctness/trust risk, not just duplication.

## Required Fix

1. When `cpu_accounting` itself is absent (the common case), populate `UtilizationAnalyzer.effective_cpus` from `host_cpu_count`/`cpu_budget` (preferring `cpu_budget` when present, matching `UX-15`'s own governing-ceiling precedent) rather than leaving `cpu_accounting_available` permanently `False`. When a real `cpu_accounting.effective_cpus` measurement *is* present, keep using it - it's a strictly better source than a declared/detected core count.
2. Delegate evidence source 1 (`Configuration: builders x max_jobs > effective_cpus`) to `_check_process_oversubscription`'s (`bga/analyzer.py`, `UX-12`) own logic and result, rather than re-deriving a second, divergent-threshold answer. `UtilizationAnalyzer` should read the already-computed verdict, not recompute a competing one.
3. Fix the `builders`-wiring bug and the `max_jobs`-vs-`native_max_jobs` field bug as part of this consolidation (moot as separate items once delegation is in place, but the underlying data must still flow correctly into whatever `_check_process_oversubscription` itself already consumes).
4. Rename the misleadingly-named `UtilizationAnalyzer.__init__`'s `max_jobs` parameter/attribute - once evidence source 1 delegates elsewhere, this class may not need to hold `max_jobs`/`native_max_jobs` directly at all; resolve during implementation.
5. Evidence sources 2/3 (observed CPU utilization, duration degradation) stay as `UtilizationAnalyzer`'s own genuinely distinct, real signals - only evidence source 1 is being consolidated, since only it duplicates `UX-12`'s own already-correct check.

## Out of Scope

- A full rename of `RunContext.max_jobs` itself or a wire-format schema change - `max_jobs` is a spec-defined `run-context/v9` field name (Part 32.1).
- Evidence sources 2/3 - not implicated in this bug, not touched here.
- Building real CPU-accounting measurement infrastructure (cgroup/proc sampling) - out of scope for `P1-33` and still out of scope here; `host_cpu_count`/`cpu_budget` are a real, sufficient, already-available substitute for this specific check's purpose.

## Acceptance Test

1. A real `bga analyze` run with `host_cpu_count`/`cpu_budget` present (no `cpu_accounting`) and a genuine `builders x native_max_jobs` oversubscription condition produces `potential_oversubscription: true` in `--format json`'s utilisation section, matching (not contradicting) `_check_process_oversubscription`'s own `resource_oversubscription` violation for the same run.
2. A run within `UX-12`'s own default-demand threshold produces no oversubscription evidence from either check - confirms delegation, not two independently-computed answers that could disagree.
3. A test drives `UtilizationAnalyzer` through the real `bga/analyzer.py` call site (not just direct instantiation) and confirms the real fields are threaded through - a guard against this exact class of "parameter silently never populated" regression recurring.
4. Full suite green.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
