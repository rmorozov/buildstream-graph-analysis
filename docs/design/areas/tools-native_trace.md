# Plane 2: intra-element native-build-system tracing (`UX-11`)

Moved from [`docs/design/architecture.md`](../architecture.md)'s
Plane 2 chapter (`UX-806`); the four `tools/native_trace/` members
stay named there, where their guard reads them.

`tools/bst_native_build_tracer.py` wraps a real `bst build` invocation: a `bwrap` shim placed ahead of the real binary in `$PATH` injects an `LD_PRELOAD` hook (`tools/native_trace/hook.c`) into every dynamically-linked process the sandbox execs, recording real `CLOCK_MONOTONIC` start/end timestamps. Validated end-to-end against a real `cmake`+`make`+`gcc` build (98 real traced processes, reproduced real `-j4` compile concurrency across independent runs). Known, honestly-reported limitation: statically-linked processes are invisible to this mechanism and there is no way to detect that gap from outside — every report carries a fixed disclaimer rather than a false completeness claim. Full design history (five brainstormed options, an external design contribution, a risk-reduction spike, a second external review that was checked and refuted, and the final validated mechanism) is in `docs/backlog/scenarios/UX-0011-native-build-system-profiler-tool.md` — read that only if you need the *why*; this doc is the *what, today*.

The hook records four things per process. The first is what `UX-11` shipped; the rest arrived as later rounds found questions timing alone could not answer:

