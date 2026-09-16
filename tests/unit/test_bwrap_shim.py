"""Tests for tools/native_trace/bwrap_shim.py's split_bwrap_args/
build_shim_argv - the one piece of real logic UX-11's tracer depends on
to survive contact with BuildStream's own real, generated bwrap argv
(see docs/backlog/scenarios/UX-0011-native-build-system-profiler-tool.md's Deep
Experiment Findings for the two real bugs this was built to prevent
regressing: injecting before BuildStream's own root-filesystem bind
wipes the injection out, and mis-guessing `--dir`'s arity corrupts the
whole split).

REAL_BWRAP_ARGV below is a trimmed-but-real shape captured from a real
`bst build core.bst` invocation against examples/05-cmake-cpp-toolchain
during that Deep Experiment - real option ordering/arity, not invented.
"""
import json
import os
import subprocess
import sys

from tools.native_trace.bwrap_shim import (
    JOBSERVER_CAPPED_PENDING,
    JOBSERVER_JOINED,
    JOBSERVER_PINNED,
    JOBSERVER_UNKNOWN_KIND,
    _downgrade_fifo_to_fd_if_sandbox_make_rejects_it,
    _element_kind_env,
    _make_probe_cache_path,
    _resolve_kind_and_probe,
    _resolve_proxy_auth,
    build_shim_argv,
    element_from_build_root,
    extract_element_name,
    jobserver_decision,
    kind_job_env,
    parse_element_max_jobs,
    parse_ninja_help,
    probe_make,
    probe_ninja,
    record_jobserver_decision,
    sandbox_make_auth_style,
    split_bwrap_args,
    style_for_make_version,
)

REAL_BWRAP_ARGV = [
    "--unshare-pid", "--die-with-parent",
    "--bind", "/root/.cache/buildstream/cas/staging/cas-tmpdirABCDEF", "/",
    "--unshare-net", "--unshare-uts", "--hostname", "buildbox", "--unshare-ipc",
    "--dir", "buildstream/cmake-cpp-toolchain-example/core.bst",
    "--chdir", "buildstream/cmake-cpp-toolchain-example/core.bst",
    "--unshare-user", "--uid", "0", "--gid", "0", "--cap-drop", "ALL",
    "--unsetenv", "PATH", "--unsetenv", "SHELL",
    "--setenv", "PATH", "/usr/bin:/bin:/usr/sbin:/sbin",
    "--setenv", "HOME", "/tmp",
    "--setenv", "JOBS", "-j4",
    "--proc", "/proc", "--tmpfs", "/tmp", "--dev", "/dev",
    "sh", "-c", "-e", "cmake -B_builddir -H. -G Unix_Makefiles",
]


def test_split_separates_all_options_from_trailing_command():
    opts, cmd = split_bwrap_args(REAL_BWRAP_ARGV)

    assert cmd == ["sh", "-c", "-e", "cmake -B_builddir -H. -G Unix_Makefiles"]
    assert opts == REAL_BWRAP_ARGV[:-4]


def test_split_handles_bind_with_two_trailing_args_correctly():
    """--bind takes exactly 2 trailing args (src, dest) - the real
    root-filesystem bind ("/root/.cache/.../cas-tmpdir...", "/") must
    stay intact as one 3-token unit, not get split across the
    options/command boundary."""
    opts, _cmd = split_bwrap_args(REAL_BWRAP_ARGV)

    bind_idx = opts.index("--bind")
    assert opts[bind_idx:bind_idx + 3] == ["--bind", "/root/.cache/buildstream/cas/staging/cas-tmpdirABCDEF", "/"]


def test_split_handles_dir_with_exactly_one_trailing_arg():
    """Regression for the real arity bug hit during UX-11's Deep
    Experiment: --dir takes 1 trailing arg, not 2 like --bind. Getting
    this wrong shifts every subsequent option by one token and corrupts
    the whole parse - confirmed by the real observed failure "bwrap:
    Can't chdir to --bind: No such file or directory"."""
    opts, cmd = split_bwrap_args(REAL_BWRAP_ARGV)

    dir_idx = opts.index("--dir")
    assert opts[dir_idx:dir_idx + 2] == ["--dir", "buildstream/cmake-cpp-toolchain-example/core.bst"]
    # and the next real option must be --chdir, not a swallowed command token
    assert opts[dir_idx + 2] == "--chdir"
    assert "sh" not in opts
    assert cmd[0] == "sh"


def test_split_handles_zero_arg_flags():
    opts, _cmd = split_bwrap_args(REAL_BWRAP_ARGV)

    for flag in ("--unshare-pid", "--die-with-parent", "--unshare-net"):
        assert flag in opts


def test_split_handles_proc_dev_tmpfs_as_one_arg_flags():
    """Regression: --proc/--dev/--tmpfs each take exactly 1 trailing arg
    (the mount destination), not 0 - the same class of arity mistake as
    the --dir bug above, and one this design got wrong on its first
    Python transcription of the already-validated bash spike logic."""
    opts, cmd = split_bwrap_args(REAL_BWRAP_ARGV)

    proc_idx = opts.index("--proc")
    assert opts[proc_idx:proc_idx + 2] == ["--proc", "/proc"]
    dev_idx = opts.index("--dev")
    assert opts[dev_idx:dev_idx + 2] == ["--dev", "/dev"]
    tmpfs_idx = opts.index("--tmpfs")
    assert opts[tmpfs_idx:tmpfs_idx + 2] == ["--tmpfs", "/tmp"]
    assert cmd[0] == "sh"


def test_split_empty_args():
    assert split_bwrap_args([]) == ([], [])


def test_split_stops_at_first_non_option_token():
    opts, cmd = split_bwrap_args(["--unshare-pid", "sh", "-c", "echo hi"])

    assert opts == ["--unshare-pid"]
    assert cmd == ["sh", "-c", "echo hi"]


def test_build_shim_argv_injects_after_bstS_own_root_bind():
    """The real bug this whole split exists to prevent: injecting the
    trace bind *before* BuildStream's own "--bind <cas-tmpdir> /" gets
    silently wiped out once that root rebind happens. The injected bind
    must appear strictly after every one of BuildStream's own options in
    the final argv, and strictly before the trailing command."""
    argv = build_shim_argv(
        real_bwrap="/usr/bin/bwrap",
        bst_args=REAL_BWRAP_ARGV,
        bind_src="/tmp/host-trace-dir",
        bind_dst="/tmp/.bst-native-trace",
        preload_so="/tmp/.bst-native-trace/hook.so",
        trace_log="/tmp/.bst-native-trace/trace.log",
    )

    assert argv[0] == "/usr/bin/bwrap"
    root_bind_idx = argv.index("/") if "/" in argv else None
    inject_idx = argv.index("--bind", argv.index("--bind") + 1)  # the *second* --bind is ours
    setenv_ld_preload_idx = next(
        i for i, tok in enumerate(argv) if tok == "--setenv" and argv[i + 1] == "LD_PRELOAD"
    )
    sh_idx = argv.index("sh")

    setenv_trace_log_idx = next(
        i for i, tok in enumerate(argv) if tok == "--setenv" and argv[i + 1] == "BST_TRACE_LOG"
    )

    assert root_bind_idx is not None and root_bind_idx < inject_idx
    assert inject_idx < setenv_ld_preload_idx < sh_idx
    assert inject_idx < setenv_trace_log_idx < sh_idx
    assert argv[inject_idx:inject_idx + 3] == ["--bind", "/tmp/host-trace-dir", "/tmp/.bst-native-trace"]
    assert argv[setenv_ld_preload_idx:setenv_ld_preload_idx + 3] == [
        "--setenv", "LD_PRELOAD", "/tmp/.bst-native-trace/hook.so",
    ]
    assert argv[setenv_trace_log_idx:setenv_trace_log_idx + 3] == [
        "--setenv", "BST_TRACE_LOG", "/tmp/.bst-native-trace/trace.log",
    ]


