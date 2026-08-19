# 08 — process storm

A fixture with one job: be the worst case for per-process tracing cost.

## Why it exists

`UX-106`'s overhead budget is "<2% wall on `examples/06`'s baseline **and
on a configure-heavy fixture** (thousands of short-lived processes)",
with an instruction to build that fixture if no project exhibits it.
None did:

| project | processes | wall | density |
|---|---|---|---|
| `06-macro-micro-optimization` | 822 | ~45s | **18/s** |
| `08-process-storm` | 2003 | ~3.5s | **575/s** |

`examples/06`'s cost is dominated by `cc1plus`, so a per-process tracing
overhead disappears into it. A real `configure` run inverts that ratio —
hundreds of two-millisecond `sh`/`cat`/`grep` probes — and this project
reproduces the ratio without reproducing the autotools.

## The shape

One `manual` element whose install-commands are a shell loop:

```sh
i=0
while [ "$i" -lt 2000 ]; do
  cat /dev/null
  i=$((i + 1))
done
```

`cat /dev/null` rather than a shell builtin, because the point is the
`exec`. The processes are deliberately **dynamically** linked (the same
staged gcc sysroot `05`, `06` and `07` use) — a fixture whose processes
the `LD_PRELOAD` hook cannot see would measure the ptrace spine against
nothing rather than against the hook.

## Running it

```bash
examples/stage_cpp_toolchain.sh      # stages the shared sysroot
python3 -m tools.bst_native_build_tracer run \
    examples/08-process-storm /tmp/08.json -- bst build all.bst
```

Real output from that command:

```
Processes traced: 2003 (2000 matched, 3 no observed exit)
Wall span: 3.484s
```

The three unmatched are the sandbox's own `sh` wrappers, which are still
alive when the trace is cut.
