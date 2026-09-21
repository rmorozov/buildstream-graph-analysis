# UX-874: the jobserver auth style follows the make that consumes it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-841, UX-869 | **Found by:** round 122, the user (a make-kind element from a tar source, GNU Make 4.4 on the host) | **Serves:** R2 (a make element joins the jobserver whatever make its own sysroot ships) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical

## Motivation

`jobserver_auth_style("auto")` runs `make --version` **on the
host** and picks `fifo:` for GNU Make 4.4 and newer
(`tools/bst_native_build_tracer.py:1090`), then hands the one style to
every sandbox through `BST_TRACE_JOBSERVER_AUTH`. Its docstring states
the assumption - "the sandboxes here run the host's own toolchain, so
the host's version is representative" - and the field falsified it: a
`kind: make` element built from a `tar` source stages its own older
`make`, and that make rejects the string the host's 4.4 chose:
`make: *** internal error: invalid --jobserver-auth string
'fifo:/tmp/.bst-native-trace/jobserver'. Stop`, exit 2, the build
dead on that element. `UX-869` put the FIFO where the sandbox can
reach it; the path is right (`/tmp/.bst-native-trace/jobserver`, no
`mkdir parents` error) - the *style* is wrong, chosen from a make that
is not the one that runs. `fd` style is accepted by every make from
4.0 up, so the host that picked `fifo` loses nothing by falling back
to it when the sandbox make is older. The instrument reads a proxy
(the host make) for the thing it names (the sandbox make); fixing
guide section 5.

## Required Fix

`tools/native_trace/bwrap_shim.py`: when the resolved style is
`fifo` (`BST_TRACE_JOBSERVER_AUTH == "fifo"`), the shim probes the
sandbox's own `make --version` before it injects - through the real
`bwrap` the way `probe_ninja` already does, cached beside
`ninja_probe.json` under the jobserver dir - and falls back to `fd`
for that element when the sandbox make is below 4.4 (or make is
absent/unparseable, which `jobserver_auth_style` already treats as
`fd`). The fd path needs the descriptor open, so the downgrade opens
the jobserver read-write and inheritable as `open_jobserver_fd` does
for the fd case. The global FIFO and UX-849's per-element proxy both
follow the downgrade, since both are consumed by the same sandbox
make. `jobserver_auth_style`'s host probe stays as the *request*
default; the sandbox probe is the *consumer* check that can only
narrow fifo to fd, never widen.

## Decomposition

Input classes: sandbox make >= 4.4 (fifo stands), sandbox make <
4.4 (downgrade to fd), make absent or unparseable (fd), a proxy under
each. Boundary: the exact 4.4 cutoff `jobserver_auth_style` already
uses, shared not re-coded. Surfaces: `tools/native_trace/bwrap_shim.py`
(the probe, the downgrade, `open_jobserver_fd`) ·
`tests/unit/test_bwrap_shim.py` and
`tests/unit/test_the_jobserver_fifo_has_a_lifecycle.py`. Serial after
nothing; parallel with UX-875 (disjoint surfaces).

## Out of Scope

The host request default (`UX-841`'s `auto` -> fifo/fd from the host
make) - only the sandbox-consumer narrowing is new here. Making a
sandbox with no make at all join anything. The make probe's own cache
is keyed per element (`_make_probe_cache_path`), not per capture -
`ninja_probe.json`'s own per-capture sharing is a separate,
pre-existing matter, not claimed fixed here.

## Acceptance Test

`tests/unit/test_bwrap_shim.py`: with `BST_TRACE_JOBSERVER_AUTH=fifo`
and a fake `make` on the sandbox `PATH` reporting `GNU Make 4.3`, the
composed `MAKEFLAGS` carries `--jobserver-auth=<fd>,<fd>`, not
`fifo:`, and the build runs clean through the read-only-root fake
bwrap; with the fake make at `4.4` the `fifo:` string stands.
Mutation: drop the sandbox-make probe so the host style is used
verbatim - the `4.3` case keeps `fifo:` and reddens. A live pair on a
make-kind element whose sysroot make is below 4.4, pasted in the
Outcome (or, if this box has only one make, a fake-make sandbox
reading pasted instead, said to be that).

## Outcome

