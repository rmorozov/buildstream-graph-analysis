"""UX-106: a process spine the dynamic linker cannot hide from.

`hook.c` sees a process because the dynamic linker loads it into that
process; a fully static executable never invokes the linker, so the hook
is never loaded and - as its own header says - cannot detect its own
absence. `UX-105` measured how large that hole gets: every command
`examples/01` runs is static busybox, and its Plane 2 capture has always
been empty.

These cover the spine's contract. The two properties that matter most
are not about tracing at all: the wrapped build's exit status must be
what it would have been untraced, in every failure mode, and a tracer
that dies must leave the build running.
"""
import os
import shutil
import subprocess

import pytest

from tools.bst_native_build_tracer import compile_spine, parse_trace_log
from tools.native_trace.bwrap_shim import build_shim_argv

CC_AVAILABLE = shutil.which("cc") is not None or shutil.which("gcc") is not None


@pytest.fixture(scope="module")
def spine(tmp_path_factory):
    """The real tracer, compiled the way a capture compiles it."""
    if not CC_AVAILABLE:
        pytest.skip("no C compiler on PATH")
    return compile_spine(str(tmp_path_factory.mktemp("spine")))


def _run(spine_bin, script, log=None, env=None):
    environment = dict(os.environ)
    if log:
        environment["BST_TRACE_LOG"] = str(log)
    environment.update(env or {})
    return subprocess.run(
        [spine_bin, "--", "/bin/sh", "-c", script],
        env=environment, capture_output=True, text=True,
    )


# --- injection ----------------------------------------------------------

def test_the_spine_wraps_the_sandboxed_command_not_the_bwrap_options():
    """It has to run *inside* the sandbox, after bwrap has set the
    namespaces up - that is what makes every process BuildStream starts
    its own descendant, and so traceable with no capability under Yama
    `ptrace_scope=1`."""
    argv = build_shim_argv(
        "/usr/bin/bwrap", ["--dir", "/buildstream/x/core.bst", "--", "sh", "-c", "make"],
        "/bind", "/dst", "/dst/hook.so", "/dst/trace.log", spine="/dst/spine",
    )
    assert argv[-5:] == ["/dst/spine", "--", "sh", "-c", "make"]
    # And the injected options still precede it, unchanged.
    assert "--setenv" in argv and "/dst/hook.so" in argv


def test_without_a_spine_the_argv_is_byte_for_byte_what_it_was():
    """Opt-in until `UX-108` measures the overhead, and opt-in has to
    mean the untraced path is untouched."""
    args = ["--dir", "/buildstream/x/core.bst", "--", "sh", "-c", "make"]
    assert build_shim_argv("/usr/bin/bwrap", args, "/b", "/d", "/d/h.so", "/d/t.log") == \
        build_shim_argv("/usr/bin/bwrap", args, "/b", "/d", "/d/h.so", "/d/t.log",
                        spine=None)


# --- the record format --------------------------------------------------

def test_spine_records_round_trip_through_the_existing_parser():
    """`src=` and `exit=` are new fields, and the parser's key loop
    *stops* at the first key it does not know - so an unhandled field
    would not be ignored, it would swallow `cmd=` and leave every spine
    record with an empty command line."""
    text = (
        "START pid=7 ppid=3 ts=1.5 element=work-a.bst inv=42 src=spine cmd=busybox true\n"
        "END pid=7 ppid=3 ts=1.9 element=work-a.bst inv=42 utime=0.010000 "
        "stime=0.020000 maxrss_kb=1412 exit=0 src=spine cmd=busybox true\n"
    )
    start, end = parse_trace_log(text)
    assert start["src"] == "spine" and start["cmd"] == "busybox true"
    assert end["cmd"] == "busybox true"
    assert end["cpu_us"] == 30_000
    assert end["max_rss_kb"] == 1412
    assert end["exit_status"] == "0"


def test_a_hook_record_still_says_it_came_from_the_hook():
    """Every capture taken before the spine existed carries no `src=`,
    and defaulting it to `hook` gives those records one honest answer
    rather than None."""
    text = "START pid=7 ppid=3 ts=1.5 element=core.bst inv=9 cmd=cc1plus a.cpp\n"
    assert parse_trace_log(text)[0]["src"] == "hook"


