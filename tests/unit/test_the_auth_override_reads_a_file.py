"""UX-1312: `--jobserver-auth-override @PATH` reads `style:glob[,glob ...]`
groups from a file, for `capture run` and `bga snapshot` alike; a missing
file or a bad style exits 2 naming the file (and line), never "no overrides"."""

import os

import pytest

from bga import cli
from tests.unit.test_the_snapshot_forwards_the_translated_flags import project, recorded  # noqa: F401
from tools.native_trace.bwrap_shim import _AUTH_OVERRIDE_STYLES, resolve_auth_override

VAR = "BST_TRACE_JOBSERVER_AUTH_MAP"


def _map(*values) -> str:
    argv = ["capture", "run"]
    for value in values:
        argv += ["--jobserver-auth-override", value]
    cli._translate_capture_jobserver_auth_override(argv + ["--", "true"])
    return os.environ.pop(VAR, "")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv(VAR, raising=False)
    monkeypatch.chdir(tmp_path)


def _write(name, text):
    path = os.path.join(os.getcwd(), name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def test_the_styles_match_the_shims():
    assert cli.AUTH_OVERRIDE_STYLES == _AUTH_OVERRIDE_STYLES


def test_a_file_parses_one_group_per_line_with_comma_or_space_globs():
    _write("o.conf", "off:a.bst\nfd:b-*.bst, c.bst  d.bst\nflto:sub.bst:x/*.bst\n")
    assert _map("@o.conf") == "off:a.bst;fd:b-*.bst,c.bst,d.bst;flto:sub.bst:x/*.bst"


def test_comments_and_blank_lines_are_skipped():
    _write("o.conf", "# header\n\n   # indented\noff:a.bst\n\n")
    assert _map("@o.conf") == "off:a.bst"


def test_a_trailing_comment_is_not_a_glob():
    _write("o.conf", "off:a.bst  # keeps its own -j\r\nfd:b.bst#why\r\n")
    assert _map("@o.conf") == "off:a.bst;fd:b.bst"


def test_a_path_with_a_space_is_one_file():
    os.mkdir("sp ace")
    _write("sp ace/o.conf", "off:a.bst\n")
    assert _map("@sp ace/o.conf") == "off:a.bst"


def test_a_file_mixes_with_inline_values_and_repeats():
    _write("a.conf", "off:a.bst\n")
    _write("b.conf", "fifo:b.bst\n")
    assert _map("fd:x.bst @a.conf", "@b.conf", "flto:y.bst") == "fd:x.bst;off:a.bst;fifo:b.bst;flto:y.bst"


def test_the_file_map_resolves_through_the_shim():
    _write("o.conf", "off:giant.bst\nfd:lib-*.bst\n")
    auth_map = _map("@o.conf")
    assert resolve_auth_override(auth_map, "giant.bst") == "off"
    assert resolve_auth_override(auth_map, "lib-z.bst") == "fd"


def test_a_missing_file_exits_2_naming_the_path(capsys):
    with pytest.raises(SystemExit) as exc:
        _map("@nope.conf")
    assert exc.value.code == 2
    assert "nope.conf" in capsys.readouterr().err
    assert VAR not in os.environ


def test_a_bad_style_exits_2_naming_file_and_line(capsys):
    _write("o.conf", "# c\noff:a.bst\n\nbogus:b.bst\n")
    with pytest.raises(SystemExit) as exc:
        _map("@o.conf")
    assert exc.value.code == 2
    assert "o.conf:4" in capsys.readouterr().err


def test_a_style_with_no_glob_is_an_error(capsys):
    _write("o.conf", "off:\n")
    with pytest.raises(SystemExit):
        _map("@o.conf")
    assert "o.conf:1" in capsys.readouterr().err


def test_the_equals_form_reads_a_file_too():
    _write("o.conf", "off:a.bst\n")
    cli._translate_capture_jobserver_auth_override(["capture", "run", "--jobserver-auth-override=@o.conf"])
    assert os.environ.pop(VAR) == "off:a.bst"


def test_snapshot_forwards_a_file_override_into_the_env(project, recorded):  # noqa: F811
    _write("o.conf", "off:a.bst\nfd:b.bst\n")
    argv = ["snapshot", "--project", str(project), "--jobserver", "auto"]
    assert cli.main(argv + ["--jobserver-auth-override", "@o.conf", "--", "bst", "build", "all.bst"]) == 0
    [seen] = recorded
    assert seen[VAR] == "off:a.bst;fd:b.bst"
