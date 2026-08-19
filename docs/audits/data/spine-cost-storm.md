# Raw figures: the spine's cost on `examples/08-process-storm`

`UX-112`'s verification log cited a `matrix.json` that was never checked
in. `UX-129` required that a cited file exist; this is that file, in the
form the repository can actually keep — markdown a reader can read
without a tool, beside the task that quotes it.

Every row is one real `bga capture run` of
`examples/08-process-storm`'s `all.bst`, cold BuildStream cache,
`--builders 4 --max-jobs 4`, `--trace-opens` on in every cell (the
configuration `real-project-capture.yml` actually runs). 2003 processes
traced in every run, so the per-process figure is a division by a
constant rather than by a measurement.

## Run order

**Interleaved and paired**, `off` then `on` within each repeat, one
repeat after another. This is the load-bearing detail: the earlier
measurements varied the machine's state between the cells they compared
(`UX-112`'s own file records the baseline halving as the machine warmed),
and a paired design cancels drift that a blocked one absorbs into the
result. One warm-up build preceded repeat 1 and is discarded.

## The runs

| repeat | spine off | spine on | paired delta |
| ---: | ---: | ---: | ---: |
| 1 | 5.72s | 6.42s | +0.70s |
| 2 | 7.12s | 7.91s | +0.79s |
| 3 | 7.27s | 8.12s | +0.85s |
| 4 | 6.98s | 7.76s | +0.78s |
| 5 | 6.99s | 7.80s | +0.81s |
| **median** | **6.99s** | **7.80s** | **+0.79s** |

Paired delta range +0.70s to +0.85s — a 0.15s spread, against a 1.55s
spread in the `off` cell alone. Per process: **0.39 ms median, 0.35 to
0.42 ms**.

Wall clock is measured around the whole `bga capture run` invocation
(`date +%s.%N` either side), so it includes the hook compile and report
render, not only the build. That makes it an upper bound on the build's
own cost, which is the useful direction for a budget.

## Environment

BuildStream 2.7.0, real `bwrap` sandbox, 4-core container, 2026-08-19.
The same container that produced round 12's and round 13's figures.
