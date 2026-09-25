# When `--jobserver auto` pays

`--jobserver auto` lets an element's `make` borrow the cores the other
builders leave idle. It pays when **one wide element sits on the critical
path running below the host's cores**; elsewhere it costs about one
`bst show`. Every number below is a pasted reading from one host:
CodSpeed's Graviton runner, 16 Cortex-A72 cores, cold cache, 3 repeats
per arm, `examples/11-serial-giant/graviton_arms.sh`.

## The extremes

| Graph shape | Off | Auto | Wall | Record |
|---|---|---|---|---|
| One wide element, `max-jobs: 3` on 16 cores (the 8-of-40 server shape) | 261.4s | 112.3s | **−57%** | `UX-905`, runs 36095261434, 36103304381 |
| One wide element, BuildStream's default `max-jobs` (8 on 16 cores) | 139.2s | 112.2s | **−19%** | `UX-905`, run 36086044196 |
| One giant plus 25 single-job elements, `--builders 8` (= 16 − the giant's 8) | 143.6s | 118.3s | **−18%** | `UX-1005`, run 36163582462 |
| Independent parallel elements that already fill every core | 22.6s | 23.6s | +1.1s | `UX-1011`, run 36129369038 |
| Serial chain of `-j1` elements | 30.25s | 30.46s | no change | `UX-679` |
| 4-vCPU cloud runner (2 cores with SMT) | 235s | 233s | −1%, inside noise | `UX-1004` |

Medians of three except the last two rows, which are single pairs.

## What to tell a user

If `bga analyze` shows a wide element on the critical path whose peak
width is its `max-jobs` and below the host's cores, set `--builders` to
the host's cores less that element's `max-jobs` and turn on auto. On 16
cores with an 8-wide giant:

```text
bga capture run --jobserver auto . run.json -- bst --builders 8 build all.bst
```

`bga analyze --format text` prints the builder count itself (`UX-1005`). Expect
about 20% on BuildStream's defaults and up to about 55% where `max-jobs`
is capped far below the machine.

## What it costs

- **Host CPU +12% to +15%** for identical work (751s → 842s; 729s →
  841s at `max-jobs: 3`) — mostly the compiler running slower with 16
  jobs on the chip (`cc1` 454s → 540s).
- **Peak host memory 448 MB → 1611 MB** on the `max-jobs: 3` pair. Check
  it on memory-tight agents.
- **About 2.3s fixed** per build: one `bst show` before the build starts
  (`UX-1011`).

## What not to do

**Do not raise `--builders` alone.** On `13-mixed-graph`, 8 builders read
the same 143.6s as 4, and 32 read about 206s (+44%): the 25 single-job
elements start at once and crowd the giant off the cores. Auto at 32
builders recovers part of it (about 182s) and sandbox admission
(`BGA_ADMISSION=1`) made it worse (202/217/203s), which is why admission
is opt-in.

## What is not measured yet

One arm64 host with slow cores carries every row. Two critical chains, a
memory-bound giant, an x86 16-core host and a real project are
`UX-1014`; per-element "drew from the jobserver" in the report is
`UX-1012`.