def test_build_shim_argv_preserves_trailing_command_unmodified():
    argv = build_shim_argv(
        real_bwrap="/usr/bin/bwrap",
        bst_args=REAL_BWRAP_ARGV,
        bind_src="/tmp/host-trace-dir",
        bind_dst="/tmp/.bst-native-trace",
        preload_so="/tmp/.bst-native-trace/hook.so",
        trace_log="/tmp/.bst-native-trace/trace.log",
    )

    assert argv[-4:] == ["sh", "-c", "-e", "cmake -B_builddir -H. -G Unix_Makefiles"]


# --- extract_element_name (UX-23) -----------------------------------------

def test_extract_element_name_from_real_dir_option():
    opts, _cmd = split_bwrap_args(REAL_BWRAP_ARGV)

    assert extract_element_name(opts) == "core.bst"


def test_extract_element_name_handles_different_real_elements():
    argv = list(REAL_BWRAP_ARGV)
    dir_idx = argv.index("--dir")
    argv[dir_idx + 1] = "buildstream/cmake-cpp-toolchain-example/lib-a.bst"

    opts, _cmd = split_bwrap_args(argv)

    assert extract_element_name(opts) == "lib-a.bst"


def test_extract_element_name_returns_none_when_dir_absent():
    opts, _cmd = split_bwrap_args(["--unshare-pid", "--die-with-parent"])

    assert extract_element_name(opts) is None


def test_build_shim_argv_injects_bst_trace_element_after_the_real_dir():
    argv = build_shim_argv(
        real_bwrap="/usr/bin/bwrap",
        bst_args=REAL_BWRAP_ARGV,
        bind_src="/tmp/host-trace-dir",
        bind_dst="/tmp/.bst-native-trace",
        preload_so="/tmp/.bst-native-trace/hook.so",
        trace_log="/tmp/.bst-native-trace/trace.log",
    )

    setenv_element_idx = next(
        i for i, tok in enumerate(argv) if tok == "--setenv" and argv[i + 1] == "BST_TRACE_ELEMENT"
    )
    assert argv[setenv_element_idx:setenv_element_idx + 3] == ["--setenv", "BST_TRACE_ELEMENT", "core.bst"]
    assert argv[setenv_element_idx + 3] == "sh"  # lands right before the trailing command, like the others


def test_build_shim_argv_omits_bst_trace_element_when_no_real_dir_present():
    """Element tagging is additive, never load-bearing - a bwrap
    invocation with no --dir option (defensive, forward-compatibility
    case) must still work, just without element attribution."""
    argv = build_shim_argv(
        real_bwrap="/usr/bin/bwrap",
        bst_args=["--unshare-pid", "sh", "-c", "true"],
        bind_src="/tmp/host-trace-dir",
        bind_dst="/tmp/.bst-native-trace",
        preload_so="/tmp/.bst-native-trace/hook.so",
        trace_log="/tmp/.bst-native-trace/trace.log",
    )

    assert "BST_TRACE_ELEMENT" not in argv


# --- jobserver fd injection (UX-679, a spike) ------------------------------

def test_build_shim_argv_omits_makeflags_when_no_jobserver_fd():
    """The flag's own promise: the FIFO is bound only when it is given."""
    argv = build_shim_argv(
        real_bwrap="/usr/bin/bwrap",
        bst_args=REAL_BWRAP_ARGV,
        bind_src="/tmp/host-trace-dir",
        bind_dst="/tmp/.bst-native-trace",
        preload_so="/tmp/.bst-native-trace/hook.so",
        trace_log="/tmp/.bst-native-trace/trace.log",
    )

    assert "MAKEFLAGS" not in argv


def test_build_shim_argv_injects_one_makeflags_setenv_naming_a_real_open_fd():
    """UX-843: the table applies only to a recognized kind - `"make"`
    here, since this test exercises the fd-injection mechanism itself,
    not which kind gets which env (see the per-kind cases below)."""
    read_fd, write_fd = os.pipe()
    try:
        argv = build_shim_argv(
            real_bwrap="/usr/bin/bwrap",
            bst_args=REAL_BWRAP_ARGV,
            bind_src="/tmp/host-trace-dir",
            bind_dst="/tmp/.bst-native-trace",
            preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log",
            jobserver_fd=read_fd,
            element_kind="make",
        )

        setenv_makeflags = [
            i for i, tok in enumerate(argv)
            if tok == "--setenv" and argv[i + 1] == "MAKEFLAGS"
        ]
        assert len(setenv_makeflags) == 1
        idx = setenv_makeflags[0]
        assert argv[idx:idx + 3] == [
            "--setenv", "MAKEFLAGS", f"--jobserver-auth={read_fd},{read_fd}",
        ]
        os.fstat(read_fd)  # the fd named is real and still open
    finally:
        os.close(read_fd)
        os.close(write_fd)


# --- pinned/joined/capped_pending decisions (UX-842) -----------------------

def _bwrap_argv_with_job_setenv(var, value):
    """REAL_BWRAP_ARGV, with its `--setenv JOBS -j4` triple replaced by
    `--setenv var value` - the argv-level fact a real `notparallel`
    element (`-j1`) or an element-level cap (any other `-jK`) is."""
    argv = list(REAL_BWRAP_ARGV)
    idx = argv.index("JOBS")
    argv[idx - 1:idx + 2] = ["--setenv", var, value]
    return argv


def test_a_pinned_elements_makeflags_j1_leaves_the_argv_unchanged():
    """`-j1` - the Motivation's `notparallel` pin - means the shim
    injects nothing for the jobserver mode at all: the argv with
    jobserver_fd given is byte for byte the argv without it."""
    pinned_argv = _bwrap_argv_with_job_setenv("MAKEFLAGS", "-j1")
    read_fd, write_fd = os.pipe()
    try:
        kwargs = dict(
            real_bwrap="/usr/bin/bwrap",
            bst_args=pinned_argv,
            bind_src="/tmp/host-trace-dir",
            bind_dst="/tmp/.bst-native-trace",
            preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log",
        )
        with_mode = build_shim_argv(jobserver_fd=read_fd, project_max_jobs=4, **kwargs)
        without_mode = build_shim_argv(**kwargs)

        assert with_mode == without_mode
        assert not any(tok.startswith("--jobserver-auth") for tok in with_mode)
        assert jobserver_decision(parse_element_max_jobs(split_bwrap_args(pinned_argv)[0]), 4) == JOBSERVER_PINNED
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_a_mesons_bare_integer_jobs_of_1_is_also_pinned():
    """UX-843: meson composes `JOBS` as a bare integer, not `-jN`
    (verified against installed `buildstream-plugins` 2.7.0: `bst show
    --format '%{env}'` on a `notparallel` meson element prints
    `JOBS: 1`). Before this shape was parsed, `parse_element_max_jobs`
    returned `None` for it, the decision was `joined`, and the auth was
    injected - the exact bug this row exists to close."""
    pinned_argv = _bwrap_argv_with_job_setenv("JOBS", "1")
    read_fd, write_fd = os.pipe()
    try:
        kwargs = dict(
            real_bwrap="/usr/bin/bwrap",
            bst_args=pinned_argv,
            bind_src="/tmp/host-trace-dir",
            bind_dst="/tmp/.bst-native-trace",
            preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log",
        )
        with_mode = build_shim_argv(jobserver_fd=read_fd, project_max_jobs=4, **kwargs)
        without_mode = build_shim_argv(**kwargs)

        assert with_mode == without_mode
        assert not any(tok.startswith("--jobserver-auth") for tok in with_mode)
        assert parse_element_max_jobs(split_bwrap_args(pinned_argv)[0]) == 1
        assert jobserver_decision(1, 4) == JOBSERVER_PINNED
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_an_element_at_the_projects_own_max_jobs_joins():
    """`-jK` equal to the project's own `max-jobs` (read once by the
    tracer from `bst show`) joins uncapped, exactly as today. `"make"`
    kind, for the same reason as the fd-injection test above."""
    argv = _bwrap_argv_with_job_setenv("JOBS", "-j8")
    read_fd, write_fd = os.pipe()
    try:
        result = build_shim_argv(
            real_bwrap="/usr/bin/bwrap",
            bst_args=argv,
            bind_src="/tmp/host-trace-dir",
            bind_dst="/tmp/.bst-native-trace",
            preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log",
            jobserver_fd=read_fd,
            project_max_jobs=8,
            element_kind="make",
        )

        setenv_makeflags = [i for i, tok in enumerate(result)
                            if tok == "--setenv" and result[i + 1] == "MAKEFLAGS"]
        assert len(setenv_makeflags) == 1
        assert jobserver_decision(8, 8) == JOBSERVER_JOINED
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_an_element_capped_above_the_project_default_records_capped_pending_and_joins():
    """`-jK` unequal to the project's `max-jobs` is an element-level
    cap; until `UX-849`'s proxy it joins uncapped and is recorded
    `capped_pending`, not `joined` - the two must stay distinguishable
    even though the injected argv is identical today. `"make"` kind,
    for the same reason as the fd-injection test above."""
    argv = _bwrap_argv_with_job_setenv("JOBS", "-j16")
    read_fd, write_fd = os.pipe()
    try:
        result = build_shim_argv(
            real_bwrap="/usr/bin/bwrap",
            bst_args=argv,
            bind_src="/tmp/host-trace-dir",
            bind_dst="/tmp/.bst-native-trace",
            preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log",
            jobserver_fd=read_fd,
            project_max_jobs=8,
            element_kind="make",
        )

        setenv_makeflags = [i for i, tok in enumerate(result)
                            if tok == "--setenv" and result[i + 1] == "MAKEFLAGS"]
        assert len(setenv_makeflags) == 1  # joins uncapped, same injection as `joined`
        assert jobserver_decision(16, 8) == JOBSERVER_CAPPED_PENDING
    finally:
        os.close(read_fd)
        os.close(write_fd)


