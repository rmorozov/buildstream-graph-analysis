# BuildStream Build Efficiency Analyzer (bga) - CLI Reference

The `bga` command-line interface provides access to the BuildStream Build Efficiency Analyzer, allowing you to analyze build traces, generate efficiency reports, and export data.

This is the reference. If you are pointing `bga` at a real project for the first time, read [`docs/guides/real-project.md`](real-project.md) instead — it walks the whole cycle end to end with real output at every step, and links back here for flags.

This covers the `bga` command itself — the whole-project analysis plane. For real per-process tracing *inside* one element's own sandbox (a separate tool, `tools/bst_native_build_tracer.py`, with its own Chrome Trace export), see [`docs/design/architecture.md`](../design/architecture.md#plane-2-intra-element-native-build-system-tracing-ux-11).

The JSON outputs and their schemas are [`json-contracts.md`](json-contracts.md);
the browser report `bga view` draws is [`viewer.md`](viewer.md).

## Installation

```bash
pip install ./buildstream-graph-analysis   # or the git URL directly
```

That is **user mode**, and it is what the README teaches. `pip install
-e .` from inside a checkout is **contributor** mode — the two differ in
ways that have shipped bugs (`UX-77`, `UX-203`, `UX-325`: an editable
install has the repository root on `sys.path`, a wheel does not), so
this guide names which one it means rather than showing one and
describing the other (`UX-327`).

Add `bga[bst]` for a real BuildStream in the same environment,
`bga[completion]` for tab completion, `bga[all]` for both; `pip install
-e '.[dev]'` is the contributor set that `make test` needs.

## One entry point (`UX-67`)

`bga` dispatches to the producer programs in `tools/` as well as running
its own analysis subcommands, so a session reads as one tool:

```bash
bga doctor  PROJECT                                 # can this machine capture at all?
bga wrap    PROJECT build.log -- bst build TARGET   # capture a log bga can read
bga extract PROJECT build.log run/                  # log + project -> run directory
bga analyze run/                                    # the analysis
bga capture run PROJECT native.json -- bst build T  # Plane 2, inside the sandboxes
bga correlate run/ native.json                      # join the two planes
bga blast https://…/monorepo.git                    # what rebuilds if I touch this
```