**Gap measured.** This box's own `make --version` is `GNU Make 4.3`
(`apt list --installed`: `make/noble,now 4.3-4.1build2`) - one make,
already below the 4.4 cutoff, so `jobserver_auth_style("auto")` never
even reaches `fifo` here on its own; the field defect (host 4.4,
sandbox 4.3) needs a fake sandbox make to reproduce, per the
Acceptance Test's own fallback. Pre-fix, `build_shim_argv` with
`BST_TRACE_JOBSERVER_AUTH=fifo` and `element_kind="make"` always
injected `--jobserver-auth=fifo:<path>` regardless of what the
sandbox's own make could parse.

**Close measured.** `sandbox_make_auth_style`/`probe_make` (modeled on
`probe_ninja` via a shared `_probe_tool_version` call site, so a second
sandbox-tool probe adds no new `S603` finding) now probe this element's
own sandbox `make --version` through the real bwrap whenever the
request is `fifo`, and `_downgrade_fifo_to_fd_if_sandbox_make_rejects_
it` opens the fd (`_open_inheritable_rdwr`, shared with
`open_jobserver_fd`/`_resolve_proxy_auth`) for both the global FIFO and
UX-849's proxy when that probe resolves `fd`. `jobserver_auth_style`'s
own 4.4 cutoff is now `bwrap_shim.style_for_make_version`, imported,
not re-coded. Verifier fix: the cache is keyed per element
(`_make_probe_cache_path`, `make_probe-<element>.json`), not shared
per capture like `ninja_probe.json` - two make-kind elements whose own
sandbox makes genuinely differ (the junctioned/toolchain shape) each
probe their own now, instead of the second reading the first's stale
answer. `main`'s own wiring moved into `_narrow_jobserver_to_sandbox_
make` (verifier fix: kept `main` under `PLR0915`'s 50-statement cap;
`{probe}`/`{pool}` dict params kept it under `PLR0913`'s arg cap too).

Fake-make sandbox reading (this box has one make; said to be a fake,
GNU Make 4.3/4.4 built by `_fake_bwrap_with_make`), pasted:
`pytest -q tests/unit/test_bwrap_shim.py -k "fifo_style_downgrades or
fifo_style_stands or proxy_follows_the_same_downgrade or
outside_make_like or second_probe_make or style_for_make_version or
cache_path_is_keyed or two_make_kind_elements"`: `8 passed in 0.15s`.
Full file plus the lifecycle guard: `pytest -q
tests/unit/test_bwrap_shim.py
tests/unit/test_the_jobserver_fifo_has_a_lifecycle.py`: `71 passed in
0.56s`. `make test-touching` (post-amend diff, narrower than the
first close's): `47 file(s) selected (28 census + 19 naming the
change) - 1809 passed, 7 skipped in 41.81s`. `make lint`:
`clean: 566 finding(s) match tests/quality_baseline.json; ...`, exit
0 - no `new:` line (the earlier commit's `PLR0915` on `main` and the
duplicate `S603` on `probe_make` are both gone). `python3
tools/dev_sizes.py --check` (post `--adopt --force`, 2 cells changed):
`sizes ok: 122 file(s) measured`. `python3 tools/dev_baseline.py
--check`: exit 0, no `new:` line. `pymarkdown scan` on this file:
clean. `make check-clean`: `OK: no ignored files are tracked`.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| `sandbox_make_auth_style` returns `"fifo"` unconditionally (probe dropped) | `test_fifo_style_downgrades_to_fd_when_the_sandbox_make_is_4_3`, `test_the_proxy_follows_the_same_downgrade_as_the_global_fifo`, `test_two_make_kind_elements_in_one_capture_each_probe_their_own_sandbox_make` | 3 failed, 5 passed -> reverted, 71/71 |
| `_make_probe_cache_path` drops the element tag (shared `make_probe.json`) | `test_make_probe_cache_path_is_keyed_per_element`, `test_two_make_kind_elements_in_one_capture_each_probe_their_own_sandbox_make` | 2 failed, 6 passed -> reverted, 71/71 |

**Deviation (merge):** the verifier held once - `make lint` was red
(PLR0915 on `main()`, S603 on `probe_make`) though the Outcome claimed
exit 0, and the make probe was cached per capture, not per element, so
two make-kind elements with different sandbox makes would share one
answer. Both fixed on the amend: the downgrade factored into
`_narrow_jobserver_to_sandbox_make`, `probe_make` sharing
`_probe_tool_version` so it adds no baseline entry, and the cache
keyed `make_probe-<element>.json` with a guard that reds on a shared
key. `ninja_probe.json`'s own per-capture cache is left as a separate
pre-existing matter. The box has only GNU Make 4.3, so the pair is a
fake-make sandbox reading, not a live host-4.4/sandbox-4.3 build.
