# bga's own cost on the snapshot → view path (2026-09-28)

Measured on `39d89d4`, a 4-core / 15 GB container, Python 3.11; the
real captures with BuildStream 2.8.1 and buildstream-plugins 2.8.0. Rows filed: `UX-1072`..`UX-1083`. Related, not
re-filed: `UX-1069` (the anonymized export's whole-file loads) and
`UX-1071` (its residue scan at ~0.4 MB/s).

## The one contradiction

`UX-296` settled *capture computes, view serves*: the analysis runs
once, where the user already waits for a build. But that moved the
analysis onto the hot path of every build, and the code does not run
it once. After `bst` exits, the tail runs the full analyzer **four
times** (`_analyze`, the element slice, and both sides of `compare`),
and `bga view` runs it **twice more** before the page exists. Each run
builds a quadratic reachability closure **five times**. So the tail
grows with the square of the graph, not with the work the build did.

The resolution is *compute once, reuse everywhere*: one analysis per
snapshot, published, and every later reader (slice, compare, view)
takes the published result. The next contradiction is already
visible: a reused analysis can be stale. When the analyzer changes,
every stored `analyze.json` is out of date at once, and the first view
after an upgrade pays the full cost again. `UX-1073` therefore requires
a currency check, not only reuse.

## Measurements

Stores from `bga gen-synthetic --store --seed 1`: 74 elements
(`--layers 6 --width 12`), 1,202 (`20 x 60`) and 5,002 (`40 x 125`).
Plane 2 logs scaled with `genlog.py` below: per element, one `make`
root plus P−1 compiler children, each with 50 opened paths drawn from
a 3,000-header sysroot.

### The tail after the build, per step (`step.py` below)

```text
store   step      wall     peak RSS
74      analyze    0.09s     40 MB
74      slice      0.03s     37 MB
74      compare    0.18s     40 MB
1,202   analyze    1.85s    127 MB
1,202   slice      0.75s    125 MB
1,202   compare    3.44s    140 MB
5,002   analyze   35.58s   1967 MB
5,002   slice     18.62s   1965 MB
5,002   compare   49.27s   2010 MB
60 snapshots   weigh 0.02s   listing 0.01s
```

1,202 → 5,002 elements is 4.2x the elements and 17x the tail
(6.0 s → 103.5 s). cProfile of `_analyze` at 5,002 (50.8 s under the
profiler): `set.update` 17.3 s, `compute_reachability` 21.6 s cum over
5 calls. `_compare`: 2 `analyze` calls, 80.0 of 81.6 s; 8 reachability
calls.

### Reachability alone (`bga/graph/edg.py:219`)

```text
elements   set entries   time   RSS after one call
1,202        660,754     0.1s      78 MB
5,002     14,481,214     6.8s     995 MB
```

### The Plane 2 report (`capture report --json`, the tail's first step)

```text
processes  raw log   wall     peak RSS   note
 12,020     24 MB     1.02s     54 MB    from .gz
 48,080    ~95 MB     4.60s    113 MB    from .gz
192,320    417 MB    12.5s     374 MB    from .gz - opens pass read nothing (UX-1079)
192,320    417 MB    20.9s     714 MB    plain log, as the tail reads it
400,160   ~800 MB    32.0s     763 MB    from .gz - opens pass read nothing
```

About 20 MB/s on the plain log, in two passes. The opens pass alone:
7.4 s and 552 MB for 3,710,972 per-element set entries; with
`sys.intern` on each path, 5.5 s and 261 MB (`UX-1076`).

### The raw log's compression (`_compress_raw_log`, 417 MB)

```text
level 9 (default)  16.0s  30 MB
level 6             3.1s  31 MB
level 1             1.5s  42 MB
copyfile            1.6s
```

### bga view --export

```text
store   wall     peak RSS   HTML (page / data)
74      0.49s     49 MB      477 KiB (137 / 340)
1,202   3.74s    148 MB      672 KiB (137 / 535)
5,002  54.93s   2038 MB     1285 KiB (137 / 1148)
```

At 5,002: compare's two analyses are 80.4 of 89.1 s profiled, the
timeline renders twice (7.2 s, `UX-1081`). Nothing is printed before
the final `Wrote` line.

### The page in Chromium (`tests/browser.py`, headless)

```text
store   DOMContentLoaded   DOM settled   DOM nodes
74       38 ms              0.4 s         5,406
1,202    33 ms              0.8 s         7,293
5,002    67 ms              2.9 s         7,598
```

The fold works: nodes stay flat. Boot time grows about linearly.

## Before the build: entry to `bst build`

`pre.py` below times each step `bga snapshot` runs before the build,
on generated BuildStream projects (`genproj.py`: 10 local files per
element, 3 build-depends each):

```text
step                                 1,201 el   5,001 el
import bga_snapshot + tracer           0.17s      0.15s
project check, list_runs, context      0.00s      0.01s
detect_stale_casd                      0.00s      0.00s
compile_hook (cc -O2)                  0.17s      0.13s
compile_spine (cc -static)             0.23s      0.21s
census for spine=auto (ticker)         0.19s      0.82s   (12,010 / 50,010 files)
```

bga's own work before the build is under 1.5 s at 5,001 elements, and
the one step that grows (the census) already draws a ticker. What this
container cannot time is BuildStream: before the build, bga starts it
up to three times (`bst --version`, the key-set `bst show`, and one
more `bst show` under `--jobserver`), about 2 s each for startup alone
on the Graviton host (2026-09-25) plus project load (`UX-1080`). The
key-set `bst show` is also silent for up to 300 s and drops the build's
own `-o`/`--option` flags, so two variants record one key set
(`UX-1082`).

## Real captures: `examples/06` with BuildStream 2.8.1

`bga snapshot` on a cache-busted copy (the `measure` skill's recipe),
every `bst` timed by a PATH shim (`bstshim` below), output lines
timestamped:

```text
                                  cold             warm (all cached)
snapshot wall                     40.2s            5.1s
bst build itself                  34.72s           1.07s
before the build (bga + bst)      2.3s             2.2s
after the build (bga + bst)       3.3s             1.8s
bga's own share outside build     5.6s (14%)       4.0s (79%)

bst calls around the build        cold             warm
--version (doctor, before)        0.38s            0.31s
show, key set (before)            1.16s            1.18s
artifact list-contents (after)    1.29s            -
show --deps all (after)           1.17s            1.27s
--version (hostinfo, after)       0.29s            0.26s
```

On the warm build, the one a review pipeline takes most, the snapshot
is 4.8x the build and 3.0 of bga's 4.0 s are BuildStream restarts.
`bst show` scales with the project (`genproj.py` projects):

```text
elements   key-set format   graph format (--deps all)
1,201        5.87s             11.21s
5,001       23.68s             42.28s
```

The key-set call is redundant: the build's own `build.log` lists every
element's 64-hex key in its `Pipeline` block, and parsed from there the
set is identical to `bst show`'s on both captures (11 of 11, strict
plan) - `UX-1082`. The warm snapshot's `graph.json` is structurally
identical to the cold one's, so an equal key set could reuse it -
`UX-1083`. At 5,001 elements the two together are 66 s per snapshot.

## Findings, ranked by what the tail costs

| Rank | Row | Finding | At 5,002 el / 192k proc |
|---|---|---|---|
| 1 | `UX-1073` | compare re-analyzes both runs; tail and view both pay it | 49 s tail, 80 s of view |
| 2 | `UX-1074` | reachability as sets, 5x per analysis, O(V²) memory | ~1 GB per call, 22 s |
| 3 | `UX-1072` | the element slice runs the analyzer a second time | 18.6 s |
| 4 | `UX-1077` | 6 phases run silent; no timing anywhere | 20-55 s each |
| 5 | `UX-1079` | a gzipped log drops every opened path (correctness) | declared-vs-used absent |
| 6 | `UX-1075` | gzip level 9 on the raw log | 16.0 s → 3.1 s |
| 7 | `UX-1076` | opened paths held uninterned | 552 → 261 MB |
| 8 | `UX-1080` | the `bst` calls around the build are unmeasured | no reading |
| 9 | `UX-1078` | the snapshot does not record bga's own cost | — |
| 10 | `UX-1081` | the export renders a timeline it then refuses | 7.2 s |
| 11 | `UX-1082` | the pre-build key set is a second project load, drops the build's options, and is silent; the build log already has it | 23.7 s |
| 12 | `UX-1083` | an equal key set still re-reads the graph with `bst show` | 42.3 s |

Rows 1-3 remove about 70 of the 104 s tail at 5,002 elements before
the analyzer itself gets faster; row 2 then cuts the rest's memory.

## Scenarios that shape the snapshot → view experience

1. **The incremental build.** The tail does not depend on how much was
   built. Measured on `examples/06`: a warm build of 1.07 s took a
   5.1 s snapshot. At 5,002 elements the analysis and compare alone are
   about 104 s, plus 66 s of `bst show` (inferred by adding the
   readings above; not one capture). When the pre-build key set (`UX-844`) equals the
   baseline's, the tail could reuse the baseline's analysis.
2. **Hundreds of review builds a day.** The tail competes with the
   next job on the agent: 2 GB peak at 5,002 elements. An option to
   return the build's exit code first and finish the tail in the
   background would take it off the CI job's wall.
3. **An analyzer upgrade.** Every stored `analyze.json` goes stale at
   once. With `UX-1073`'s currency check, the first view of each old
   snapshot re-analyzes; the page should say that it is doing so.
4. **A long build's raw log.** The log grows with processes × opened
   paths, and the tail passes over it up to four times (copy-out from
   scratch when used, two parse passes, gzip). Compressing while the build runs would remove the
   copy and the gzip from the tail.
5. **A memory-tight agent right after a build.** The tail runs when
   the page cache is full. If it is killed for memory, the raw data is
   already on disk; whether anything then tells the user to re-run
   the analysis is unchecked.
6. **Opening a bundle on another machine.** `bga view` does the
   compare on the reader's laptop, silently, before it binds.
7. **The timeline on first click.** It renders on request, 3.6 s per
   render at 5,002 elements, and the page shows no progress meanwhile.
8. **A large store.** Windowed at 12 (`STORE_WINDOW`), and 60
   snapshots list in 0.02 s: this one is not a problem today.
9. **Two snapshots into one store at once** (parallel CI jobs on one
   agent). A compare could pick the other job's half-written snapshot
   as its baseline. Not measured.

## Not measured here

- `bst artifact list-contents` at scale (`UX-1080`): it needs built
  artifacts, and the large projects here were only loaded, not built.
- Non-strict build plans, where the log's keys may not all resolve.
- A real capture's Plane 2 shape. The scaler is a model: real logs
  have deeper process trees, `configure` storms and less repetitive
  paths.
- The page's JS heap (`performance.memory` is quantized in headless
  mode).

