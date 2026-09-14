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
import os

from tools.native_trace.bwrap_shim import (
    JOBSERVER_CAPPED_PENDING,
    JOBSERVER_JOINED,
    JOBSERVER_PINNED,
    JOBSERVER_UNKNOWN_KIND,
    build_shim_argv,
    extract_element_name,
    jobserver_decision,
    kind_job_env,
    parse_element_max_jobs,
    parse_ninja_help,
    split_bwrap_args,
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


def _build_with_kind(kind, **extra):
    """REAL_BWRAP_ARGV (`-j4`), a real fd, `project_max_jobs=4` (joined -
    the table applies) - the one input this whole section varies is the
    element's own kind and, for cmake/meson, the ninja probe."""
    read_fd, write_fd = os.pipe()
    try:
        return build_shim_argv(
            real_bwrap="/usr/bin/bwrap",
            bst_args=REAL_BWRAP_ARGV,
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


def test_an_unknown_kind_gets_no_injection():
    for kind in ("manual", "script", "import", "some-custom-plugin"):
        argv, read_fd = _build_with_kind(kind)
        try:
            assert _job_env_ops(argv) == []
            assert kind_job_env(kind, "AUTH")[2] == JOBSERVER_UNKNOWN_KIND
        finally:
            os.close(read_fd)


def test_an_element_absent_from_the_map_gets_no_injection():
    """`element_kind=None` - what `_element_kind_env` returns for an
    element the map does not name, same as no map at all."""
    argv, read_fd = _build_with_kind(None)
    try:
        assert _job_env_ops(argv) == []
        assert kind_job_env(None, "AUTH")[2] == JOBSERVER_UNKNOWN_KIND
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


def test_ninja_without_a_client_and_a_wrapper_dir_empties_jobs_only():
    probe = {"available": True, "version": "1.11.1", "jobserver_client": False}
    argv, read_fd = _build_with_kind(
        "cmake", ninja_probe=probe, wrappers_dir="/tmp/.bst-native-trace/wrappers")
    try:
        assert _job_env_ops(argv) == [("--setenv", "JOBS", "")]
    finally:
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
