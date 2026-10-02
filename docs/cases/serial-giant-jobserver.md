# One giant element held to `max-jobs`, and `--jobserver auto`

A stand-in: the owner's symptom is an LLVM element; the build measured
here is [`examples/11-serial-giant`](../../examples/11-serial-giant/README.md),
the same shape at 256 C files x 9800 lines (`UX-905`, `UX-1009`).

Host: CodSpeed Graviton runner, 16 Cortex-A72 cores, 31 GB, Ubuntu
22.04, `bst` 2.8.1; runs from `bst-perf-tools/bga-bench`'s
`codspeed-probe.yml`, 3 interleaved repeats per arm, cold caches every
build. A wall is `/usr/bin/time` over `bga capture run ... -- bst build
all.bst`; spread is (max - min) / mean of the 3 repeats. Per-repeat
walls are the runs' `::notice::` annotations (`gh run view <id> --repo
bst-perf-tools/bga-bench`); run 36103304381's were read there at
`UX-902`, the others are also pasted in `UX-905`'s Outcome.

**Where the Finding text comes from.** The bench step never runs `bga
analyze`, its logs could not be fetched (403), and BuildStream is not
installed where this case was written. So both Findings below are the
code's own output for this shape, reproduced by:

```bash
PYTHONPATH=. python3 -c "from bga.cli import _builder_pool_text_lines as t; from bga.correlate import compute_builder_pool_recommendation as r; print('\n'.join(t(r(3, 16, MJ))))"   # MJ=3 (Case 1), MJ=8 (Case 2)
```

Inputs: ready-set width 3, which is what `compute_ready_set_width`
returned on a hand-built replay of toolchain, giant and leaf-a/b/c
(the graph omits `switch-4-4.bst`, `switch-4-2.bst` and the `all.bst`
stack); 16 host cores; the critical path's max-jobs `MJ`. The
parenthesis `(13-mixed-graph, 16 cores: 143.6s -> 118.3s)` is the
CLI's hard-coded reference to a different example
(`examples/13-mixed-graph`), not a number from this case.

## Case 1: `cap3`, the 8-of-40 server shape

**Symptom:** the giant builds alone on the critical path at
`max-jobs: 3` on 16 cores, and the leaves wait on it. The `off`
captures read the giant's `peak_work_concurrency` as 3, so about 13
cores sat idle while it built (inferred from that peak, not measured
per core).

**Command:**

```bash
examples/11-serial-giant/graviton_arms.sh cap3   # per arm: bga capture run --jobserver off|auto . p2.json -- bst build all.bst
```

**Finding** (verbatim output of the command above, `MJ=3`):

```text
Builders: 13 with --jobserver auto - the host's cores less the critical path's own max-jobs=3, so it can widen into the rest (13-mixed-graph, 16 cores: 143.6s -> 118.3s)
  Ready-set width: 3, from the replay's ready-set width - wider than the safe cap only with admission (BGA_ADMISSION=1), not yet measured faster
Pool size: 16, from host_cpu_count (16) — no calibrated knee supplied via $BGA_CALIBRATED_CORES, so this is uncalibrated
```

**Change:** `--jobserver off` to `--jobserver auto`, nothing else; the
builder count stayed at `bst`'s default, so this measures the
jobserver half of the advice only. The giant's `peak_work_concurrency`
went 3 to 16.

**Before:** run 36095261434, arm `off`, leg `cap3`: 263.10 / 260.75 /
260.34 s, mean 261.4 s, host CPU 729 s. Reproduce with
`examples/11-serial-giant/graviton_arms.sh` driven by
`.github/workflows/codspeed-probe.yml`.

**After:** run 36095261434, arm `auto`, leg `cap3`: 112.85 / 111.90 /
112.13 s, mean 112.3 s, host CPU 841 s. Reproduce with
`examples/11-serial-giant/graviton_arms.sh` driven by
`.github/workflows/codspeed-probe.yml`.

**Delta:** -57.0 % wall, band: 3-repeat spread 1.1 % (`off`) and
0.8 % (`auto`); host CPU +15 %. Run 36103304381 reproduced it at
-57.0 % (261.95 / 260.49 / 260.77 s to 112.59 / 112.09 / 112.52 s,
means 261.07 s to 112.40 s). No `UX-899` band exists, because there
is no baseline store of Graviton runs.

## Case 2: `pairs`, `bst`'s own default `max-jobs` 8

**Symptom:** the same giant at `bst`'s default `max-jobs`
(min(cpus, 8) = 8) on 16 cores. The `off` captures read the giant's
`peak_work_concurrency` as 8, so about half the host idled while it
built (inferred from that peak, not measured per core).

**Command:**

```bash
examples/11-serial-giant/graviton_arms.sh pairs
```

**Finding** (verbatim output of the command above, `MJ=8`):

```text
Builders: 8 with --jobserver auto - the host's cores less the critical path's own max-jobs=8, so it can widen into the rest (13-mixed-graph, 16 cores: 143.6s -> 118.3s)
  Ready-set width: 3, from the replay's ready-set width - wider than the safe cap only with admission (BGA_ADMISSION=1), not yet measured faster
Pool size: 16, from host_cpu_count (16) — no calibrated knee supplied via $BGA_CALIBRATED_CORES, so this is uncalibrated
```

**Change:** `--jobserver off` to `--jobserver auto`; the giant's
`peak_work_concurrency` went 8 to 16.

**Before:** run 36086044196, arm `off`, leg `pairs`: 139.91 / 139.20 /
138.71 s, mean 139.27 s, host CPU 751 s. Reproduce with
`examples/11-serial-giant/graviton_arms.sh` driven by
`.github/workflows/codspeed-probe.yml`.

**After:** run 36086044196, arm `auto`, leg `pairs`: 113.28 / 112.19 /
112.20 s, mean 112.56 s, host CPU 842 s. Reproduce with
`examples/11-serial-giant/graviton_arms.sh` driven by
`.github/workflows/codspeed-probe.yml`.

**Delta:** -19.2 % wall, band: 3-repeat spread 0.9 % (`off`) and
1.0 % (`auto`); host CPU +12 %. Run 36103304381 reproduced it at
-19.5 % (139.72 / 139.22 / 139.08 s to 112.49 / 111.86 / 112.11 s,
means 139.34 s to 112.15 s).