def test_a_signal_death_is_distinguishable_from_that_exit_code():
    """`exit=signal:9` and `exit=9` are different facts. The hook has no
    equivalent at all: its destructor runs before the process has a
    status, and does not run when one is killed."""
    text = ("END pid=7 ppid=3 ts=1.9 element=e.bst inv=1 exit=signal:9 src=spine "
            "cmd=/bin/sleep 5\n")
    assert parse_trace_log(text)[0]["exit_status"] == "signal:9"


# --- the tracer itself --------------------------------------------------

@pytest.mark.parametrize("script,expected", [
    ("exit 0", 0),
    ("exit 7", 7),
    # Negative: Python reports a signal death as -N, and that is exactly
    # why this case is checked through Python rather than a shell.
    ("kill -TERM $$", -15),
])
def test_the_exit_status_is_the_commands_own(spine, script, expected):
    """`hook.c`'s standing rule - never break the wrapped build - is
    harder to keep here, because this process sits between BuildStream
    and the command it asked for.

    The signal case caught a real difference. Returning `128 + N` reads
    identically to a shell, but the *wait status* a parent inspects is
    not the same: `WIFEXITED` against `WIFSIGNALED`, and BuildStream is
    that parent. The spine now dies the way the command died instead of
    exiting with a number that looks like it.
    """
    assert _run(spine, script).returncode == expected
    assert subprocess.run(["/bin/sh", "-c", script],
                          capture_output=True).returncode == expected


def test_a_static_binary_is_traced(spine, tmp_path):
    """The whole point. `LD_PRELOAD` produces nothing for a static
    executable; this produces a START and an END with argv, CPU time and
    peak RSS."""
    busybox = shutil.which("busybox")
    if busybox is None:
        pytest.skip("no busybox on PATH to exercise a static binary with")
    log = tmp_path / "trace.log"
    assert _run(spine, f"{busybox} true", log=log).returncode == 0
    records = [r for r in parse_trace_log(log.read_text()) if "busybox true" in r["cmd"]]
    assert {r["event"] for r in records} == {"START", "END"}
    end = next(r for r in records if r["event"] == "END")
    assert end["src"] == "spine"
    assert end["exit_status"] == "0"
    assert end["max_rss_kb"] > 0


def test_a_killed_process_is_recorded_with_how_it_died(spine, tmp_path):
    """The acceptance asks for "START without a fabricated END". What
    the spine produces is better and not a fabrication: the kernel's own
    exit-stop fires for a SIGKILLed process too, so the END carries real
    CPU and RSS read while the task still existed, plus `exit=signal:9`.
    Nothing is invented - a measurement the hook simply cannot take."""
    log = tmp_path / "trace.log"
    _run(spine, "/bin/sleep 5 & p=$!; /bin/sleep 0.2; kill -9 $p; wait", log=log)
    ends = [
        r for r in parse_trace_log(log.read_text())
        if r["event"] == "END" and r["cmd"] == "/bin/sleep 5"
    ]
    assert [r["exit_status"] for r in ends] == ["signal:9"]


def test_the_timestamps_share_the_hooks_clock(spine, tmp_path):
    """Both streams read `CLOCK_MONOTONIC`, so they share one timeline by
    construction rather than by correlation - which is what lets `UX-107`
    join them at all."""
    import time

    log = tmp_path / "trace.log"
    before = time.clock_gettime(time.CLOCK_MONOTONIC)
    _run(spine, "/bin/true", log=log)
    after = time.clock_gettime(time.CLOCK_MONOTONIC)
    stamps = [r["ts"] for r in parse_trace_log(log.read_text())]
    assert stamps and all(before <= ts <= after for ts in stamps)


