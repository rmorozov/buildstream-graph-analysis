# Real BuildStream example projects

Four real BuildStream projects, each targeting a different corner case
this tool cares about, built for real (not just `bst show`) in CI
(`.github/workflows/ci.yml`'s `bst-examples` job) to generate real traces,
`bga` run directories, and reports for later analysis. See
`docs/tasks/` for the specific backlog items 01-03 map to, and
`docs/scenarios/` for 04's.

All sources are `kind: local` or a throwaway `kind: git` remote generated
at build time - no network access needed, nothing sensitive committed.

## 01-resource-contention

Eight independent elements (`work-a.bst`..`work-h.bst`), each doing 3
real seconds of work, all simultaneously ready to build. Built with a
builder count smaller than the fan-out width to force genuine
`RESOURCE_WAIT`/`SCHEDULER_WAIT` gaps (P1-31, P1-32).

```
bst --builders 2 build all.bst
```
(run from inside `01-resource-contention/`)

## 02-deep-chain-mixed-kinds

A depth-4 chain across mixed element kinds (`import` -> `manual` ->
`compose` -> `manual`), plus a junction reached through a runtime-only
dependency - real build, not just `bst show` (P4-12).

```
bst build all.bst
```
(run from inside `02-deep-chain-mixed-kinds/`)

## 03-project-refs-identity

A git-sourced element under `ref-storage: project.refs`, exercising
`tools/bst_extract_run.py --strict`'s real consistency check (P4-13) and
generating real "touch and rebuild" retry/rebuild data (P1-37). The git
source's upstream is a throwaway repo generated deterministically by
`../stage_project3_remote.sh` (fixed committer identity/dates, so the
resulting commit SHA is reproducible from committed seed content alone).
The same script also renders `elements/libbar.bst` from
`elements/libbar.bst.in`, substituting the real (per-checkout) absolute
path to that remote - BuildStream project options have no free-form
string type to hold an arbitrary path (only
`bool`/`enum`/`flags`/`element-mask`/`arch`/`os`), confirmed via a real
CI failure, so this is templated rather than passed as a `--option`.

```
../stage_project3_remote.sh
bst source track libbar.bst
bst build all.bst
```
(run from inside `03-project-refs-identity/`)

## 04-critical-path-optimization

Ten elements with two deliberate, independently discoverable optimization
opportunities: a scheduling bottleneck (a 4-way fan-out constrained by
`--builders`) and a structural one (an unnecessary serial split plus one
oversized step on the critical path). `optimized/` is a second, complete
BuildStream project - the same shape with both fixes applied - so the pair
can be run through `bga compare` as a real before/after. See
`docs/optimization-walkthrough.md` for the full worked walkthrough (every
command and its real output) and `docs/scenarios/UX-05-optimization-walkthrough-tutorial.md`
for the task this was built for.

```
bst --builders 2 build all.bst   # baseline, from inside 04-critical-path-optimization/
bst --builders 4 build all.bst   # scheduling fix - no project change needed
(cd optimized && bst --builders 4 build all.bst)   # structural fix
```

**Capture note**: unlike 01-03 above, this project's CI step captures each
build with `tools/bst_run_wrapped.py` and extracts with `--format wrapped`,
not `--format raw` - `--format raw` was found, while building this example,
to corrupt cross-task ordering on a real saved multi-task log (BuildStream's
own `[HH:MM:SS]` elapsed prefix resets per-task, not per-invocation; see
`docs/scenarios/UX-06-raw-log-timestamp-corruption.md`). If you're capturing
this project's build yourself rather than reading CI's artifacts, do the
same:

```
python3 -m tools.bst_run_wrapped 04-critical-path-optimization build.log -- bst --builders 4 build all.bst
python3 -m tools.bst_extract_run --format wrapped 04-critical-path-optimization build.log run/
```
(run from `examples/`)

## Shared setup

`01-resource-contention`, `02-deep-chain-mixed-kinds`, and
`04-critical-path-optimization` (including its `optimized/` variant)'s
`manual.bst`/`compose` elements need a real shell in the sandbox, which
BuildStream doesn't provide on its own (the sandbox is assembled purely
from staged dependencies). Run once before building any project:

```
sudo apt-get install -y busybox-static
../examples/stage_runtimes.sh   # (or ./stage_runtimes.sh from examples/)
```

On Ubuntu 24.04+ runners, bubblewrap also needs one more thing to build a
network-namespaced sandbox at all - see `.github/workflows/ci.yml`'s
`bst-smoke`/`bst-examples` jobs for the exact `sysctl` workaround
(confirmed via a real CI run, not a guess).
