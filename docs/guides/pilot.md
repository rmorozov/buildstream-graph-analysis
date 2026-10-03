# Pilot it in your CI, report-only

> **R4's page** — the CI gatekeeper ([the role model](../design/roles.md)),
> for the first two weeks, before the gate may fail anything (`UX-1288`).
> The full wiring is [`ci-comment.md`](ci-comment.md); this page is the kit.

Every default the gate depends on is reasoned, not measured on your
pipeline: the band window of 10 (`UX-899`), the capture overhead (one
shape, `UX-895`), the jobserver's pool size ("uncalibrated", `UX-1005`).
A pilot measures them. Until it has, the kit **never fails a job on a
verdict**: it comments, and records the verdict.

## What you copy

Two files, then three variables:

| file | goes to | what it is |
|---|---|---|
| [`examples/ci/bga-pilot.sh`](../../examples/ci/bga-pilot.sh) | `ci/bga-pilot.sh` | the kit, CI-agnostic: `setup`, `capture`, `report` |
| [`examples/ci/bga-pilot.yml`](../../examples/ci/bga-pilot.yml) | `.github/workflows/bga-pilot.yml` | the GitHub Actions wrapper; every switch below is in its `env:` |

Set `PILOT_BGA_COMMIT` (a full 40-character commit of this repository),
`PILOT_PROJECT` and `PILOT_TARGET`. Everything else has a default.
Another CI system calls the same three subcommands in the same order:

```bash
ci/bga-pilot.sh setup                       # install, then bga doctor
ci/bga-pilot.sh capture                     # the build, under bga
ci/bga-pilot.sh report > bga-comment.md     # the comment; exits 0
```

## The three steps, and what each costs

**`setup`** installs `bga` from a pinned commit, never from PyPI (the
kit refuses anything but a full sha), then runs `bga doctor` on the
project. Doctor checks `bst`, `bwrap` and the C compiler the capture
compiles its hook with (`UX-1287`). A failing doctor fails **this step
only**: `capture` then runs the plain build and says why. Install time
is not measured here.

**`capture`** runs the build under `bga capture run`, declares its class
(`BGA_BUILD_TYPE`, `BGA_BUILD_VARIANT`) and keeps the run as a bundle in
`PILOT_KEEP_DIR/<type>/<variant>/`. The build's own exit code is the
step's. Overhead, the one reading there is (`UX-895`,
[`real-project.md`](real-project.md), Step 0:
CodSpeed Graviton, 16 cores, `examples/11-serial-giant`, n=3 per arm):

| arm | wall | host CPU |
|---|---|---|
| the kit's default (no `--trace-opens`, spine off) | +7.1% | +1.9% |
| `PILOT_TRACE_SPINE=on` | +7.1% | +1.9% |
| `PILOT_TRACE_OPENS=on` | +8.9% | +2.9% |
| both on | +9.3% | +3.2% |

Memory differences between arms sat under 50 MB, inside the uncaptured
build's own spread. One shape on one host: your pilot's first number.

**`report`** unpacks the newest kept bundle of the same class as the
baseline and runs `bga compare --band-from-class --bundles` against
the kept tree with both regression gates and `--format ci-comment`
(`UX-1286`; the band skips members from another host, `UX-1285`). It
prints the comment, appends one line to `PILOT_KEEP_DIR/verdicts.tsv`,
and exits 0 whatever the verdict. Below 4 kept runs of the class before
this build the band refuses (exit 8): the band needs 3 runs besides the
two it compares, and the baseline is one of the kept. The kit then
comments against the fixed 1% rule, which the comment names.

## Every switch

Set any of these in the workflow's `env:` (or the job's environment on
another CI). Nothing else is read; no task file or `cli.md` table is
needed to find or turn off one.