## Recipe

```bash
S=/tmp/perf; mkdir -p $S
bga gen-synthetic $S/l --store --seed 1 --layers 40 --width 125
d=$(ls -d $S/l/.bga/runs/* | tail -1)
python3 genlog.py $d/plane2.log.gz $S/l_p80.log.gz 80 50
bga capture report --json $S/l_p80.log.gz > $S/l_p80.json
for s in $S/l/.bga/runs/*; do cp $S/l_p80.json $s/plane2.json; done
for st in analyze slice compare; do python3 step.py $S/l $st; done
python3 -m tools.bga_view $d/run --export $S/l.html
```

`genlog.py` (scales a synthetic `plane2.log.gz`; args: source, target,
processes per element, paths per process):

```python
import gzip, random, sys
src, dst, P, U = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
rnd = random.Random(1)
elems = []
for line in gzip.open(src, "rt"):
    if line.startswith("START "):
        f = dict(kv.split("=", 1) for kv in line.split(" cmd=")[0].split()[1:])
        elems.append((f["element"], float(f["ts"])))
sysroot = [f"/usr/include/c++/13/bits/h{i:04d}.h" for i in range(3000)]
pid = 100000
with gzip.open(dst, "wt", compresslevel=1) as out:
    for el, t0 in elems:
        base = el.replace(".bst", "")
        root = pid; pid += 1
        out.write(f"START pid={root} ppid=1 ts={t0:.6f} element={el} inv=inv-{root} src=spine cmd=/bin/sh -c make -j8\n")
        t = t0
        for k in range(P - 1):
            p = pid; pid += 1
            t += 0.01
            cmd = f"/usr/bin/cc -O2 -c -o {base}/u{k}.o {base}/u{k}.c"
            out.write(f"START pid={p} ppid={root} ts={t:.6f} element={el} inv=inv-{root} src=hook cmd={cmd}\n")
            paths = rnd.sample(sysroot, U - 2) + [f"/buildstream/{base}/u{k}.c", f"/buildstream/{base}/u{k}.o"]
            out.write(f"OPENS pid={p} element={el} inv=inv-{root} unique={len(paths)} dropped=0\n")
            out.write("\n".join(paths) + "\n")
            out.write(f"END pid={p} ppid={root} ts={t+0.5:.6f} element={el} inv=inv-{root} src=hook exit=0 utime=0.400 stime=0.050 maxrss_kb={rnd.randint(20000,300000)} cmd={cmd}\n")
        out.write(f"END pid={root} ppid=1 ts={t+1:.6f} element={el} inv=inv-{root} src=spine exit=0 utime=0.010 stime=0.010 maxrss_kb=4000 cmd=/bin/sh -c make -j8\n")
```