# --- the per-kind environment table (UX-843) -------------------------------

def _job_env_ops(argv):
    """The job-related `--setenv`/`--unsetenv` ops this shim injected,
    in order - scanned from after `LD_PRELOAD` (the first thing this
    shim itself adds) so REAL_BWRAP_ARGV's own pre-existing `--setenv
    JOBS -j4` (BuildStream's, untouched) is never mistaken for one."""
    names = ("MAKEFLAGS", "JOBS", "CARGO_BUILD_JOBS")
    start = argv.index("LD_PRELOAD")
    argv = argv[start:]
    ops, i = [], 0
    while i < len(argv):
        if argv[i] == "--setenv" and argv[i + 1] in names:
            ops.append(("--setenv", argv[i + 1], argv[i + 2]))
            i += 3
        elif argv[i] == "--unsetenv" and argv[i + 1] in names:
            ops.append(("--unsetenv", argv[i + 1]))
            i += 2
        else:
            i += 1
    return ops


def _build_with_kind(kind, bst_args=None, **extra):
    """REAL_BWRAP_ARGV (`-j4`), a real fd, `project_max_jobs=4` (joined -
    the table applies) - the one input this whole section varies is the
    element's own kind and, for cmake/meson, the ninja probe. `bst_args`
    overrides the fixture argv (UX-859: a table-less kind's policy turns
    on whether `JOBS` is in it)."""
    read_fd, write_fd = os.pipe()
    try:
        return build_shim_argv(
            real_bwrap="/usr/bin/bwrap",
            bst_args=bst_args if bst_args is not None else REAL_BWRAP_ARGV,
            bind_src="/tmp/host-trace-dir",
            bind_dst="/tmp/.bst-native-trace",
            preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log",
            jobserver_fd=read_fd,
            project_max_jobs=4,
            element_kind=kind,
            **extra,
        ), read_fd
    finally:
        os.close(write_fd)


def _argv_without_jobs():
    """REAL_BWRAP_ARGV with its own `--setenv JOBS -j4` triple removed -
    UX-859: a table-less kind with no `JOBS` at all stays `unknown_kind`."""
    argv = list(REAL_BWRAP_ARGV)
    i = argv.index("JOBS")
    del argv[i - 1:i + 2]
    return argv


def _argv_with_jobs(value):
    """REAL_BWRAP_ARGV with its own `--setenv JOBS` value swapped - a
    value distinct from the cmake/meson fixtures' `-j4` so a passing
    assertion proves the read, not a coincidence of the shared fixture."""
    argv = list(REAL_BWRAP_ARGV)
    argv[argv.index("JOBS") + 1] = value
    return argv


def test_make_and_autotools_get_makeflags_auth_only():
    for kind in ("make", "autotools"):
        argv, read_fd = _build_with_kind(kind)
        try:
            assert _job_env_ops(argv) == [
                ("--setenv", "MAKEFLAGS", f"--jobserver-auth={read_fd},{read_fd}")]
        finally:
            os.close(read_fd)


def test_cmake_and_meson_get_jobs_emptied_and_makeflags_auth():
    for kind in ("cmake", "meson"):
        argv, read_fd = _build_with_kind(kind)
        try:
            assert _job_env_ops(argv) == [
                ("--setenv", "JOBS", ""),
                ("--setenv", "MAKEFLAGS", f"--jobserver-auth={read_fd},{read_fd}")]
        finally:
            os.close(read_fd)


def test_cargo_unsets_cargo_build_jobs_and_carries_the_auth_in_makeflags():
    argv, read_fd = _build_with_kind("cargo")
    try:
        assert _job_env_ops(argv) == [
            ("--setenv", "MAKEFLAGS", f"--jobserver-auth={read_fd},{read_fd}"),
            ("--unsetenv", "CARGO_BUILD_JOBS")]
    finally:
        os.close(read_fd)


def test_an_unknown_kind_with_no_jobs_gets_no_injection():
    for kind in ("manual", "script", "import", "some-custom-plugin"):
        argv, read_fd = _build_with_kind(kind, bst_args=_argv_without_jobs())
        try:
            assert _job_env_ops(argv) == []
            assert kind_job_env(kind, "AUTH")[2] == JOBSERVER_UNKNOWN_KIND
        finally:
            os.close(read_fd)


def test_an_element_absent_from_the_map_gets_no_injection():
    """`element_kind=None` - what `_element_kind_env` returns for an
    element the map does not name, same as no map at all."""
    argv, read_fd = _build_with_kind(None, bst_args=_argv_without_jobs())
    try:
        assert _job_env_ops(argv) == []
        assert kind_job_env(None, "AUTH")[2] == JOBSERVER_UNKNOWN_KIND
    finally:
        os.close(read_fd)


def test_a_junctioned_elements_kind_resolves_through_the_real_env_map(
        tmp_path, monkeypatch):
    """UX-871: the map is the tracer's own `_parse_element_kinds`
    output, written to disk the way the tracer writes `element_kinds.json`
    - the shim's `_element_kind_env` still does the exact lookup
    (UX-843), but the element it looks up, `element_from_build_root`'s
    project-relative name, is now a key the junctioned map carries too."""
    from tools.bst_native_build_tracer import _parse_element_kinds

    kinds = _parse_element_kinds(
        "sdk.bst:foo/bar.bst cmake\nplain.bst autotools\n"
        "a.bst:b.bst:deep.bst meson\n")
    kinds_path = tmp_path / "element_kinds.json"
    kinds_path.write_text(json.dumps(kinds))
    monkeypatch.setenv("BST_TRACE_ELEMENT_KINDS", str(kinds_path))

    element = element_from_build_root("buildstream/proj/foo/bar.bst")
    assert element == "foo/bar.bst"
    assert _element_kind_env(element) == "cmake"
    assert _element_kind_env("plain.bst") == "autotools"
    assert _element_kind_env("deep.bst") == "meson"


