"""UX-844 / Direction 20 argument 3: the shim splices `MAKEFLAGS` into
`bwrap`'s argv *after* BuildStream composed the key, so it never
reaches `Element._calculate_cache_key`. This is the measurement the
tree never took: `bst show --format '%{name} %{full-key}'` over the
fixture project with a clean host environment and with everything the
mode could leak, diffed.
"""
import re
import subprocess
from pathlib import Path

import pytest

from ._bst_env import isolated_bst_env
from .test_bst_extract_run import BST_AVAILABLE

REPO = Path(__file__).resolve().parents[2]
PROJECT = REPO / "tests/fixtures/bst_show_project"
GUIDE = REPO / "docs/guides/cli.md"
BST_SKIP_REASON = "bst not found on PATH - see docs/spec/ingestion-pipeline.md"

#: The mode's own leakage surface, named in the Motivation: `make`'s
#: and `cargo`'s real jobserver auth variables, plus every `BST_TRACE_*`
#: name the tracer's capture path uses - read from the guide rather
#: than copied, so a name added there is a name checked here.
_JOBSERVER_ENV = {
    "MAKEFLAGS": "--jobserver-auth=3,4 -j4",
    "JOBS": "-j4",
    "CARGO_BUILD_JOBS": "4",
}


def _bst_trace_names() -> list:
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index("### `BST_TRACE_*`")
    end = text.index("## `bga timeline`", start)
    return sorted(set(re.findall(r"`(BST_TRACE_[A-Z0-9_]+)`", text[start:end])))


def _leaking_env() -> dict:
    env = dict(_JOBSERVER_ENV)
    for name in _bst_trace_names():
        env[name] = "1"
    return env


def _full_keys(env_extra: dict, tmp_path) -> dict:
    env = isolated_bst_env(tmp_path / "home", **env_extra)
    result = subprocess.run(
        ["bst", "show", "--format", "%{name} %{full-key}", "app.bst"],
        cwd=PROJECT, capture_output=True, text=True, env=env, timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    keys = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        name, key = line.rsplit(" ", 1)
        keys[name] = key
    assert keys, "bst show produced no element/key pairs to compare"
    return keys


def _env_field(env_extra: dict, tmp_path) -> str:
    env = isolated_bst_env(tmp_path / "home", **env_extra)
    result = subprocess.run(
        ["bst", "show", "--format", "%{name} %{env}", "app.bst"],
        cwd=PROJECT, capture_output=True, text=True, env=env, timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason=BST_SKIP_REASON)
def test_the_key_is_equal_with_and_without_the_mode_environment(tmp_path):
    clean = _full_keys({}, tmp_path)
    leaking = _full_keys(_leaking_env(), tmp_path)
    differing = sorted(name for name in clean if clean[name] != leaking.get(name))
    assert differing == [], (
        f"{differing[0]}'s %{{full-key}} changed between a clean host "
        f"environment and one carrying everything the jobserver mode "
        f"could leak ({clean[differing[0]]!r} vs "
        f"{leaking.get(differing[0])!r}) - the key is not safe by "
        f"construction for this element."
    )
    assert clean.keys() == leaking.keys(), (
        "the two `bst show` runs resolved a different element set: "
        f"{sorted(clean)} vs {sorted(leaking)}"
    )


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason=BST_SKIP_REASON)
def test_the_shipped_kinds_env_does_not_embed_a_host_value(tmp_path):
    """The fixture's own `%{env}` (import/junction kinds) never carries
    the mode's variables at all - the shim's splice lives outside
    BuildStream's composed environment entirely, not merely nocached."""
    leaked = _env_field(_leaking_env(), tmp_path)
    for name in (*_JOBSERVER_ENV, *_bst_trace_names()):
        assert name not in leaked, (
            f"{name} appears in the fixture's %{{env}} - a host value "
            f"reached BuildStream's composed environment"
        )
