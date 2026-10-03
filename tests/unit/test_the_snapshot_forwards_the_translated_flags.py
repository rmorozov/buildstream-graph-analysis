"""UX-1302: `bga snapshot` takes each flag `bga/cli.py`'s env-setting
`_translate_capture_*` functions own and sets the environment its
capture runs under exactly as `bga capture run` would; absent, a stale
value is cleared. The capture is faked, as in
`test_the_snapshot_takes_the_jobserver_switch.py`."""

import inspect
import os
import re
import stat

import pytest

from bga import cli
from tools.bga_snapshot import PLANE2_NAME

ENV = (
    "BST_TRACE_JOBSERVER_AUTH_MAP",
    "BST_TRACE_LTO_CAP",
    "BST_TRACE_WRAPPER_DIR_OVERRIDE",
    "BST_TRACE_WRAPPER_MODE",
)
VALUES = {
    "--jobserver-auth-override": "off:x.bst fd:lib-*.bst",
    "--lto-cap": "4",
    "--wrapper-dir": "/opt/wrappers",
    "--wrapper-dir-mode": "replace",
}


def _env_translated_flags() -> set:
    """Every flag a translator strips, less `--jobserver`, which the tracer parses itself."""
    flags = set()
    for name, fn in inspect.getmembers(cli, inspect.isfunction):
        if name.startswith("_translate_capture_"):
            flags |= set(re.findall(r"tok == '(--[a-z-]+)'", inspect.getsource(fn)))
    return flags - {"--jobserver"}


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    return root


@pytest.fixture
def recorded(monkeypatch, tmp_path_factory):
    """`capture run` replaced by a recorder of the environment it would read."""
    binaries = tmp_path_factory.mktemp("path")
    stub = binaries / "bst"
    stub.write_text("#!/bin/sh\necho 'BuildStream 2.0.0+stub'\n", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    for name in ENV:
        monkeypatch.delenv(name, raising=False)
    calls = []

    def fake_capture(argv):
        calls.append({name: os.environ.get(name) for name in ENV})
        run_dir = argv[argv.index("--run-dir") + 1]
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(os.path.dirname(run_dir), PLANE2_NAME), "w") as handle:
            handle.write("{}")
        return 0

    import tools.bst_native_build_tracer as tracer

    monkeypatch.setattr(tracer, "main", fake_capture)
    yield calls
    # The snapshot sets these in this process, as `capture run` does; no later test inherits them.
    for name in ENV:
        os.environ.pop(name, None)


def _env_under_capture(project, *flags) -> dict:
    """What the `capture run` that `bga snapshot <flags>` drives reads."""
    for name in ENV:
        os.environ.pop(name, None)
    assert (
        cli.main(
            ["snapshot", "--project", str(project), "--jobserver", "auto", *flags, "--", "bst", "build", "all.bst"]
        )
        == 0
    )
    return {name: os.environ.get(name) for name in ENV}


def _env_capture_run_sets(*flags) -> dict:
    for name in ENV:
        os.environ.pop(name, None)
    cli._translate_capture_wrapper_dir(
        cli._translate_capture_lto_cap(cli._translate_capture_jobserver_auth_override(["capture", "run", *flags]))
    )
    return {name: os.environ.pop(name, None) for name in ENV}


def test_the_flag_set_is_the_translators():
    assert _env_translated_flags() == set(VALUES)


@pytest.mark.parametrize("flag", sorted(VALUES))
def test_each_flag_reaches_the_capture_as_capture_run_would_set_it(project, recorded, flag):
    _env_under_capture(project, flag, VALUES[flag])

    [seen] = recorded
    expected = _env_capture_run_sets(flag, VALUES[flag])
    assert seen == expected
    assert any(expected.values()), f"{flag} set nothing under `capture run` either"


def test_the_override_is_repeatable(project, recorded):
    _env_under_capture(project, "--jobserver-auth-override", "off:a.bst", "--jobserver-auth-override", "fd:b.bst")

    [seen] = recorded
    assert seen["BST_TRACE_JOBSERVER_AUTH_MAP"] == "off:a.bst;fd:b.bst"


def test_a_stale_value_is_cleared_when_the_flag_is_absent(project, recorded, monkeypatch):
    for name in ENV:
        monkeypatch.setenv(name, "stale")
    assert cli.main(["snapshot", "--project", str(project), "--", "bst", "build", "all.bst"]) == 0

    [seen] = recorded
    assert seen == dict.fromkeys(ENV)