def test_a_table_less_kind_that_spends_jobs_gets_the_jobs_env_policy():
    """UX-859: a manual-kind recipe calling `cmake --build … ${JOBS}` by
    hand carries `JOBS` in its own sandbox env just like a cmake
    element's does - through `build_shim_argv`'s real argv path, not
    `kind_job_env` called alone."""
    argv, read_fd = _build_with_kind("manual", bst_args=_argv_with_jobs("-j8"))
    try:
        assert _job_env_ops(argv) == [
            ("--setenv", "JOBS", ""),
            ("--setenv", "MAKEFLAGS", f"--jobserver-auth={read_fd},{read_fd}")]
        assert kind_job_env("manual", "AUTH", jobs_present=True)[2] == "jobs_env"
    finally:
        os.close(read_fd)


def test_a_table_less_kind_with_no_jobs_stays_unknown_kind():
    argv, read_fd = _build_with_kind("manual", bst_args=_argv_without_jobs())
    try:
        assert _job_env_ops(argv) == []
        assert kind_job_env("manual", "AUTH", jobs_present=False)[2] == \
            JOBSERVER_UNKNOWN_KIND
    finally:
        os.close(read_fd)


def test_a_table_kind_is_unaffected_by_jobs_present():
    """cmake is already in the table - `jobs_present` never reaches its
    branch, so its own policy and injection are unchanged (UX-843)."""
    argv, read_fd = _build_with_kind("cmake", bst_args=_argv_with_jobs("-j8"))
    try:
        assert _job_env_ops(argv) == [
            ("--setenv", "JOBS", ""),
            ("--setenv", "MAKEFLAGS", f"--jobserver-auth={read_fd},{read_fd}")]
        assert kind_job_env("cmake", "AUTH", jobs_present=True)[2] == "cmake_meson"
    finally:
        os.close(read_fd)


def test_cmake_ninja_with_a_jobserver_client_passes_the_auth_through():
    probe = {"available": True, "version": "1.12.0", "jobserver_client": True}
    argv, read_fd = _build_with_kind("cmake", ninja_probe=probe)
    try:
        assert _job_env_ops(argv) == [
            ("--setenv", "JOBS", ""),
            ("--setenv", "MAKEFLAGS", f"--jobserver-auth={read_fd},{read_fd}")]
    finally:
        os.close(read_fd)


def test_ninja_without_a_client_and_no_wrapper_dir_is_static_and_untouched():
    """`ninja_static`: JOBS is neither emptied nor overwritten - the
    element's own `-jN` (BuildStream's own, already in REAL_BWRAP_ARGV)
    is the pre-mode behaviour, and no oversubscription beyond it."""
    probe = {"available": True, "version": "1.11.1", "jobserver_client": False}
    argv, read_fd = _build_with_kind("meson", ninja_probe=probe)
    try:
        assert _job_env_ops(argv) == []
        assert argv.count("JOBS") == 1  # BuildStream's own, unmodified
        idx = argv.index("JOBS")
        assert argv[idx - 1:idx + 1] == ["--setenv", "JOBS"]
        assert argv[idx + 1] == "-j4"
    finally:
        os.close(read_fd)


def test_ninja_without_a_client_and_a_wrapper_dir_empties_jobs_and_mounts_the_wrappers():
    """UX-843 + UX-846: the wrapper reads the auth from MAKEFLAGS, so
    JOBS is emptied, the auth stays, and the wrapper directory is bound
    ahead of BuildStream's own PATH."""
    probe = {"available": True, "version": "1.11.1", "jobserver_client": False}
    argv, read_fd = _build_with_kind(
        "cmake", ninja_probe=probe, wrapper_dir="/host/wrappers")
    try:
        ops = _job_env_ops(argv)
        assert ops[0] == ("--setenv", "JOBS", "")
        assert ops[1][:2] == ("--setenv", "MAKEFLAGS") and "--jobserver-auth=" in ops[1][2]
        assert argv[argv.index("--ro-bind") + 1:argv.index("--ro-bind") + 3] == [
            "/host/wrappers", "/tmp/.bst-native-trace/wrappers"]
    finally:
        os.close(read_fd)


def _path_setenv(argv):
    """The last `--setenv PATH` value in argv - the one bwrap keeps."""
    values = [argv[i + 2] for i, a in enumerate(argv) if a == "--setenv" and argv[i + 1] == "PATH"]
    return values[-1] if values else None


def test_the_wrapper_path_is_prepended_to_buildstreams_own():
    """UX-846's verifier: the sandbox PATH BuildStream composed survives
    behind the wrapper directory, and the cap rides along."""
    argv, read_fd = _build_with_kind("make", wrapper_dir="/host/wrappers", wrapper_cap="3")
    try:
        bst_path = [REAL_BWRAP_ARGV[i + 2] for i, a in enumerate(REAL_BWRAP_ARGV)
                    if a == "--setenv" and REAL_BWRAP_ARGV[i + 1] == "PATH"]
        assert bst_path, "the fixture argv carries BuildStream's own PATH"
        assert _path_setenv(argv) == "/tmp/.bst-native-trace/wrappers:" + bst_path[-1]
        assert argv[argv.index("BST_TRACE_WRAPPER_CAP") + 1] == "3"
    finally:
        os.close(read_fd)


def test_no_path_from_buildstream_falls_back_to_the_system_one():
    stripped = [a for i, a in enumerate(REAL_BWRAP_ARGV)
                if not (a == "--setenv" and REAL_BWRAP_ARGV[i + 1] == "PATH")
                and not (i >= 1 and REAL_BWRAP_ARGV[i - 1] == "--setenv" and a == "PATH")
                and not (i >= 2 and REAL_BWRAP_ARGV[i - 2] == "--setenv" and REAL_BWRAP_ARGV[i - 1] == "PATH")]
    read_fd, write_fd = os.pipe()
    try:
        argv = build_shim_argv(
            real_bwrap="/usr/bin/bwrap", bst_args=stripped, bind_src="/tmp/host-trace-dir",
            bind_dst="/tmp/.bst-native-trace", preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log", jobserver_fd=read_fd,
            project_max_jobs=4, element_kind="make", wrapper_dir="/host/wrappers")
        assert _path_setenv(argv) == "/tmp/.bst-native-trace/wrappers:/usr/bin:/bin"
    finally:
        os.close(write_fd)
        os.close(read_fd)


def test_a_pinned_element_mounts_no_wrappers():
    read_fd, write_fd = os.pipe()
    try:
        pinned = [("-j1" if a == "-j4" else a) for a in REAL_BWRAP_ARGV]
        argv = build_shim_argv(
            real_bwrap="/usr/bin/bwrap", bst_args=pinned, bind_src="/tmp/host-trace-dir",
            bind_dst="/tmp/.bst-native-trace", preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log", jobserver_fd=read_fd,
            project_max_jobs=4, element_kind="make", wrapper_dir="/host/wrappers")
        assert "--ro-bind" not in argv and _path_setenv(argv) is None or "/tmp/.bst-native-trace/wrappers" not in (_path_setenv(argv) or "")
    finally:
        os.close(write_fd)
        os.close(read_fd)


# --- mutations (UX-843: falsify) -------------------------------------------

def test_dropping_the_cargo_row_is_caught_by_the_exact_set_assertion():
    """What `--mutate: drop the cargo row` looks like from the test
    side - documented so the mutation table's claim is checked against
    real code, not asserted from memory."""
    pairs, unsets, policy = kind_job_env("cargo", "AUTH")
    assert pairs == [("MAKEFLAGS", "AUTH")]
    assert unsets == ["CARGO_BUILD_JOBS"]
    assert policy == "cargo"


# --- the ninja probe parser (UX-843) ----------------------------------------

