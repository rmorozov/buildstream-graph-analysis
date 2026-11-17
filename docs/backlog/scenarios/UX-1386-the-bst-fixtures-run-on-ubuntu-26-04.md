# UX-1386: the bst fixtures and wrapper run on Ubuntu 26.04

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** `ubuntu-latest` moved to 26.04 (image 20261111.196.1); `bst-tests` and `test (3.12)` red on #350, run 44047213573, 2026-11-17; Ruslan chose adapting over pinning 24.04 on the decision card, 08:54 UTC | **Serves:** R8 | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** runner:bst-tests

**Guard:** `tests/unit/test_a_captured_workload_matches_its_plan.py`, `tests/unit/test_a_patched_ninja_joins_the_jobserver.py`, `tests/unit/test_the_sysroot_declares_both_axes.py`

## Motivation

26.04's coreutils is uutils 0.10.0 (Rust, multicall) and its glibc 2.43.
Four reds followed, none a PR's own: the fake `/opt/fakebin/*` copies of
`sleep` exit 1 (`coreutils: unknown program 'lognormal-078'`); the host
glibc probe looks for `libc.so.6` beside the loader and reads `did not
run`; uutils `dd` ignores `iflag=nonblock` on stdin, so the wrapper's
token read blocks and, with `count=$cap` one-byte reads, drops what it
had read; and uutils `dd` and `sync` fault alike, so the minflt clause
has no other process to measure against.

## Required Fix

A compiled sleeper for the fake binaries, refused when a copy will not
run under another name; the glibc probe finds the one real `libc.so.6`;
the wrapper reads tokens with one `dd if=/dev/fd/9 bs=$cap count=1`;
the hook/spine workload's writer is Python; `HOST_COMPONENTS` declares
26.04's glibc 2.43 and coreutils 0.10.0.

## Out of Scope

Pinning `runs-on: ubuntu-24.04`; re-deriving example figures, which
read the pinned toolchain axis, not these rows.

## Acceptance Test

`bst-tests` and `test (3.12)` green on `ubuntu-26.04`, with no
`sysroot_manifest:` divergence line in the staging step; each new guard
reddens under its mutation on this container (24.04, GNU).

## Outcome (round 177, 2026-11-17) — 🟢 Done

**Premise:** held - all four reds are the image, not a diff: `#350`'s
diff touches none of these files, and Timing on main reds identically
(run 43871571767, `ubuntu-26.04`, 2026-11-16).

### The gap, measured

```text
# bst-tests, job 133916115806 (ubuntu-26.04 20261111.196.1)
sysroot_manifest: libc.so.6 is did not run: [Errno 2] No such file or directory: '.../files/toolchain/lib/x86_64-linux-gnu/libc.so.6', declared 2.39
sysroot_manifest: /usr/bin/env is 0.10.0, declared 9.4      (uname, sort, cat alike)
    coreutils: unknown program 'lognormal-078'
E   assert 255 == 0                     ==== 1 failed, 54 passed ====
# test (3.12), job 133915878658
minflt: the two mechanisms differ by 8 on the worker (hook 757, spine 765) and the nearest other process the spine recorded is 0 away
test_an_unpatched_1_10_still_gets_a_held_width - subprocess.TimeoutExpired ... after 10 seconds
```

The archive agrees with the probe: `resolute-updates` ships `libc6
2.43-2ubuntu2.7` and `rust-coreutils 0.10.0-1ubuntu2~26.04.1`. uutils
0.10.0's `dd.rs` applies `iflag` only on `if=` (`new_file`/`new_fifo`),
never on stdin, and its `fill_consecutive` returns a read error before
writing the bytes it already read; the fixture's own `dd <&9` then
blocked on an empty pool, which is the 10 s timeout.

### After

```text
$ python3 -m pytest -q tests/unit/test_a_captured_workload_matches_its_plan.py \
    tests/unit/test_a_patched_ninja_joins_the_jobserver.py tests/unit/test_the_sysroot_declares_both_axes.py \
    tests/unit/test_a_spine_record_carries_what_the_hook_would_have.py tests/unit/test_the_toolchain_axis_is_pinned.py
# 24.04 container, unstaged; 26.04 is the pull request's bst-tests and test (3.12)
```

The Python writer reads minflt 3438-3442 under both mechanisms over 4
runs, the next process 83-95. The wrapper's tool now inherits fd 9 at
`flags 0100002` (blocking); the stdin `dd` left it `0104002`.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| A1 | the wrapper reads tokens from stdin again (`git stash` of `_common.sh`) | `test_the_held_read_leaves_the_tools_pool_fd_blocking`, 1 |
| A2 | the glibc probe joins `libc.so.6` to the loader's directory | `test_the_host_glibc_is_probed_where_it_is_staged_not_beside_the_loader`, 1 |
| A3 | `write_workload_project` skips the renamed-copy run | `test_a_sleeper_that_dispatches_on_its_name_is_refused`, 1 |

No mutation here can stand in for uutils itself on a GNU host; the
26.04 reading is the pull request's own CI.

### Deviation from the Required Fix

None. A 24.04 container that stages the sysroot now warns on the two
host rows, by UX-914's design. `dev_sizes --adopt --force` moved three
`file_lines` cells up: `bga_gen_project.py` 365 -> 394 (the sleeper),
`nix_store_fetch.py` 342 -> 344, `sysroot_manifest.py` 312 -> 313; two
`S603` findings are forced in the baseline under this row.