For the local loop specifically, those are the plumbing: `bga snapshot`
runs the capture, the extraction and the analysis together and compares
against the previous one. See
[`bga snapshot`](#bga-snapshot--the-local-loop-ux-126) below.

Before this, the same workflow alternated between `bga <cmd>` and
`python3 -m tools.<module>` at nearly every step — 74 occurrences across  <!-- docs-style: allow-direct-module -->
the docs and CI.

**The tools are still separate programs**, and deliberately so: the
analyzer is a library with a stable contract, and each tool in `tools/`
is independently useful and independently testable. Every one of them
remains runnable directly, unchanged:

```bash
python3 -m tools.bst_extract_run PROJECT build.log run/   # still works (docs-style: allow-direct-module)
```

`bga --help` lists each alias with the module it wraps, so a script that
wants the underlying program can find it. Dispatch is lazy — only the
module actually invoked is imported, so `bga analyze` does not pay to
import the native tracer and the trace converters on every run.

**The table below is that block**, alias for alias and module for
module:
[`test_the_alias_table_is_the_help.py`](../../tests/unit/test_the_alias_table_is_the_help.py)
compares the two, in both directions, so a new alias is a red test
rather than a row somebody notices (`UX-552`).

| alias | wraps |
|---|---|
| `bga wrap` | `tools.bst_run_wrapped` |
| `bga extract` | `tools.bst_extract_run` |
| `bga capture` | `tools.bst_native_build_tracer` |
| `bga rebuild-set` | `tools.bst_rebuild_set` |
| `bga checkout-cost` | `tools.bst_checkout_cost` |
| `bga run-context` | `tools.bst_run_context` |
| `bga graph-from-show` | `tools.bst_show_to_graph` |
| `bga timeline` | `tools.bga_timeline` |
| `bga view` | `tools.bga_view` |
| `bga log-to-chrome` | `tools.bst_log_to_chrome_trace` |
| `bga chrome-to-trace` | `tools.chrome_trace_to_bga_trace` |
| `bga native-to-chrome` | `tools.native_trace_to_chrome_trace` |
| `bga cross-check` | `tools.bga_cross_check` |
| `bga release-notes` | `tools.bga_release_notes` |
| `bga gen-synthetic` | `tools.gen_synthetic_scale_run` |
| `bga snapshot` | `tools.bga_snapshot` |
| `bga doctor` | `tools.bga_doctor` |
| `bga cache-logs` | `tools.bst_cache_logs` |
| `bga baseline` | `tools.bst_baseline_set` |

## Tab completion (`UX-191`)

```bash
pip install "bga[completion]"
eval "$(register-python-argcomplete bga)"          # bash/zsh, in your rc
register-python-argcomplete --shell fish bga | source
```

What it completes:

| where | what |
|---|---|
| `bga <TAB>` | every subcommand **and** every `UX-67` alias |
| any run argument — `bga compare @<TAB>` | `@last`, `@prev`, and this project's own snapshot stamps |
| `bga blast <TAB>` | element names, read from the project's `.bst` files |
| any `--flag` with choices | its choices |

Without the shell hook it is completely inert, and without `argcomplete`
installed the import is skipped — the CLI behaves exactly as it did.

**Why not `click`.** The feedback suggested migrating; `argcomplete`
completes an argparse program as it stands, while a rewrite would touch
every subcommand, re-litigate the help formatting `UX-158` measured, and
buy nothing beyond what completion already gives. Recorded as considered
and declined, revisitable if argcomplete cannot complete something users
need.

## The environment `bga` reads (`UX-630`)

`bga --help` cannot list an environment variable — which is the reason
`bga/report/rate.py` gives for choosing one — so this table is the
inventory instead. Its population is derived from `bga/` and `tools/`
rather than from the parser, by
`tests/unit/test_the_environment_surface_is_an_inventory.py`: a name
added tomorrow with no flag beside it appears here, or that guard is
red.

### Switches you set

A pilot sets these through its own switches, one table in
[`pilot.md`](pilot.md#every-switch); the capture's own switches are
flags, not variables (`--trace-opens`, `--trace-spine`, `--jobserver`).

| name | default | how to turn it off | cost | what it changes | where |
|---|---|---|---|---|---|
| `BGA_BUILD_TYPE` | unset: nothing recorded | unset it | none | what kind of build this was — `night`, `review`, `guard`, or whatever else the pipeline declares (`UX-898`). Free text: two runs declaring different types are two populations, and `bga compare`'s gates refuse the pair with exit 6 unless `--blend` is passed. Unset, nothing is recorded and every comparison behaves as it did | `tools/_run_context_common.py` |
| `BGA_BUILD_VARIANT` | unset: nothing recorded | unset it | none | the named dimensions of what the build did, comma-separated — `arch=aarch64,sanitizer=address,coverage=on` (`UX-903`). Several are true at once, which is why it is a map and not a string; the comparison class is the pair with `BGA_BUILD_TYPE`. An entry without `=` is refused naming it | `tools/_run_context_common.py` |
| `BGA_CALIBRATED_CORES` | unset: `host_cpu_count`, labelled uncalibrated | unset it | none | `UX-1004`'s recorded knee (effective cores) for this host, from `calibrate_width.py`'s printed `knee: width N` — sizes `bga analyze`'s pool recommendation (`UX-1005`). Unset, the pool falls back to `host_cpu_count`, labelled uncalibrated | `bga/cli.py` |
| `BGA_ADMISSION` | off | unset it, or anything but `1` | measured slower than none on its first Graviton reading (`UX-1005`) | `1` turns on sandbox admission under `--jobserver` (`UX-1005`): each sandbox takes a token from the recipe pool before `bwrap` starts, ranked by slack. Off by default — its first Graviton reading was slower than none | `tools/bst_native_build_tracer.py` |
| `BGA_INTERRUPT_GRACE_SECONDS` | 300 | cannot: a value of 0 or less is read as 300 | a stopped build waits up to that long | seconds a wrapped `bst` gets to stop by itself after `SIGINT` before `bga` escalates; 300 by default, and raising it is how a big build keeps the `queue_summary` written during that shutdown | `tools/bst_run_wrapped.py` |
| `BGA_NO_PROGRESS` | unset: the line is drawn on a terminal | unset it | none | suppresses the in-phase progress line even on a terminal — the same off-switch as `bga snapshot --no-progress` | `bga/progress.py` |
| `BGA_WRAPPER_ACQUIRE_MS` | 50 | cannot; a wrapper runs only with `--jobserver` on | up to that long per wrapped tool, waiting for tokens | how long a jobserver wrapper (`ld.lld`, `lld`, `ld.gold`, `mold`, `ninja`) may spend acquiring tokens before running its tool; 50 by default, passed to `timeout` as seconds with three decimals. Raised by the test suite so an exact-token-count assertion is never also a bet against `make test`'s own xdist contention (`UX-846`) | `tools/native_trace/wrappers/_common.sh` |
| `BGA_RATE` | unset: no block | unset it | none | adds the *In Your Units* block to `bga analyze` and `bga whatif`, converting build seconds at `<amount> <unit>/machine-hour` (or `/build-hour`). Unset, nothing is converted and no block is printed; malformed, the block says why rather than staying silent | `bga/report/rate.py` |
| `BGA_REQUESTED_AT` | unset: `CI_PIPELINE_CREATED_AT`, else none | unset it | none | the ISO-8601 instant a capture publishes as `requested_at_us`, and the `queue_wait_us` it derives from that. `CI_PIPELINE_CREATED_AT` is the fallback, and the published `requested_at_source` says which was used | `tools/_run_context_common.py` |
| `BGA_TRACE_PROCESSOR` | unset: `PATH`, then the pinned download | unset it | none | the Perfetto `trace_processor_shell` the canned-question runner uses, ahead of `PATH` and ahead of the pinned download | `tests/trace_processor.py` |

### Set by `bga` itself, listed for debugging

`BGA_BASELINE_RUN_DIR` and `BGA_JOBSERVER_MODE` are written by
`bga snapshot` and `bga capture` into the child they start.

Four more names sit in the same namespace and are **not** switches to
use. They are listed because a reader who greps the tree finds them and
deserves an answer:

| name | what it is | where |
|---|---|---|
| `BGA_BASELINE_RUN_DIR` | a previous run directory whose `graph.json` `tools/bst_extract_run.py`'s `extract_run` compares this build's own fingerprint against, reusing it on an exact match instead of a fresh `bst show --deps all` (`UX-1083`) — the same `BGA_JOBSERVER_MODE` shape, set by `bga snapshot` beside the previous healthy snapshot it already picks for the compare. Unset when there isn't one (a first capture) or the tracer's `run` command is invoked directly | `tools/bga_snapshot.py`, `tools/bst_native_build_tracer.py` |
| `BGA_JOBSERVER_MODE` | `off`/`auto`/`n` — `bga capture` sets it beside the `--jobserver N` it already resolves from `--jobserver auto\|N\|off` (`UX-851`), so `tools/bst_native_build_tracer.py run` can record which mode ran without parsing its own argv for the distinction. Unset (read as `off`) when the tracer's `run` command is invoked directly, outside `bga capture` | `tools/bst_native_build_tracer.py` |
| `BGA_FORCE_PROGRESS` | draws the progress line onto a pipe, so a test can compare a run with progress genuinely on against one with it off. Deliberately not a user-facing switch: it writes control characters into a redirected stderr, which is the one thing `UX-183` exists to prevent | `bga/progress.py` |
| `BGA_STRICT_HINTS` | not an environment variable at all — a page global, set from the browser console, that makes the report complain about a number carrying no declared `bga:quantity` | `bga/viewer/format.js` |
| `BGA_TIER_ANY` | set into the child environment by `make test-touching` and by the pre-commit selector, and read by nothing in this tree (`UX-630`) | `tools/dev_touching.py` |
| `BGA_WRAPPER_TOOL` | set by a jobserver wrapper on itself before running the real tool or its `--help`, so a re-entry (a symlink or a relocated copy that fooled `bga_find_real`) refuses outright rather than recursing (`UX-846`, a post-merge incident) | `tools/native_trace/wrappers/_common.sh` |

The capture path's own namespace, `BST_TRACE_*` — how `bga snapshot`
drives the `bwrap` shim, the `LD_PRELOAD` hook and the ptrace spine,
and the failure paths a test forces — is listed in
[`tools-native_trace.md`](../design/areas/tools-native_trace.md#bst_trace--plane-2-and-plane-3-ux-635).

The system variables `bga` merely *consumes* — `TMPDIR`,
`XDG_CACHE_HOME`, `XDG_CONFIG_HOME`, `LD_PRELOAD`, `PATH`,
`PYTHONPATH` — are deliberately not in this table. They are not this
project's names, and a table that listed them would be describing the
platform rather than the tool.

## `bga snapshot` — the local loop (`UX-126`)

```bash
cd /path/to/your/project
bga snapshot -- bst build target.bst   # capture + extract + analyze
# ...edit...
bga snapshot -- bst build target.bst   # ...and compare against the previous one
```

That is the whole local workflow. It replaces three commands and five
paths the user has to invent:

```bash
bga capture run --wrapped-log /tmp/plane1.log --trace-opens \
    /path/to/project /tmp/plane2.json -- bst build target.bst
bga extract --format wrapped /path/to/project /tmp/plane1.log /tmp/run
bga analyze /tmp/run --plane2 /tmp/plane2.json
```

`snapshot` composes exactly those commands — it does not reimplement
them — so every number, every refusal and every hedge is the one the
explicit form produces. In particular a cross-mode pair (a caches-off
run against a caches-on one) is refused with exit 6, as it is when the
paths are typed out (`UX-78`).

Captures go to `.bga/runs/<UTC-stamp>/` under the project, holding
`run/`, `plane2.json`, the wrapped log and a `capture-context.txt` — the
same layout the published capture refs use, so nothing downstream learns
a second shape. `.bga/` gitignores itself.

### Naming runs: `@last`, `@prev`, `@<stamp-prefix>`

Every argument that names a run directory takes one of these instead —
and so does every argument that names a Plane 2 report, since a snapshot
holds both halves of the capture (`UX-134`):

```bash
bga analyze @last
bga compare @prev @last
bga cache-trend @prev @last
bga analyze @20260819                          # by stamp prefix, if unambiguous
bga analyze @last                              # the Plane 2 report beside it is found
bga analyze @last --no-plane2                  # ...unless you say not to
bga compare @prev @last --baseline-plane2 @prev --candidate-plane2 @last
bga cache-logs . --native-report @last
```

`bga analyze` finds the `plane2.json` beside a snapshot on its own
(`UX-329`), as `bga correlate` and `bga view` always have — before that
the same run published `plane2_coverage: null` in the terminal and the
full coverage in the page, which `bga view --help` promises can never
happen. `--plane2` still names a different report; `--no-plane2`
declines the sibling and the report says it declined.

**When Plane 2 is not in a report, the report says which absence it
is** — never captured, captured with its raw log not kept (so no
timeline), or declined. One sentence pair in `bga/plane2.py`, printed by
the terminal, published as `plane2_absence`, and shown by the page and
the export, so the three cannot describe one absence differently.

**One alias is one snapshot**, whichever of its files is being asked
for, so `bga correlate @prev @last` means a run from one and a report
from another *because you said so* rather than by accident.

And the join does not need to be told twice at all:

```bash
bga correlate @last          # the report beside that run is the one it came from
```

The Plane 2 report is optional whenever there is one sitting beside the
run directory, which is true of every snapshot and of anything
`bga capture run --run-dir` wrote. That is read off the filesystem, not
off whether an alias was used, so an explicit path to a snapshot's `run/`
behaves identically; the inferred path is printed. Where there is
nothing to infer the argument is still required, and says so.

The store is *resolution* and nothing else: an explicit path means what
it always meant, no run directory format changed, and comparability
rules are untouched. Outside a project an alias fails by name rather
than as a missing path, with exit 2:

```text
Error: @last is a snapshot alias, and there is no BuildStream project here to
resolve it against (no project.conf in this directory or any parent). Run it
from inside a project, or pass a path.
```

`@prev` with only one snapshot on disk gets its own message — *"@prev
needs two snapshots and PROJECT has one"* — because that is a different
problem from a typo'd path. So does an alias whose snapshot recorded
Plane 1 and not Plane 2: *"@prev resolves to 20260819T183424Z, which has
no plane2.json"*, which is a fact about that capture rather than about
your typing.

### Sticky flags

`--trace-opens` and `--trace-spine` are recorded in `.bga/config` and
reused until changed, so they are decided once per project rather than
retyped per capture:

```bash
bga snapshot --trace-spine=off -- bst build target.bst   # and stays off
```

Both are **on by default**: a new project starts at `--trace-opens
--trace-spine=auto`. `--no-trace-opens` and `--trace-spine=off` turn
them off. Measured cost (`UX-895`; CodSpeed Graviton, 16 cores,
`examples/11-serial-giant`, n=3 per arm), wall over the uncaptured
build: the capture alone +7.1%, with opens +8.9%, with the spine `on`
+7.1%, both +9.3% — the table is in
[`pilot.md`](pilot.md#the-three-steps-and-what-each-costs). Stickiness
is safe because every report records what actually ran (`UX-95`,
`UX-113`), so a remembered flag cannot make a capture *claim* something
it did not do.

### The jobserver, as a pair (`UX-856`)

`--jobserver auto|N|off` (default `off`) and `--plan @prev|@last|PATH`
compose into the capture exactly as `bga capture run --jobserver` does
(`resolve_jobserver_ceiling`, `UX-851`) — nothing to invent, one flag
per capture, like `--diagnose` (`UX-146`). `auto`'s ceiling is the
host's cores and it opens seeded to `max(0, cores - builders)`, so the
pool can grow to fill the machine rather than stall at a ceiling of 1
(`UX-858`). The comparison a mode's value is read from is the pair
itself:

```bash
bga snapshot --jobserver off -- bst build all.bst    # the baseline
bga snapshot --jobserver auto -- bst build all.bst    # ...and the mode
jobserver: off -> auto (4)                            # the compare header names both
```

| flag | what it does |
|---|---|
| `--list` | List this project's snapshots with their sizes, showing which are `@last`/`@prev` |
| `--no-compare` | Take the snapshot and report on it; skip the comparison |
| `--project PATH` | Snapshot a project other than the enclosing one |
| `--jobserver auto\|N\|off` | Cap sandbox concurrency for this capture (default `off`) |
| `--jobserver-auth fd\|fifo\|auto` | The `--jobserver-auth` style forwarded to the tracer (default `auto`), as `bga capture run --jobserver-auth` (`UX-841`, `UX-875`); unused when `--jobserver` is off |
| `--plan @prev\|@last\|PATH` | Bias the jobserver by a prior run's own slack; needs `--jobserver auto\|N` |
| `--jobserver-auth-override`, `--lto-cap`, `--wrapper-dir`, `--wrapper-dir-mode` | As `bga capture run`'s ([in full](#what-each-flag-does-in-full)): set into the capture's environment by `bga.cli.apply_capture_env_flags`, the code `capture run` runs (`UX-1302`) |
| `prune --keep N` / `--older-than DAYS` / `--max-store SIZE` | Delete old snapshots; `--dry-run` says what would go |
| `--prune` | The flag form of the same deletion; needs `--keep`, `--older-than` and/or `--max-store`, and `--keep`, `--older-than`, `--max-store` and `--dry-run` read as "with `--prune`" |

Eleven `bga capture run` flags are `capture run` only (`comm -23` of
the two `--help` outputs). `bga snapshot` writes `--wrapped-log`,
`--run-dir`, `--raw-log` and `--host-samples` itself, into the snapshot
directory (`take_snapshot`), and resolves `--jobserver-seed` from its
own `--jobserver`. `--jobserver-pool`, `--jobserver-capacity`,
`--argv-log`, `--invocation-log`, `--no-invocation-log` and `--json` it
does not take, so a snapshot's capture runs their defaults (a `dynamic`
pool among them): use `bga capture run` to set one.

`bga snapshot` exits with **the wrapped build's own exit code**. A
failed build is not a successful snapshot; equally, a comparison verdict
does not change the exit code — the CI gates live on `bga compare`
(`--fail-on-regression` and friends), which is what CI should call.

The one thing it will not do is start. If the build command's executable
is not runnable — no `bst` on `PATH` being the case that matters —
`bga snapshot` **refuses before it writes anything**, exits `2` like its
other refusals, and prints one sentence with the remedy and a pointer to
`bga doctor`, which is the command that checks the whole machine
(`UX-324`). No snapshot directory is created on that path, so there is
no debris to describe, resolve or prune afterwards. The check is
`bga doctor`'s own rather than a second copy of it.

Snapshots are build artifacts and `.bga/runs` entries can be deleted at
any time. Every capture now **says what it weighed and what the store
holds** (`UX-300`), and `bga` still warns once the store passes 2 GB.
What `prune` will never delete is `@last`, `@prev`, and — when both of
those record builds that did not finish — the newest *healthy* run,
because that is the baseline the next comparison walks back to
(`UX-167`).

```bash
bga snapshot prune --max-store 20G --dry-run   # oldest-first, under a budget
```

`--max-store` is the question a disk actually asks. Age and count are
proxies for it: a nightly capture that grew from 4 MB to 2 GB makes
`--keep 5` mean something different every month, and `--max-store 20G`
means the same thing forever. Combined with the others it is the
stricter of the two, never an override, and a store it cannot reach
without deleting `@last`/`@prev` says so rather than emptying itself.

`bga snapshot --aggregate` reports what the store weighs as a
distribution — the median capture against the p95 is what names the run
worth looking at — and its total counts *every* snapshot, including
captures excluded from the timing distributions for failing: a failed
run is not a sample, and still occupies its disk. See [the real-project
guide](real-project.md) for the store at big-project scale.

### Carrying a capture to another machine (`UX-520`)

The steps in order, and what each discloses, are
[`sharing-a-capture.md`](sharing-a-capture.md); this is every flag.

**`run/` is not the capture.** It holds Plane 1 — `graph.json`,
`trace.json`, `run-context.json` — and the Plane 2 report, the raw
per-process trace, the host samples, the published analysis and the
build log all sit *beside* it. A `tar` of `run/`, which is the directory
every command's help names, arrives with Plane 2 missing; the far side
then says so rather than lying, but that is a poor substitute for
packing the right set:

```bash
bga bundle --export @last -o run.tar.gz
scp run.tar.gz laptop:
ssh laptop 'cd myproject && bga bundle --load run.tar.gz && bga analyze @last'
```

`--export` takes a stamp, `@last`/`@prev`, or a path, and writes one
archive holding every member `capture-layout/v1` names that exists for
that snapshot — derived from the contract, so a member added to the
layout travels without anyone remembering it. Members the contract calls
`derived` are skipped: that word means "absent means nothing; it is
rebuilt on demand", so leaving them out cannot make the far report
quieter.

```console
$ bga bundle --export @last -o run.tar.gz
Wrote run.tar.gz
  snapshot 20260902T101112Z: 7 member(s), 56.3K before compression
  load it with: bga bundle --load run.tar.gz
```

*Kept, not current* — `UX-520`'s measurement, 2026-09-02, on a
seven-member capture that is not in this repository, so nothing here can
re-run it. Cuts: none; the whole of what that command printed is above.

**`--load` unpacks under the bundle's own stamp**, not a new one. The
stamp is the capture's identity, so a run carried from a runner to a
laptop keeps the name it was compared under at home — and `UX-186`'s
host manifest rides inside `run-context.json` untouched, so `bga
compare` on the far machine caps confidence and refuses exactly as it
would have at the other end.

**It refuses rather than half-loads.** Every member carries its contract
version in the bundle's manifest (`bundle-manifest/v1`, inside
`bundle.json`), so a bundle packed by a newer `bga` is recognised and
declined with nothing written:

```console
$ bga bundle --load newer.tar.gz
Error: this bundle carries contract(s) this bga does not read: graph/v10.
It was packed by bga 9.9.9; upgrade to read it. Nothing was written.
```

*Kept, not current* — `UX-520`'s refusal, 2026-09-02, against a bundle
hand-packed as `graph/v10` by a `bga` that does not exist; the guard on
it is `tests/unit/test_a_run_bundle_you_can_carry.py`, not this page.
Cuts: none.

It refuses the same way when the stamp is already in the store and its
contents differ — two different captures cannot share one identity.
Loading the *same* bundle twice is a re-send, not a collision, and
succeeds.

**Everything ships by default.** `--no-plane2` trades the large member
for a small bundle, says what it left out, and records the omission in
the manifest so `--load` says so too — because "why is Plane 2 missing
over there" is a worse question than a large file:

```console
$ bga bundle --export @last --no-plane2 -o small.tar.gz
Wrote small.tar.gz
  snapshot 20260902T101112Z: 6 member(s), 10.8K before compression
  left out (--no-plane2): plane2.json
```

*Kept, not current* — the same 2026-09-02 capture as above, which held
one Plane 2 member. Cuts: the `load it with: bga bundle --load
small.tar.gz` line the command prints after the `left out` line, and the
`left out` list carries **every** `plane2*` member the capture had —
`plane2.json, plane2.log.gz, plane2-resource.json` on a capture holding
all three.

**A directory tree of bundles is a store** (`UX-900`) — the shape CI
keeps them in, one directory per build number. Every file under it
named `*bga-bundle.tar.gz` is a bundle, at any depth; anything else is
ignored. Two ways in, one loader, one refusal:

```console
$ bga snapshot --list --bundles ci
2 snapshots in ci:
  20260901T100000Z       2.0K  @prev
  20260902T100000Z       1.4K  @last
  total                  3.4K
$ bga bundle --load ci
Loaded 2 bundles from ci into /home/me/myproject/.bga/runs
  20260901T100000Z
  20260902T100000Z
  read them with: bga snapshot --list, or in place: bga snapshot --list --bundles ci
```

*Kept, not current* — 2026-09-29, the two `same_build_twice_*` fixture
runs exported into `ci/100/` and `ci/101/` beside a stray `console.log`;
the tree is built by hand, so nothing here re-runs it. Cuts: the
`--load` store path is shortened to a project's. The guard is
`tests/unit/test_a_tree_of_bundles_is_a_store.py`.

`--bundles DIR` goes with `--list`, `--aggregate` or `--capacity`, reads
the tree into a temporary copy and deletes it on exit — nothing is
added to the project's store. `--load DIR` materialises the runs into
the store, and is idempotent: a nightly can run it over a growing tree,
because a stamp already held with the same bytes is a re-send. The
trade is disk against repetition: on `tests/fixtures/same_build_twice_*`
the tree is 1,824 bytes and the store it becomes 3,466, which `--load`
keeps and `--bundles` holds only while it runs. Every bundle is checked
before any is written, so one bad bundle refuses the whole tree, by name:

```console
$ bga snapshot --aggregate --bundles ci
Error: 1 bundle refused, so nothing was written:
  ci/102/20260903T100000Z.bga-bundle.tar.gz is not a readable archive: Compressed file ended before the end-of-stream marker was reached
```

*Kept, not current* — 2026-09-29, the same tree with a 300-byte cut of
one bundle added as `ci/102/`. Cuts: none.

`bga compare --band-from-class [N] --bundles DIR` reads the same tree
the same way (`UX-1286`): the band's members are selected from it, with
the host filter, through a temporary store deleted on exit, so a review
runner needs no `project.conf` and keeps no `.bga`. A principal whose
stamp is also in the tree does not vote on its own band; a bad bundle
refuses the whole tree with exit `2` before anything is judged; and
`--bundles` without `--band-from-class` is a usage error. The comment
names the tree as the band's source, and `--format json` carries it as
`baseline_band_origin` — `{"kind": "store"|"bundles", "path"}` — beside
`baseline_band_skipped_for_host`, `{"count", "fields"}`: how many members
were skipped as measured on another host and which host fields differed
(`UX-1298`). Both are `null` when the band was not selected by class, and
the comment's sentence is rendered from them.

**`--resolve` rewrites pseudonyms back to real names, on this machine
only** (`UX-1064`) — a fourth mode of the same mutually-exclusive group,
for reading a reply that quotes an anonymized bundle's element names:

```console
$ echo "rebase j-xlqb.bst:d-tbec/d-ozlr/e-gap6.bst plus e-abcdef" | \
    bga bundle --resolve --key-fingerprint <fp>
rebase base.bst:components/gtk/gtk3.bst plus e-abcdef
Unresolved pseudonym-shaped tokens (1 token): e-abcdef
```

*Kept, not current* — the task file's own manual repro (`UX-1064`), not
re-run here. `--key-fingerprint` must match the project's local map or
the command refuses (`Error: map key fingerprint … does not match the
bundle's …`, exit 2) before it touches stdin. Cuts: none.

**`--anonymize` sends a capture out with every name replaced**
(`UX-1295`). It pseudonymizes under the project's key, `.bga/anon/key`,
created 0600 on first use, and records each pseudonym in
`.bga/anon/map.json` beside it, the map `--resolve` reads. Before
writing it shows one review screen and asks; anything but `y` writes
nothing, map included. With no terminal on stdin it prints the review
and refuses, and a name the residue scan finds refuses whatever the
answer. It goes with `--export` alone, not `--no-plane2`:

```console
$ bga bundle --export @last --anonymize -o out.bga-bundle.tar.gz
Anonymized bundle out.bga-bundle.tar.gz: 4 members
  members: run/graph.json, run/trace.json, run/run-context.json, plane2.json
  dropped: none
  values rewritten, per class: A 451 · E 15 · F credential 12 · F dropped 34 · F rebuilt 40 · H 13
  kept verbatim (71): --cyan, --help, --progress-dir, …
  residue scan: clean over 47 dictionary tokens; a tripwire, blind to a name it never held
  the graph's shape alone can identify a project (anonymized-bundle.md 6.5)
  key fingerprint 4dd12723ed46370a; the map stays on this machine
Write this bundle? [y/N] y
Wrote out.bga-bundle.tar.gz
  4 members, 43.6K before compression
  read a reply with: bga bundle --resolve --key-fingerprint 4dd12723ed46370a
```

*Kept, not current*: 2026-10-02, `tests/fixtures/macro_micro` copied
into a scratch project as one snapshot, answered on a pty. Cuts: the
output path shortened, and the `kept verbatim` list after its third
entry. The guard is
`tests/unit/test_bundle_export_has_an_anonymize_switch.py`.

For the CI direction — publishing to a git ref rather than one file —
see `bga baseline` and the capture-ref scheme below.

### The same job in CI

Use published capture refs (`bga baseline`, `UX-96`) rather than the
store. The store is the laptop's analogue of them, and a CI runner has
no persistent project directory to keep one in.

## `.bga/config` — the project's remembered settings (`UX-1303`)

`<project>/.bga/config` is one JSON object (`run_store.write_config`:
indent 2, sorted keys). `bga snapshot` rewrites it on every run and
keeps keys it does not know, so hand-edited keys survive. A file that
is missing, not JSON, or not an object reads as `{}`
(`run_store._json_dict`), and the next snapshot overwrites it.

| key | default | written by | format | what it changes |
|---|---|---|---|---|
| `trace_opens` | `true` | `bga snapshot` (`--trace-opens` / `--no-trace-opens`) | JSON boolean | whether the next capture traces file opens (`take_snapshot` in `tools/bga_snapshot.py`) |
| `trace_spine` | `"auto"` | `bga snapshot` (`--trace-spine=off\|on\|auto`) | JSON string | the ptrace spine policy of the next capture; see [Sticky flags](#sticky-flags) |
| `builds_per_day` | absent | by hand | JSON number > 0; anything else reads as undeclared (`bga/build_rate.py`) | the viewer's decision panel and `bga snapshot --list` carry `build_rate` (`per_day`, `source`), and the panel prices a saving in agent-hours a day beside it (`UX-1276`); never counted from snapshot stamps |
| `public_junctions` | `{}` | by hand | `{"<junction>.bst": {"checkout": "<path>", "tag": "<git tag>"}}` | `bga bundle --export --anonymize` passes the element names of that junction's tagged tree through unchanged instead of pseudonymizing them (`public_junctions` in `bga/run_store.py`, `bga/bundle.py`); a checkout or tag it cannot read refuses the export |

```json
{
  "builds_per_day": 40,
  "public_junctions": {"freedesktop-sdk.bst": {"checkout": "../fdo-sdk", "tag": "freedesktop-sdk-24.08"}},
  "trace_opens": true,
  "trace_spine": "auto"
}
```

Every key `bga/` and `tools/` read from this file is a row above;
`tests/unit/test_the_config_section_names_every_key_the_code_reads.py`
collects them from the source.

## `bga doctor` — before anything else (`UX-125`)

```bash
bga doctor                 # the environment
bga doctor PROJECT_DIR     # and whether this project can be captured
bga doctor --format json   # findings-style ids per check, for scripting
```

`bga doctor --capture` goes further (`UX-149`): it runs the whole capture
chain — `bst` → `buildbox-run` → the `$PATH` shim → the rewritten argv →
the recorders inside the sandbox — on a canned one-element build, and
reports per link in chain order. Seconds, and it needs a staged runtime
(`examples/stage_runtimes.sh`); it skips rather than building one. This
is the check to run when a capture fails on a build plain `bst`
completes — the first `FAIL` names the broken link, where `--diagnose`
would need the real failing build to say the same thing.

Read-only, one line per check, and a concrete remedy on every failure. It invents no check — each one fronts a failure that really happened while standing this project up, and the remedy quoted is the one that actually fixed it: a virtualenv for `pluginbase` under a distro-patched setuptools, `buildstream-plugins` for the `cmake` kind, the `apparmor_restrict_unprivileged_userns` sysctl for bwrap's loopback, `build-essential` for the hook and spine compile, `stage_runtimes.sh`/`stage_cpp_toolchain.sh` for a sandbox with no shell.

Details worth knowing:

- **bwrap is probed, not just found.** Presence is not the check that matters — bwrap's namespace setup succeeds and then the sandbox fails to bring up loopback, deep inside a build. `doctor` runs the same trivial sandboxed command CI's `bst-smoke` job does.
- **The compiler is the capture's own, and it compiles the real hook** (`UX-1287`). `c-compiler` resolves `cc` then `gcc` exactly as `compile_hook` does and compiles `tools/native_trace/hook.c` once into a scratch directory it removes, so a missing compiler and one that cannot build the hook (no libc headers) are both a `FAIL` worded as the capture would raise it, naming `build-essential`. A compiler that cannot link `-static` stays a warning: only `--trace-spine` needs it.
- **"No element plugin registered for kind" gets two different remedies**, because it has two different causes: the package is missing, or the project has not declared it. Telling a user to install what they already have is how a diagnostic loses its reader.
- **A stale `buildbox-casd` is checked before the build, not guessed at afterwards** (`UX-161`). Any plain `bst` command leaves a daemon holding the cache directory, and a capture that starts under one fails in a way the summary could previously only speculate about. `doctor` reads `/proc` for a casd already holding this project's cache — the directory `bst` itself would use, `buildstream2.conf` before `buildstream.conf` (`UX-166`) — and prints the remedy.

Exit `1` only on a failure. A static-binary blind spot (`--trace-spine=auto` is the answer) and an empty Plane 3 log tree are **warnings**: facts to read, not broken environments. `bst-tests` runs it as a step, so its checks cannot drift from what CI actually installs.

## `bga analyze` — basic usage

### Analyze a Build Run

The primary command analyzes a directory containing `run-context.json`, `graph.json`, and `trace.json` (the run-context/v9, graph/v9, and trace/v9 schemas, Part 32) - **not** a raw BuildStream cache/artifacts path directly; nothing in a live BuildStream cache is already in this shape.

```bash
bga analyze RUN/
```

To produce a real run directory in this shape from an actual BuildStream project and build log in one step, see `tools/bst_extract_run.py` (`docs/spec/ingestion-pipeline.md`) - or try the CLI right now against a checked-in sample fixture with no BuildStream install needed at all: `bga analyze tests/fixtures/golden/mixed_task_kinds` (see the README's Quick Start).

**Output:**
By default, `bga` prints a human-readable summary to stdout, leading with a synthesized **Key Findings** block (confidence headline, the single largest wait-category opportunity, the top elements by blast radius/criticality probability when `--diagnostics` ran, and certified headroom in plain language) before the detailed sections:

- **Confidence & Violations**: Overall confidence score, any failed hard gates, and a one-line summary per violation - previously only visible via `--format json`.
- **Certified Floors**: $T_\infty$, Lower Bound ($LB$), Certified Headroom, and an Efficiency Score ($LB$ / **horizon**, 0.0-1.0 — the horizon is first-task-start to last-task-finish, *not* total duration, which also contains the untracked head and tail; on `tests/fixtures/golden/mixed_task_kinds` the two give 1.00 and 0.875) - measures scheduling efficiency of the observed work, not whether that work itself is minimal; see Critical Path for the latter. $LB$/Efficiency Score certify against this run's *recorded* resource capacities (`--builders`/`--fetchers`/`--pushers`), not real host CPU cores - a native build system's own internal parallelism (`--max-jobs`, e.g. `make -jN`) is a separate axis `bga` does not model here, and the two can genuinely compete for the same cores (see `docs/backlog/scenarios/UX-0009-builders-max-jobs-joint-optimization.md`'s real evidence). A one-line note to this effect always accompanies the Certified Floors block, naming this run's own real numbers when a `resource_oversubscription` violation was detected for it (see `docs/backlog/scenarios/UX-0012-capture-native-max-jobs-and-host-cores.md`). When the run declares its own CPU budget (`--cpu-budget` at extraction time, e.g. because a cgroup CPU quota isn't visible to raw host-core detection), that declared budget - not the detected host core count - governs this check (see `docs/backlog/scenarios/UX-0015-declared-cpu-budget-overrides-host-detection.md`).
- **Efficiency Metrics**: Parallelism, Utilization, and Attribution breakdown.
- **Critical Path**: The sequence of tasks determining the minimum build time.
- **Bottlenecks**: Elements with high blast radius or criticality probability.

The Key Findings/Confidence blocks are shown for the full `analyze` report only - the section subcommands (`graph`/`floors`/`replay`/`utilisation`/`diagnostics`) and `--format csv` do not render them. They are **not** presentation-only: since `UX-75` every conclusion in them is computed once in `bga/findings.py` and published to `--format json` as the `findings` array described below, so the two formats cannot disagree.

### Options

#### Evidence under each claim (`--explain`)

`--explain` prints, under each claim, its evidence fields, the rule that fired and the query that deepens it. Opt-in, and the same flag on `bga analyze`, `graph`, `floors`, `replay`, `utilisation`, `diagnostics` and `bga correlate`.

#### Output Format

Control the output format using `--format` (or `-f`):

- `text` (default): Human-readable summary.
- `json`: Machine-readable JSON object (suitable for piping to `jq`).
- `csv`: Comma-separated values for attribution data.

```bash
bga analyze RUN/ --format json > report.json
```

The JSON carries a **`findings` array** — the same conclusions the text report's `Key Findings` block renders, as data. Each entry has a stable `id` (what a CI gate keys on, and what a run-to-run diff joins on — it does not change when the wording does), a `severity` (`critical`/`high`/`medium`/`info`), the `elements` it concerns, and an `evidence` object with the raw numbers behind the sentence. Both formats render from this one list, so they cannot disagree, and a consumer never has to re-derive a threshold from `bga/report/text.py`:

#### Declaring a foundation tier (`UX-683`)

A toolchain or base image can have the widest reach in the graph *by
design*, and the kind-based exemption (`blast-radius-structural`,
`fan-in-structural`) only misses it when it is built as an
`autotools`/`manual`/`cmake` element rather than an `import`/`stack`.
`project.conf`'s own `variables: {bga-foundation: "a.bst,b.bst"}` — a
comma-separated string, not a list, and not a top-level `bga:` key: real
`bst show` rejects both — declares it instead. Read at extraction
(`tools/bst_extract_run.py:222-260`) and validated against the graph; a
declared name absent from it is a warning, never a crash.

Declared, the element publishes at `blast-radius-foundation` /
`fan-in-foundation` below — present, separated, never the top row of
`blast-radius-ranking` / `fan-in-ranking` — and its
`expected_rebuild_cost` row sorts last regardless of cost. Undeclared,
`foundation-candidates` proposes it: the owner declares, the tool only
proposes. On `tests/fixtures/foundation_declared` (`sink.bst` is the
sole consumer of four dependencies, and its own `graph.json` declares
it foundation):

```bash
bga analyze tests/fixtures/foundation_declared/run --diagnostics --format json \
  | jq -c '{top_fan_in: .elements.top_fan_in, fan_in_findings: [.findings[] | select(.id | test("fan-in")) | .id]}'
```

```text
{"top_fan_in":[],"fan_in_findings":["fan-in-foundation"]}
```

With the same graph's `"foundation": ["sink.bst"]` key removed (the same
command against a copy):

```text
{"top_fan_in":["sink.bst"],"fan_in_findings":["fan-in-ranking"]}
```

`sink.bst` leads `top_fan_in` and `fan-in-ranking` undeclared, and
neither once declared — the tier, not the graph, moved. One
comma-separated `bga-foundation` line is the whole declaration; nothing
downstream of it needs its own flag.

#### Declaring a custom source kind (`UX-833`)

`bga/blast.py` names a source kind by heuristic over the kinds
BuildStream ships — a project sourcing through a custom plugin (a
Gerrit source, an internal mirror) matches nothing and its blast goes
unreported. The sibling declaration, beside `bga-foundation`:
`variables: {bga-source-kinds: "gerrit=git,mirror=tar"}` — each entry
maps a plugin kind onto a kind `bga/sources.py`'s `KEYING_BY_KIND`
already knows, whose keying (`ref` or `content`) it then inherits.
Read and validated at extraction (`tools/bst_extract_run.py`,
`_read_bga_source_kind_map`): an entry that is not `custom=known`, or
whose right side names no known kind, raises, naming the entry. A kind
still unmapped after resolution stays `unknown` and is named in
`bga analyze --format json`'s `resource_blast.unmapped_source_kinds`,
never silently folded into an unestimated blast.

#### The full `findings[].id` set

`id` is the contract — it does not change when the wording does, so a CI gate keys on it. Every id `bga` can emit, and nothing else:

`bga analyze --format json` → `.findings[].id` (all defined in `bga/findings.py`; the set is test-enforced against this table):

| id | severity | what it says |
|---|---|---|
| `build-failed` | critical | one or more elements ended in FAILURE; every figure below describes an incomplete build |
| `failed-task-time` | high | how much of the measured chain was work that was thrown away |
| `confidence` | varies | the confidence headline and any failed hard gates |
| `run-mode-incremental` | info | this run was incremental, so its durations are not a cold-build baseline |
| `cache-hit-ratio` | varies | how much of the project the cache reused, and for the requested target's own closure. On a caches-off run it reports the fact at `info` rather than banding it (`UX-86`) |
| `cache-capacity` | varies | the local cache is at or past the low watermark it is configured with, or its quota is larger than the volume under it can give - so a rebuild here may be an evicted artifact rather than a moved cache key (`UX-896`) |
| `artifact-weight` | info | which elements' artifacts are the heaviest in the local cache, walked per element from the CAS (`bga extract --artifact-weights`). Each figure is that artifact's whole weight, so the rows overlap where two artifacts share a blob; the finding says by how much (`UX-907`) |
| `cache-transfer-cost` | medium | this build spent a notable share of wall-clock moving artifacts rather than making them |
| `wait-category` | varies | the single largest non-execution wait category, when it clears the 1% floor |
| `execution-bound` | info | no wait category clears the floor — the time is in the work itself |
| `certified-headroom` | varies | proven room to improve scheduling without changing any element |
| `efficiency-score` | varies | how close the scheduler got to the certified floor |
| `time-concentration` | varies | which elements the critical path's duration is actually in |
| `mesh-graph` | info | most elements have zero slack **and some are off the critical path** — several chains of equal length, so a saving on one is capped by the next (`UX-475`) |
| `graph-width` | info | how many dependency stages the graph has and how many elements its widest holds — the ceiling on concurrency the shape imposes, read from the dependencies alone and from no duration (`UX-478`) |
| `chain-graph` | info | most elements have zero slack and all of them are on the critical path — one chain, so a saving on any of them is worth its own duration (`UX-475`) |
| `blast-radius-reach` | medium | elements a change to which rebuilds something else, named with their downstream count. Published whatever the diagnosis says — a chain-bound build has a blast radius too (`UX-479`) |
| `blast-radius-ranking` | varies | elements worth fixing first by downstream reach (needs `--diagnostics`) |
| `blast-radius-structural` | info | elements whose reach is the graph's shape rather than a task — a base image, a toolchain, a stack. Reported, not ranked (`UX-258`) |
| `blast-radius-foundation` | info | a project-declared foundation element with the widest reach — the kind exemption above misses it; the owner's declaration doesn't (`UX-683`) |
| `foundation-candidates` | info | non-structural elements at or above the top p5 fan-out and not declared foundation — [declare or dismiss](#declaring-a-foundation-tier-ux-683) (`UX-683`) |
| `fan-in-ranking` | info | the mirror: elements that *pull in* the most, ranked by upstream closure, with each count placed in the graph's own deciles |
| `fan-in-structural` | info | a stack or a base image whose closure is the widest — it depends on everything on purpose, so the count is shape and not a task |
| `fan-in-foundation` | info | a project-declared foundation element with the widest closure — the fan-in mirror of `blast-radius-foundation` (`UX-683`) |
| `criticality` | varies | elements most likely to be on the critical path under duration variance (needs `--diagnostics`) |
| `optimization-horizon` | varies | what the build drops to after each of the next few fixes |
| `joint-saving` | varies | whether the recommended set's savings add up or overlap |
| `latent-heavies` | info | heavy elements off the critical path, worth nothing to fix today |
| `capacity-recommendation` | varies | the joint `--builders` × `--max-jobs` answer (`UX-116`): the sweep's scheduling knee, Plane 2's measured cores-busy, the `UX-104` memory ceiling and the host's cores, intersected, with the **binding** constraint named and the others shown beneath it. `high` when the run is configured above what its own measurements support, `medium` when there is room to grow, `info` when it is already at its ceiling. Needs `--plane2` |
| `memory-envelope` | varies | what this build's measured per-element peak RSS implies for `--builders` against the host's RAM — `high` when the current builders count does not fit, `medium` when one more would not, `info` otherwise. Needs `--plane2` and a capture that recorded the host's memory (`UX-104`) |
| `swap-observed` | high | pages were written to swap while the host's CPU was oversampled — the window span and the elements building in it, from `overcommitted_intervals`' own `swapped_out` count (`UX-676`, `UX-860`). Needs a capture with a host CPU series that recorded a rising `pswpout` |
| `costliest-binary` | info | the binary that spent the most CPU, `by_binary[0]`, when its share of measured CPU clears the 1% opportunity floor (`UX-1255`). Needs `--plane2` with per-element binaries |
| `jobs-waiting` | medium | elements that asked for more than one job and ran under 1.25 cores busy, each element's own CPU over its own wall — the line `bga correlate` calls waiting, not computing — counted, with their median (`UX-1255`). Needs `--plane2` |
| `configure-share` | medium | configure is at least 10% of measured CPU, from `configure_phase` (`UX-1255`). Needs `--plane2` |
| `remote-execution-whatif` | info | what remote execution would buy, priced two ways and never summed (`UX-680`): `bga sweep`'s own unbounded-builder row (BuildStream REAPI moves whole sandboxes, so it removes the builder cap) and Plane 2's compiler/linker CPU on the critical path (compiler-level RE like recc/reclient moves compiles out of the sandbox, so it removes compile seconds from the agent). `evidence.additive` is always `false` - both remove the same critical-path seconds. The compiler-offload half needs `--plane2` and a capture with `binary_cost`; without one, only the builder-cap half publishes |
| `shared-source-blast` | medium | one repository's ref decides most of this build's rebuilds: any commit to it rebuilds N of M elements, because its direct elements key on its ref rather than on the files they stage (`UX-171`). Needs a run whose `sources.json` the extraction wrote |

`bga correlate --format json` → `.actionable[].recommendations[].id` (9) and `.restructuring[].id` (1):

| id | severity | what it says |
|---|---|---|
| `pinned-to-one-job` | high | waiting rather than computing, and its native build asked for `-j1` |
| `underachieved-requested-jobs` | high | waiting rather than computing despite asking for more jobs |
| `waiting-not-computing` | high | waiting rather than computing, cause not named by Plane 2 |
| `already-compute-bound` | high | a negative result: nothing to gain from its parallelism |
| `cpu-concentration` | high | one binary is most of its measured CPU |
| `serialization-point` | high | a single process holds a material share of its wall time |
| `peak-memory` | medium | its largest process's peak RSS, to multiply by concurrency |
| `redundant-operation` | medium | it pays for an operation other elements also run |
| `declared-not-used` | info | opened no file staged by a declared build dependency — evidence, not a verdict |
| `unread-gating-chain` | high | a *group* of never-read edges chains elements along the critical path (`UX-82`) |
| `merge-candidate` | medium | sibling elements spending at least half their time on sandbox toll rather than building — needs `--cache-logs` (`UX-100`) |
| `merge-not-indicated` | info | no element pays more sandbox tax than it builds, and how far the worst one is from the line |
| `split-candidate` | info | an element holding a material share of the critical path with real internal parallelism — evidence, never a projection (`UX-100`) |
| `consolidate-by-co-change` | medium | two elements co-rebuild in ≥ 90% of both their histories and neither is consumed alone — needs `--cache-logs`'s change frequency (`UX-682`) |
| `split-by-co-change` | info | an element's direct consumers split into ≥ 2 groups that never co-rebuild with each other — needs `--cache-logs`'s change frequency (`UX-682`) |

`bga cache-logs --format json` → `.findings[].id` (1), built in `tools/bst_cache_logs.py` rather than `bga/findings.py` because it reads BuildStream's own logs and, optionally, a Plane 2 report — neither of which the run-directory analyzer has:

| id | severity | what it says |
|---|---|---|
| `configure-tax` | varies | how much of this log tree's element time went to the build system configuring itself, who paid the most, and — with `--native-report` — the same figure measured from the traced process tree (`UX-102`) |

`bga cache-trend --format json` → `.findings[].id` (1):

| id | severity | what it says |
|---|---|---|
| `cache-trend-regression` | high | a trended cache metric on the newest run left the band its trailing window describes — the metric, both values and the band are in `evidence` (`UX-103`) |

A finding not in the run's output simply did not fire; ids are never emitted with an empty or placeholder value.

```bash
# Is this build chain-bound, and which elements is its time in?
bga analyze RUN/ --format json \
  | jq '.findings[] | select(.id == "time-concentration") | .evidence'

# Anything critical or high, as a gate condition
bga analyze RUN/ --format json \
  | jq -e '[.findings[] | select(.severity == "critical")] | length == 0'
```

#### Conditioning capacity advice on Plane 2 (`--plane2`) — `UX-83`

```bash
bga analyze RUN/ --plane2 PLANE2.json
bga sweep   RUN/ --resource PROCESS --plane2 PLANE2.json
```

The `RESOURCE WAIT` hint and `sweep`'s knee point are both replay-model answers, and the replay model does not know about CPU (`UX-09`/`UX-14`). Measured once on a real dual-plane capture: `analyze` said *"31.9% of wall-clock is RESOURCE WAIT — try `--capacity N` with a higher N"* and `sweep` put the knee at capacity 5, on a 4-core host — while `correlate` on the **same capture** named the real fix, an element pinned to `-j1`, worth −32.4% and costing no extra capacity.

With `--plane2`, both consult what was actually measured inside the sandboxes:

- a host Plane 2 measured as already CPU-saturated is told **not** to raise capacity, with the measurement quoted;
- an element pinned to `-j1` is named **first**, because intra-element parallelism is capacity you already have and, unlike `--builders`, it cannot contend with itself.

- the four constraints on the joint (`--builders` × `--max-jobs`) choice are **intersected** into one
  recommendation naming the binding one (`UX-116`), instead of four blocks a reader has to reconcile:

```text
Capacity: builders 4 x max-jobs unrecorded on 4 core(s): CPU binds at 4 (the host's cores bound it, not the raw 7) - at the 4 configured
  graph allows 6: the sweep's knee is at 6 builder(s)
  CPU allows 4: 2.11 of 4 core(s) busy at builders=4, i.e. 0.53 core(s) per concurrent element - 7 before the host's 4 cores bound it
  memory allows 9: the 9-builder envelope fits in 15.7 GB (measured over 9 element peak(s), so it says nothing above 9)
  Free capacity you already have: core.bst asked its native build for -j1 - a builder slot drawing one core.
```

  The CPU ceiling is derived, not assumed: `cores_busy / builders` is what one concurrently-building element
  actually drew, and the ceiling is how many of those the host's cores can feed - never more builders than
  the host has cores (`UX-861`; the raw figure stays beside it as `clamped_from`). A constraint nothing measured
  is omitted rather than treated as unbounded, and the whole block declines to appear at all when Plane 2 has
  no `cores_busy` — the same bar `UX-83` uses.

Without `--plane2` every line is byte-identical to before — including `UX-09`/`UX-15`'s standing "native
build-system parallelism is a separate, currently unmodeled axis" note, which is retired **only** in captures
where the block above actually ran.

#### Resource Capacity

Override the detected system capacity (useful for simulating different hardware):

```bash
bga analyze RUN/ --capacity 16
```

*Note: This affects the calculation of the Lower Bound ($LB$) and Replay Makespan ($T_C$).*

#### Replay Simulation

Run the deterministic replay scheduler to compute a feasible makespan ($T_C$) under the chosen scheduling heuristic - a counterfactual model for scheduler comparison, capacity sweeps, and model slack (Part 18), not a claim that $T_C$ is the mathematically optimal schedule:

```bash
bga analyze RUN/ --replay
```

You can specify the scheduling heuristic:

- `lpt` (Longest Processing Time first) - Default; a common, reasonable heuristic, not guaranteed optimal.
- `spt` (Shortest Processing Time first).
- `fifo` (First In First Out).
- `depth` (Dependency depth priority).

```bash
bga analyze RUN/ --replay --heuristic lpt
```

#### Diagnostics

Enable advanced diagnostic signals (adds computation time):

```bash
bga analyze RUN/ --diagnostics        # -d is the short form
```

This computes:

- **Blast Radius**: Number of downstream dependents for each element.
- **Criticality Probability**: Likelihood an element appears on the critical path under duration variance.
- **Wall-Clock Shares**: Attribution of wall-clock time to specific elements.

#### Output File

Save the report to a file instead of stdout:

```bash
bga analyze RUN/ --output report.txt
```

#### Cold Structural Floor (advisory)

Compute the advisory **cold floor** (`T∞,cold`) using prior runs' observed durations as an estimate source. *Two unrelated "cold"s meet here* (`UX-138`): this structural floor, and the **cold capture mode** (caches off) that `run-mode-incremental` above is about. This flag is the floor; nothing here changes how a build was captured. Off by default - never affects `LB`, `certified_headroom`, primary `confidence`, or measured attribution:

```bash
bga analyze RUN/ --cold --history-dir PRIOR-RUN-1/ --history-dir PRIOR-RUN-2/
```

- `--cold` alone (no `--history-dir`) has nothing to estimate from. In `--format json` the cold fields are present and null; the **text report prints no cold line at all** rather than a line saying "unavailable" — absence is the report's way of saying a number was not computed, and it is the same in both formats in the sense that neither fabricates one.
- By default, if any element on the resolved cold critical path has no resolvable historical duration, `T∞,cold` reports as unavailable rather than a misleading partial number.
- `--allow-partial-cold` (only meaningful together with `--cold`; a no-op with a warning if passed alone) instead publishes a value with `partial=true`/`confidence=low` in that case.

#### CPU floor (`UX-891`, needs Plane 2)

Every other certified floor divides by **builder slots**. A build whose
elements each run a native build system under one slot can be core-bound
long before it is slot-bound, and no slot-denominated floor can see it.
When a Plane 2 report is joined in, `analyze` publishes a second floor
that divides total measured CPU time by the governing core count:

```text
  LB_cpu (CPU over cores):     17.45s (4 cores from host_cpu_count, coverage 0.82)
```

It sits **beside** `LB`, never folded into it: `LB` stays the certified
slot-denominated floor, and the capacity-model note says which of the two
binds. In `--format json` the five keys under `floors` are

| key | meaning |
|---|---|
| `lb_cpu_us` | the floor, integer µs; **absent** without Plane 2 or without a governing core count, never `0` |
| `lb_cpu_coverage` | `measured_processes / (measured + unmeasured)` - how much of the seen process population the number rests on |
| `lb_cpu_governing_cores` | the core count it divided by |
| `lb_cpu_cores_source` | `cpu_budget` when the run declared one, otherwise `host_cpu_count` |
| `lb_cpu_binds` | whether `lb_cpu_us` exceeds `lb` |

None of them is in `required` - a run without Plane 2 carries none, which
is the same contract the cold fields keep. The three assumptions the
number rests on are printed under it in the text report, as
`bga/floors/cpu.py` declares them. See section 4c of
`in-step-parallelism.md` for why it stays beside `LB`.

## Advanced Commands

### Version

Check the installed version:

```bash
bga --version
```

### Verbose Logging

Enable debug logging to troubleshoot ingestion or normalization issues:

```bash
bga analyze RUN/ --verbose
```

## Section Subcommands

`analyze` is the primary command and produces the full report (every section together). `graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics` are thin aliases over the same analysis pipeline - each restricts output to just its own section, so you don't have to grep a full report or a `jq` filter out of `--format json` for a narrow question. They accept the same relevant `analyze` flags (`--format`/`--output`/`--capacity`/`--verbose`/`--quiet`/`--log-file`, plus each subcommand's own natural options) and the same exit-code contract.

```bash
bga graph RUN/          # static dependency graph, critical path, structural metrics
bga floors RUN/ --cold  # certified/advisory floors (T-infinity, LB, LB_cpu, certified headroom, cold floor)
bga replay RUN/ --heuristic spt   # deterministic replay makespan (T_C)
bga sweep RUN/ --resource PROCESS --min-capacity 1 --max-capacity 16  # capacity sweep (Part 19)
bga utilisation RUN/    # CPU utilisation accounting
bga diagnostics RUN/    # blast radius, criticality probability, wall-clock shares
```

## `bga graph`

Dependency graph, critical path, structural metrics. One of the section subcommands above.

`graph` has its own `--by-kind` flag (P4-12, non-spec additive signal): `bga graph RUN/ --by-kind` also shows aggregate stats (count, total/avg observed duration) grouped by each element's real BuildStream plugin kind (`import`/`manual`/`junction`/`stack`/...) - off by default, since it's extra detail beyond the base graph section.

## `bga floors`

Certified and advisory floors only. One of the section subcommands above.

`floors` accepts the same `--cold`/`--allow-partial-cold`/`--history-dir` flags as `analyze` (matching the spec's own `bga floors RUN --cold` example).

## `bga replay`

Replay makespan (T_C) only. One of the section subcommands above.

`replay` accepts `--heuristic`.

## `bga sweep`

Capacity sweep for one resource. One of the section subcommands above.

`sweep` has its own `--resource`/`--min-capacity`/`--max-capacity`/`--step` flags and isn't a slice of `analyze`'s output at all - it runs a series of replay simulations across a capacity range and reports predicted `T_C`, normalized improvement, and the diminishing-returns "knee" point per capacity value. Every replay/task duration in that sweep is fixed to what was actually observed - the model does not account for real CPU contention as concurrent `PROCESS` usage rises (`docs/backlog/scenarios/UX-0009-builders-max-jobs-joint-optimization.md`'s own real evidence: raising `--builders` can make a real build *slower*, not just plateau, once cores are oversubscribed), so `bga sweep`'s own text/JSON output always carries an explicit caveat to this effect (`docs/backlog/scenarios/UX-0014-sweep-replay-blind-to-contention-slowdown.md`) - treat the predicted curve as a shape, not an exact runtime prediction (Part 19).

## `bga utilisation`

CPU utilisation accounting only. One of the section subcommands above.

## `bga diagnostics`

Advanced diagnostics only. One of the section subcommands above.

## `bga timeline` — one trace, both planes (`UX-188`, `UX-298`)

```bash
bga timeline @last              # -> <snapshot>/timeline.perfetto-trace.gz
bga timeline @last --format chrome          # -> <snapshot>/timeline.json
bga timeline @last -o /tmp/t.gz --anchor-element components/openssl.bst
bga timeline @last --planes 1               # no process lanes
bga timeline @last --only-element core.bst  # one element's process lanes
```

Plane 1's element schedule always; Plane 2's process lanes underneath it
when the snapshot kept its raw trace log — which `bga snapshot` does by
default (gzipped, **8% of its size**, measured on two real captures).
`--no-keep-raw` opts out.

**The default is Perfetto's own format** (`UX-298`): protobuf
TrackEvent, gzipped, written packet by packet as the records are paired
rather than assembled in memory. That is what [Perfetto](https://ui.perfetto.dev)
and `trace_processor` read natively, and it is a stream — a capture too
big to hold is no longer a capture too big to render. Measured on a
40,000-process trace: 4.83 MB of packets, 1.14 MB gzipped, and bytes on
disk 10,000 slices before the writer closes.

`--format chrome` writes the legacy JSON instead, for `chrome://tracing`
and for a pipeline that already parses it. Both read the same two logs
and align on the same anchor, so the choice is about what will open the
file, not about what is in it.

**When the trace is too big to open** (`UX-430`): Perfetto draws a row
per track, and the process lanes are where that count grows — one per
element plus one per traced pid. Measured on the seeded scale run
(`bga gen-synthetic --seed 1`, 1,202 elements, twelve processes each),
re-measured in round 83, because two earlier rounds published two
different byte figures for this same trace and only one of them can be
current (`UX-578`):

```text
                  tracks   slices     bytes
  both planes     16,832   15,628   491,074
  --planes 1       1,205    1,204    71,752
  --only-element   1,219    1,216    72,694
```

Tracks and slices are exact and repeat; the byte column moves by a few
bytes between runs because the anchor element's name is written into the
trace, so it is quoted to the kilobyte everywhere else.

`--planes 1` leaves the process lanes out; `--only-element` keeps one
element's, and narrows its exec arrows and the concurrency counter with
them, so the lanes and the counter agree about what is being shown. The
byte size never noticed: 491 KB is an eighth of the 4 MiB the handoff
bounds transfer at.

The two planes are aligned on one element that appears in both; without
`--anchor-element` that is the longest-running element **both planes
know** — Plane 2's longest alone can name one Plane 1 never built, and
the merge then refuses a question that should not have been asked.

Without a raw log it renders Plane 1 and **says what is missing** rather
than silently producing half a timeline.

This composes `bga log-to-chrome` and `bga native-to-chrome combined`,
which still work on their own. Feeding either a file with no parseable
trace lines is now a **refusal**, not `Wrote 0 trace events` and exit 0 —
the usual cause is a `plane2.json` report where a raw log belongs. Every
converter's status line goes to stderr; the payload is the file.

## A capture that meets a laptop lid (`UX-185`)

The hook and the spine stamp `CLOCK_MONOTONIC`, which **does not advance
while the machine is suspended**; the Plane 1 wrapper stamps wall clock.
So a suspend mid-capture leaves Plane 2 under-reporting the elements it
crossed and Plane 1 over-reporting them, and nothing about the run looks
wrong.

**Detection is not optional.** Every capture records both clocks at both
ends; wall time running ahead of monotonic time is how long the machine
slept. Past five seconds the run declares itself incomplete, and
`UX-156`'s grammar does the rest — `bga analyze` banners it and `bga
compare` refuses the verdict, with exit 6 under a gate:

```text
This capture spans a suspend: the machine slept for about 45 minutes
while it ran. ... Re-run with `--inhibit`, or on mains power with the
lid open.
```

**Prevention is.** `--inhibit` wraps the build in `systemd-inhibit
--what=sleep:shutdown` (and `gnome-session-inhibit --inhibit idle` when
present), which is not the default because taking a lock on your power
management uninvited is not `bga`'s call:

```bash
bga snapshot --inhibit -- bst build all.bst
```

With neither inhibitor installed it says so in one line and runs anyway.
`bga doctor` warns when the machine has a sleep policy that could fire.

The spans are **not** corrected — which processes were mid-flight at the
suspend is recorded nowhere, so there is nothing to correct them with.
Refusal is the honest output.

## Long reports (`UX-187`)

On a build whose critical path is hundreds of elements, the path alone
used to be **405 of the report's 498 lines** — 81% of it, with every
section a reader acts on below the fold. The list-shaped sections now
render their two ends and fold the middle:

```text
    layer10/mod003.bst                          7.90s (  0.3% of path)
    ... 382 more element(s) (--full-path to print all)
    layer393/mod005.bst                         4.60s (  0.2% of path)
```

A chain's two ends are where an optimizer starts — the root everything
waits on, and the last link before the build finishes — so the middle
is what goes.

| flag | restores |
|---|---|
| `--full-path` | every element of the critical path |
| `--full-sources` | every row of the Shared Sources table |

**Nothing is cut silently**: every elision names its own count and the
flag that undoes it. **JSON never truncates** — the caps are a
text-rendering concern, `--format json` carries the whole thing, and
the `--full-*` flags do not change one byte of it.

## Progress on a long run (`UX-183`)

The phases that take minutes — parsing a 200k-process trace, pairing it,
the census walk, `bst show`, measuring the store — draw a single
self-overwriting line on **stderr**:

```text
  parsing trace: 120000/480000
```

**Only when stderr is a terminal.** Redirect it to a log file or a pipe
and the output is exactly what it was before: `UX-159`'s whole phase
lines, and nothing else. No carriage returns, no partial lines.

**stdout is never touched.** `bga analyze --format json | jq .` produces
the same bytes whether or not anything is being drawn, and there is a
guard asserting exactly that.

Turn it off on a terminal with `BGA_NO_PROGRESS=1`, or
`bga snapshot --no-progress`.

## `bga blast` — what rebuilds if I touch this (`UX-172`)

The blast-radius question from whichever end you have it:

```bash
bga blast https://gitlab.example.com/org/monorepo.git @last   # a repository
bga blast components/lib-a                                    # a path in the project
bga blast lib-a.bst                                           # an element
bga blast gitlab.example.com/org/monorepo --no-cost           # structure only
```

The run defaults to `@last`. The target is resolved **url, then path,
then element**, and the answer says which reading it used and which
others also matched — a project can name an element after a directory,
and the command picks deterministically rather than silently.

An identity the run's `sources.json` already knows resolves *before*
those heuristics, so the resource cell the `Shared Sources` table
printed can be pasted straight back in (`UX-178`; `UX-192` stopped the
table eliding long identities, which had reopened it).

| flag | what it does |
|---|---|
| `--project PATH` | the project a relative path resolves against; defaults to the enclosing BuildStream project |
| `--no-cost` | skip the measured rebuild time. The direct set, the closure and the kind split come from the graph and the inventory alone, which on a project of thousands of elements is the difference between a lookup and a full analysis — **0.10s against 3.22s** on the 1,202-element synthetic run (`UX-182`). The answer then says `Cost: not measured` rather than reporting zero |
| `-f, --format` | `text` or `json` |
| `-o, --output` | write to a file instead of stdout |

**A question, not a gate**: `bga blast` exits 0 on an answer of zero the
same as on an answer of two hundred. Gating belongs in `bga compare`,
where the refusal grammar already lives.

The work it reports is the **sum of the blast elements' own durations**,
not wall clock — a build with any parallelism completes it in less.

## `bga compare` — Run-to-Run Comparison

Not a spec-mandated command (`UX-1`) - compares a baseline run against a candidate run and reports signed deltas in certified floors, efficiency score, and attribution, plus a verdict:

```bash
bga compare /path/to/before-run /path/to/after-run
bga compare /path/to/before-run /path/to/after-run --format json | jq '.verdict'
```

The verdict is one of `improved`/`regressed`/`no significant change`/`within the baseline set's own observed range` (`UX-170` — outside the band, but a duration the baseline runs themselves reached, so not evidence of a change)/`not comparable (baseline has no measurable duration)` (a >=1% change in total build duration, relative to the baseline, is the significance threshold), always followed by an explicit caveat when either run's confidence is below the "high" band, and a **refusal** (`UX-78`) when the two runs are not comparable at all — either their graphs share fewer than half their element UIDs (they may not even be the same project) or one is a caches-off run and the other incremental. A refusal prints the failing check to stderr, prints no comparison, and exits **6** — deliberately not 4 or 5, so a CI job keying on the gates cannot read a wrong-artifact-path bug as a regression. `--allow-mismatch` restores the older behaviour: the warning is printed above the comparison and the exit code is the gates' own. Otherwise the exit code is 0 for a successful comparison regardless of verdict — comparing is not itself a failure condition. `--capacity`, if given, applies symmetrically to both runs.

`--band-k K` sets the noise band's width in scaled-MAD units; `bga baseline --band-k K` passes it through to this compare.

### CI Regression Gate (`--fail-on-regression`)

Not spec-mandated (`UX-3`) - opt-in gating mode for a CI pipeline that wants to actually *fail* on a genuine regression, not just report it:

```bash
bga compare /path/to/baseline-run /path/to/candidate-run --fail-on-regression
```

Exits `4` (a distinct code from 1/2/3, which all mean "`bga` itself failed" - see Exit Codes below) when the candidate run's real total duration (Part 4.3) regressed beyond the threshold - by default, the same >=1% significance rule the verdict uses **when no baseline set was supplied**. With `--baseline-run`s the two can diverge deliberately (`UX-180`): the verdict is judged against the noise band, and `UX-170`'s disputed region withholds a verdict the gate would still fail on. Neither is silent — the report names the rule it applied, and a pipeline that wants the band's judgement should read `verdict`, not only the exit code. Override the threshold with `--regression-threshold PCT` (e.g. `--regression-threshold 5` to only fail on a regression of 5% or more). `total_duration_us` is the one primary gating metric - deliberately not an ambiguous multi-metric combination.

`--format ci-comment` renders the same verdict as markdown for a pull-request comment — the band verdict, every gate with a one-sentence reason, the elements the change added or moved onto the critical path, and (with `--native-report`) which of their declared dependencies nothing read. Render-only: no number in it is computed there, and the gate verdicts come from the same predicates the exit code does. See [`ci-comment.md`](ci-comment.md) for the worked GitHub Actions wiring.

A refused comparison (`--allow-mismatch` not given, exit 6) is checked before any gate, since "these runs are not comparable" is not a verdict about the build. A low-confidence comparison (either run's confidence below the "high" band) **fails open**: exits `0` with a warning printed to stderr, rather than blocking a pipeline on a possibly-noisy signal. The comparison report itself is always printed to stdout/`--output` regardless of the gate outcome, so a failing pipeline still shows *why*.

Worked GitHub Actions example - extract two runs and gate on the comparison:

```yaml
- name: Extract baseline and candidate runs
  run: |
    bga extract "$PROJ" baseline-build.log runs/baseline
    bga extract "$PROJ" candidate-build.log runs/candidate

- name: Fail if the candidate build regressed
  run: |
    bga compare runs/baseline runs/candidate --fail-on-regression
```

The job fails (exit `4`) only on a real, high-confidence regression; a genuine improvement, a change within tolerance, or a low-confidence comparison all let the job continue.

Pass `--fail-on-low-confidence` (`UX-40`) to treat "this comparison was too low-confidence to gate on" as a failure rather than failing open - a gate that silently stops gating still reports green, and some pipelines would rather see that.

### CI Efficiency Gate (`--fail-on-efficiency-regression`, `--min-efficiency`)

Not spec-mandated (`UX-39`). The duration gate above answers *"did the build get slower"*. That is the wrong question when a project is legitimately growing: adding three new elements makes the build slower, and a duration gate cannot tell that apart from a real regression. The question a build owner actually wants gated is **"adding work is allowed; adding work *inefficiently* is not."**

```bash
# fail if the build became meaningfully less efficient than the baseline
bga compare runs/baseline runs/candidate --fail-on-efficiency-regression

# ...or state an absolute floor, with no baseline needed at all
bga compare runs/baseline runs/candidate --min-efficiency 0.45
```

Exits `5` - a code distinct from `4`, so a pipeline can warn on "slower" and fail on "less efficient", or vice versa. Gates on **Dispatch Occupancy** (`floors.occupancy_share`, `UX-27`), which is invariant to how much work the build does: adding well-parallelized elements barely moves it, adding serialized ones moves it sharply.

Real, measured illustration on one project (`examples/06-macro-micro-optimization`), same runner:

| change | wall-clock | duration gate | Dispatch Occupancy | efficiency gate |
|---|---|---|---|---|
| two more fan-out libraries added | 25.98s → 26.64s (+2.5%) | **fails** (exit 4) | 60.0% → 73.8% | passes |
| graph serialized + one element pinned to `-j1` | 27.50s → 39.57s | fails | 63.0% → 27.8% | **fails** (exit 5) |
| `--builders 8 --max-jobs 8` on a 4-core host | 27.50s → 32.66s | fails | 63.0% → 48.6% | **fails** (exit 5) |
| nothing changed (repeat capture) | 25.98s → 24.07s | fires on ±1% noise | 60.0% → 59.0% | passes |

Two knobs:

- `--max-efficiency-drop PP` - how many **percentage points** of occupancy may be lost before failing. Default `5.0`, derived rather than guessed: three repeat captures of an unchanged project on one real runner spread **1.0pp** of occupancy (and 7.4% of wall-clock, which is why the duration gate's own 1% default fires on noise). Re-derive it the same way on your own runner rather than trusting the default.
- `--min-efficiency RATIO` - an absolute floor (`0.0`-`1.0`) on the candidate run's own occupancy, consulting no baseline. This is what makes *"we accept 55%, we do not accept 30%"* expressible on a first run, and what stops a slow drift that no single delta ever trips. No default: what counts as acceptable is a statement about your project, not a universal constant.

The efficiency gate inherits the same low-confidence fail-open rule as the duration gate, and the same `--fail-on-low-confidence` opt-out.

### What each flag does, in full

Each command's `--help` gives a flag one line; this is the whole entry. `bga capture run --help` ends with the four flags `bga` strips before the tracer parses (`CAPTURE_RUN_BGA_FLAGS`, `bga/cli.py`):

- `bga sweep --calibration-dir DIR` (`UX-14` tier 2) — replaces the sweep's fixed-duration model with a contention-aware one calibrated from real runs in `DIR`. Without it the sweep's own caveat applies: the predicted curve is a shape, not a runtime prediction, because the replay model does not know about CPU.
- `bga capture run --diagnose` / `--no-inject` (`UX-146`) — what the bwrap shim received and what it exec'd, one JSON line per sandbox, written as `<output>.diagnostics.jsonl` with a summary that **leads with the invocation count**. Zero means the `$PATH` shadow never reached `buildbox-run` and the build ran unmodified, which is a different problem from a sandbox that failed; the two are otherwise the same silence. `--no-inject` runs the build with the shim installed and injecting nothing — it captures nothing and says so, and exists to bisect the argv rewrite against the shadowing itself. Both are on `bga snapshot` too, and neither is sticky.
- `bga capture run --invocation-log PATH` / `--argv-log PATH` / `--raw-log PATH` — where Plane 2 writes its own capture logs. `--invocation-log` defaults to a path beside the report (`UX-80`); `--no-invocation-log` turns it off.
- `bga capture run --jobserver auto|N|off` (`UX-679`'s spike, `UX-851`'s mode; default `off`) — runs a GNU jobserver outside every sandbox and binds its FIFO into each one via the shim, so `make`/`cmake`'s Makefiles generator can join it instead of each sandbox believing it owns `N` cores alone. `N` binds that many tokens; `auto` sizes the pool to the host's cores minus BuildStream's own `--builders` in the wrapped command (or minus 1 when that is not named), floored at 1 — `bga` resolves `auto`/`off` to the tracer's own `--jobserver N`/absent before dispatching, so the tracer's own `--jobserver` takes only the integer; its help line names `auto|N|off`. One element can be kept out or given another style: [`jobserver.md`](jobserver.md#one-element-not-the-whole-build) names every switch. Recorded in the report as `jobserver`, and in the snapshot's `run_instance.jobserver` (below) as the mode actually used. The report also carries `cache_key_set`, a hash of one pre-build `bst show --format '%{name} %{full-key}'`, comparable against a later capture's own field — `bst show` reads the same key with or without the mode, because the shim's injection never passes through BuildStream's own environment composition (`UX-844`); a custom plugin whose own `environment:` declares `JOBS` or `MAKEFLAGS` must nocache them (`environment-nocache`) to keep that promise for itself, the way the shipped kinds already do. A manual-kind recipe that spends BuildStream's own composed `JOBS` (a `cmake --build … ${JOBS}` call inside a `manual` element, say) joins the jobserver too, whatever its kind - `JOBS` set is the recipe's own promise to spend it (`UX-859`). The per-kind table's own read (`bst show --format '%{name} %{kind}'`) carries every global option the wrapped command gave `bst` - `-o`, `--config`, `--directory` included - and on any failure writes `kinds_read.json` beside `element_kinds.json` naming the argv, the exit status and why (`UX-870`).
- `bga capture run --jobserver-auth fd|fifo|auto` (`UX-841`, `UX-876`; default `auto`) — the `--jobserver-auth` style handed to `make`: `auto` always resolves to `fd`, accepted by every GNU Make from 4.2 up, because a recipe can invoke a make below 4.4 by absolute path from inside its own sandbox and there is no way to know that ahead of the build. `fifo` is the opt-in, for an operator whose whole sandbox toolchain is known to be GNU Make 4.4 or newer (`UX-874` narrows an explicit `fifo` to `fd` per element when the sandbox make it actually runs is older). Recorded in the report as `jobserver_auth`. For the cmake/meson/manual-with-`JOBS` and cargo elements whose own `MAKEFLAGS` an *unwrapped* native jobserver client reads directly — `gcc -flto`'s lto-wrapper, cargo — a resolved `fd` auth is normalized to a path-based `fifo:`: a raw fd is only valid for a direct child, and the compiler's lto-wrapper is a deep grandchild that cannot use it (`UX-878`, GCC-13 ICE `opts-common.cc:2123`). When a sub-4.4 make shares the recipe and would reject `fifo:` too, what happens next depends on the policy (`UX-913`): a **cmake/meson** element keeps its raw `fd` — its MAKEFLAGS consumer is `make` itself, a direct child — and an element that also drives LTO takes the per-element `flto` override to put `UX-880`'s GCC-driver shims on `PATH`, which are not mounted by default because they shadow the staged `cc`/`gcc` with a script a minimal sandbox cannot source; `jobs_env` and cargo, which have no shim between the client and `MAKEFLAGS`, are dropped entirely and the recipe's own `-jN` stands.
- `bga capture run --jobserver` (with the jobserver active): a one-line preflight note to stderr for every element that is both on a sub-4.4 sandbox make and one of the compiler-driving kinds `UX-878`'s scrub above narrows (cmake/meson, `jobs_env`, cargo). A dropped element reads `Warning: <element> scrubbed to recipe -jN (sandbox make <4.4); move it to make >=4.4 for fifo pool-fill, or force fd/flto (UX-879/880)`; a cmake/meson element, which `UX-913` keeps, reads `Note: <element> keeps its jobserver auth (sandbox make <4.4, cmake_meson); make reads the fd directly. An element that also drives LTO needs the flto override (UX-913)` — silence would leave a reader unable to tell an engaged mode from a warning that stopped firing. Reads the per-element sandbox-make probe UX-874/878 already cached, never re-probes; one line per element, de-duplicated (`UX-883`).
- `bga capture run --jobserver-auth-override 'fd:<glob>[,<glob>] fifo:<glob> off:<glob> flto:<glob>'` (`UX-879`, `flto` added `UX-880`; repeatable, or one value with space-separated groups) — a per-element override of the style above, resolved by the shim against the element name (`fnmatch`) and taking precedence over the auto/`compiler_safe` decision: `fd` forces the raw, pre-`compiler_safe` auth (no fifo rewrite, no scrub); `fifo` forces the `fifo:` path; `off` scrubs (no `--jobserver-auth`, no wrapper mount, `JOBS` left alone so the recipe's own `-jN` stands); `flto` keeps the raw `fd` auth like `fd` does (`make` still fills the pool) **and** mounts a reference GCC-driver shim (`gcc`/`g++`/`cc`/`c++`) ahead of `PATH` — the shim strips `--jobserver-auth=…` from the `MAKEFLAGS` it hands the real compiler unconditionally, and only when `-flto`/`-flto=jobserver`/`-flto=auto` is already in argv, rewrites it to a static `-flto=$BST_TRACE_LTO_CAP` lto-wrapper can honour without a jobserver; a non-LTO invocation's argv is untouched. First matching glob wins. Translated to `BST_TRACE_JOBSERVER_AUTH_MAP` before the tracer ever sees it, same channel as `--jobserver`'s own `auto`/`N`/`off` resolution. **Caveat**: forcing plain `fd` (not `flto`) on an element that does LTO will still hit the GCC-13 ICE `compiler_safe` exists to avoid — use `flto` for an LTO element on a make ≤4.2.1, `off` for one the shim's static cap is not wanted for.
- `public: { bga: { jobserver-auth: fd|fifo|off|flto } }` (`UX-882`) — an element annotation naming the same four styles, version-controlled in the project instead of the operator's command line. Read from the `%{public}` field of the tracer's one RS/US-delimited `bst show` (`UX-1011` folded the separate call into it) into `BST_TRACE_ELEMENT_AUTH_MAP`. Resolved **after** `--jobserver-auth-override` and before auto — a run's own override still wins over a committed default, and an element with neither falls through to auto unchanged. Advisory input, not a versioned contract: no `bga.contracts` id, no `specification.md` edit; a malformed or absent `public:` block is silently no annotation, never a build failure.
- `bga capture run --lto-cap N` (`UX-880`) — the static `-flto=N` cap the `flto` override's GCC-driver shim rewrites an already-present `-flto` to; default `nproc`, read inside the shim itself. Sets `BST_TRACE_LTO_CAP`, translated before the tracer ever sees the flag.
- `bga capture run --wrapper-dir PATH` / `--wrapper-dir-mode augment|replace` (`UX-881`; default `augment`) — an operator's own wrapper directory, for a custom-prefix toolchain invoked by absolute path or via `toolchain.cmake`'s `CMAKE_C_COMPILER`, which PATH-shadowing cannot reach and which `bga`'s own shipped shims (`tools/native_trace/wrappers/`) cannot be edited to add. The directory must satisfy `docs/guides/wrapper-contract.md`'s published contract (`_common.sh`'s `bga_run_wrapped <flag_style> "$@"` entry point). `augment` mounts the operator's directory ahead of the shipped one on `PATH` — the shipped `ninja`/`ld.lld`/… coverage stays; `replace` mounts only the operator's directory, dropping the shipped shims and the shipped `flto/` subdir entirely. Sets `BST_TRACE_WRAPPER_DIR_OVERRIDE`/`BST_TRACE_WRAPPER_MODE`, translated before the tracer ever sees either flag.
- `bga capture run --jobserver-pool fixed|dynamic` (`UX-845`; default `dynamic`) — dynamic runs a `PoolController` daemon that writes or withdraws a token every 250ms from `cpu_busy_cores` and, where present, `/proc/pressure/cpu`'s `some avg10`, rather than leaving the pool at its static seed; `fixed` is `UX-679`/`UX-841`'s prior behaviour. Recorded in the report as `jobserver_pool`. With `--plan` the report's `jobserver_pool.memory` block (`UX-850`) counts the grants the broker withheld because `MemAvailable` fell under the element's planned peak RSS times the tokens it would hold (`withheld`), whether `/proc/pressure/memory` was present, and the tokens the pool withdrew on its `some avg10` over the same bound the CPU one uses (`psi_memory_withdraws`); an unreadable `/proc/meminfo` withholds nothing.
- `bga capture run --jobserver-capacity N` (`UX-845`) — overrides the host core count the dynamic pool compares busy cores against; defaults to `os.cpu_count()`.
- `bga capture run --jobserver-seed N` (`UX-858`) — overrides the FIFO's opening token count the resolved ceiling would otherwise seed to (`max(0, ceiling - builders)` under `auto`, `ceiling - 1` otherwise), clamped below the ceiling either way. Recorded in the snapshot's `run_instance.jobserver.seed`.
- `bga capture run --plan analyze.json` (`UX-849`; needs `--jobserver`) — a per-element proxy replaces the shared FIFO's first-come order: the tracer pre-creates one proxy per element in the kinds map, and a `Broker` thread moves the global pool's tokens into the proxy of whichever *running* element has the least slack (`analyze.json`'s own `elements.slack`) first, capped at that element's own `-jK` minus one, and drains a proxy back to the global pool the moment its sandbox ends. An element the plan does not name is treated as the plan's own median slack. Without `--plan` nothing changes — no proxies, the global FIFO as today, byte for byte. Recorded in the report as `jobserver_pool.broker` (`plan`, `grants`, `drains`, `elements_in_plan`, `elements_median_slack`, `leaks`, `tokens_refilled`), present only when a plan actually ran.
- `bga correlate --cache-logs PLANE3.json` — adds the per-element sandbox tax from a Plane 3 report, which is what the merge half of the granularity findings is computed from (`UX-100`). Without it the split half still runs; the merge half is silent, because the toll is the whole basis for calling an element too small.
- `bga compare --baseline-plane2 A.json --candidate-plane2 B.json` — notes when the candidate's measured memory envelope grew (`UX-104`). Two flags, because reusing one report for both runs would compare a run against itself. A note, never a gate: peak RSS has no measured noise band.
- `bga compare` analyzes each side as `bga analyze` does, with that side's own Plane 2 report (the flag above, else the snapshot's sibling), and reads a side's published `analyze.json` instead when its `fingerprint` matches (`UX-1073`). `--reanalyse` analyzes both regardless; `bga view --reanalyse` passes it on.
- `bga cache-trend RUN...` — a series, oldest first: per-run hit ratio, transfer seconds and seconds per artifact, churn against the predecessor (with `UX-93`'s labels), and a finding when the newest run leaves the band its trailing window describes (`UX-103`). Refuses a verdict, with exit 6, over a series whose runs are not of the same project and targets — the band would describe neither (`UX-111`). The *commit* is deliberately allowed to vary: a cache-health trend across commits is the only kind there is. The noise model is `bga compare`'s, widened to the fixed rule when the measured band is narrower. Four runs minimum — three trailing plus the one being judged — and it says so rather than trending fewer.
- `bga baseline --glob 'captures/<project>/<commit>-<mode>-b<N>j<M>-*' -n 3 --candidate RUN` — assembles a baseline set from published capture refs and band-compares against it in one command (`UX-96`). Fetches the newest N, untars the refs that predate the uncompressed `run/`, refuses a set whose captures are not comparable (exit 6), and warns when the set was produced by more than one `bga` revision. Absence in a capture's context is read per field (`UX-114`): `trace_spine` and `trace_opens` have a defined default, so a ref published before the field existed is taken under it and mismatches a capture instrumented differently — the assumption is stated either way; `target` and the rest have none, so partial coverage is reported as **unverified** rather than passed over. A band member whose run mode differs from the candidate's is refused with exit 6 too, not the generic exit 2 it used to produce. Every member supplies the band, the newest is also the positional baseline — with three refs that is exactly the `MIN_BASELINE_RUNS` the band needs.
- `bga capture census PROJECT [--json]` — classifies every executable the project's `local` sources stage as static or dynamic, per element, without building anything (`UX-105`). A static ELF has no `PT_INTERP`, never invokes the dynamic linker, and so is invisible to Plane 2's `LD_PRELOAD` hook. `bga capture run` and `bga capture report --project-dir` run the same census and use it to replace the generic static-binary footnote with a named one — or with silence, when there is nothing to name.
- `bga capture run --trace-spine[=off|on|auto]` (`UX-106`/`UX-108`) — also runs a static ptrace process-event tracer inside the sandbox, which records every process whatever its linkage. It is what makes a static toolchain visible at all: `examples/01-resource-contention` traces **0 processes** without it and **24** with it. Each process then carries `spine+hook`, `spine-only` or `hook-only`, and the coverage line is a counted number rather than a disclaimer (`UX-107`). It costs **0.3–1.1 ms per process** — a measured range, not a constant ([why it is a range, with the raw figures](../design/architecture.md#plane-2-knows-the-size-of-its-own-blind-spot)) — which is below the run-to-run spread on a compile-bound build and plainly visible on a process-dense one. **`auto` is the setting to use** (`UX-113`, and what `bga snapshot` defaults to): it pays that cost only for the elements the pre-build census says the hook is blind for, plus any it could not assess — no elements on an all-dynamic project, all of them on a busybox one. The hook stays on either way, since opened paths need in-process interposition and the spine deliberately does not do that. Bare `--trace-spine` means `on`; write `--trace-spine=auto` with the `=`, because the value is optional and a following positional would otherwise be eaten by the flag.
- `bga cache-logs [PROJECT_DIR|LOG_ROOT] --graph RUN/graph.json --native-report PLANE2.json` — Plane 3, BuildStream's own persisted element logs (`UX-91`). Needs no capture at all: it reads what BuildStream already wrote, under `$XDG_CACHE_HOME/buildstream/logs`. **Hand it the project directory** (`UX-127`): it reads the name from `project.conf` and resolves the log root itself. A log root still works, `--list` (or a bare invocation) enumerates the tree — projects, log counts, time spans — and `--all` reports over every project at once. Given a project the tree has no logs for, the error names the project it derived, where it looked, and what is actually there. Reports the per-element phase breakdown, the sandbox tax (`UX-99`) and the configure tax (`UX-102`); `--native-report` puts the traced configure measurement beside the build tool's self-reported one, and `--graph` lets the developer-tax ranking (`UX-101`) tell a rebuild caused by an upstream key change from one whose own definition changed — the logs alone carry no dependency edges.

## `bga correlate` — Join the Two Planes

```bash
bga correlate RUN_DIRECTORY NATIVE_REPORT.json
bga correlate RUN_DIRECTORY NATIVE_REPORT.json --format json
```

Joins this run's whole-project analysis (Plane 1) with a native trace report of the *same build* (Plane 2, from `tools/bst_native_build_tracer.py run`) on **element UID** — the only contract between the planes.

It answers what neither plane can alone. Plane 1 knows an element dominates the critical path; Plane 2 knows what happened inside it; only the join says what to do:

```text
Joined 9 element(s) on element UID (11 in Plane 1, 9 traced in Plane 2)
  Memory envelope: 4 builders of this shape peak at ~0.6 GB of 15.7 GB (4%);
  9 would still fit, so memory is not what binds first here

What to do next (ranked by Plane 1 impact):
  core.bst:
    - holds 45% of the critical path and fixing it is worth 8.0s (20.2% of the build),
      but runs at only 0.89 cores busy - it is waiting, not computing, and its native
      build asked for -j1: remove `notparallel` / raise its job count before touching
      its sources
    - 82% of its measured CPU is one binary, `cc1plus` (10 process(es), 9 CPU s) -
      this element is a `cc1plus` problem, so look there before anywhere else
    (81% of this element's processes were measured)
```

(`examples/06-macro-micro-optimization`, one `bga snapshot`. The
freedesktop-sdk version of the same shape, at 1500× the scale, is in
[`real-project.md`](real-project.md).)

Inside a project this is one line, because `bga snapshot` already
captured both halves and kept them together:

```bash
bga correlate @last
```

Elsewhere, capture both artifacts from one build and name them:

```bash
bga capture run --wrapped-log /tmp/plane1.log --run-dir /tmp/run \
    /path/to/project /tmp/plane2.json -- bst build <target>
bga correlate /tmp/run /tmp/plane2.json
```

Notes on reading it:

- **Ranking is Plane 1's.** Plane 2 explains the top of that list and never reorders it — the question "what should I optimize" is answered by whole-project impact.
- **A restructuring finding comes first, when there is one** (`UX-82`). When a *group* of declared build edges was measured never-read *and* those edges chain elements along the critical path, the join names the chain as one finding and replays this run with those edges removed — same durations, same capacity — to say what removing them would be worth. Five per-element rows saying "`lib-b` never read `lib-a`" are five bricks; this is the wall. The hedge is unchanged: it recommends *checking* the edges, and says the projection is a replay, not a re-capture.
- **Rows are ordered by evidence strength.** A measured CPU concentration or a single-process serialization point leads; the declared-vs-used candidate, which the producer itself calls "evidence, not a verdict", comes last. Dependency pairs `UX-68` set aside as *aggregating* — a `stack` stages almost nothing of its own, so "nobody opened it" says nothing about it — are counted under the coverage line rather than mixed into the findings.
- **The ranking metric is `UX-70`'s realizable saving** — what the build would actually lose if the element became instant, which is the same number `bga analyze` ranks on, so the two commands cannot name different elements first. Share of the critical path is reported beside it because they routinely disagree: an element can hold a large share of a mesh graph and be worth very little to fix. If the metric saturates (every candidate carrying the same value), the report says so rather than presenting the alphabetical tiebreak as an impact order.
- **A negative result is a result.** "Already compute-bound — nothing to gain from its parallelism" tells you to stop looking inside that element.
- **Elements with identical findings share one block** (`UX-89`). Six sibling libraries that are all compute-bound and all `cc1plus`-dominated are one story, not six; the block names them, collapses their figures to ranges, and carries the total worth, while `--format json` still publishes every element separately. A group takes the position of its strongest member, so grouping never reorders what leads, and a finding whose figures do not generalize (peak RSS, a redundant operation's own element list) keeps its own per-element words rather than being averaged into something the measurement does not say.

```text
app.bst, lib-a.bst..lib-f.bst (7 elements, 6-9% of the critical path each, 2.0-3.0s apiece, 19.7s together):
  - already compute-bound at 1.4-1.8 cores busy - nothing to gain from their parallelism;
    shortening them means less work
  - `cc1plus` is 72-78% of each one's measured CPU - they are all the same problem, so look
    there before anywhere else
  (81% of each element's processes were measured)
```

- **A serialization point has to be material** (`UX-89`). `ar` and `ranlib` are single processes by construction, so before this rule had a bar every element that linked a static library earned a "SINGLE process holding 0.2s" line. The bar is `max(1.0s, 1% of the element's realizable saving)` — the same shape the redundancy rule already used — so a 12s `ld` still reports and a 0.2s `ranlib` does not.
- **Coverage is carried through.** A recommendation built on 81% of an element's processes says so (`UX-45`), and elements Plane 1 ranks that Plane 2 never traced are named rather than passed over.
- The two planes' timelines are **not** merged and cannot be — see [`docs/design/architecture.md`](../design/architecture.md). This is a join, and is deliberately named as one.

## `bga whatif`

What would the build drop to if I fixed these? See [its contract and worked example](json-contracts.md#choosing-the-fixes-ux-230).

- `--element UID` — an element to treat as fixed (instant); repeatable. One longest-path recompute with every named element zeroed, never a sum of their individual savings.

## `bga junction-cost`

N variant builds, or one junctioned invocation? See [its contract and worked example](json-contracts.md#n-variant-builds-or-one-junctioned-invocation-ux-904).

## `bga cache-trend`

Is the cache getting worse? A series of runs, not a pair — `bga cache-trend @prev @last`. See [its finding, `cache-trend-regression`](#the-full-findingsid-set).

## `bga bundle`

Pack a capture into one file, load one, or resolve pseudonyms. See [its modes](#carrying-a-capture-to-another-machine-ux-520), and [`sharing-a-capture.md`](sharing-a-capture.md) for the five steps in order.

## `bga view`

Open a run's report in a browser (`tools.bga_view`). See [the page, chapter by chapter](viewer.md).

- `--perfetto` — skip the report and hand the run's timeline straight to ui.perfetto.dev, tab to tab; nothing is uploaded.
- `--no-browser` — print the URL instead of opening it, for a remote shell or to `curl` the payloads.
- `--port N` — listen on port `N` instead of the ephemeral one the kernel picks (the server stays on 127.0.0.1).
- `--compare BASELINE` — draw the band against `BASELINE` instead of the run before `RUN` in the same store; same alias grammar (`@last`, `@prev`, a stamp prefix, a path). Read in `main` as `run_store.resolve(args.compare)`; [the band](viewer.md#three-views-that-draw-ux-196) says what it changes.

## `bga capture`

Plane 2: trace processes inside sandboxes (`tools.bst_native_build_tracer`). See [its flags](#what-each-flag-does-in-full).

- `bga capture run --host-samples PATH` — where to write the host's memory series while the build runs: JSON Lines (`host-samples/v1`), one sample every `HOST_SAMPLE_INTERVAL_S` seconds, of `/proc/meminfo` keys. It sits beside the report, not inside it.

## `bga wrap`

Run a command, writing a log bga can ingest (`tools.bst_run_wrapped`); every flag is in `bga wrap --help`.

## `bga extract`

Turn a log + project into a run directory (`tools.bst_extract_run`); every flag is in `bga extract --help`. The ones no other page names:

- `--format auto|wrapped|raw` — the input log's format, with `bga log-to-chrome`'s semantics.
- `--cpu-budget N` — the CPU cores the build is *intended* to use, the operator's declared envelope as against the detected host core count; it governs the oversubscription check (`UX-15`).
- `--artifact-weights` — walk each element's artifact in the local CAS to record what it weighs (`UX-907`). Off by default: it reads one blob per directory in every artifact.
- `--build-type TYPE` — what kind of build this was (`night`, `review`, `guard`, free text); two runs declaring different types are two populations (`UX-898`). Defaults to `$BGA_BUILD_TYPE`.
- `--variant NAME=VALUE` — a named dimension of what the build did (`arch=aarch64`, `sanitizer=address`); repeatable. Defaults to `$BGA_BUILD_VARIANT`, comma-separated (`UX-903`). Both are in [the environment table](#switches-you-set).
- `--cache-usage` — walk the local CAS and record what the cache currently holds (`UX-896`). Off by default: it is the only part of the capacity block that costs anything; without it the block still carries the configured quota and the volume under it.
- `--memory-budget-mb N` — the memory (MB) the build is *intended* to use, operator-declared. With `--estimated-job-memory-mb` it drives the memory oversubscription check (`UX-21`).
- `--estimated-job-memory-mb N` — a rough, operator-supplied footprint (MB) of one concurrent build job: a constant, not a measurement. Meaningful only with `--memory-budget-mb`.
- `--native-max-jobs N` — override the real `--max-jobs` the build ran with (`make -jN` inside each sandbox, not `--builders`). Without it the value is the wrapped log's recorded invocation (`UX-29`), else the invocation parse, else the graph's resolved `max-jobs` (`UX-377`; `bst_extract_run.py`'s `typical_resolved_max_jobs`); the flag always wins, and the run records which source the published value came from (`native_max_jobs_source`).
- `--trace-epsilon-us N` — quantization epsilon of the trace in microseconds (default 50000, Part 3.2).
- `--start-time ISO8601` — anchor for a raw log's elapsed timestamps; defaults to the log file's mtime.
- `--interrupted` — record that the log's build was interrupted, so the run declares itself unfinished. Needed when re-running from the hint an interrupted capture printed; `bga snapshot` sets it for you.
- `--strict` — fail instead of warning unless the project uses `ref-storage: project.refs` and that file has no uncommitted changes (`P4-13`).
- `--bst-bin PATH` — the `bst` executable to call (default `bst` on `PATH`).

## `bga rebuild-set`

Which elements a change would force a rebuild of (`tools.bst_rebuild_set`); every flag is in `bga rebuild-set --help`.

- `--cut ELEMENT` — required; the element to rebuild, with everything above it over build edges. Repeatable.
- `--count-only` — print only the size of the resulting set, not its members.

## `bga checkout-cost`

Measure what checking out an artifact costs (`tools.bst_checkout_cost`); every flag is in `bga checkout-cost --help`.

- `compare --format auto|wrapped|raw` — the log format, as `bga log-to-chrome`'s; `--json` emits JSON instead of the human-readable summary.
- `compare --individual LOG [LOG ...]` — the logs of checking the elements out one invocation each (BuildStream's per-invocation overhead is paid once per log).
- `compare --consolidated LOG` — the log of checking out one `kind: stack` element depending on all of them (one payment of that overhead). Both are required.

## `bga run-context`

Produce run-context.json on its own (`tools.bst_run_context`); every flag is in `bga run-context --help`. It takes the same `--build-type`, `--variant`, `--memory-budget-mb`, `--estimated-job-memory-mb`, `--native-max-jobs`, `--trace-epsilon-us` and `--start-time` as [`bga extract`](#bga-extract), with the same meaning, plus `--format` and `--cpu-budget` (same meaning), and:

- `--host NAME` — optional host identifier to record.

## `bga graph-from-show`

Turn `bst show` output into graph.json (`tools.bst_show_to_graph`); every flag is in `bga graph-from-show --help`.

- `--bst-bin PATH` — the `bst` executable to call (default `bst`, resolved via `PATH`).

## `bga log-to-chrome`

Convert a BuildStream log to Chrome Trace JSON (`tools.bst_log_to_chrome_trace`); every flag is in `bga log-to-chrome --help`.

- `--start-time ISO8601` — anchor for raw-format elapsed timestamps (only meaningful with `--format raw` or `auto`'s raw fallback); defaults to the input file's mtime.

## `bga chrome-to-trace`

Convert Chrome Trace JSON to trace/v9 (`tools.chrome_trace_to_bga_trace`); every flag is in `bga chrome-to-trace --help`.

## `bga native-to-chrome`

Plane 2 trace to Chrome Trace JSON (`tools.native_trace_to_chrome_trace`); every flag is in `bga native-to-chrome --help`.

- `--anchor-element ELEMENT` — required; a real element present in both traces, used to put Plane 2's `CLOCK_MONOTONIC` onto Plane 1's wall-clock timeline.

## `bga cache-logs`

Plane 3: mine BuildStream's own element logs (`tools.bst_cache_logs`); every flag is in `bga cache-logs --help`. Beyond the prose [above](#what-each-flag-does-in-full):

- `--project NAME` — only this project's logs.
- `--all` — report over every project in the log tree at once (`UX-127`).
- `--list` — list the projects the tree holds, with log counts and time spans, and exit.
- `--graph RUN/graph.json` — a run directory's graph, so a rebuild caused by an upstream key change can be told from one whose own definition changed.
- `--native-report PLANE2.json` — a Plane 2 report from the same build, to put the traced configure measurement beside the self-reported one.
- `-f text|json` / `--format text|json`, `-o PATH` / `--output PATH` — the output format, and a file to write instead of stdout.

## `bga cross-check`

Cross-check an analysis against other figures (`tools.bga_cross_check`); every flag is in `bga cross-check --help`.

## `bga release-notes`

Generate a release body from the closed backlog rows (`tools.bga_release_notes`); every flag is in `bga release-notes --help`.

- `--from START` — required; the closed-row marker of the previous release.
- `--to END` — the closed-row marker of this release; default every row there is now.

## `bga gen-synthetic`

Generate a synthetic run directory at a scale (`tools.gen_synthetic_scale_run`); every flag is in `bga gen-synthetic --help`. Byte-reproducible from `--seed`.

- `--builders N` — the builders count recorded in the run (see `--store` for its store default).
- `--layers N` / `--width N` — the graph's shape: how many layers (default 12), how many elements per layer (default 100). With `--store`, a `--layers`, `--width` or `--builders` left at its default is replaced by the store's small values (3, 4, 4); one you pass still means what it says.
- `--run-id ID` — the `run_identity_hash` written to every file; it must match across the three files or ingestion rejects the directory.
- `--store` — plant a whole store (a project root, two snapshots, and per snapshot the wrapped log and Plane 2 records `timeline` and `capture report` need) instead of one run directory; the no-BuildStream seed the README's quick start points at. Defaults to a small graph.
- `--runs N` — with `--store`, how many snapshots to plant (default 2, the minimum that makes `@prev`, `compare` and the trend answer).
- `--workload cc|binaries` — with `--store`, Plane 2's population: `cc`, one compiler per element; `binaries`, 8 elements exec'ing 200-500 fake binaries each and the rest 3-10.

## `bga baseline`

Assemble a baseline set and band-compare against it (`tools.bst_baseline_set`); every flag is in `bga baseline --help`. Its CI use: [`ci-comment.md`](ci-comment.md#the-sequence).

- `--glob GLOB` — the ref glob selecting one comparable set, e.g. `'captures/fdsdk/953683fb-incremental-b4j4-*'`. The default takes every incremental capture, which is a set only if one commit is under capture; name the tuple explicitly in CI.
- `--candidate RUN` — a candidate run directory (or snapshot alias). Given one, `baseline` band-compares it against the fetched set and returns that compare's exit code.
- `-f text|json` / `--format text|json` — the output format.
- `-n COUNT` / `--count COUNT` — how many of the newest captures to fetch; default 3.
- `--exclude PATTERN` — drop a capture before the newest N are taken: a run id or a glob over the ref name (`'*-cold-*'`); repeatable. The remedy for a set that differs on `target`, `trace_spine` or `trace_opens`, none of which the ref name carries.
- `--repo DIR` — the checkout to run the remote queries from; default the working directory.
- `--band-k K` — passed through to `bga compare --band-k`.
- `--remote REMOTE` — the remote (name or URL) the captures were published to; default `origin`. Read as `list_capture_refs(args.remote, …)`.
- `--workdir DIR` — where the fetched run directories are materialised; default a temporary directory removed on exit, so pass it to keep them.

## How many builders, and what stops you

Two Plane 2 numbers answer the `--builders` question, and they answer
different halves of it. Both need a Plane 2 report for the *same* run —
`bga snapshot` keeps one beside every capture, and `bga analyze` takes
one with `--plane2`:

```bash
bga analyze .bga/runs/<stamp>/run --plane2 .bga/runs/<stamp>/plane2.json
```

### The capacity recommendation (`UX-116`)

`capacity_recommendation` intersects every constraint on the joint
`--builders` × `--max-jobs` choice. Each one is already a measured
number in a capture; what was missing was the sentence that puts them
together. Below is one `bga snapshot` of
`examples/06-macro-micro-optimization`, committed at
[`tests/fixtures/macro_micro/`](../../tests/fixtures/macro_micro/) so
you can run it from a clone:

```bash
bga analyze tests/fixtures/macro_micro/run \
    --plane2 tests/fixtures/macro_micro/plane2.json
```


```text
  Capacity: builders 4 x max-jobs unrecorded on 4 cores: graph binds at 2, below the 4 configured - more builders contend rather than overlap here
    graph allows 2: the sweep's knee is at 2 builders
    CPU allows 4: 1.60 of 4 cores busy at builders=4, i.e. 0.40 cores per concurrent element
    memory allows 9: the 9-builder envelope fits in 15.7 GB (measured over 9 element peaks, so it says nothing above 9)
    Free capacity you already have: core.bst asked its native build for -j1 - a builder slot drawing one core. Fix that before raising anything, then re-measure.
```

Three constraints, each with the measurement behind it, and the
**smallest one binds**. Here it is the graph: the capacity sweep's knee
is at 2, so the 4 builders configured are already more than this
dependency shape can use, and adding builders would make them contend
rather than overlap. The CPU ceiling is `host_cores × builders ÷
cores_busy` — measured draw per concurrently-building element, not an
assumption — and the memory ceiling comes from the envelope below.

**Reading it as data.** The block is a key of `analyze/v7`, so a CI job
asks for it the same way it asks for anything else:

```bash
bga analyze tests/fixtures/macro_micro/run \
    --plane2 tests/fixtures/macro_micro/plane2.json --format json \
  | jq '.capacity_recommendation | {binding_constraint, recommended_builders}'
```

```json
{
  "binding_constraint": "graph",
  "recommended_builders": 2
}
```

Absent, not empty, when the block declines — the table below says when
that is. Read `caveat` before acting on `recommended_builders`: it is a
hypothesis to time, not a setting to apply.

**How it is derived, and what it will not do.** One capture in, one
recommendation out: no configuration is tried. The sweep replays the
durations it observed and does not model contention, and
cores-busy is an average over the whole run rather than over the
contended window — both stated in the payload's own `caveat`, because a
recommendation that hides its shape is worse than none.

**When it declines**, and this is the part worth knowing, because a
missing recommendation looks exactly like an absent feature:

| the block is absent when | because |
|---|---|
| no `--plane2` was given | `cores_busy` is a Plane 2 measurement and there is no Plane 1 substitute |
| the capture recorded no host core count | the CPU ceiling is `host_cores × …`; without it there is no ceiling to state |
| the run context has no builders value | every constraint is expressed *per builder*, so there is no baseline to move from |
| the capacity sweep cannot run | the graph constraint is the sweep's knee; the block does not guess one |
| Plane 2 saw no CPU at all | a recommendation resting on a missing `cores_busy` is a guess wearing a measurement's clothes |

It never recommends a value it has no measurement for. `--builders`
advice that clears the CPU check and blows the memory one is advice to
build into swap, which is why the two are computed together and the
binding one is named.

**Per element: `max_jobs_advice` (`UX-677`).** The same document also
carries, per element, a recommended `--max-jobs` under a no-overcommit
constraint: at every instant the recommended values for the elements
building then sum to at most `host_cpu_count`, and their measured peak
RSS sums to at most the host's memory. Evidence is `UX-675`'s raw host
CPU series joined directly to each element's own BUILD span, not the
ranked, 40-row-capped `underutilized_intervals`/`overcommitted_intervals`
tables above.

| key | what it is |
|---|---|
| `current_max_jobs` | the `-j` this element's own build used (`UX-377`) |
| `recommended_max_jobs` | what the no-overcommit constraint allows; `None` when `refusal` is set |
| `max_jobs_change` | `recommended_max_jobs` minus `current_max_jobs`, signed |
| `local_max_concurrency` | the most elements ever seen building at once in a host-sample interval this element's span touches |
| `samples_in_span` | how many host-CPU-sample intervals overlap this element's span; too few and the row refuses rather than guesses |
| `refusal` | why no number was published - thin evidence, or an overlap whose measured peak RSS already exceeds the host's memory |
| `priced` | `UX-739`: this recommendation's own replay price, applied alone - `{replayed_baseline_us, projected_us, cost_us, duration_before_us, duration_floor_us, kind: "floor"}`. Absent for an unchanged/raised/already-refused row |
| `price_cost_us`, `price_kind` | `UX-831`: `priced.cost_us`/`priced.kind`, read out flat - `priced` stayed nested and drew its own table per row; these two are what the page's `elements` table draws as columns |
| `price_refusal` | `UX-739`: why a changed recommendation was not priced - a raise this run has no evidence for, or no Plane 2 `binary_cost` measurement. Absent when `priced` is set or `refusal` already explains the row |

`elements` is ranked (`UX-831`): priced lowerings first, by
`price_cost_us` ascending, then everything else, refusals last - the
order in the JSON is the order the page draws.

**Priced by replay (`UX-739`).** Two replays of this run under
`ReplayScheduler(tasks, run_context).replay(compute_default_capacities
(run_context))` - one baseline, one with a lowered element's BUILD
task duration overridden to a floor,
`max(observed_build_dur_us, binary_cost[element].measured_cpu_us /
recommended)`: an element capped in isolation is no slower than
observed, and cannot finish its measured CPU work faster than that
work spread over the recommended job count. The figure therefore errs
**optimistic** - the real build under these caps is this long or
longer - and the neighbours' benefit (less overcommit) is not
modelled. Dispatch order is re-derived from the graph and the builder
budget by Part 18's LPT rule for both replays rather than kept from
bst's own observed order, so that rule's own distance from real
dispatch cancels to first order between the two. A raised
recommendation is refused outright: this run has no evidence of how
the element scales up. `priced_jointly` (on the document, not the row)
applies every priced, lowered recommendation together in one replay -
a recompute, not a sum - as `{replayed_baseline_us, projected_us,
cost_us, elements}`; `pricing_assumptions` carries the two sentences
above, machine-readable.

**The sweep behind it, as data: `sweep/v1`** (`UX-339`). The graph
constraint above is the *knee* of a capacity sweep, and `bga sweep`
prints that whole curve rather than the one number the recommendation
uses:

```bash
bga sweep tests/fixtures/macro_micro/run --format json | jq '.knee_points'
```

| key | what it is |
|---|---|
| `resource` | which resource was swept — `PROCESS`, `DOWNLOAD` or `UPLOAD`. One sweep answers about one of them |
| `sweeps` | one row per capacity tried: the full capacity vector, the makespan the replay produced, and `normalized_improvement` — a **step** gain over the capacity before it, not a total |
| `knee_points` | per resource, the capacity past which more buys little. A resource with no knee is absent rather than zero |
| `monotonicity_violations` | capacities where the makespan got *worse* as capacity rose. The replay model says that cannot happen, so each is a hole in the model rather than a finding about the build |
| `capacity_model_caveat` | what the projection does not model, carried with the numbers rather than beside them: the replay replays already-observed durations and does not model CPU contention rising with concurrency |
| `calibration_capacities` | the capacities that had real measurements behind them. Empty means every point is a projection — the difference between a curve with data in it and one without |
| `memory_knee_points` (`UX-678`) | per resource, the largest swept capacity whose own replayed schedule's concurrent elements' peak RSS still fit host RAM. `{}` unless `--plane2` supplied both a measured peak RSS per element and a host memory total; `0` is a real answer, unlike an absent `knee_points` entry |
| `binding_constraints` (`UX-678`) | per resource, which of `knee_points` or `memory_knee_points` is the tighter ceiling, as `{name, builders}`. `{}` under the same condition as `memory_knee_points` |

**The same two figures, on `capacity_recommendation` (`UX-678`).** The
block above (`analyze/v7`) runs this same memory-aware sweep for its
own `PROCESS` knee and carries the answer as `sweep_memory_builders`
(the `memory_knee_points` value) and `sweep_binding` (the
`binding_constraints` entry) - absent under the same condition. It sits
beside `constraints[].name == "memory"`, which is a different
computation (the top-N summed peaks of `memory_envelope`'s projections,
not this replay's own concurrent set) and can disagree with it; a
consumer wanting the sweep's own reading, not the envelope's, reads
`sweep_binding`.

It had **no `schema:` key at all** until `UX-339`, and `bga sweep
--schema` answered the analyze contract — one this document has none of
the required keys of. `UX-328` found that while enrolling three others,
said what was true in the meantime, and filed the contract this is.

**Where it appears.** In the text report, under the headline. It is
**not** a key of `analyze/v7` — `bga analyze -f json` does not carry it
(`UX-275`).

### The memory envelope (`UX-104`)

`memory_envelope` is what decides whether `--builders` can go up, and it
is a published key of [`correlate/v2`](json-contracts.md#the-two-plane-join-published-ux-215):

```bash
bga correlate @last -f json | jq .memory_envelope
```

```json
{
  "host_memory_bytes": 16855859200,
  "builders": 4,
  "elements_measured": 9,
  "largest_element_peak_bytes": 160956416,
  "at_observed_builders": {"builders": 4, "envelope_bytes": 643497574,
                           "share_of_host": 0.038, "fits": true},
  "first_builders_that_does_not_fit": null
}
```

Every figure is in **bytes** (`UX-341`: the payload has one spelling
per dimension, and `ru_maxrss` is converted once at the input
boundary), and `share_of_host` is a fraction of `host_memory_bytes`.
The same thing in the text report reads:

```text
  Memory: 4 builders of this shape peak at ~0.6 GB of 15.7 GB (4%); 9 would still fit at ~1.3 GB, so memory is not what binds first here
```

**What it is an envelope of.** The envelope at N builders is the sum of
the **N largest measured per-element peaks**, as if those N elements
built at once *and* peaked at the same instant. That is deliberately a
concurrent peak and not a sum over the whole build: summing every
element's peak would count memory that was never held at the same
moment, and summing only the *observed* concurrency would answer a
question about the run you already have rather than the one you are
considering. Both are upper bounds, and for "is it safe to raise
`--builders`?" an upper bound is the useful direction to be wrong in.

**No safety margin is invented.** `fits` is a strict comparison against
the host's RAM, with nothing reserved for the OS or page cache — so
headroom below 100% is not the same as safe. A reserve would be a
threshold picked from nothing.

**It projects only as far as it measured.** `elements_measured` bounds
the table: N builders can only be N elements building at once, and past
the elements whose peak was measured there is nothing to sum but a
guess. That is why the constraint line above says *"measured over 9
element peak(s), so it says nothing above 9"* rather than reporting a
ceiling it did not reach.

**When it declines.** It is `{}` — and the line simply absent — when
`--plane2` was not given, when Plane 2 recorded no per-element peak RSS,
or when the capture did not record the host's RAM. The arithmetic needs
the peaks and the host together; half of it is not an estimate, it is a
guess. As with the recommendation above, an absent line means *this
capture cannot answer*, not *this tool has no answer*.

## Example Workflows

### CI Marginal Gate (`--fail-on-inefficient-additions`) — `UX-79`

The gate above reads dispatch occupancy, which is a **whole-build average**, so its sensitivity is inversely proportional to project size. Measured on fixtures at two scales, with the *same* two maximally-mis-added elements:

| project size | whole-build occupancy | that gate | marginal stretch |
|---|---|---|---|
| 11 elements | −14.6pp | **fails** | 1.00 |
| 1201 elements | −0.5pp | passes (blind) | **1.00** |

A gate that weakens as the project grows is weakest exactly where CI matters most, and a growing project approaches the blind spot with every element added.

```bash
bga compare runs/baseline runs/candidate --fail-on-inefficient-additions
bga compare runs/baseline runs/candidate --fail-on-inefficient-additions --max-addition-stretch 0.3
```

**Stretch** is `added critical-path time / added work time`, over the elements this change *added* — so it mentions nothing about the rest of the repository and does not dilute:

- **0.0** — the additions were fully absorbed by existing parallelism; they cost wall-clock nothing.
- **1.0** — every second of added work extended the chain; the additions are perfectly serial.

`--max-addition-stretch` defaults to **0.5** — "at most half of what you added may land on the chain" — which sits in the wide, scale-invariant gap the measurement above found between a well-added set (0.00) and a serialized one (1.00). Exit code is `5`, the same "less efficient" family as the gate above.

Two deliberate limits:

- **A change that adds no elements is an empty check, and says so** rather than reporting green. The whole-build gate is what catches an *existing* element that got worse.
- **The per-element diff is published either way**, in `element_diff` (`new`/`removed`/`moved_onto_critical_path`) and `marginal_efficiency`, so a CI comment can render "New this change: … 8.0s added, 8.0s of it on the critical path" without running any gate at all.

### When the efficiency gates cannot run

Both efficiency gates read `occupancy_share`, which needs a
`resource_capacities.PROCESS` in `run-context.json`. Any legacy or
hand-built run directory may have none, and both gates then pass —
correctly, since a verdict must not be fabricated from missing data, but
for a long time silently. A pipeline that believed it was gating on
efficiency saw exit `0`, an empty stderr, and JSON indistinguishable
from a run that had really passed.

Fail-open is still the default. It is no longer silent (`UX-87`):

- stderr carries `Efficiency gate NOT APPLIED: … the baseline run has no
  \`occupancy_share\` signal …`, naming the gate and the run.
- `--format json` publishes `efficiency_gate_evaluated` — `true` (asked
  for and evaluated), `false` (asked for, could not run), or `null`
  (no efficiency gate was requested), plus `efficiency_gate_signal` with
  `missing_occupancy_in` and `gates_not_applied`.
- `--require-efficiency-signal` turns it into a failure, exit `7`, for
  pipelines that would rather break than not gate.

The two gates are reported separately because they need different
things: `--min-efficiency` is a statement about the candidate run alone,
so a baseline with no occupancy does not stop it; only
`--fail-on-efficiency-regression` needs both.

### 1. Quick Efficiency Check

Get a quick overview of build efficiency:

```bash
bga analyze RUN/
```

### 2. Generate JSON Report for CI

Integrate into a CI pipeline to track metrics over time:

```bash
bga analyze RUN/ --format json --output metrics.json
# Then process with jq, e.g. (certified_headroom, not certified_headroom_us -
# confirmed against a real --format json run):
# jq '.floors.certified_headroom' metrics.json
```

### 3. Simulate Hardware Upgrade

Estimate build time improvement if moving from 4 to 16 cores:

```bash
# Current 4-core simulation
bga analyze RUN/ --capacity 4 --replay

# Hypothetical 16-core simulation
bga analyze RUN/ --capacity 16 --replay
```

### 4. Deep Dive into Bottlenecks

Identify which elements to optimize for maximum speedup:

```bash
# criticality_probability is a JSON *object* keyed by element UID
# (confirmed against a real --format json run), not an array - to_entries
# converts it to an array of {key, value} pairs before sorting.
bga analyze @last --diagnostics --format json | \
  jq '.elements.criticality_probability | to_entries | sort_by(.value.probability) | reverse | .[0:10]'
```

## Reading the report

- **Confidence** — how much to trust the numbers below (data completeness/quality of this specific trace). Below "high"? Fix the underlying trace before acting on anything else. A build that *failed* is called out even louder, before any efficiency figure.
- **Certified Headroom** — a *proven* lower bound, not a guess: given the work this build actually did, it cannot possibly finish faster than `T∞`/`LB` (whichever is larger) without changing that work. Headroom above zero means real room to improve scheduling *without touching any element's build steps*; zero means rescheduling cannot help at all.
- **Efficiency Score and Dispatch Occupancy** — deliberately two numbers, because one cannot do the job. **Efficiency Score** asks *"did the scheduler pack this graph well?"*, and everything it is built from comes from the graph this run actually had — so a build whose independent elements were accidentally chained scores a perfect 1.00, correctly and uselessly. **Dispatch Occupancy** asks *"how much of the available slot-time did the run actually use?"* and never consults the graph, so serializing work that could have run concurrently pushes it down. Read them together: a high score with low occupancy means the scheduler did fine and the *graph* is the problem. (Real measured pair: three one-line fixes made a build 30.5% faster while Efficiency Score fell 1.00 → 0.83 and Dispatch Occupancy rose 27.8% → 63.0%. See [`UX-27`](../backlog/scenarios/UX-0027-efficiency-score-certifies-the-graph-it-was-given.md).)
- **Where the time is** — on a build the chain constrains, the headline is one table: each heavy element's duration, its share of the critical path, and what fixing it would actually recover. The rows are ordered by duration because that is what "where is the time" means; the fix order is named separately, because on a dense graph the two disagree.
- **What to do after that** — the next few fixes projected from the same capture: what the build drops to after each, whether the recommended set's savings *add*, and which heavy elements sit off the critical path worth nothing to fix today. Without it, finding the second thing to fix costs another full build. ([`UX-74`](../backlog/scenarios/UX-0074-one-capture-one-finding.md))
- **Elements Most Worth Optimizing First** — on a build the *graph* constrains rather than the chain, this ranks by blast radius instead: fixing a slow element near the root helps every downstream element too.
- **Biggest wait category / Attribution Breakdown** — where wall-clock time went, by category: execution, dependency wait, resource wait, scheduler wait, idle, retries, plus **untracked head and tail** (real wall-clock before the first task started and after the last one finished, which belongs to no task at all). All eight sum to exactly the total build time — nothing is hidden or double-counted, and the two untracked categories are why: on the quick-start fixture above, untracked tail is 12.5% of the build and is the *largest* non-execution category.
- **Critical Path** — the chain that determines total build time, printed in full with each link's duration and share.
- If a hard gate fails (e.g. `critical_path_coverage`), the violation names the specific missing element(s) and whether each is a structural element (`stack`/`import`/…) that never had a real compute task or a genuine gap worth investigating.

Everything in that block is also published as **data**, with a stable `id`, a `severity` and the numbers behind each sentence — so a CI job acts on `.findings[]` rather than re-deriving a threshold or grepping prose:

```bash
bga analyze /tmp/run --format json | jq '.findings[] | select(.id == "time-concentration") | .evidence'
```

```json
{
  "path_us": 3610500000,
  "share_of_path": 0.94035,
  "chain_bound": true,
  "rows": [
    { "element_uid": "components/_private/cmake-stage1.bst", "duration_us": 1569800000,
      "share_of_path": 0.43478, "realizable_saving_us": 1569800000 },
    { "element_uid": "components/python3.bst", "duration_us": 639800000,
      "share_of_path": 0.17720, "realizable_saving_us": 114100000 }
  ]
}
```

The `rows` array is the part a CI comment renders: each heavy element's measured duration, its
share of the chain, and — separately — what fixing it would actually recover, which on a dense
graph is a much smaller number than its share suggests.

## Exit Codes

Every code below is `bga/exceptions.py`'s `EXIT_CODES`; the two are compared
by `tests/unit/test_the_exit_table_derives_from_the_codes.py`.

- `0`: Success.
- `1`: General error (e.g., invalid arguments, missing files) — including
  argparse's own usage errors (unrecognized flag, invalid choice, missing
  positional), which `UX-574` moved here from argparse's default `2` so a CI
  job reading `2` can trust it means the run could not be read.
- `2`: Data ingestion failure (e.g., malformed v9 artifacts), and
  `bga snapshot`'s own refusals — no project here, nothing to run, and
  (`UX-324`) a build command whose executable will not run, which is
  declined before anything is written.
- `3`: Analysis failure (e.g., graph cycles detected).
- `4`: **not "slower" alone.** `bga compare` returns it for any of three things, and a CI job that triages it as a duration regression will mis-read two of them:
  - `--fail-on-regression` and the build's total duration really did regress beyond the threshold (`UX-3`);
  - the **build-failure gate** (`UX-54`) - either run describes a build in which an element FAILED, so no scheduling verdict is meaningful. This fires whenever *any* gate was requested, including when only the efficiency gates were;
  - `--fail-on-low-confidence` and a run's confidence is below the "high" band.

  Read the stderr line, which names which of the three fired. All three are distinct from 1/2/3, which mean `bga` itself failed to run.
- `5`: `bga compare --fail-on-efficiency-regression`/`--min-efficiency`/`--fail-on-inefficient-additions` only - the build became meaningfully *less efficient*, whether or not it also got slower. Deliberately distinct from `4`: "slower" and "less efficient" are different verdicts and often different teams' problems (`UX-39`).
- `6`: **refused as not comparable** - not a verdict about the build at all, which is why it does not share a code with one. Two commands return it: `bga compare`, when the two runs share fewer than half their element UIDs or one is a caches-off run and the other incremental (`UX-78`; `--allow-mismatch` overrides); `bga cache-trend`, when the series is not all of one project and target set, in which case the per-run rows still print and only the band verdict is withheld (`UX-111`); and `bga baseline`, when the assembled set's captures are not comparable to each other (`UX-96`).
- `7`: `bga compare --require-efficiency-signal` only - an efficiency gate was requested but could not be evaluated, because a run has no `occupancy_share`. Like `6`, not a verdict about the build: `4` would say it got slower and `5` would say it got less efficient, and neither was determined (`UX-87`). Without `--require-efficiency-signal` the same situation exits `0`, prints an `Efficiency gate NOT APPLIED` line to stderr, and publishes `efficiency_gate_evaluated: false`.
- `8`: `bga compare --band-from-class` only - a measured band was asked for and this store (or the `--bundles` tree, `UX-1286`) does not hold one, because fewer than three runs of the candidate's own class besides the two principals (`UX-898`), measured on its host (`UX-1285`: the refusal names how many were skipped for host; `--allow-cross-host` pools them), fall inside the window. A refusal to judge, like `6` and `7`, and for the same reason: the alternative is the fixed 1% rule, which five captures of one unchanged `freedesktop-sdk` commit spanned 33% against, so a gate that fell back to it would be gating on the cries-wolf comparison the band exists to replace (`UX-899`). Capture more runs of that class, widen the window, or drop the flag to accept the fixed rule.
- `130`: **interrupted** (`UX-157`, `UX-163`). Ctrl-C during a capture is
  not a failure and not a verdict: whatever the build completed is kept,
  analyzed, and labelled as a build that did not finish. A comparison
  against that snapshot obeys the same incompleteness rules as any
  unfinished build. Interrupting *before* the build starts leaves
  nothing behind and says so — and so does a machine that cannot start
  the build at all, which refuses with `2` before creating a snapshot
  (`UX-324`).

This table is `bga`'s own codes; `bga snapshot` does not map into it for
the wrapped build's outcome (line 194 above) — a `bst` that dies at
`255` surfaces `255`, not one of the numbers here. `UX-738`: a non-zero
wrapped exit now also gets one printed sentence naming that code and, if
the wrapped log's tail shows a write failed, the path that could not be
written — the number was always right, only the silence around it changed.

## See Also

- [Project README](../../README.md)
- [Architecture Overview](../design/architecture.md) — both analysis planes, and every extension beyond the original spec
- [v9 Specification](../spec/specification.md)
- [The JSON contracts](json-contracts.md) — every schema id, its keys, and the versioning rule
- [The browser report](viewer.md) — `bga view`, chapter by chapter
