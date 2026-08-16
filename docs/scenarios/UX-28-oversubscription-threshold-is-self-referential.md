# UX-28: the oversubscription check compares against BuildStream's own defaults, which are themselves oversubscribed - so it cannot fire on real contention

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-12, UX-15, UX-16 (all done - this is a threshold-semantics fix to the check they built)

## Motivation

`bga/analyzer.py::_check_process_oversubscription` (UX-12, hardened by UX-16, extended by UX-21, delegated to by UX-17) is the tool's answer to `UX-09`'s confirmed finding that `--builders` and native `max-jobs` compete for the same cores. Its threshold is:

```python
actual_demand  = builders * resolved_native_max_jobs
default_demand = 4 * min(governing_cores, 8)

if actual_demand > default_demand:   # -> resource_oversubscription
elif actual_demand < governing_cores: # -> resource_undersubscription
```

`default_demand` is what BuildStream would run unconfigured. On a 4-core host that is `4 × min(4, 8) = 16` concurrent processes - **4× the core count**. So the check's own "acceptable" baseline is already four-fold oversubscribed, and the two branches leave a dead zone of `[governing_cores, 4 × min(cores, 8)]` in which nothing is ever reported. On a 4-core host that dead zone is `[4, 16]`, which is every configuration a person would plausibly run.

Real repro, `examples/06-macro-micro-optimization/optimized` on a 4-core host, `bst --builders 4 --max-jobs 4`, extracted **with** `--native-max-jobs 4` explicitly supplied so the check had every input it wanted:

```
$ bga analyze -f json -d /tmp/run-06-optimized-nmj | jq .violations
[]
```

`4 × 4 = 16`, `4 × min(4,8) = 16`, `16 > 16` is false. Silence.

That silence is wrong on this run, and the contention is measured rather than assumed. Plane 2 traced the same project twice and priced the identical eight translation units of `core.bst`:

| | `core.bst` compile process-lifetime | peak concurrent `cc1plus` |
|---|---|---|
| serialized baseline (element had the host to itself) | 11.05s | 1 |
| optimized (five sibling elements compiling alongside) | 20.00s | 4 |

Same source, same compiler, same flags: +81% for the same work, exactly the effect `UX-09` documented and `UX-14` tier 2 models. The check that exists to name it reported nothing.

The undersubscription branch has the mirror-image problem: it needs `builders × max_jobs < cores`, i.e. fewer than one potential process per core, which on a 4-core host means a configuration like `1 × 2`. A run at `2 × 1` on a 32-core machine is genuinely, badly under-using the host and is likewise silent.

## Required Fix

Make the comparison about the real governing core count rather than about BuildStream's own defaults. Concretely:

- Compare `actual_demand` against `governing_cores` with an explicit, named, documented over/under tolerance band (e.g. warn above `k × cores` for a small `k`, and below `cores`), instead of against `4 × min(cores, 8)`.
- Keep BuildStream's default as *context in the message* ("BuildStream would default to N here"), not as the threshold - it is useful for a user to know, and useless as a bar.
- Say what the tolerance is and why, in the violation payload as well as the log line - this codebase's own "no silent gaps" discipline (`UX-11`'s static-binary disclaimer, `UX-26`'s omitted-groups line).

Whether `k` should be `1`, `1.5`, or `2` is a real design question with real evidence available: `UX-09`'s own 6-configuration timing table, plus the 11.05s→20.00s measurement above, are the inputs. Resolve it when picked up; do not pick a constant silently.

## Out of Scope

- `UX-29` (`native_max_jobs` never being auto-extracted). That is the *other*, independent reason this check does not fire on a real run, and it is filed separately because fixing either one alone leaves the check inert.
- `UX-21`'s memory guard, which is a separate resource dimension with its own thresholds - though it inherits the same "what is the bar" question and should be revisited alongside this.
- Feeding Plane 2's *measured* concurrency back into the check. That is the genuinely right long-term answer and is much larger; see `UX-32`, which builds the measurement this would consume.

## Acceptance Test

1. `examples/06-macro-micro-optimization/optimized` at `--builders 4 --max-jobs 4` on a 4-core host produces a real `resource_oversubscription` violation.
2. A run whose `builders × max_jobs` genuinely fits the governing core count produces no violation.
3. A badly under-provisioned run (e.g. `2 × 1` against 32 cores) produces `resource_undersubscription`.
4. The existing `UX-16` `max-jobs=0` sentinel resolution and `UX-15` `cpu_budget` precedence are unchanged. Full suite green.

## Verification Log

Filed 2026-08-16 from a real session (`docs/optimization-walkthrough-06.md`): BuildStream 2.7.0, real `bwrap` sandboxes, 4-core host. The `violations: []` output above is from a real `bga analyze` against a real capture that had `native_max_jobs` explicitly declared, and the 11.05s vs 20.00s figures are computed from two real Plane 2 traces of the same project's `core.bst`. The threshold arithmetic was read directly from `bga/analyzer.py`, not inferred from behavior.