# Real, pasted: `ninja --help` on this box, ninja 1.11.1 - no jobserver
# mention at all.
_NINJA_1_11_1_HELP = """usage: ninja [options] [targets...]

if targets are unspecified, builds the 'default' target (see manual).

options:
  --version      print ninja version ("1.11.1")
  -v, --verbose  show all command lines while building
  --quiet        don't show progress status, just command output

  -C DIR   change to DIR before doing anything else
  -f FILE  specify input build file [default=build.ninja]

  -j N     run N jobs in parallel (0 means infinity) [default=6 on this system]
  -k N     keep going until N jobs fail (0 means infinity) [default=1]
  -l N     do not start new jobs if the load average is greater than N
  -n       dry run (don't run commands but act like they succeeded)

  -d MODE  enable debugging (use '-d list' to list modes)
  -t TOOL  run a subtool (use '-t list' to list subtools)
    terminates toplevel options; further flags are passed to the tool
  -w FLAG  adjust warnings (use '-w list' to list warnings)
"""

_NINJA_SYNTHETIC_HELP_WITH_CLIENT = _NINJA_1_11_1_HELP + (
    "  --jobserver     participate in a POSIX jobserver, if one is "
    "available via MAKEFLAGS\n")


def test_ninja_1_11_1s_real_help_names_no_jobserver_client():
    assert parse_ninja_help(_NINJA_1_11_1_HELP) is False


def test_a_help_naming_jobserver_is_read_as_a_client():
    assert parse_ninja_help(_NINJA_SYNTHETIC_HELP_WITH_CLIENT) is True


# --- UX-849's proxy: the same auth style as the global FIFO ---------------
#
# The coordinator's fix: a proxy always used `fifo:` regardless of the
# host's own `make --version` - GNU Make 4.3 (this box, CI's runner)
# rejects that string outright (`internal error: invalid --jobserver-auth
# string`, measured live). `_resolve_proxy_auth` reads the same
# `BST_TRACE_JOBSERVER_AUTH` the global FIFO already resolved from.

def test_a_proxy_under_fd_style_opens_its_own_fd_and_binds_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH", "fd")
    fifo = str(tmp_path / "mod-a.bst.fifo")
    os.mkfifo(fifo)
    proxy_fd, proxy_fifo = _resolve_proxy_auth(fifo)
    try:
        assert proxy_fifo is None
        assert proxy_fd is not None
        os.fstat(proxy_fd)  # a real, open fd
        argv = build_shim_argv(
            real_bwrap="/usr/bin/bwrap", bst_args=REAL_BWRAP_ARGV,
            bind_src="/tmp/host-trace-dir", bind_dst="/tmp/.bst-native-trace",
            preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log",
            project_max_jobs=4, element_kind="make",
            proxy_fd=proxy_fd, proxy_fifo=proxy_fifo)
        assert _job_env_ops(argv) == [
            ("--setenv", "MAKEFLAGS", f"--jobserver-auth={proxy_fd},{proxy_fd}")]
        assert fifo not in argv, "fd style binds nothing - the fd travels through exec"
    finally:
        os.close(proxy_fd)


def test_a_proxy_under_fifo_style_names_the_bind_dst_path_with_no_bind_of_its_own(
        tmp_path, monkeypatch):
    """UX-869: the proxy dir (`bind_src/proxies`) already lives inside
    the whole-tree bind at `bind_dst` - a second `--bind` of the FIFO
    onto its own host path failed on a read-only sandbox root whenever
    the project was not under `/tmp`."""
    monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH", "fifo")
    bind_src = str(tmp_path / "host-trace-dir")
    os.makedirs(os.path.join(bind_src, "proxies"))
    fifo = os.path.join(bind_src, "proxies", "mod-a.bst.fifo")
    os.mkfifo(fifo)
    proxy_fd, proxy_fifo = _resolve_proxy_auth(fifo)
    assert proxy_fd is None
    assert proxy_fifo == fifo
    argv = build_shim_argv(
        real_bwrap="/usr/bin/bwrap", bst_args=REAL_BWRAP_ARGV,
        bind_src=bind_src, bind_dst="/tmp/.bst-native-trace",
        preload_so="/tmp/.bst-native-trace/hook.so",
        trace_log="/tmp/.bst-native-trace/trace.log",
        project_max_jobs=4, element_kind="make",
        proxy_fd=proxy_fd, proxy_fifo=proxy_fifo)
    assert _job_env_ops(argv) == [
        ("--setenv", "MAKEFLAGS",
         "--jobserver-auth=fifo:/tmp/.bst-native-trace/proxies/mod-a.bst.fifo")]
    assert fifo not in argv
    assert "--bind" not in argv[argv.index("MAKEFLAGS"):]


def test_no_proxy_leaves_build_shim_argv_byte_for_byte():
    """No `BST_TRACE_JOBSERVER_AUTH` set at all (`_resolve_proxy_auth`
    never called - no `BST_TRACE_PROXY_DIR`, `main`'s own gate) - the
    default `proxy_fd`/`proxy_fifo` both `None` change nothing."""
    read_fd, write_fd = os.pipe()
    try:
        kwargs = dict(
            real_bwrap="/usr/bin/bwrap", bst_args=REAL_BWRAP_ARGV,
            bind_src="/tmp/host-trace-dir", bind_dst="/tmp/.bst-native-trace",
            preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log",
            jobserver_fd=read_fd, project_max_jobs=4, element_kind="make",
        )
        assert build_shim_argv(**kwargs) == build_shim_argv(
            proxy_fd=None, proxy_fifo=None, **kwargs)
    finally:
        os.close(read_fd)
        os.close(write_fd)


# --- UX-869: a real read-only sandbox root refuses a bind outside the
# trace mount - a fake `bwrap` on `PATH`, built on UX-855's
# `_fake_real_bwrap`, that behaves the way the real one did on the user's
# report (`Can't mkdir parents for <dst>: Read-only file system`).

def _fake_readonly_root_bwrap(path, marker, bind_dst):
    """Refuses any `--bind`/`--ro-bind`/`--dev-bind` whose destination is
    not under `bind_dst` or `/tmp` - real bwrap's own read-only-root
    refusal, reproduced without a real sandbox."""
    body = (
        'while [ $# -gt 0 ]; do\n'
        '  case "$1" in\n'
        '    --bind|--ro-bind|--dev-bind)\n'
        '      dst="$3"\n'
        '      case "$dst" in\n'
        f'        {bind_dst}|{bind_dst}/*|/tmp|/tmp/*) ;;\n'
        '        *) echo "bwrap: Can'"'"'t mkdir parents for $dst: '
        'Read-only file system" >&2; exit 1 ;;\n'
        '      esac\n'
        '      shift 3\n'
        '      ;;\n'
        '    *) shift ;;\n'
        '  esac\n'
        'done\n'
        'exit 0\n'
    )
    return _fake_real_bwrap(path, marker, body)


def _run_argv_through(fake_bwrap, argv, tmp_path):
    """Runs the composed argv's own tail (everything after the
    `real_bwrap` element `build_shim_argv` returns) through `fake_bwrap`,
    with it on `PATH` under its real name so it is found the way a
    shadowed real `bwrap` is."""
    on_path = tmp_path / "on-path"
    on_path.mkdir(exist_ok=True)
    bwrap_on_path = on_path / "bwrap"
    if not bwrap_on_path.exists():
        bwrap_on_path.symlink_to(fake_bwrap)
    env = {**os.environ, "PATH": f"{on_path}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run(["bwrap", *argv[1:]], env=env,
                          capture_output=True, text=True, check=False)


def test_fifo_style_runs_clean_through_a_bwrap_that_refuses_binds_outside_bind_dst_or_tmp(
        tmp_path):
    """The bind dir sits under a fake project path, not `/tmp` - the
    user's report. No FIFO `--bind` of its own means the composed argv
    holds no destination outside `bind_dst`/`/tmp`, and the fake refuses
    nothing."""
    marker = tmp_path / "marker"
    bind_dst = "/tmp/.bst-native-trace"
    fake = _fake_readonly_root_bwrap(tmp_path / "real-bwrap", marker, bind_dst)
    bind_src = "/not/tmp/my_project/.bga/tmp/trace-1/bind"

    argv = build_shim_argv(
        real_bwrap=fake,
        bst_args=["--unshare-pid", "--dir", "core.bst", "--chdir", "core.bst",
                 "sh", "-c", "make"],
        bind_src=bind_src, bind_dst=bind_dst,
        preload_so=f"{bind_dst}/hook.so", trace_log=f"{bind_dst}/trace.log",
        jobserver_fifo=f"{bind_src}/jobserver", element_kind="make")

    result = _run_argv_through(fake, argv, tmp_path)

    assert result.returncode == 0, result.stderr
    setenv = argv.index("MAKEFLAGS")
    assert argv[setenv + 1] == f"--jobserver-auth=fifo:{bind_dst}/jobserver"


