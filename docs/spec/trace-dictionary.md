# The trace dictionary

What a slice in `bga timeline`'s Perfetto trace carries, and what each
key means. This is the contract `UX-312`'s canned questions are written
against and the one `extract_arg(arg_set_id, 'debug.<key>')` selects
on.

**A rename is a break.** These keys are the surface a saved query
depends on, exactly as `UX-190` treats a published payload's field
names: adding a key is additive, removing or renaming one breaks every
query built on it. `tests/unit/test_the_questions_ask_what_the_trace_answers.py`
holds this table and `tools/bga_timeline.ANNOTATION_CONTRACT` equal in
both directions, so a key added to one and not the other reddens rather
than drifting.

## How to read a key

Annotations land in `trace_processor` under the `debug.` namespace:

```sql
select extract_arg(s.arg_set_id, 'debug.element') as element
from slice s
where s.category glob '*native-process*';
```

Not `args.` — that is the legacy Chrome JSON converter's namespace,
which `bga timeline --format chrome` still writes and the default
TrackEvent format does not. Verified against Perfetto v49.0 on
`examples/06`.

## The keys

| key | rides | what it is |
|---|---|---|
| `element` | Plane 1, Plane 2 | the BuildStream element this belongs to - the task it is for on Plane 1, the sandbox the process ran in on Plane 2. The same uid on both, which is what lets one query join them |
| `element_kind` | Plane 1 | its kind from the run's own graph (`cmake`, `import`, `manual`, ...), or `unknown` where the capture recorded none |
| `task_type` | Plane 1 | what the scheduler was doing: `build`, `fetch`, `pull`, `push`, `track` |
| `outcome` | Plane 1 | the status BuildStream's log closed the task with - `SUCCESS`, `FAILURE`, `CACHED` or `SKIPPED`. The cache outcome is the last two, and only where the log states it |
| `depth` | Plane 1 | how far down the dependency graph this element sits - the longest path in edges from a source, which is the level `parallelism.levels` decomposes the build by. Absent where the snapshot carries no analysis. **`slice` has a `depth` column of its own** - the slice's nesting depth - so a query must project this into a subquery under another name before it groups by it, or the alias is shadowed and every row falls into one group (`UX-434`) |
| `on_critical_path` | Plane 1 | whether this element is on the chain that sets the build's finish time. The set every finding in the report is ranked against. **The value is the text `true` or `false`**, not a number - Plane 1's booleans reach the arg table as strings, so `sum(...)` over this column is 0 on every capture and a query has to compare it (`UX-434`) |
| `downstream_count` | Plane 1 | how many elements rebuild when this one changes - its blast radius in elements |
| `resource` | Plane 1 | the scheduler queue this task held a slot of while it ran - `PROCESS` for a build, `DOWNLOAD` for a fetch or pull, `UPLOAD` for a push, `CACHE` for a cache query. BuildStream limits each queue separately, so this is the one axis `attribution.resource_wait_us` cannot be read along: that figure sums the waiting for every queue at once and cannot say which of them was full (`UX-469`) |
| `exe` | Plane 2 | the program this process ran, argv stripped - the path as it was exec'd, so `/usr/bin/cc` and a compiler's own `cc1` stay different programs. The key a **pivot** groups on: the slice's *name* is the whole command line and groups one row per invocation (`UX-433`). Absent where the record carried no command |
| `src` | Plane 2 | which mechanism recorded it: `hook` (the LD_PRELOAD hook, loaded at exec) or `spine` (the ptrace supervisor) |
| `cpu_us` | Plane 2 | CPU microseconds this process itself used, from its own `getrusage` at exit or the spine's read at the exit-stop |
| `max_rss_kb` | Plane 2 | peak resident kilobytes of this process alone - never summed with another's, which never held it at the same moment |
| `exit_status` | Plane 2 | how it ended, in the spine's own vocabulary: a decimal exit code, or `signal:N` for a process the kernel killed. The hook cannot see one - its destructor runs before the process has a status, and not at all when it is killed - so a hook-only record carries no key rather than a zero |
| `exec_chain` | Plane 2 | how many `execve`s this one record collapses - a shell that exec'd a compiler is one process and two commands |
| `read_bytes` | Plane 2 | block-layer bytes this process read - what reached the device, so a read served from the page cache is 0 and a large figure is genuinely disk |
| `written_bytes` | Plane 2 | block-layer bytes this process wrote, on the same terms as `read_bytes` |
| `major_faults` | Plane 2 | page faults this process had to go to disk for - the signal a memory-starved host produces |
| `involuntary_switches` | Plane 2 | times the run queue preempted this process while it still had work. Rises with oversubscription rather than with work, which is what separates a contended build from a busy one |
| `run` | run | the snapshot directory's own stamp - which run this is |
| `project` | run | the project identity the run was captured under |
| `targets` | run | the elements `bst build` was asked for |
| `manifest_hash` | run | the run identity hash two runs are compared by |
| `project_git_commit` | run | the commit the project was at, where it is a git checkout |
| `bga_version` | run | the version of `bga` that wrote this trace |
| `bst_version` | run | the BuildStream the capture ran against |
| `host_cpu_model` | run | the CPU the build ran on, from the host manifest |
| `host_cpu_count` | run | how many cores that host had |
| `host_memory_bytes` | run | how much memory it had |
| `kernel_release` | run | the kernel the sandboxes ran under |
| `distro_id` | run | the distribution the capture was taken on |
| `builders` | run | BuildStream's element-dispatch concurrency for this run |
| `native_max_jobs` | run | the per-element concurrency the native build systems ran with - `bst --max-jobs`, or what the graph resolved `%{max-jobs}` to. Absent where the capture could establish neither |
| `native_max_jobs_source` | run | which of the three the number came from - `operator_declared`, `parsed_from_invocation` or `resolved_from_graph` |
| `incomplete_reason` | run | why this run is not a measurement - `failed`, `interrupted` or `suspended`. Absent on a run that finished, which is the only thing its absence means |
| `anchor_element` | run | the element the two planes were aligned on |
| `plane_offset_us` | run | the single offset that alignment applied, in microseconds |
| `lane_order` | run | the rule the element lanes are ordered by |

