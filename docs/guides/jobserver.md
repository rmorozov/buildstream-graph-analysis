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

## One element, not the whole build

Four switches decide what one element gets; read top down, the first
that applies wins (`tools/native_trace/bwrap_shim.py`'s
`_jobserver_injection`):

| switch | where it lives | reaches |
|---|---|---|
| `--jobserver off` | the command line | every element: no pool at all |
| `notparallel: True` (its `make` composed `-j1`) | the element's `variables` | pinned: nothing is injected, the element builds serially, whatever the two rows below say |
| `--jobserver-auth-override 'style:glob ...'` | the `bga capture run` or `bga snapshot` command line | one capture |
| `public: bga: jobserver-auth: style` | the element's `.bst`, committed | every capture of the project |

An element none of them names gets `auto`, and what `auto` gives it
depends on its kind: a kind outside the shipped table (`make`,
`autotools`, `cmake`, `meson`, `cargo`) joins when BuildStream
composes `MAKEFLAGS`, `JOBS` or `MAXJOBS` into its sandbox
(`kind_job_env`). Without one, it joins only if `project.conf`
declares the variable its plugin reads the width from:

```yaml
variables:
  bga-jobserver-env: "MYJOBS=-j"
```

Each `NAME=PREFIX` entry is then set to `PREFIX` followed by the
project's `max-jobs` (`MYJOBS=-j4`), beside the `MAKEFLAGS` auth, and
`jobserver_decisions` reads policy `declared_env`. An element that
already composes any declared `NAME` owns its width: nothing is
injected, no other `NAME` and no auth (`unknown_kind`), and `MYJOBS=-j1`
reads `pinned`; a value off the declared prefix (`--jobs=1` against
`-j`) blocks injection the same way. A composed `MAKEFLAGS` keeps its
contents, with the auth appended. With
no declaration, or the project's `max-jobs` unread or `1`, the element
gets nothing (`unknown_kind`).

The four styles, for the last two rows:

| style | what the element's `make` gets | use it for |
|---|---|---|
| `off` | no `--jobserver-auth`, no wrappers; the recipe's own `-jN` stands | an element that must keep its own width, or misbehaves in the pool |
| `fd` | the raw `--jobserver-auth=R,W`, never rewritten to `fifo:` or scrubbed | an element on a sandbox make below 4.4 that does **not** do LTO |
| `fifo` | the `fifo:` path form | an element whose sandbox make is 4.4 or newer |
| `flto` | `fd`, plus a GCC-driver shim that strips the auth and rewrites `-flto` to a static cap | an LTO element on a make below 4.4 - `fd` there crashes GCC 13 |

```text
bga capture run --jobserver auto \
    --jobserver-auth-override 'off:giant.bst fd:libfoo-*.bst,libbar.bst flto:llvm.bst' \
    . run.json -- bst build all.bst
```

```yaml
# elements/giant.bst
public:
  bga:
    jobserver-auth: off
```

A long list reads from a file, `@PATH` (relative to the cwd, mixable
with inline groups): one group per line, globs comma- or
whitespace-separated, `#` comments and blank lines skipped. A missing file
or a style outside the four exits 2, naming `PATH:LINE`.

```conf
# overrides.conf  ->  --jobserver-auth-override @overrides.conf
off:giant.bst
fd:libfoo-*.bst libbar.bst
flto:llvm/*.bst   # inside a junction: no junction prefix
```

Globs match the element name, the first matching group wins, and the
flag repeats. A style outside the four is ignored, as is a malformed
`public:` block: the element falls through to `auto`.
The annotation works on a junctioned element too, and a glob matches the
element's name inside its own project, without the junction prefix
(`my_recipe.bst`, not `toolchain.bst:my_recipe.bst`). The flag's full
entry is in [`cli.md`](cli.md#what-each-flag-does-in-full).

To check it took effect, read the capture's summary on stderr: one
`Jobserver auth: giant.bst forced to off by ...` line per element an
override reached, and a `Warning:` per glob that matched no element in
the build, per annotation on an element the build never ran, and per
annotated style outside the four. The report's `jobserver_decisions`
rows carry the same fact: `forced_style` and `forced_by`
(`command_line` or `annotation`), absent when nothing forced the
element or it was pinned.

## What is not measured yet

One arm64 host with slow cores carries every row. Two critical chains, a
memory-bound giant, an x86 16-core host and a real project are
`UX-1014`; per-element "drew from the jobserver" in the report is
`UX-1012`.
