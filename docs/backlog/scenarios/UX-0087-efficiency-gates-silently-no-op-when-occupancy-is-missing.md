# UX-87: the efficiency gates silently stop gating when occupancy_ratio is absent

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-39, UX-40 (both done)

## Motivation

Both efficiency gates read `occupancy_ratio` from the two runs; if
either run lacks it, the gate helpers return False — pass — with
nothing printed (`bga/compare.py:468-500`). A pipeline that believes it
is gating on efficiency is not, and no output says so. This is the
identical failure mode UX-40 was filed to eliminate for the confidence
interaction ("a gate that is not running must say it is not running"),
one field over. UX-40's own fix text is the precedent: fail-open is a
legitimate policy, *silent* fail-open is not.

## Required Fix

When `--fail-on-efficiency-regression`, `--max-efficiency-drop` or
`--min-efficiency` is requested and either run has no `occupancy_ratio`,
print a one-line stderr warning naming the run and the missing field
(mirroring the UX-40 low-confidence warning), and publish
`efficiency_gate_evaluated: false` in compare's JSON so a CI consumer
can distinguish "passed" from "did not run". Optionally a strict flag
(`--require-efficiency-signal`) that turns the condition into a failure
for pipelines that would rather break than not gate.

## Out of Scope

- Why a run might lack occupancy (producer-side; any legacy or
  hand-built run directory can).

## Acceptance Test

Compare a run directory with `occupancy_ratio` stripped against a
normal one with `--fail-on-efficiency-regression`: exit 0 **and** a
stderr line naming the missing signal, and
`.efficiency_gate_evaluated == false` in `--format json`. With
`--require-efficiency-signal`, non-zero exit. Existing behavior with
both signals present is unchanged, including the gate exit codes.

---

## Resolution (round 11)

**Status:** 🟢 Done

Fail-open stays; silence does not.

### What a pipeline sees now

A run directory with `resource_capacities.PROCESS` removed — the real
route by which `occupancy_ratio` goes missing, not a doctored field —
compared against a normal one:

```
$ bga compare no-occupancy/ normal/ --fail-on-efficiency-regression
$ echo $?
0
```
```
Efficiency gate NOT APPLIED: --fail-on-efficiency-regression was requested,
but the baseline run has no `occupancy_ratio` signal, so there is nothing to
gate on. This is not a pass - it is an unevaluated check
(`efficiency_gate_evaluated: false` in --format json). Pass
--require-efficiency-signal to treat this as a failure instead.
```

```json
"efficiency_gate_evaluated": false,
"efficiency_gate_signal": {
  "evaluated": false,
  "missing_occupancy_in": ["baseline"],
  "gates_not_applied": ["--fail-on-efficiency-regression"]
}
```

```
$ bga compare no-occupancy/ normal/ --fail-on-efficiency-regression --require-efficiency-signal
$ echo $?
7
```

With both signals present: exit 0, stderr empty, and
`efficiency_gate_evaluated: true`.

### Three states, not two

`efficiency_gate_evaluated` is `null` when no efficiency gate was
requested at all. Publishing `false` there would tell every consumer
that never uses the gate that something is wrong. "Not asked for" and
"asked for and could not run" are different, and only the second is a
problem.

### The two gates are reported separately

`--min-efficiency` is a statement about the candidate run alone, so a
baseline with no occupancy must not turn it into a no-op. Verified end
to end — a stripped baseline still trips the floor gate on its own exit
code:

```
$ bga compare no-occupancy/ normal/ --min-efficiency 0.9
Efficiency gate FAILED: dispatch occupancy 64.3% is below the declared floor
of 90.0% (--min-efficiency). ...
$ echo $?
5
```

while a stripped *candidate* stops it, because that is the run it is
about. Reporting the two gates together would have made the first case
look broken when it is fine.

### Exit code 7, and a recorded inconsistency

The task asked only for "non-zero". `7` rather than reusing `4` or `5`:
`4` already means "your build got slower" — an overload `UX-88` records
as a mis-triage hazard in its own right — and `5` asserts the build is
less efficient, which is precisely what could not be determined.

**Recorded deviation:** `--fail-on-low-confidence` (`UX-40`) is the same
shape of flag and keeps returning `4`. It shipped that way and a
pipeline may key on it; changing it is a breaking change this task does
not own. So the two strict flags return different codes, deliberately,
and `docs/guides/cli.md` now documents both.

### Acceptance

- Stripped baseline + `--fail-on-efficiency-regression`: exit **0**,
  stderr names the gate and the run, `.efficiency_gate_evaluated ==
  false` in `--format json`. ✅
- `--require-efficiency-signal`: exit **7**. ✅
- Both signals present: unchanged — exit 0, empty stderr,
  `evaluated: true`, and the floor gate still reaches exit 5 on a real
  number. ✅
- 12 new tests in `tests/unit/test_efficiency_gate_signal.py`, one of
  which checks the *premise* (that stripping `PROCESS` really is what
  makes `occupancy_ratio` None) so the rest cannot silently start
  testing nothing. Suite 1181 passed; `make lint`, `make check-clean`
  green.
