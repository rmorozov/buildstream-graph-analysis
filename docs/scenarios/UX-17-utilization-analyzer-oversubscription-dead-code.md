# UX-17: `UtilizationAnalyzer`'s own oversubscription check (Part 30.3) is dead code, and would use the wrong field if fixed naively

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** `UX-12`

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

## Required Fix

1. Wire `native_max_jobs` (not `run_context.max_jobs`) and `builders` (`resource_capacities.get('PROCESS')`) into `UtilizationAnalyzer` at its real call site in `bga/analyzer.py`, so evidence source 1 actually reflects BuildStream's real two-axis concurrency model - the same distinction `UX-12`'s own `_check_process_oversubscription` already gets right.
2. Given `UX-12` already implements a correct, real oversubscription/undersubscription check using the properly-distinguished fields (and, per `UX-15`, a governing `cpu_budget`), decide explicitly whether `UtilizationAnalyzer._analyze_oversubscription`'s evidence-source-1 should be: (a) fixed to delegate to/reuse `_check_process_oversubscription`'s own logic (avoiding two independently-maintained oversubscription checks that could silently drift apart again), or (b) kept as a genuinely distinct, Part-30.3-specific signal with its own corrected wiring. Don't fix the wiring bug and leave two divergent implementations without deciding which.
3. While touching this: rename the misleadingly-named `UtilizationAnalyzer.__init__`'s `max_jobs` parameter (and `self.max_jobs` attribute) to something explicit (e.g. `builder_capacity`) if it's meant to represent `builders`, or replace it with `native_max_jobs` if that's what evidence source 1 should actually use - don't leave a parameter named `max_jobs` holding a `builders` value in a class whose whole job is CPU-oversubscription analysis, the single place this ambiguity is most dangerous.

## Out of Scope

- A full rename of `RunContext.max_jobs` itself or a wire-format schema change - `max_jobs` is a spec-defined `run-context/v9` field name (Part 32.1); this task is about the internal `UtilizationAnalyzer` parameter/attribute naming and wiring, not the schema.
- Evidence sources 2/3 (observed CPU utilization, duration degradation) - not implicated in this bug, not touched here.

## Acceptance Test

1. A real `bga analyze` run with real CPU accounting data (`cpu_accounting.effective_cpus` present) and a genuine `builders x native_max_jobs > effective_cpus` configuration produces `potential_oversubscription: true` with real evidence in `--format json`'s utilisation section - currently always `false`/`INSUFFICIENT_EVIDENCE` or `LOW` regardless of input.
2. A test constructs `UtilizationAnalyzer` (or drives it through the real `bga/analyzer.py` call site, not just direct instantiation) and confirms `builders`/the correct native-parallelism value are both actually threaded through - a real guard against this specific class of "parameter silently never populated" regression recurring.
3. Full suite green.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
