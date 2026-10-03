"""UX-1325: `bga cache-logs PROJECT_DIR` reads every project its local
junctions bring in, nested, and names their elements junction-qualified."""

import json

from tools.bst_cache_logs import junction_projects, main

LOG = """BuildStream 2.8.1 - Saturday, 03-10-2026 at 13:50:{second:02d}
[--:--:--] START   [{key}] {element}: Build
[--:--:--] START   {element}: Running commands
[00:00:0{secs}] SUCCESS {element}: Running commands
[00:00:0{secs}] SUCCESS [{key}] {element}: Build
"""

MID = "junctions/mid.bst"
BASE = "junctions/mid.bst:junctions/base.bst"


def _project(path, name, junctions=()):
    (path / "elements" / "junctions").mkdir(parents=True)
    (path / "project.conf").write_text(f"name: {name}\nmin-version: 2.0\nelement-path: elements\n")
    for filename, source in junctions:
        (path / "elements" / "junctions" / filename).write_text(f"kind: junction\nsources:\n{source}")
    (path / "elements" / "zlib.bst").write_text("kind: manual\n")


def _log(root, project, element, written_as, key, second):
    directory = root / project / element.replace("/", "-").replace(".bst", "")
    directory.mkdir(parents=True)
    text = LOG.format(second=second, key=key, element=written_as, secs=2)
    (directory / f"{key}-build.20261003-1350{second:02d}.log").write_text(text)


def _setup(tmp_path, monkeypatch):
    top = tmp_path / "top"
    _project(
        top,
        "top-os",
        [
            ("mid.bst", "- kind: local\n  path: sub/mid\n"),
            ("remote.bst", "- kind: git_repo\n  url: https://example.invalid/r.git\n"),
        ],
    )
    _project(top / "sub" / "mid", "mid-platform", [("base.bst", "- kind: local\n  path: sub/base\n")])
    _project(top / "sub" / "mid" / "sub" / "base", "base-sdk")
    logs = tmp_path / "cache" / "buildstream" / "logs"
    _log(logs, "top-os", "zlib.bst", "zlib.bst", "aaaa0001", 10)
    _log(logs, "mid-platform", "zlib.bst", f"{MID}:zlib.bst", "aaaa0002", 11)
    _log(logs, "base-sdk", "zlib.bst", f"{BASE}:zlib.bst", "aaaa0003", 12)
    # a standalone build of the base project writes its names unqualified
    _log(logs, "base-sdk", "gcc.bst", "gcc.bst", "aaaa0004", 13)
    _log(logs, "stranger", "zlib.bst", "zlib.bst", "aaaa0005", 14)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return top


def test_the_junctions_resolve_to_their_projects_with_prefixes(tmp_path, monkeypatch):
    top = _setup(tmp_path, monkeypatch)
    resolved, unresolved = junction_projects(str(top))
    assert resolved == [
        {"project": "mid-platform", "prefix": MID},
        {"project": "base-sdk", "prefix": BASE},
    ]
    assert unresolved == [{"prefix": "junctions/remote.bst", "source_kinds": ["git_repo"]}]


def test_every_junctioned_projects_elements_are_read_qualified(tmp_path, monkeypatch, capsys):
    top = _setup(tmp_path, monkeypatch)
    assert main([str(top), "-f", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["provenance"]["projects"] == ["base-sdk", "mid-platform", "top-os"]
    assert report["provenance"]["junctions"] == {"mid-platform": MID, "base-sdk": BASE}
    assert sorted(row["element"] for row in report["phase_breakdown"]) == [
        f"{BASE}:gcc.bst",
        f"{BASE}:zlib.bst",
        f"{MID}:zlib.bst",
        "zlib.bst",
    ]


def test_the_header_names_the_projects_and_the_unresolved_junction(tmp_path, monkeypatch, capsys):
    top = _setup(tmp_path, monkeypatch)
    assert main([str(top)]) == 0
    out = capsys.readouterr().out
    assert f"from base-sdk (via {BASE}), mid-platform (via {MID}), top-os" in out
    assert "junctions/remote.bst: a git_repo junction" in out and "--project NAME" in out
    assert "stranger" not in out


def test_project_keeps_reading_one_project(tmp_path, monkeypatch, capsys):
    top = _setup(tmp_path, monkeypatch)
    assert main([str(top), "--project", "top-os", "-f", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["provenance"]["projects"] == ["top-os"]
    assert "junctions" not in report["provenance"]