def test_fd_style_still_runs_clean_through_the_same_bwrap(tmp_path):
    marker = tmp_path / "marker"
    bind_dst = "/tmp/.bst-native-trace"
    fake = _fake_readonly_root_bwrap(tmp_path / "real-bwrap", marker, bind_dst)
    bind_src = "/not/tmp/my_project/.bga/tmp/trace-1/bind"

    read_fd, write_fd = os.pipe()
    try:
        argv = build_shim_argv(
            real_bwrap=fake,
            bst_args=["--unshare-pid", "--dir", "core.bst", "--chdir", "core.bst",
                     "sh", "-c", "make"],
            bind_src=bind_src, bind_dst=bind_dst,
            preload_so=f"{bind_dst}/hook.so", trace_log=f"{bind_dst}/trace.log",
            jobserver_fd=read_fd, element_kind="make")

        result = _run_argv_through(fake, argv, tmp_path)

        assert result.returncode == 0, result.stderr
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_a_fifo_bound_onto_its_own_host_path_reds_under_the_same_bwrap(tmp_path):
    """The mutation `falsify` checks: restoring `--bind <fifo> <fifo>`
    (the defect) makes the fake refuse it exactly as the user's real
    sandbox root did."""
    marker = tmp_path / "marker"
    bind_dst = "/tmp/.bst-native-trace"
    fake = _fake_readonly_root_bwrap(tmp_path / "real-bwrap", marker, bind_dst)
    bind_src = "/not/tmp/my_project/.bga/tmp/trace-1/bind"
    fifo_path = f"{bind_src}/jobserver"

    argv = build_shim_argv(
        real_bwrap=fake,
        bst_args=["--unshare-pid", "--dir", "core.bst", "--chdir", "core.bst",
                 "sh", "-c", "make"],
        bind_src=bind_src, bind_dst=bind_dst,
        preload_so=f"{bind_dst}/hook.so", trace_log=f"{bind_dst}/trace.log",
        jobserver_fifo=fifo_path, element_kind="make")
    # The mutation itself: re-inject the own-path bind `_jobserver_injection`
    # used to add, right where it used to land - before the MAKEFLAGS setenv.
    setenv = argv.index("MAKEFLAGS") - 2  # the "--setenv" token before it
    mutated = argv[:setenv] + ["--bind", fifo_path, fifo_path] + argv[setenv:]

    result = _run_argv_through(fake, mutated, tmp_path)

    assert result.returncode == 1
    assert "Read-only file system" in result.stderr


# --- UX-874: the jobserver auth style follows the make that consumes it --
#
# `_fake_bwrap_with_make` extends `_fake_readonly_root_bwrap`'s own
# read-only-root refusal with a `make --version` case ahead of it - one
# fake `real_bwrap` serves both UX-874's sandbox-make probe and the
# final composed argv's own real run, the way one real sandbox's make is
# probed and then actually invoked.

def _fake_bwrap_with_make(path, marker, bind_dst, version):
    body = (
        'case "$*" in\n'
        f'  *"make --version") printf "GNU Make {version}\\n"; exit 0 ;;\n'
        'esac\n'
        'while [ $# -gt 0 ]; do\n'
        '  case "$1" in\n'
        '    --bind|--ro-bind|--dev-bind)\n'
        '      dst="$3"\n'
        '      case "$dst" in\n'
        f'        {bind_dst}|{bind_dst}/*|/tmp|/tmp/*) ;;\n'
        '        *) echo "bwrap: Can'"'"'t mkdir parents for $dst: '
        'Read-only file system" >&2; exit 1 ;;\n'
        '      esac\n'
        '      shift 3\n'
        '      ;;\n'
        '    *) shift ;;\n'
        '  esac\n'
        'done\n'
        'exit 0\n'
    )
    return _fake_real_bwrap(path, marker, body)


def test_fifo_style_downgrades_to_fd_when_the_sandbox_make_is_4_3(tmp_path):
    """Motivation, pasted live: GNU Make 4.3 rejects `fifo:` outright
    (`internal error: invalid --jobserver-auth string`) - `fifo:/tmp/
    .bst-native-trace/jobserver` would kill this element's build. The
    shim probes this element's own sandbox make, finds 4.3, and opens
    the fd fallback instead - a real, open, inheritable fd threaded
    through `--jobserver-auth=<fd>,<fd>`, not the string."""
    bind_dst = "/tmp/.bst-native-trace"
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 bind_dst, "4.3")
    bind_src = str(tmp_path / "host-trace-dir")
    os.makedirs(bind_src)
    fifo_path = os.path.join(bind_src, "jobserver")
    os.mkfifo(fifo_path)

    pool = _downgrade_fifo_to_fd_if_sandbox_make_rejects_it(
        {"element_kind": "make", "real_bwrap": fake, "opts": []},
        str(tmp_path / "make_probe.json"),
        pool={"fd": None, "fifo": fifo_path, "proxy_fd": None, "proxy_fifo": None})
    try:
        assert pool["fifo"] is None
        assert pool["fd"] is not None
        os.fstat(pool["fd"])  # a real, open fd

        argv = build_shim_argv(
            real_bwrap=fake,
            bst_args=["--unshare-pid", "--dir", "core.bst", "--chdir", "core.bst",
                     "sh", "-c", "make"],
            bind_src=bind_src, bind_dst=bind_dst,
            preload_so=f"{bind_dst}/hook.so", trace_log=f"{bind_dst}/trace.log",
            jobserver_fd=pool["fd"], jobserver_fifo=pool["fifo"], element_kind="make")

        setenv = argv.index("MAKEFLAGS")
        assert argv[setenv + 1] == f"--jobserver-auth={pool['fd']},{pool['fd']}"
        assert "fifo:" not in argv[setenv + 1]

        result = _run_argv_through(fake, argv, tmp_path)

        assert result.returncode == 0, result.stderr
    finally:
        os.close(pool["fd"])


def test_fifo_style_stands_when_the_sandbox_make_is_4_4(tmp_path):
    """The other side of the same cutoff: a sandbox make new enough to
    parse `fifo:` gets it unchanged - the probe narrows, never widens."""
    bind_dst = "/tmp/.bst-native-trace"
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 bind_dst, "4.4")
    bind_src = str(tmp_path / "host-trace-dir")
    os.makedirs(bind_src)
    fifo_path = os.path.join(bind_src, "jobserver")
    os.mkfifo(fifo_path)

    pool = _downgrade_fifo_to_fd_if_sandbox_make_rejects_it(
        {"element_kind": "make", "real_bwrap": fake, "opts": []},
        str(tmp_path / "make_probe.json"),
        pool={"fd": None, "fifo": fifo_path, "proxy_fd": None, "proxy_fifo": None})

    assert pool["fd"] is None
    assert pool["fifo"] == fifo_path

    argv = build_shim_argv(
        real_bwrap=fake,
        bst_args=["--unshare-pid", "--dir", "core.bst", "--chdir", "core.bst",
                 "sh", "-c", "make"],
        bind_src=bind_src, bind_dst=bind_dst,
        preload_so=f"{bind_dst}/hook.so", trace_log=f"{bind_dst}/trace.log",
        jobserver_fifo=pool["fifo"], element_kind="make")

    setenv = argv.index("MAKEFLAGS")
    assert argv[setenv + 1] == f"--jobserver-auth=fifo:{bind_dst}/jobserver"

    result = _run_argv_through(fake, argv, tmp_path)

    assert result.returncode == 0, result.stderr


