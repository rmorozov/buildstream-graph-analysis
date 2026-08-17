# Capturing a real third-party project

Every capture `bga` had ever been measured against, up to round 5, was
produced by a build this repository wrote itself. Round 5 pointed the
*structural* plane at a real project's graph for the first time
(`freedesktop-sdk`) and found `UX-52` immediately, because a real project
mixes `runtime` and `build` dependencies and no fixture here contained a
single runtime edge.

That left the sharper question open: everything downstream of the graph —
attribution, floors, occupancy, both efficiency signals, and all of
Plane 2 — had still only ever seen a timeline this repository produced.
This document records how a real one is captured, and why it is done the
way it is.

## Why not simply build it locally

`freedesktop-sdk` cannot be built from the development container this
repository is normally worked on from, for two independent reasons. Both
were reproduced directly rather than inferred, and both are network
policy, not tooling:

**1. The bootstrap seed.** `bootstrap/base-sdk/binary-seed-x86_64.bst` is
an `import` element whose source is a 238MB OCI image. Its blobs are
served from `cdn.registry.gitlab-static.net`, which the environment's
egress proxy refuses at the tunnel:

```
$ bst --no-interactive source fetch bootstrap/base-sdk/binary-seed-x86_64.bst
    [   fetch:bootstrap/base-sdk/binary-seed-x86_64.bst] FAILURE
    HTTPSConnectionPool(host='cdn.registry.gitlab-static.net', port=443):
    Max retries exceeded with url: /gitlab/docker/registry/v2/blobs/sha256/a1/...
    (Caused by ProxyError('Unable to connect to proxy',
     OSError('Tunnel connection failed: 403 Forbidden')))
```

The registry *API* host is reachable — `https://registry.gitlab.com/v2/`
answers `401`, the normal unauthenticated challenge — so this is
specifically the blob CDN, and specifically a `CONNECT` denial:

```
$ curl -sS -o /dev/null -w "%{http_code}\n" https://cdn.registry.gitlab-static.net/v2/
curl: (56) CONNECT tunnel failed, response 403
```

**2. The project's own caches.** `freedesktop-sdk`'s `project.conf`
recommends `https://cache.freedesktop-sdk.io:11001` as both an artifact
and a source cache, which would have made the seed unnecessary. The
proxy allows `CONNECT` to that host and port (`HTTP/1.1 200 Connection
Established`), but the TLS handshake through the tunnel is reset:

```
$ bst --no-interactive artifact pull bootstrap/base-sdk/binary-seed-x86_64.bst
  WARNING Failed to initialize remote https://cache.freedesktop-sdk.io:11001:
  Remote initialisation failed with status UNAVAILABLE: FetchBlob: 14:
  failed to connect to all addresses; last error: UNAVAILABLE:
  ipv4:127.0.0.1:42231: recvmsg:Connection reset by peer

No artifact caches available for pulling artifacts
```

Nothing in `freedesktop-sdk` avoids this. The only elements in the
project with no declared dependencies at all are config/import elements
(`components/hosts.bst`, `abi/reference-abi.bst`, and similar) which
perform no build work — building them yields a timeline with nothing in
it.

So the capture happens on a GitHub-hosted runner, which has unrestricted
egress, and the analysis happens here against the uploaded artifact:
`.github/workflows/real-project-capture.yml`.

## Why the capture is warm-then-cut

Two obvious approaches both fail, in opposite directions:

- **Build from source with caches disabled.** The bottom of
  `freedesktop-sdk` is a full compiler bootstrap. This takes many hours
  and does not fit a CI job.
- **Build with the project's cache enabled.** Everything is pulled,
  nothing is built, and the resulting timeline contains no build work at
  all — the thing the analysis is about.

The capture therefore does both, in order:

1. **Warm.** `bst build <target>` with the project's own remote cache
   enabled. Everything is pulled into the local CAS. Nothing is timed.
