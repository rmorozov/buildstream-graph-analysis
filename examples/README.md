# Real BuildStream example projects

Three real BuildStream projects, each targeting a different corner case
this tool cares about, built for real (not just `bst show`) in CI
(`.github/workflows/ci.yml`'s `bst-examples` job) to generate real traces,
`bga` run directories, and reports for later analysis. See
`docs/tasks/` for the specific backlog items each maps to.

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

```
../stage_project3_remote.sh
bst --option remote_path "$(pwd)/.generated-remote" source track libbar.bst
bst --option remote_path "$(pwd)/.generated-remote" build all.bst
```
(run from inside `03-project-refs-identity/`)

## Shared setup

Both `01-resource-contention` and `02-deep-chain-mixed-kinds`'s
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
