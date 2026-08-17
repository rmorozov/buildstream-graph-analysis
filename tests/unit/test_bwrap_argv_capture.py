"""UX-58: record the bwrap argv the shim rewrites.

Every capture this project has ever taken discarded it. The shim receives
BuildStream's complete bwrap command line, splits it, injects into it and
`execv`s it, writing nothing — so the artifact `UX-56` needs to pick an
authoritative element identifier has never existed, and `UX-56`
mis-attributed that absence to the capture workflow's tarball size limit.

Bounded on purpose: a real build spawns one bwrap per element task and
thousands on a large project, while identifying *which option carries the
element* needs a handful.
"""
import json
import os

from tools.native_trace.bwrap_shim import (
    DEFAULT_ARGV_RECORD_LIMIT,
    record_argv,
)

ARGV = ["--ro-bind", "/usr", "/usr", "--dir", "buildstream/proj/core.bst", "sh", "-c", "make"]


def test_an_argv_is_recorded_verbatim(tmp_path):
    log = tmp_path / "argv.jsonl"

    assert record_argv(str(log), ARGV, 8) is True

    record = json.loads(log.read_text().strip())
    assert record["argv"] == ARGV
    assert record["pid"] == os.getpid()


def test_records_accumulate_one_per_line(tmp_path):
    log = tmp_path / "argv.jsonl"

    for _ in range(3):
        record_argv(str(log), ARGV, 8)

    assert len(log.read_text().splitlines()) == 3


def test_the_limit_stops_recording(tmp_path):
    log = tmp_path / "argv.jsonl"

    written = [record_argv(str(log), ARGV, 2) for _ in range(5)]

    assert written == [True, True, False, False, False]
    assert len(log.read_text().splitlines()) == 2


def test_a_zero_limit_records_nothing(tmp_path):
    log = tmp_path / "argv.jsonl"

    assert record_argv(str(log), ARGV, 0) is False
    assert not log.exists()


def test_an_unwritable_path_never_raises(tmp_path):
    """A diagnostic that can fail a real build is worse than no
    diagnostic. Every error path here has to end in 'record nothing and
    let the build proceed'."""
    unwritable = tmp_path / "no-such-directory" / "argv.jsonl"

    assert record_argv(str(unwritable), ARGV, 8) is False


def test_the_default_limit_is_small(tmp_path):
    """The bound is the design: a handful answers the question, and a
    real build would otherwise write thousands of 349-token lines."""
    assert 0 < DEFAULT_ARGV_RECORD_LIMIT <= 64


def test_the_recorded_argv_is_the_one_buildstream_generated(tmp_path):
    """Not the rewritten one. The whole point is to see what BuildStream
    emits, and the shim's own injected `--bind`/`--setenv` options would
    be noise at best and misleading at worst."""
    from tools.native_trace.bwrap_shim import build_shim_argv

    log = tmp_path / "argv.jsonl"
    record_argv(str(log), ARGV, 8)
    rewritten = build_shim_argv(
        "/usr/bin/bwrap", ARGV, "/src", "/dst", "/dst/hook.so", "/dst/trace.log"
    )

    recorded = json.loads(log.read_text().strip())["argv"]
    assert recorded == ARGV
    assert "BST_TRACE_ELEMENT" not in recorded
    assert "BST_TRACE_ELEMENT" in rewritten


def test_a_real_captured_argv_carries_the_element_only_via_the_build_root(tmp_path):
    """The finding this capability immediately produced, pinned so the
    next attempt at `UX-56` starts from it rather than re-deriving it.

    In a real captured argv (BuildStream 2.7.0, `examples/07`, 349
    tokens) the element name appears three times - `--dir`, `--chdir`,
    and `--setenv PWD` - and all three are the *same* build-root-relative
    path. A project that overrides `build-root`, as `freedesktop-sdk`
    does, therefore loses all three at once rather than losing one of
    three independent sources. That makes it likely `UX-56` needs a
    mechanism outside the argv entirely.
    """
    real = [
        "--bind", "/root/.cache/buildstream/cas/staging/cas-tmpdir2wnYto", "/",
        "--dir", "buildstream/dep-usage-example/base.bst",
        "--chdir", "buildstream/dep-usage-example/base.bst",
        "--setenv", "PWD", "/buildstream/dep-usage-example/base.bst",
        "sh", "-c", "-e", "cmake -B_builddir",
    ]
    log = tmp_path / "argv.jsonl"
    record_argv(str(log), real, 8)

    recorded = json.loads(log.read_text().strip())["argv"]
    element_bearing = [a for a in recorded if a.endswith("base.bst")]

    assert len(element_bearing) == 3
    # All three are the same path modulo a leading slash - one source.
    assert len({a.lstrip("/") for a in element_bearing}) == 1