def test_the_proxy_follows_the_same_downgrade_as_the_global_fifo(tmp_path):
    """`UX-849`'s per-element proxy is consumed by the same sandbox make
    as the global FIFO - the downgrade has to apply to both."""
    bind_dst = "/tmp/.bst-native-trace"
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 bind_dst, "4.3")
    proxy_fifo_path = str(tmp_path / "proxy.fifo")
    os.mkfifo(proxy_fifo_path)

    pool = _downgrade_fifo_to_fd_if_sandbox_make_rejects_it(
        {"element_kind": "make", "real_bwrap": fake, "opts": []},
        str(tmp_path / "make_probe.json"),
        pool={"fd": None, "fifo": None, "proxy_fd": None, "proxy_fifo": proxy_fifo_path})

    try:
        assert pool["proxy_fifo"] is None
        assert pool["proxy_fd"] is not None
        os.fstat(pool["proxy_fd"])
    finally:
        os.close(pool["proxy_fd"])


def test_a_kind_with_no_makeflags_is_never_probed_and_never_narrowed(tmp_path):
    """`unknown_kind` never gets a `MAKEFLAGS` from `kind_job_env` - the
    fake's marker (written on every invocation) never appears, so the
    probe never ran."""
    marker = tmp_path / "marker"
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", marker,
                                 "/tmp/.bst-native-trace", "4.3")

    style = sandbox_make_auth_style("unknown_kind", fake, [],
                                    str(tmp_path / "make_probe.json"))

    assert style == "fifo"
    assert not marker.exists()


def test_ninja_static_is_never_probed_and_never_narrowed(tmp_path):
    """UX-877: a cmake element whose sandbox has an available, non-client
    ninja gets `ninja_static` - `[]` pairs, no `MAKEFLAGS` at all, so the
    probe never runs."""
    marker = tmp_path / "marker"
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", marker,
                                 "/tmp/.bst-native-trace", "4.3")
    ninja_probe = {"available": True, "jobserver_client": False}

    style = sandbox_make_auth_style("cmake", fake, [], str(tmp_path / "make_probe.json"),
                                    kind_probe={"ninja_probe": ninja_probe})

    assert style == "fifo"
    assert not marker.exists()


def test_cmake_on_the_makefiles_path_is_now_narrowed(tmp_path):
    """UX-877: `cmake --build ... -- ${JOBS}` invokes the sandbox make
    directly when there is no jobserver-client ninja to hand `MAKEFLAGS`
    to instead - the exact defect UX-874 was meant to stop, skipped
    because `cmake` was outside `_MAKE_LIKE_KINDS`."""
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 "/tmp/.bst-native-trace", "4.3")

    style = sandbox_make_auth_style("cmake", fake, [], str(tmp_path / "make_probe.json"))

    assert style == "fd"


def test_a_jobs_env_kind_is_now_narrowed(tmp_path):
    """UX-877: a table-less kind carrying its own `JOBS` gets the same
    `cmake_meson`-shaped injection (policy `jobs_env`) and so the same
    narrowing."""
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 "/tmp/.bst-native-trace", "4.3")

    style = sandbox_make_auth_style("manual", fake, [], str(tmp_path / "make_probe.json"),
                                    kind_probe={"jobs_present": True})

    assert style == "fd"


def test_a_cmake_element_resolving_to_a_jobserver_client_ninja_is_unnarrowed(tmp_path):
    """UX-877: a jobserver-client ninja reads `MAKEFLAGS` itself, not a
    make - ninja accepts the `fifo:` path, so this case stays unnarrowed
    even though `kind_job_env` does inject `MAKEFLAGS` for it."""
    marker = tmp_path / "marker"
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", marker,
                                 "/tmp/.bst-native-trace", "4.3")
    ninja_probe = {"available": True, "jobserver_client": True}

    style = sandbox_make_auth_style("cmake", fake, [], str(tmp_path / "make_probe.json"),
                                    kind_probe={"ninja_probe": ninja_probe})

    assert style == "fifo"
    assert not marker.exists()


def test_a_second_probe_make_call_is_served_from_the_cache_without_rerunning(tmp_path):
    marker = tmp_path / "marker"
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", marker,
                                 "/tmp/.bst-native-trace", "4.3")
    cache_path = str(tmp_path / "make_probe.json")

    first = probe_make(fake, [], cache_path)
    second = probe_make(fake, [], cache_path)

    assert first == second == {"available": True, "version": "GNU Make 4.3"}
    assert marker.read_text().splitlines() == ["run"]


def test_style_for_make_version_shares_the_4_4_cutoff_with_jobserver_auth_style():
    """`jobserver_auth_style`'s own host-probe values (UX-841), read
    through the shared function rather than a second regex/tuple."""
    assert style_for_make_version("GNU Make 4.4\n") == "fifo"
    assert style_for_make_version("GNU Make 4.3\n") == "fd"
    assert style_for_make_version("GNU Make 5.0\n") == "fifo"
    assert style_for_make_version("") == "fd"
    assert style_for_make_version(None) == "fd"
    assert style_for_make_version("not a version string") == "fd"


def test_make_probe_cache_path_is_keyed_per_element():
    """`_make_probe_cache_path` (verifier): two elements share
    `dirname(BST_TRACE_JOBSERVER)` but must not share a probe file -
    `ninja_probe.json`'s own per-capture sharing is wrong for a make
    that can genuinely differ element to element."""
    jobserver_path = "/tmp/.bst-native-trace/jobserver"

    cache_a = _make_probe_cache_path(jobserver_path, "mod-a.bst")
    cache_b = _make_probe_cache_path(jobserver_path, "mod-b.bst")

    assert cache_a != cache_b
    assert os.path.dirname(cache_a) == os.path.dirname(cache_b) == "/tmp/.bst-native-trace"
    assert _make_probe_cache_path(None, "mod-a.bst") is None


def test_two_make_kind_elements_in_one_capture_each_probe_their_own_sandbox_make(
        tmp_path):
    """UX-874 (verifier): the junctioned/toolchain shape - two make-kind
    elements in one capture whose own tar-staged makes genuinely differ
    (4.4 and 4.3) must each get their own style, not the first
    element's cached answer."""
    jobserver_path = str(tmp_path / "jobserver")
    fake_new = _fake_bwrap_with_make(tmp_path / "bwrap-new", tmp_path / "marker-new",
                                     "/tmp/.bst-native-trace", "4.4")
    fake_old = _fake_bwrap_with_make(tmp_path / "bwrap-old", tmp_path / "marker-old",
                                     "/tmp/.bst-native-trace", "4.3")

    cache_a = _make_probe_cache_path(jobserver_path, "mod-a.bst")
    cache_b = _make_probe_cache_path(jobserver_path, "mod-b.bst")

    style_a = sandbox_make_auth_style("make", fake_new, [], cache_a)
    style_b = sandbox_make_auth_style("make", fake_old, [], cache_b)

    assert style_a == "fifo"
    assert style_b == "fd"


# --- UX-855: probe_ninja's own outcomes, not a hand-built dict ------------
#
# `real_bwrap` is a shell script in tmp_path, passed straight through as
# the `real_bwrap` argument - never placed on PATH. It looks at its own
# trailing args to tell `ninja --version` from `ninja --help`.

def _fake_real_bwrap(path, marker, body):
    """Appends one line to `marker` per invocation, so the cache case can
    count how many times the fake actually ran."""
    path.write_text(f'#!/bin/sh\necho run >> "{marker}"\n{body}')
    path.chmod(0o755)
    return str(path)