1. **Lifecycle** (`UX-11`) — `CLOCK_MONOTONIC` START/END, which is what every timing analysis below is built on.
2. **Real CPU time** (`UX-45`) — `getrusage(RUSAGE_SELF)` plus `RUSAGE_CHILDREN` in the destructor, the one place with access to the kernel's own accounting for a process about to exit. This is `bga`'s **only** CPU-time measurement anywhere; everything in Plane 1 is slot occupancy, and deliberately still says so (see `UX-36` below). Its value is a question Plane 1 structurally cannot answer — *was this element CPU-bound or waiting?* On a real capture, `core.bst` (pinned with `notparallel: True`) runs at **0.87 cores busy** while every sibling runs at ~1.7. Coverage is always reported: a process killed by a signal, or one replaced by `exec`, runs no destructor and is counted as **unmeasured**, never as zero (~19% of processes in a real `examples/06` build).
3. **Peak resident memory** (`UX-63`) — `ru_maxrss` from that same `getrusage` call, giving a *measured* per-element peak where the memory-oversubscription guard had only ever had operator-declared estimates. Reported as "no single process here exceeded this", never summed: two processes peaking at different moments never held the sum between them.
4. **Opened file paths** (`UX-46`, opt-in via `--trace-opens`) — `open`/`openat` interposition, deduplicated in-process and flushed once at exit, and re-flushed rather than dropped when the window fills (`UX-57` — the fixed buffer had been losing 70% of a real build's opens). Opt-in because unlike the others it runs on a genuinely hot path. Matched against `bst artifact list-contents`, this answers *"which of this element's declared build dependencies did its sandbox never read?"* — the last macro-level gap, and the one problem in `examples/06` that no Plane 1 signal could find. It **refuses rather than guesses**: an element with no observed opens (a statically-linked build looks identical to one that used nothing) or with a truncated read set is reported `uncovered`, never as having unused dependencies.

### Element attribution: the hardest thing in Plane 2

Every traced process is tagged with its owning BuildStream element (`UX-23`, originally parsed from BuildStream's own `--dir` bwrap option). That parse is a *path convention*, and a real project overrides it: on `freedesktop-sdk`, which sets `build-root: /buildstream-build`, **99.4% of 127,630 processes landed in one bucket that is not an element** (`UX-56`), and every per-element figure was a whole-build figure wearing an element's name.

The fix does not guess. Each sandbox is correlated against Plane 1's own BUILD spans, on the sandbox's **end** edge — chosen by measurement, not by argument: requiring the whole interval inside the span resolved 2 of 9 sandboxes with 7 unmatched, because Plane 1 timestamps a line when the wrapper reads it and every sandbox therefore begins *before* its element's logged BUILD START; matching on the end edge resolved 8 of 9 with none unmatched (`UX-64`). The same work removed an unsound elimination pass: a real project runs more than one sandbox per element, so striking a resolved element from every other candidate set could attribute a sandbox to the *wrong* element.

Measured on a real capture, in order: **0.6% → 14.9% → 86.1%** of processes attributed to a named element. The remainder sits in an explicitly unresolved bucket, and every consumer states its coverage rather than folding it in — including `detect_redundant_operations`, which had been counting that bucket as a second element and thereby sourcing **87% of its claimed recoverable time from an element that does not exist** (`UX-73`).

### What is built on the per-element split

`compute_binary_cost` (`UX-69`) reports, per element, where the CPU actually went — binaries ranked by measured CPU rather than by invocation count, with the single-process case called out separately. On a real capture `cc1plus` is **81.3% of the CPU** of the element that is 43.5% of the build, and `dwz` is **one process holding 138.6s**, a serialization point no job count can help. Ranked by count neither is visible: `as` runs twice as often as `cc1plus` for a tenth of the cost.

`compute_per_element_parallelism` (`UX-32`) reports, per element, the parallelism its native build system *actually achieved* against the `-jN` it asked for - splitting real work processes (compilers, assemblers, linkers) from orchestration that spends its life waiting on children, and emitting two findings: `pinned_to_one_job` (this element asked for `-j1` while its siblings asked for more - the `notparallel` case, invisible to any achieved-vs-requested ratio, since a pinned element gets exactly what it asked for) and `underachieved_requested_jobs`. `detect_redundant_operations` (`UX-23`, rescored by `UX-37`) flags real operations repeated independently across multiple elements' own sandboxes, ranked by *recoverable wall-clock* rather than by process time summed across elements that ran concurrently, and excluding both each element's own build driver (identical across elements by construction, entirely different work in each — `UX-37`) and its own top-level command block, which bwrap's PID namespace identifies structurally rather than by string matching (`UX-73`). `tools/native_trace_to_chrome_trace.py` (`UX-24`) exports Plane 2 traces as Chrome Trace JSON, standalone or combined with Plane 1's own real export for the same run — `bst_native_build_tracer.py run --wrapped-log PATH` captures both planes from one single real `bst build` invocation.

### The jobserver: a subtool behind an import boundary (`UX-901`)

`UX-841`..`UX-852` gave the tracer a second, opt-in mechanism: a token
pool it injects into sandboxes, so several elements' native build
systems (`make`/`ninja` and their wrapped tools) can share the host's
real core count rather than each assuming it owns it. Acting on a
sandbox is a different risk class from reading it - round 126's
minimal-sandbox breakage and `UX-878`'s GCC LTO ICE are both on the
record - so `UX-901` moved it behind an import boundary rather than
distributing it through the capture path: `tools/jobserver/` owns the
pool (`open_jobserver`/`close_jobserver`, `PoolController`, `Broker`,
`create_jobserver_proxies`, the plan/PSI/meminfo readers) and the
ledger (the raw-row reader, the per-element/summary reductions,
`jobserver_auth_style`), and `tools/bst_native_build_tracer.py` is its
only caller. `report_block()` is the one function that crosses back:
every `jobserver*` key `analyze/v7` publishes, built from inputs the
tracer already had to read (the wrapper-policy probe reaches
`bga.progress`; the raw log's pid/tool maps need the tracer's own
stream parser) rather than re-read inside the package. The package
imports stdlib and `tools/native_trace/bwrap_shim.py` only - never the
tracer, never `bga` - so a capture with `--jobserver off` publishes
every key one with the mode on does, minus the ledger the mode itself
writes, and the code can leave for a separate project of BuildStream
helpers without a call-site hunt. Not a plugin system: nothing here is
discovered or loaded dynamically, and `bga` gains no second one for
anything else this way.

## `BST_TRACE_*` — Plane 2 and Plane 3 (`UX-635`)

The capture path has a second namespace the same size, and until
`UX-635` [`cli.md`](../../guides/cli.md#the-environment-bga-reads-ux-630)'s table's population was as wide as the one prefix somebody
typed into the guard. These are not `bga`'s own switches in the sense of
that table: they are how `bga snapshot` drives the `bwrap` shim, the
`LD_PRELOAD` hook and the ptrace spine, and most of them are set *for*
you. The three kinds are separated because a reader needs to know which
is which before touching any of them.

**What you may set, driving a capture by hand:**

| name | what it changes | where |
|---|---|---|
| `BST_TRACE_OPENS` | records `open()` as well as `exec`, forwarded into the sandbox by the shim. The `opens` half of Plane 2, and the more expensive half | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_OPENS_SEEN` | the sandbox's table of path hashes already written, so a path its processes repeat is written once (`UX-1241`); set by the shim per invocation, a file in the bind directory | `tools/native_trace/bwrap_shim.py`, `tools/native_trace/hook.c` |
| `BST_TRACE_SPINE` | turns the ptrace spine on for this element — Plane 3, which sees the processes `LD_PRELOAD` cannot | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_SPINE_POLICY` | `auto`, `on` or `off`; `auto` resolves per element against the census below rather than for the whole build | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_SPINE_CENSUS` | the census `auto` consults to decide whether this element is worth the spine's price | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_NO_INJECT` | `=1` runs the shim through to the real `bwrap` injecting nothing, so a refusal can be told from a capture defect. `bga snapshot --no-inject` sets it | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_DIAGNOSTICS` | a path the shim writes `bwrap`'s own stderr to, so a sandbox that refused says what it objected to | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_ARGV_MAX` | with `BST_TRACE_ARGV_LOG` set, the most `bwrap` invocations the shim records into that log; the default is the shim's `DEFAULT_ARGV_RECORD_LIMIT` (32), a non-integer falls back to it, 0 records none | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_WRAPPER_CAP` | the most tokens one jobserver wrapper (`ld.lld`, `lld`, `ld.gold`, `mold`, `ninja`) may acquire before running its tool — the pool's own ceiling, set only when `--jobserver` is on (`UX-846`) | `tools/native_trace/wrappers/_common.sh` |
| `BST_TRACE_LTO_CAP` | the static `-flto=N` cap the GCC-driver shim (`gcc`/`g++`/`cc`/`c++`) rewrites an already-present `-flto`/`-flto=jobserver`/`-flto=auto` to — default `nproc`, the same ceiling `resolve_jobserver_ceiling`'s own `auto` uses; `bga capture run --lto-cap N` sets it (`UX-880`) | `tools/native_trace/wrappers/_common.sh` |
| `BST_TRACE_WRAPPER_DIR_OVERRIDE` | an operator's own wrapper directory (`docs/guides/wrapper-contract.md`), mounted alongside or instead of the shipped one; `bga capture run --wrapper-dir PATH` sets it (`UX-881`) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_WRAPPER_MODE` | `augment` (default) or `replace` — whether the operator's directory above adds to the shipped mount or takes its place entirely; `bga capture run --wrapper-dir-mode` sets it (`UX-881`) | `tools/native_trace/bwrap_shim.py` |

**What the capture path sets for you.** Setting these by hand does not
configure a capture, it desynchronises one — the tracer writes them
into the child environment and the shim requires them:

| name | what it is | where |
|---|---|---|
| `BST_TRACE_REAL_BWRAP` | the real `bwrap` the shim shadows and finally executes; the tracer sets it to `shutil.which("bwrap")`, and the shim's `set BST_TRACE_REAL_BWRAP` message is read in [`real-project.md`](../../guides/real-project.md#troubleshooting-plane-2-recorded-zero-processes) | `tools/bst_native_build_tracer.py` |
| `BST_TRACE_BIND_SRC` | the host directory holding the hook and the spine | `tools/bst_native_build_tracer.py` |
| `BST_TRACE_BIND_DST` | where that directory is bound inside the sandbox | `tools/bst_native_build_tracer.py` |
| `BST_TRACE_PRELOAD_SO` | the hook's path *inside* the sandbox, for `LD_PRELOAD` | `tools/bst_native_build_tracer.py` |
| `BST_TRACE_LOG_DST` | where the trace log lands inside the sandbox | `tools/bst_native_build_tracer.py` |
| `BST_TRACE_LOG` | the same path as the hook and the spine read it | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_ELEMENT` | the element a record belongs to — the key Plane 1 joins on | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_INVOCATION` | which invocation of that element, so a retry is not merged into its first attempt | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_INVOCATION_LOG` | the host-side file the shim appends one line to per invocation | `tools/bst_native_build_tracer.py` |
| `BST_TRACE_ARGV_LOG` | the host-side `argv` log, written only when argv recording is on | `tools/bst_native_build_tracer.py` |
| `BST_TRACE_JOBSERVER` | the jobserver FIFO's path; `run --jobserver N` sets it, the shim opens it read-write and injects `MAKEFLAGS=--jobserver-auth` (`UX-679`, a spike) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_JOBSERVER_AUTH` | `fd` or `fifo`, resolved from `--jobserver-auth` before the build starts; the shim reads it to choose which `--jobserver-auth` style to inject (`UX-841`) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_JOBSERVER_AUTH_MAP` | `bga capture run --jobserver-auth-override`'s own map (`style:glob[,glob];...`, styles `fd`/`fifo`/`off`/`flto`), resolved in `bga/cli.py` and carried unchanged through `tools/bst_native_build_tracer.py`; the shim's `resolve_auth_override` matches it against the element name and forces the style, ahead of the auto/`compiler_safe` path (`UX-879`, `flto` `UX-880`) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_PROJECT_MAX_JOBS` | the project's own `max-jobs`, read once from `bst show` before the build; the shim compares it against each sandbox's own `-j` to tell a `notparallel` pin from an element-level cap (`UX-842`) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_JOBSERVER_DECISIONS` | the host-side path the shim appends one `{element, max_jobs, decision, kind, policy}` line to per sandbox, folded into the report as `jobserver_decisions` (`UX-842`/`UX-843`). An element the shim probed a sandbox `make` for also carries `sandbox_make` (that `make --version`'s first line) and `auth_style` (`fifo` for 4.4 and up, `fd` below it) - added as the file is copied out of the capture, since the probe cache dies with the FIFO (`UX-916`) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_ELEMENT_KINDS` | a JSON `{name: kind}` map, read once from `bst show` before the build; the shim looks its own element up in it to pick a row from the per-kind environment table (`UX-843`) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_ELEMENT_AUTH_MAP` | a JSON `{name: style}` map, read once from a *separate* `bst show --format '%{name}<US>%{public}<RS>'` before the build - each element's own `public: bga: jobserver-auth: fd\|fifo\|off\|flto` annotation, version-controlled in the project; the shim falls back to it in `resolve_auth_override or _annotation_style` only when `BST_TRACE_JOBSERVER_AUTH_MAP` (the command-line override) does not match the element (`UX-882`) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_WRAPPER_DIR` | the host path of `tools/native_trace/wrappers/`, bound read-only at `wrappers/` under the trace bind (`/tmp/.bst-native-trace/wrappers`; the sandbox root is read-only, measured on examples/06) and prepended to `PATH` ahead of BuildStream's own (`UX-846`; also holds the `flto` shim's `gcc`/`g++`/`cc`/`c++` scripts, `UX-880`) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_JOBSERVER_LEDGER` | the in-sandbox path a wrapper appends an acquire or release row to — the same file `PoolController`'s own ticks land in, under the existing trace bind (`UX-846`) | `tools/native_trace/wrappers/_common.sh` |
| `BST_TRACE_FLTO_ACTIVE` | `1` when *this* element's own `--jobserver-auth-override` resolved to `flto` — and only then: `UX-913` keeps a cmake/meson element's auth without the shims, because `flto/` shadows the staged `cc`/`gcc` with a script that opens on `dirname`, which a staged-toolchain sandbox has not got (`examples/06` exit 255) — set only by `_jobserver_injection`, never by hand; the GCC-driver shim gates its entire strip-auth/rewrite-`-flto` transform on it, since the shim scripts sit in the one wrapper directory every jobserver-active sandbox mounts and would otherwise touch every element's compiler, matched or not (`UX-880`, verifier fix) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_PROXY_DIR` | the host directory holding one jobserver proxy FIFO per element, set only when `run --plan` named an `analyze.json`; the shim looks its own element up in it and injects that proxy's auth instead of the global FIFO's when one exists — its path already lands under `BST_TRACE_BIND_DST`, no bind of its own (`UX-849`, `UX-869`) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_ADMISSION_POOL` | a host-side admission FIFO's path, never bound into the sandbox; when set and the jobserver is active (`--jobserver off` leaves it unread, same as today) the shim reads one real token before starting `bwrap` and releases it only after `waitpid` returns, logging the wait as its own ledger row (`UX-1005` track B) | `tools/native_trace/bwrap_shim.py` |
| `BST_TRACE_ADMISSION_BROKER_DIR` | the host directory an `AdmissionBroker` writes this element's own admission grant FIFO into and reads `requests.jsonl` from, set only when `run --plan` named an `analyze.json`; a waiting shim asks it for a ranked grant before falling back to the raw `BST_TRACE_ADMISSION_POOL` FIFO on any timeout or absence (`UX-1005` track C) | `tools/native_trace/bwrap_shim.py` |

**What a test sets to reach a failure path.** The spine's degrade and
refusal branches are unreachable on a machine that *has* `ptrace`, so
these exist to reach them; `bwrap_shim.py` passes a fixed list of
`BST_TRACE_*` through and none of these is on it:

| name | what it forces | where |
|---|---|---|
| `BST_TRACE_SPINE_FAIL_SEIZE` | `PTRACE_SEIZE` fails, taking the branch every machine without `ptrace` takes | `tools/native_trace/spine.c` |
| `BST_TRACE_SPINE_FAIL_CONT_AT` | a named restart site fails; the spine lists the known sites when the name is not one | `tools/native_trace/spine.c` |
| `BST_TRACE_SPINE_DEGRADE_AFTER` | degrades after N events, which is `UX-117`'s hang reproduced on purpose | `tools/native_trace/spine.c` |
| `BST_TRACE_SPINE_SELFTEST` | runs one self-test instead of a capture (`detach-signal`) | `tools/native_trace/spine.c` |
