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
| `cmd` | Plane 2 | the full command line, untruncated - the slice name is the first 120 characters and this is the rest |
| `src` | Plane 2 | which mechanism recorded it: `hook` (the LD_PRELOAD hook, loaded at exec) or `spine` (the ptrace supervisor) |
| `cpu_us` | Plane 2 | CPU microseconds this process itself used, from its own `getrusage` at exit or the spine's read at the exit-stop |
| `max_rss_kb` | Plane 2 | peak resident kilobytes of this process alone - never summed with another's, which never held it at the same moment |
| `exit_status` | Plane 2 | how it ended, in the spine's own vocabulary: a decimal exit code, or `signal:N` for a process the kernel killed. The hook cannot see one - its destructor runs before the process has a status, and not at all when it is killed - so a hook-only record carries no key rather than a zero |
| `exec_chain` | Plane 2 | how many `execve`s this one record collapses - a shell that exec'd a compiler is one process and two commands |
| `run` | run | the snapshot directory's own stamp - which run this is |
| `project` | run | the project identity the run was captured under |
| `targets` | run | the elements `bst build` was asked for |
| `manifest_hash` | run | the run identity hash two runs are compared by |
| `project_git_commit` | run | the commit the project was at, where it is a git checkout |
| `bga_version` | run | the version of `bga` that wrote this trace |
| `bst_version` | run | the BuildStream the capture ran against |
| `host_cpu_model` | run | the CPU the build ran on, from the host manifest |
| `host_cpu_count` | run | how many cores that host had |
| `host_memory_mb` | run | how much memory it had |
| `kernel_release` | run | the kernel the sandboxes ran under |
| `distro_id` | run | the distribution the capture was taken on |
| `builders` | run | BuildStream's element-dispatch concurrency for this run |
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