## Scopes

Every slice carries exactly one scope category, so a query scoped by
one can never silently miss a class of slice. They partition the trace.

| category | what it scopes |
|---|---|
| `bst-builder` | a Plane 1 element task — what the BuildStream scheduler was doing |
| `native-process` | a Plane 2 process — what ran inside a sandbox |
| `bst-invocation` | the run itself: `UX-311`'s identity slice, which belongs to neither plane |

One further category is additive rather than a scope, so a slice may
carry two and `trace_processor` joins them into one comma-separated
string — which is why a query matches with `glob` and not `=`:

| category | what it marks |
|---|---|
| `failed` | a process whose `exit_status` is neither absent nor `0` |

## Counter tracks

| track | unit | what it counts |
|---|---|---|
| `traced processes running` | `processes` | traced processes running at that instant; its peak equals the report's `max_concurrency` by construction |
| `host memory available` | `bytes` | `MemAvailable` from the host's `/proc/meminfo`, in bytes |
| `host swap free` | `bytes` | `SwapFree` from the host's `/proc/meminfo`, in bytes |
| `host major faults` | `faults` | `pgmajfault` from `/proc/vmstat`, cumulative since boot |
| `host pages swapped in` | `pages` | `pswpin` from `/proc/vmstat`, cumulative since boot |
| `host pages swapped out` | `pages` | `pswpout` from `/proc/vmstat`, cumulative since boot |

The first is Plane 2's, folded from the records. The five `host` tracks
are `UX-378`'s sampler, read from `host-samples.jsonl` and placed on the
build's own time axis by `UX-437` — the sampler runs whether or not the
build was traced, so they are on every capture that has the file,
including one with no Plane 2 at all. Three of them are **cumulative
counters, not levels**: a query wanting the rate over a window has to
difference them.

## Flows

`UX-309` draws two kinds of edge, both as Perfetto flows:

- **dependency** — from a Plane 1 element task to the tasks of the
  elements that declared it a dependency. The declared graph, not
  timestamp proximity.
- **exec chain** — from a Plane 2 process to the process it `execve`d
  into, where the capture collapsed a chain.

A flow is captured causation only. Nothing here infers an edge from two
things happening near each other, which is why there are no
cross-element Plane 2 flows: no captured relation exists.