`step.py` (run from the repository root; args: store, step):

```python
import contextlib, io, os, resource, sys, time
sys.path.insert(0, os.getcwd())
from tools import bga_snapshot as s
store, step = sys.argv[1], sys.argv[2]
runs = os.path.join(store, ".bga/runs")
snaps = sorted(os.path.join(runs, d) for d in os.listdir(runs))
cur, prev = snaps[-1], snaps[-2]
t = time.monotonic()
with contextlib.redirect_stdout(io.StringIO()):
    if step == "analyze":
        s._analyze(os.path.join(cur, "run"), os.path.join(cur, "plane2.json"),
                   publish_to=os.path.join(cur, "analyze.json"))
    elif step == "slice":
        s.write_element_slice(cur, os.path.join(cur, "run"))
    elif step == "compare":
        s._compare(prev, cur)
    elif step == "weigh":
        s._say_what_it_weighs(cur, store); s._warn_if_large(store)
    elif step == "listing":
        s.store_listing(store)
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
print(f"{step}\t{time.monotonic() - t:.2f}s\tpeakRSS={rss}MB")
```

`genproj.py` (args: output, layers, width, files per element):

```python
import os, random, shutil, sys
out, L, W, F = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
rnd = random.Random(1)
os.makedirs(f"{out}/elements", exist_ok=True)
open(f"{out}/project.conf", "w").write("name: perf\nmin-version: 2.0\nelement-path: elements\n")
names = []
for l in range(L):
    layer = []
    for w in range(W):
        n = f"l{l:02d}/e{w:03d}.bst"
        os.makedirs(f"{out}/elements/l{l:02d}", exist_ok=True)
        src = f"files/l{l:02d}/e{w:03d}"; os.makedirs(f"{out}/{src}", exist_ok=True)
        for k in range(F):
            p = f"{out}/{src}/f{k}.c"
            if k == 0: shutil.copy("/bin/true", f"{out}/{src}/tool")
            else: open(p, "w").write("int x;\n" * 20)
        deps = rnd.sample(names[-1], min(3, len(names[-1]))) if names else []
        body = "kind: manual\n"
        if deps: body += "build-depends:\n" + "".join(f"- {d}\n" for d in deps)
        body += f"sources:\n- kind: local\n  path: {src}\n"
        open(f"{out}/elements/{n}", "w").write(body)
        layer.append(n)
    names.append(layer)
top = [n for layer in names for n in layer]
open(f"{out}/elements/all.bst", "w").write("kind: stack\ndepends:\n" + "".join(f"- {n}\n" for n in names[-1]))
print(len(top) + 1, "elements")
```

