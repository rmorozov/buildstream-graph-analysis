# UX-1009: the examples cannot stage their toolchain on aarch64

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-915, UX-925, UX-927 | **Found by:** CodSpeed's bare-metal Graviton runner (16 real Cortex-A72 cores, measured 1:161.3s 2:80.7s 4:40.6s 8:23.0s 16:15.1s 32:14.6s compile width, sudo and `bwrap --unshare-net` work) is the only real-core host available for UX-905/UX-895, and it is aarch64. Owner decision (Ruslan, 2026-09-24): the jobserver showcase uses `examples/11-serial-giant` on real cores rather than freedesktop-sdk | **Serves:** R4, R5 (UX-905/UX-895 need a real-core host, and the only one available is aarch64) | **Topic:** capture | **Area:** tools | **Shape:** judgement

## Motivation

Two gaps block staging on aarch64. `tools/nix_store_fetch.py` `PINS` and
`tools/nix_toolchain.py` `TOOLCHAIN_PINS` hold only an `x86_64` key;
`host_arch()`/`pins()` refuse any other arch, and
`examples/stage_cpp_toolchain.sh` hardcodes `ld-linux-x86-64.so.2`.
Separately, BuildStream 2.8.1 publishes wheels only for x86_64 and those
wheels bundle `buildbox-casd`/`buildbox-run`; on aarch64 pip builds from
the sdist and carries neither, so no build can run at all.

## Decomposition

surfaces: `tools/nix_store_fetch.py`'s `PINS`, `tools/nix_toolchain.py`'s
`TOOLCHAIN_PINS`, `examples/stage_cpp_toolchain.sh`'s loader lookups, a
new `tools/nix_buildbox.py`, `examples/11-serial-giant`'s `project.conf`/
`giant.bst`/`calibrate_width.py`, `.github/workflows/codspeed-probe.yml`
guards: an `aarch64` pin group exists in both tables with the aarch64
glibc's own loader/interpreter dir; the stager reads the loader from the
pin rather than naming `ld-linux-x86-64.so.2`; a pinned buildbox closure
answers `buildbox-casd`/`buildbox-run` on `PATH` for an arch whose
BuildStream wheel carries neither; `giant.bst`'s calibration is
affordable in a 90-minute job without moving its committed default
gap: whether buildbox needs its own pin table or a bare `nix_closure
--root` in the workflow; a small tool entrypoint keeps it declared and
tested the way `nix_toolchain.TOOLCHAIN_PINS` already is
track: implementer
gate: `make test-touching`, `make push-check`

## Required Fix

- Add `aarch64` groups to both pin tables, same shape as `x86_64`, the
  interpreter_dir/loader from the aarch64 glibc
  (`jjjpj4p9bz505ac1c747f2j5z3xw170p-glibc-2.40-224`). Keep the refusal
  for any other arch.
- Remove the `ld-linux-x86-64.so.2` hardcodes in `stage_cpp_toolchain.sh`
  by reading the loader name from the pin group (`nix_store_fetch
  --loader`), so x86_64 behaviour is byte-identical.
- Stage the pinned `buildbox-1.4.7` closure (aarch64 only - x86_64's own
  wheel already bundles both binaries) via a new `tools/nix_buildbox.py`,
  a declared pin in the same style as `nix_toolchain.TOOLCHAIN_PINS`
  rather than a bare `nix_closure --root` typed into the workflow, so it
  is tested the same way. BuildStream 2.8.1 locates both `buildbox-casd`
  and `buildbox-run` by a bare `PATH` lookup
  (`utils._get_host_tool_internal`, confirmed by reading the 2.8.1
  sdist's `_cas/casdprocessmanager.py` and
  `sandbox/_sandboxbuildboxrun.py`), so staging the pin's own `bin/` onto
  `PATH` is the whole fix.
- Extend `.github/workflows/codspeed-probe.yml`: drop the Ryzen matrix
  leg (never starts on the free plan), set `timeout-minutes: 90`, and add
  steps that stage buildbox, stage the toolchain, `bst build all.bst` on
  `examples/11-serial-giant` (`XDG_CONFIG_HOME` at its `xdg_config_home/`),
  then `calibrate_width.py examples/11-serial-giant 1 2 4 8 16` emitting
  `::notice title=calibrate::`.