2. **Cut.** Delete the artifacts of a bounded subgraph.
3. **Capture.** Rebuild with `--ignore-project-artifact-remotes`, under
   the dual-plane tracer, so exactly that subgraph builds from source on
   top of a cached base — with its real dependencies, real parallelism
   and real per-element durations.

### The cut set has to be upward-closed

This is the part that is easy to get wrong quietly.

BuildStream decides to build an element when **its own** artifact is
missing. A cached dependent is never rebuilt, and therefore never asks
for its dependencies at all. Deleting a mid-level element alone changes
nothing observable: its cached dependents still satisfy the build, and
the deleted element is never needed.

So the delete set must contain every element that transitively
build-depends on any cut — up to and including the requested target, or
the build stops short of it and the capture is empty.

`tools/bst_rebuild_set.py` computes that closure from the same
`graph.json` `tools/bst_show_to_graph.py` already produces, which makes
the rebuild set a reproducible function of `(project, target, cuts)`
rather than a hand-maintained list that drifts. It follows `build` edges
and ignores `runtime` ones, matching the rule `UX-52` enforced: a
runtime-only edge does not make its dependent need the dependency at
build time, so it cannot propagate a rebuild.

```
$ bga graph-from-show fdsdk components/libxml2.bst graph.json
Wrote graph.json with 126 elements, 699 dependencies

$ bga rebuild-set graph.json \
    --cut components/_private/python3-flit-core.bst \
    --cut components/openssl.bst --cut components/expat.bst \
    --cut components/bison.bst --cut components/icu.bst \
    --cut components/doxygen.bst --cut components/which.bst \
    --cut components/ninja.bst --cut components/libxml2.bst | wc -l
25
```

### Why this particular cut

The nine cuts were chosen so the resulting closure is **deep** rather
than merely numerous — depth is what the structural plane actually reads,
and a wide flat set of independent leaves would exercise almost none of
it. The 25 elements span 9 dependency levels and six element kinds
(`autotools`, `cmake`, `meson`, `pyproject`, `manual`, `stack`), with a
real chain running `python3-flit-core → python3-installer →
python3-build → python3-setuptools → meson → git-minimal → bison →
doxygen → libxml2`.

They are also bounded: the expensive elements in the set (CPython,
OpenSSL, ICU, Doxygen) are each minutes, not hours.

## Reproducing

The workflow runs on `workflow_dispatch` once it is on the default
branch. Before then it also runs on a push to a `claude/**` branch that
touches the workflow or the capture tooling it drives — deliberately
narrow, because the job costs a runner-hour or more.

The capture leaves the runner two ways, and both are needed. The
`actions/upload-artifact` upload is for humans; it is **not** reachable
from this development container, because workflow artifacts are served
from `*.blob.core.windows.net`, which the same egress policy that blocks
the `freedesktop-sdk` CDN also refuses with `403` to `CONNECT`. So the
job additionally pushes a tarball of the same directory to the
`captures/fdsdk-latest` branch, which is fetchable, and which makes each
capture a versioned object rather than something that expires in
fourteen days:

```
git fetch origin captures/fdsdk-latest
git show origin/captures/fdsdk-latest:capture.tar.gz > capture.tar.gz
```

Contents (uploaded and published on success *or* failure):

| file | what it is |
|---|---|
| `run/` | the `bga`-ready run directory (`graph.json`, `trace.json`, `run-context.json`) |
| `native-report.json` | the Plane 2 report |
| `native-trace.log` | the raw `LD_PRELOAD` trace |
| `build.log` | the wrapped-format Plane 1 log |
| `graph-declared.json` | the declared graph, extracted before any build |
| `rebuild-set.txt` | the exact elements deleted |
| `state-after-warm.txt`, `state-after-delete.txt` | `bst show %{state}` either side of the cut |
| `analyze.txt`, `analyze.json`, `correlate.txt` | the analysis as run on the runner |
| `capture-context.txt` | commit hashes, `bst` version, core count, memory, disk |