`pre.py` (args: project):

```python
import os, sys, time, resource, tempfile, io, contextlib
sys.path.insert(0, os.getcwd())
t0 = time.monotonic()
import tools.bga_snapshot as s
import tools.bst_native_build_tracer as t
print(f"import bga_snapshot+tracer\t{time.monotonic()-t0:.2f}s")
proj = sys.argv[1]
def step(name, fn):
    t1 = time.monotonic()
    with contextlib.redirect_stderr(io.StringIO()): r = fn()
    print(f"{name}\t{time.monotonic()-t1:.2f}s\trss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss//1024}MB", flush=True); return r
step("why_the_project_is_not_one", lambda: s.why_the_project_is_not_one(proj))
step("list_runs", lambda: s.run_store.list_runs(proj))
step("capture_context", lambda: s._capture_context(proj, ["bst","build","all.bst"], {}, jobserver=("off",None,None), plan=None))
step("detect_stale_casd", lambda: t.detect_stale_casd())
d = tempfile.mkdtemp()
step("compile_hook", lambda: t.compile_hook(d))
step("compile_spine", lambda: t.compile_spine(d))
step("discover_element_names", lambda: t.discover_element_names(proj))
step("census_spine_verdicts (spine=auto)", lambda: t.census_spine_verdicts(proj))
```

`bstshim` (put first on PATH as `bst`; set `REAL` to the real binary
and `LOG` to the log path):

```bash
#!/bin/bash
s=$(date +%s.%N)
$REAL "$@"; rc=$?
e=$(date +%s.%N)
echo "$s $e $rc $*" | cut -c1-200 >> "$LOG"
exit $rc
```