- `giant.bst`'s committed 9800 lines/unit is too slow to calibrate at
  width 1 (2013s measured, raw, on the Graviton) inside a 90-minute job.
  The example had no override, so one was added rather than moving the
  default: `project.conf` gained an enum option `giant_lines` (default
  `9800`, `giant.bst`'s `configure-commands` now reads `%{giant_lines}`),
  and `calibrate_width.py` gained `CALIBRATE_GIANT_LINES`, which passes
  `--option giant_lines <value>` to its own `bst build` calls only. The
  CI job sets `CALIBRATE_GIANT_LINES=1800` for the calibration step; the
  `bst build all.bst` step above is unaffected and still gets 9800.
  (Option/variable symbol names reject `-`, hence the underscore.)

## Out of Scope

Running anything on the Graviton (the session does that after this
track). UX-905/UX-895's own measurements. Any x86_64 behaviour change.

## Acceptance Test

`nix_store_fetch.host_arch("aarch64")` and `nix_toolchain.pins("aarch64")`
answer real pins referencing the aarch64 glibc; an unrelated arch is
still refused. `nix_buildbox.pin("aarch64")` answers a real store path,
`nix_buildbox.pin("x86_64")` refuses. `stage_cpp_toolchain.sh` names no
`ld-linux-x86-64.so.2` outside the RUNTIME candidate list.
`examples/11-serial-giant`'s default `giant_lines` is still `9800`, and
`--option giant_lines 1800` overrides what `bst show` resolves to.

## Outcome

Gap measured: `python3 -c "from tools import nix_store_fetch;
nix_store_fetch.host_arch('aarch64')"` raised `SystemExit: no pinned
toolchain for 'aarch64'` before this change - two pin tables, one
hardcoded loader, no buildbox pin, one Ryzen-leg workflow that never
starts on the free plan.

Close: `python3 -c "from tools import nix_store_fetch, nix_toolchain,
nix_buildbox; print(nix_store_fetch.host_arch('aarch64')['loader'],
nix_toolchain.pins('aarch64')['gcc']['store_path'],
nix_buildbox.pin('aarch64')['store_path'])"` answers
`ld-linux-aarch64.so.1 /nix/store/8ybmj60hvhl7g6kl6zhwq3zyyg4hfz5g-gcc-14.3.0
/nix/store/adhcidhjjrgih5hhfqcnddi5pz1flcsz-buildbox-1.4.7`. Every new
NAR digest was downloaded and checked against its narinfo by hand (both
`make` pins byte-for-byte; the toolchain/buildbox roots via
`nix_closure`'s own `NarHash` gate at fetch time, confirmed live against
`cache.nixos.org`, plus one full network run of
`test_buildbox_is_pinned_for_aarch64.py`'s staging test). A real x86_64
`bst build all.bst` on `examples/11-serial-giant` (venv-installed
BuildStream 2.8.1) still succeeds unchanged, and `--option giant_lines
1800` visibly changes what `bst show giant.bst` resolves to while the
unset default stays `9800`.

| mutation | reddened | count |
|---|---|---|
| aarch64 loader set to the x86_64 name | `test_aarch64_is_no_longer_refused`, `test_the_loader_flag_answers_the_pinned_groups_own_name` | 2 |
| stager's pinned-loader lookups reverted to the `x86_64` literal | `test_no_pinned_loader_lookup_hardcodes_x86_64` | 1 |
| aarch64 cmake version changed without its store path | `test_each_root_is_a_store_path_carrying_its_declared_version`, `test_the_versions_match_the_x86_64_pins` | 2 |
| `nix_buildbox`'s pinned key flipped from `aarch64` to `x86_64` | `test_x86_64_is_refused_rather_than_pinned`, `test_aarch64_names_a_real_store_path`, `test_bin_dir_is_under_the_pinned_store_path` | 3 |
| `calibrate_width.py`'s `lines_option()` call dropped from the build command | `test_the_override_reaches_the_build_command` | 1 |
| `giant_lines` default changed to `1800` / `giant.bst` reverted to the `9800` literal | `test_the_committed_default_is_still_9800`, `test_giant_bst_reads_the_variable_not_a_literal` (both clauses) | 2 |
| `lines_option()` dropped from the `artifact delete` call only | `test_the_override_reaches_the_delete_command` | 1 |
| `LINKS["buildbox-run"]` mapped back to the wrapper (`buildbox-run` instead of `buildbox-run-bubblewrap`) | `test_buildbox_run_skips_the_wrapper_that_shadows_the_bwrap_shim` | 1 |

Deviation: three departures from the Decomposition surfaced staging the
pin for real. `nix_buildbox` is staged at `/` in CI, not a sysroot, since
BuildStream's `PATH` lookup is host-wide and there is no sysroot to stage
under (`.github/workflows/codspeed-probe.yml`'s `Stage buildbox` step).
`LINKS` maps `buildbox-run` to nix's unwrapped
`buildbox-run-bubblewrap`, not `buildbox-run` itself - nix's own
`buildbox-run` wrapper prepends its own bwrap onto `PATH`, shadowing
`bga`'s capture shim, so bst must exec the unwrapped binary directly.
`calibrate_width.py`'s `artifact delete` call also carries
`lines_option()`, not just its `build` call - deleting under the
unqualified cache key would leave the 9800-line artifact cached under a
key `CALIBRATE_GIANT_LINES` never touches, and the calibration build
would silently reuse it.