def test_probe_ninja_records_availability_version_and_a_jobserver_client(tmp_path):
    marker = tmp_path / "marker"
    fake = _fake_real_bwrap(
        tmp_path / "bwrap", marker,
        'case "$*" in\n'
        '  *"ninja --version") echo "1.12.0" ;;\n'
        '  *"ninja --help") printf '
        "'usage: ninja\\n  --jobserver   participate in a POSIX jobserver\\n' ;;\n"
        "esac\n")

    result = probe_ninja(fake, [], str(tmp_path / "cache-a.json"))

    assert result == {"available": True, "version": "1.12.0", "jobserver_client": True}
    assert marker.read_text().splitlines() == ["run", "run"]


def test_probe_ninja_reads_a_help_text_that_names_no_jobserver_as_no_client(tmp_path):
    """The verifier's case: ninja 1.11.1's own help never says jobserver,
    and the probe must say so rather than assume a client."""
    marker = tmp_path / "marker"
    fake = _fake_real_bwrap(
        tmp_path / "bwrap", marker,
        'case "$*" in\n'
        '  *"ninja --version") echo "1.11.1" ;;\n'
        '  *"ninja --help") printf '
        "'usage: ninja [options] [targets...]\\n  -j N  run N jobs in parallel\\n' ;;\n"
        "esac\n")

    result = probe_ninja(fake, [], str(tmp_path / "cache-n.json"))

    assert result == {"available": True, "version": "1.11.1", "jobserver_client": False}


def test_probe_ninja_treats_exit_127_as_no_ninja(tmp_path):
    marker = tmp_path / "marker"
    fake = _fake_real_bwrap(tmp_path / "bwrap", marker, "exit 127\n")

    result = probe_ninja(fake, [], str(tmp_path / "cache-b.json"))

    assert result == {"available": False, "version": None, "jobserver_client": None}
    assert marker.read_text().splitlines() == ["run"]


def test_probe_ninja_treats_a_hang_past_its_timeout_as_no_ninja(tmp_path):
    marker = tmp_path / "marker"
    fake = _fake_real_bwrap(tmp_path / "bwrap", marker, "sleep 2\n")

    result = probe_ninja(fake, [], str(tmp_path / "cache-c.json"), timeout=0.2)

    assert result == {"available": False, "version": None, "jobserver_client": None}
    assert marker.read_text().splitlines() == ["run"]


def test_probe_ninja_treats_a_failing_bwrap_as_no_ninja(tmp_path):
    marker = tmp_path / "marker"
    fake = _fake_real_bwrap(
        tmp_path / "bwrap", marker,
        'echo "bwrap: cannot bind /nonexistent" >&2\nexit 1\n')

    result = probe_ninja(fake, [], str(tmp_path / "cache-d.json"))

    assert result == {"available": False, "version": None, "jobserver_client": None}
    assert marker.read_text().splitlines() == ["run"]


def test_a_second_probe_ninja_call_is_served_from_the_cache_without_rerunning(tmp_path):
    marker = tmp_path / "marker"
    fake = _fake_real_bwrap(tmp_path / "bwrap", marker, "exit 127\n")
    cache_path = str(tmp_path / "cache-e.json")

    first = probe_ninja(fake, [], cache_path)
    second = probe_ninja(fake, [], cache_path)

    assert first == second == {"available": False, "version": None, "jobserver_client": None}
    assert marker.read_text().splitlines() == ["run"]


# --- UX-859 (verifier): the widened gate - a table-less kind that spends
# `JOBS` gets the same real ninja probe cmake/meson do, not a skip ---------

_NINJA_WITH_CLIENT = (
    'case "$*" in\n'
    '  *"ninja --version") echo "1.12.0" ;;\n'
    '  *"ninja --help") printf '
    "'usage: ninja\\n  --jobserver   participate in a POSIX jobserver\\n' ;;\n"
    "esac\n")

_NINJA_NO_CLIENT = (
    'case "$*" in\n'
    '  *"ninja --version") echo "1.11.1" ;;\n'
    '  *"ninja --help") printf '
    "'usage: ninja [options] [targets...]\\n  -j N  run N jobs in parallel\\n' ;;\n"
    "esac\n")


def _decide_through_the_real_gate(tmp_path, monkeypatch, kind, argv,
                                  ninja_body, wrappers_dir=None):
    """Drives `_resolve_kind_and_probe` then `record_jobserver_decision`
    for real - a fake bwrap on the probe's own subprocess path (UX-855's
    `_fake_real_bwrap`), not a hand-built `ninja_probe` dict - and
    returns `(policy, marker)` from the decision log actually written."""
    kinds_path = tmp_path / "kinds.json"
    kinds_path.write_text(json.dumps({"el": kind}))
    monkeypatch.setenv("BST_TRACE_ELEMENT_KINDS", str(kinds_path))
    monkeypatch.delenv("BST_TRACE_JOBSERVER", raising=False)
    if wrappers_dir is not None:
        monkeypatch.setenv("BST_TRACE_WRAPPER_DIR", wrappers_dir)
    else:
        monkeypatch.delenv("BST_TRACE_WRAPPER_DIR", raising=False)
    monkeypatch.setattr(sys, "argv", ["bwrap-shim", *argv])
    marker = tmp_path / "marker"
    fake = _fake_real_bwrap(tmp_path / "bwrap", marker, ninja_body)

    kind_context = _resolve_kind_and_probe("el", 9, None, 4, fake)
    log_path = str(tmp_path / "decisions.jsonl")
    record_jobserver_decision(log_path, argv, "el", 4, kind_context=kind_context)
    with open(log_path, encoding="utf-8") as handle:
        record = json.loads(handle.readline())
    return record["policy"], marker


def test_a_table_less_kind_with_jobs_probes_ninja_and_reads_ninja_client(
        tmp_path, monkeypatch):
    """A manual `-G Ninja` recipe is exactly as much at risk of the
    cores+2 regression UX-843 found for cmake/meson - the widened gate
    must run the real probe, not skip it because the kind isn't cmake."""
    policy, marker = _decide_through_the_real_gate(
        tmp_path, monkeypatch, "manual", _argv_with_jobs("-j4"), _NINJA_WITH_CLIENT)
    assert policy == "ninja_client"
    assert marker.read_text().splitlines() == ["run", "run"]


def test_a_table_less_kind_with_jobs_and_a_wrapper_dir_reads_ninja_wrapper(
        tmp_path, monkeypatch):
    policy, _marker = _decide_through_the_real_gate(
        tmp_path, monkeypatch, "manual", _argv_with_jobs("-j4"), _NINJA_NO_CLIENT,
        wrappers_dir=str(tmp_path / "wrappers"))
    assert policy == "ninja_wrapper"


def test_a_table_less_kind_with_jobs_no_client_and_no_wrapper_dir_stays_static(
        tmp_path, monkeypatch):
    """Reuses cmake/meson's own `ninja_static` outcome (UX-843): ninja
    confirmed present, no client, nothing to hold tokens - emptying
    `JOBS` would run ninja at cores+2, worse than BuildStream's own
    `-jN` left alone, whatever the kind."""
    policy, _marker = _decide_through_the_real_gate(
        tmp_path, monkeypatch, "manual", _argv_with_jobs("-j4"), _NINJA_NO_CLIENT)
    assert policy == "ninja_static"


def test_a_table_less_kind_with_no_ninja_at_all_falls_back_to_jobs_env(
        tmp_path, monkeypatch):
    policy, marker = _decide_through_the_real_gate(
        tmp_path, monkeypatch, "manual", _argv_with_jobs("-j4"), "exit 127\n")
    assert policy == "jobs_env"
    assert marker.read_text().splitlines() == ["run"]


def test_a_table_less_kind_with_no_jobs_never_runs_the_probe(tmp_path, monkeypatch):
    """The gate's other half: no `JOBS` in the sandbox env stays
    `unknown_kind` and the probe never runs - the fake bwrap's own
    marker file, written on every invocation, never appears."""
    policy, marker = _decide_through_the_real_gate(
        tmp_path, monkeypatch, "manual", _argv_without_jobs(), _NINJA_WITH_CLIENT)
    assert policy == JOBSERVER_UNKNOWN_KIND
    assert not marker.exists()