| switch | default | values | what it does, and what it costs |
|---|---|---|---|
| `PILOT_BGA_COMMIT` | (required) | a full commit sha | the `bga` installed; pinned, so a pilot never changes tool mid-measurement |
| `PILOT_PROJECT` | `.` | a directory | the BuildStream project the build runs in and doctor checks |
| `PILOT_TARGET` | (required) | an element | built as `bst build TARGET`; or pass the command after `capture --` |
| `PILOT_BGA_REPO` | `https://github.com/rmorozov/buildstream-graph-analysis` | a git URL | where the pinned commit is fetched from — a mirror, if your agents have no internet |
| `PILOT_BUILD_TYPE` | `review` | free text | the class's type (`BGA_BUILD_TYPE`); the workflow sets `night` on the schedule. Two types are two populations |
| `PILOT_BUILD_VARIANT` | (empty) | `name=value,...` | the class's variant (`BGA_BUILD_VARIANT`), e.g. `arch=aarch64` |
| `PILOT_REVIEW_SAMPLE` | `25` | 0-100 | percent of `review` builds captured; the rest build plain and are your overhead control. Other types are always captured; the workflow sets 100 on push to main |
| `PILOT_JOBSERVER` | `off` | `off`, `auto`, a token count | `bga capture run --jobserver`. **Off throughout the pilot** — see below |
| `PILOT_ADMISSION` | `off` | `off`, `on` | `on` sets `BGA_ADMISSION=1`: sandbox admission under the jobserver. Measured slower, so opt-in |
| `PILOT_TRACE_OPENS` | `off` | `off`, `on` | `--trace-opens`: the comment's "Declared, never read" column. +8.9% wall against +7.1% |
| `PILOT_TRACE_SPINE` | `off` | `off`, `on`, `auto` | `--trace-spine`: the ptrace spine. No measured cost over the capture alone |
| `PILOT_BAND_WINDOW` | `10` | 3-99 | `--band-from-class N`: how many kept runs of the class form the band |
| `PILOT_CROSS_HOST` | `off` | `off`, `on` | `--allow-cross-host`: band members and baseline from other machines count. Only for a uniform fleet |
| `PILOT_KEEP_DIR` | `bga-pilot-kept` | a directory | the kept bundle tree; the workflow restores and saves it as a cache |
| `PILOT_KEEP_LAST` | `30` | a count | bundles kept per class; older ones are deleted at capture |
| `PILOT_ENFORCE` | `off` | `off`, `on` | `on` re-applies exit 4 or 5 to the job: the switch from report-only to gating |

`capture run`'s own defaults are `--trace-opens` off and the spine off;
`bga snapshot`'s are on and `auto`, sticky in `.bga/config`. The kit
calls `capture run` and passes all three flags, so the table is what
runs.

## The jobserver stays off

Turn it on with `PILOT_JOBSERVER=auto`; off is `PILOT_JOBSERVER=off`.
The pilot keeps it **off** because it changes the build being measured,
and because its memory gate reads the host's `/proc/meminfo`, not a
container's cgroup limit: on a container agent with `memory.max` below
the host's RAM the gate can admit work the cgroup's OOM killer then
kills (`UX-1282`, inferred from the code, not measured on a capped
agent). Until `UX-1282` closes, container agents keep it off.

What it does when it is on, from [`jobserver.md`](jobserver.md) (16-core
Graviton, cold cache, medians of 3):

| shape | off | auto | wall |
|---|---|---|---|
| one wide element, `max-jobs: 3` | 261.4s | 112.3s | −57% |
| one wide element, `max-jobs` 8 (BuildStream's default) | 139.2s | 112.2s | −19% |
| independent elements that already fill every core | 22.6s | 23.6s | +1.1s |

It costs host CPU +12% to +15%, peak host memory 448 MB → 1611 MB on
the `max-jobs: 3` pair, and about 2.3s per build. Sandbox admission
(`PILOT_ADMISSION=on`) read 202/217/203s against about 182s without it
on `13-mixed-graph`. The full case is
[`serial-giant-jobserver.md`](../cases/serial-giant-jobserver.md).

## What the exit codes mean here

From [`cli.md`](cli.md#exit-codes); the kit's `report` exits 0 on every
one unless `PILOT_ENFORCE=on`:

| `bga compare` | means | the kit |
|---|---|---|
| 0 | compared; no gate failed | comments |
| 4 | slower than the band (or the 1% rule), or an element FAILED in either run — stderr names which | comments; fails the job only when enforcing |
| 5 | less efficient | comments; fails the job only when enforcing |
| 6 | refused: another host or class, or not comparable | comments; the refusal is on stderr |
| 8 | fewer than 4 kept runs of the class before this build | comments against the 1% rule |

## What two weeks measure

- **Overhead on your shape**: captured against plain `review` builds,
  which the sample rate supplies as a control.
- **The band's width and its false alarms**: `verdicts.tsv` holds one
  line per report — stamp, type, variant, `band` or `rule`, exit code.
  An exit 4 on a change your team judges inert is a false alarm.
- **Whether 10 runs is the window**: `PILOT_BAND_WINDOW` against the
  same tree, re-run on kept bundles.

Five captures of one unchanged freedesktop-sdk commit spanned **33%**
(`UX-899`) — the reason the gate judges a band, not the last build.

## From report-only to gating

Set `PILOT_ENFORCE=on` once your false-alarm rate on your own
population is known and accepted. The kit then fails the job on exit 4
or 5, after the comment is written. Nothing else changes.

## Not in the kit

GitLab and other CI wrappers (the script is CI-agnostic; only the
workflow is GitHub's), a PyPI wheel, and the jobserver during the pilot.
