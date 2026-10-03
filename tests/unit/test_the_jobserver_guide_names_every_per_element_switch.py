"""UX-1300: `docs/guides/jobserver.md` names every per-element switch,
and its two examples resolve through the code a capture runs."""

import os
import re
import shlex
from pathlib import Path

import pytest

from bga.cli import _translate_capture_jobserver_auth_override
from tools.bst_native_build_tracer import _public_auth_style
from tools.native_trace.bwrap_shim import _AUTH_OVERRIDE_STYLES, resolve_auth_override

ROOT = Path(__file__).resolve().parents[2]
HEADING = "## One element, not the whole build"


def _section() -> str:
    text = (ROOT / "docs/guides/jobserver.md").read_text(encoding="utf-8")
    assert HEADING in text, "jobserver.md lost its per-element section"
    return text.split(HEADING, 1)[1].split("\n## ", 1)[0]


def _fenced(lang: str) -> list[str]:
    return re.findall(rf"```{lang}\n(.*?)```", _section(), flags=re.S)


@pytest.mark.parametrize("style", sorted(_AUTH_OVERRIDE_STYLES))
def test_every_style_the_shim_accepts_has_a_row(style):
    assert f"| `{style}` |" in _section()


def test_no_style_row_names_one_the_shim_rejects():
    rows = re.findall(r"^\| `([a-z]+)` \|", _section(), flags=re.M)
    assert set(rows) == set(_AUTH_OVERRIDE_STYLES)


@pytest.mark.parametrize(
    "switch", ["--jobserver-auth-override", "jobserver-auth:", "notparallel: True", "--jobserver off"]
)
def test_every_switch_is_named(switch):
    assert switch in _section()


def test_the_flag_example_resolves_each_named_element(monkeypatch):
    (block,) = [b for b in _fenced("text") if "--jobserver-auth-override" in b]
    argv = shlex.split(block.replace("\\\n", " "))
    monkeypatch.delenv("BST_TRACE_JOBSERVER_AUTH_MAP", raising=False)
    _translate_capture_jobserver_auth_override(argv[1:])
    auth_map = os.environ["BST_TRACE_JOBSERVER_AUTH_MAP"]
    value = argv[argv.index("--jobserver-auth-override") + 1]
    for group in value.split():
        style, _, globs = group.partition(":")
        for glob in globs.split(","):
            assert resolve_auth_override(auth_map, glob) == style, group


def test_the_annotation_example_parses_to_its_style():
    (block,) = [b for b in _fenced("yaml") if "jobserver-auth:" in b]
    public = block.split("public:\n", 1)[1]
    lines = [line[2:] for line in public.splitlines() if line.startswith("  ")]
    style = re.search(r"jobserver-auth: (\S+)", block).group(1)
    assert _public_auth_style("\n".join(lines) + "\n") == style


@pytest.mark.parametrize("guide", ["pilot.md", "cli.md"])
def test_the_guides_that_name_the_jobserver_point_here(guide):
    text = (ROOT / "docs/guides" / guide).read_text(encoding="utf-8")
    assert "jobserver.md#one-element-not-the-whole-build" in text
