# UX-1002: a capture names its physical cores, not only its logical CPUs

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-905 | **Found by:** Ruslan on the jobserver batch thread (2026-09-24): the 4-core gain should be measurable, and on `11-serial-giant` twice the busy cores bought `giant.bst` about 7% | **Serves:** R4, R5 (a host class is cores and threads per core, not `nproc`) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

`giant.bst` on the 4-vCPU runner, 2026-09-21 (job 106314552412):

```text
off  peak 2  45.78s  work 530   cores busy 1.86
auto peak 4  42.56s  work 530   cores busy 3.69
```

Twice the busy cores, 7% of the time. One explanation is that the
runner's 4 vCPUs are 2 hyperthreaded cores, and nothing a capture writes
can confirm or refute it: `capture-context.txt` records `nproc=4` alone.

## Decomposition

surfaces: `tools/bga_snapshot.py`'s `_capture_context`, `real-project-capture.yml`'s environment step
guards: sysfs fixtures for 4 cores, 2 cores with 2 threads each, and 2 sockets; an unreadable tree; the line inside the context
gap: none - sysfs `topology/` is the kernel's own statement of the layout the hypervisor exposes
track: session's own
gate: its own

## Required Fix

`cpu_topology()` reads `physical_package_id` and `core_id` for every
`cpuN` and prints `cpu: <logical> logical, <cores> cores, <sockets>
socket(s)`; both context writers carry the line.

## Out of Scope

What the effective core count is (a calibration, filed separately).

## Acceptance Test

`tests/unit/test_a_capture_names_its_physical_cores.py` passes; this
container prints `cpu: 4 logical, 4 cores, 1 socket(s)`, matching
`lscpu`'s `Thread(s) per core: 1`, `Core(s) per socket: 4`.

## Outcome

Gap measured: `grep -c "cpu:" capture-context.txt` on the fdsdk auto
arm (run 35970752554) reads `0`; the context carries `nproc=4` alone.

Close measured, this container:

```text
$ python3 -c 'from tools.bga_snapshot import cpu_topology; print(cpu_topology())'
cpu: 4 logical, 4 cores, 1 socket(s), Intel(R) Xeon(R) Processor @ 2.10GHz
```

| mutation | reddened | count |
|---|---|---|
| a hyperthread counts as its own core | the 2-cores-2-threads case | 1 |
| sockets read from `core_id` | all three layouts | 3 |
| the context drops the line | `test_the_context_carries_the_line` | 1 |
| the model name dropped | `test_the_cpu_model_is_named` | 1 |

Deviation: the model name was added after the fdsdk make-fix arm
(run 35985510741) spent 11104 CPU seconds on the 127k processes the
previous auto arm ran in 9048, on the same 4-logical, 2-core shape.