def test_no_trace_log_means_no_records_and_no_failure(spine):
    """`BST_TRACE_LOG` unset is how a caller turns tracing off, and it
    must leave the command's behaviour untouched rather than erroring."""
    environment = {k: v for k, v in os.environ.items() if k != "BST_TRACE_LOG"}
    result = subprocess.run(
        [spine, "--", "/bin/sh", "-c", "echo hi"],
        env=environment, capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "hi"


def test_a_lone_tracee_survives_the_tracers_death(spine, tmp_path):
    """`PTRACE_O_EXITKILL` is deliberately NOT set: it would kill every
    tracee when the tracer died, turning a tracer bug into a failed
    build, which is exactly the outcome forbidden. Without it the kernel
    detaches on tracer death and the command runs on, untraced.

    Measured, and the measurement is narrower than the acceptance's
    wording - see `UX-106`'s "What a SIGKILLed tracer does" for the
    process-tree case, which does not survive on this kernel and which a
    plain fork/exec wrapper does. A lone tracee is the case where
    detachment is provably doing its job.
    """
    marker = tmp_path / "finished"
    script = f"/bin/sleep 1.5; echo done > {marker}"
    process = subprocess.Popen(
        [spine, "--", "/bin/sleep", "1.5"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    _wait_until(lambda: _children_of(process.pid), timeout=3.0)
    tracee = _children_of(process.pid)
    assert tracee, "the tracer never started the command"
    process.kill()
    process.wait(timeout=5)
    # Still running after its tracer is gone, rather than killed with it.
    assert _wait_until(lambda: os.path.exists(f"/proc/{tracee[0]}"), timeout=1.0)
    del script


def _wait_until(predicate, timeout):
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def _children_of(pid):
    """Polled rather than slept for, so the test does not race on a
    loaded machine."""
    try:
        return subprocess.run(
            ["pgrep", "-P", str(pid)], capture_output=True, text=True,
        ).stdout.split()
    except OSError:
        return []


BST_AVAILABLE = shutil.which("bst") is not None
BWRAP_AVAILABLE = shutil.which("bwrap") is not None
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and CC_AVAILABLE),
    reason="bst/bwrap/cc not all found on PATH - see docs/spec/ingestion-pipeline.md",
)
def test_a_real_static_build_is_invisible_to_the_hook_and_visible_to_the_spine(tmp_path):
    """UX-106's acceptance, on the project `UX-105`'s census identified.

    `examples/01-resource-contention` runs every build command through
    static busybox. Its Plane 2 capture has been empty for as long as
    Plane 2 has existed, and nothing in the report said why until the
    census; nothing could *fix* it until the spine.

    Both halves are run here rather than only the interesting one,
    because "the spine found 24 processes" means nothing without "and
    the hook alone found 0 on the same build".
    """
    from tools.bst_native_build_tracer import run_traced_build
    from tests.unit._bst_env import isolated_bst_env

    project = os.path.join(REPO_ROOT, "examples", "01-resource-contention")
    if not os.path.isfile(os.path.join(project, "files", "runtime", "bin", "sh")):
        pytest.skip("examples/01's runtime is not staged - run examples/stage_runtimes.sh")

    def _capture(name, trace_spine):
        home = tmp_path / f"home-{name}"
        home.mkdir()
        raw = tmp_path / f"{name}.log"
        environment = isolated_bst_env(home)
        previous = dict(os.environ)
        os.environ.update(environment)
        try:
            code = run_traced_build(
                project, ["bst", "--no-colors", "build", "all.bst"], str(raw),
                trace_spine=trace_spine,
            )
        finally:
            os.environ.clear()
            os.environ.update(previous)
        return code, parse_trace_log(raw.read_text() if raw.exists() else "")

    hook_code, hook_records = _capture("hook", trace_spine=False)
    spine_code, spine_records = _capture("spine", trace_spine=True)

    # The build itself is unaffected either way - the whole point.
    assert hook_code == 0 and spine_code == 0

    assert hook_records == [], (
        "the hook is expected to see nothing here: every command is static busybox"
    )
    assert spine_records, "the spine saw nothing on a build that runs real commands"
    assert {r["src"] for r in spine_records} == {"spine"}
    # Real element attribution, inherited from the same shim env the hook
    # reads - the spine is not a second, parallel identity scheme.
    assert any(r["element"].endswith(".bst") for r in spine_records)
    # And real measurements, not just names.
    ends = [r for r in spine_records if r["event"] == "END"]
    assert ends and all("max_rss_kb" in r for r in ends)
