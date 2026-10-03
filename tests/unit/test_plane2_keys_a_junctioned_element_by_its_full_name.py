"""UX-1320: Plane 2 keys a junctioned element by its full Plane 1 name, never the short one."""

import json

from tools.bst_native_build_tracer import (
    FIELD_SEP,
    RECORD_SEP,
    _chunks,
    _claim_short_names,
    _parse_element_projects,
    load_and_summarize,
)
from tools.native_trace.bwrap_shim import extract_element_name, extract_element_project, record_invocation

# Three projects, `pkgs/zlib.bst` in each: acme-os on top, acme-platform and acme-base behind junctions.
PROJECTS = {
    "pkgs/zlib.bst": "acme-os",
    "apps/browser.bst": "acme-os",
    "junctions/platform.bst:pkgs/zlib.bst": "acme-platform",
    "junctions/platform.bst:junctions/base.bst:pkgs/zlib.bst": "acme-base",
    "junctions/platform.bst:junctions/base.bst:pkgs/gcc-libs.bst": "acme-base",
}
SANDBOXES = [
    (100, "acme-os", "pkgs/zlib.bst"),
    (200, "acme-platform", "pkgs/zlib.bst"),
    (300, "acme-base", "pkgs/zlib.bst"),
    (400, "acme-base", "pkgs/gcc-libs.bst"),
    (500, "acme-os", "apps/browser.bst"),
]


def _capture(tmp_path, sandboxes, with_project=True):
    raw, invocations = tmp_path / "plane2.log", tmp_path / "invocations.jsonl"
    lines = []
    for inv, _project, element in sandboxes:
        lines.append(f"START pid=5 ppid=1 ts={inv}.0 element={element} inv={inv} cmd=/usr/bin/cc a.c\n")
        lines.append(f"END pid=5 ppid=1 ts={inv}.5 element={element} inv={inv} exit=0 cmd=/usr/bin/cc a.c\n")
    raw.write_text("".join(lines))
    invocations.write_text("")
    for inv, project, element in sandboxes:
        assert record_invocation(str(invocations), inv, element, project=project if with_project else None)
    return str(raw), str(invocations)


def test_every_element_is_keyed_by_its_full_plane1_name(tmp_path):
    raw, invocations = _capture(tmp_path, SANDBOXES)

    report = load_and_summarize(raw, invocation_log_path=invocations, element_projects=PROJECTS)

    assert sorted(report["by_element"]) == sorted(PROJECTS)
    assert report["junction_names"] == {"projects": 3, "relabelled_sandboxes": 3, "ambiguous_projects": []}


def test_a_log_without_the_project_keeps_the_short_names(tmp_path):
    raw, invocations = _capture(tmp_path, SANDBOXES, with_project=False)

    report = load_and_summarize(raw, invocation_log_path=invocations, element_projects=PROJECTS)

    assert report["by_element"] == {"pkgs/zlib.bst": 3, "pkgs/gcc-libs.bst": 1, "apps/browser.bst": 1}


def test_one_project_behind_two_junctions_is_reported_and_never_merged(tmp_path):
    projects = dict(PROJECTS)
    projects["junctions/sdk-a.bst:pkgs/gcc.bst"] = "sdk"
    projects["junctions/sdk-b.bst:pkgs/gcc.bst"] = "sdk"
    raw, invocations = _capture(tmp_path, [*SANDBOXES, (600, "sdk", "pkgs/gcc.bst")])

    report = load_and_summarize(raw, invocation_log_path=invocations, element_projects=projects)

    assert "sdk/pkgs/gcc.bst" in report["by_element"]
    assert not any(name.endswith(":pkgs/gcc.bst") for name in report["by_element"])
    assert report["junction_names"]["ambiguous_projects"] == ["sdk"]


def test_the_shim_keeps_the_project_segment_of_the_build_root():
    opts = ["--dir", "buildstream/acme-base/pkgs/gcc-libs.bst"]

    assert (extract_element_project(opts), extract_element_name(opts)) == ("acme-base", "pkgs/gcc-libs.bst")
    assert extract_element_project(["--dir", "/buildstream-build"]) is None


def test_the_show_read_learns_each_elements_project():
    stdout = "".join(
        FIELD_SEP.join([name, f"prefix: /usr\nproject-name: {project}\n", "- toolchain.bst\n"]) + RECORD_SEP
        for name, project in PROJECTS.items()
    )

    projects = _parse_element_projects(stdout)

    assert projects == PROJECTS
    assert projects.build_deps["pkgs/zlib.bst"] == ["toolchain.bst"]


def test_a_top_level_name_shadowing_a_junctioned_one_is_a_collision():
    assert _claim_short_names(list(PROJECTS))[2] == 2


def test_no_contents_batch_holds_two_names_with_one_short_spelling():
    batches = list(_chunks(list(PROJECTS), 200))

    assert [len(batch) for batch in batches] == [3, 1, 1]
    assert all(len({n.rsplit(":", 1)[-1] for n in batch}) == len(batch) for batch in batches)


def test_a_contents_heading_in_the_short_spelling_reaches_the_full_name(monkeypatch):
    from types import SimpleNamespace

    from tools import bst_native_build_tracer as tracer

    stdout = "  pkgs/dbus.bst:\n\tusr/bin/plat_dbus\n  apps/shell.bst:\n\tusr/bin/shell\n"
    monkeypatch.setattr(tracer.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout=stdout))

    read = tracer._list_contents(".", ["junctions/platform.bst:pkgs/dbus.bst", "apps/shell.bst"])

    assert read == {
        "junctions/platform.bst:pkgs/dbus.bst": {"/usr/bin/plat_dbus"},
        "apps/shell.bst": {"/usr/bin/shell"},
    }


def test_the_show_is_paid_for_only_when_a_sandbox_ran_outside_the_top_project(tmp_path):
    from tools.bst_native_build_tracer import needs_element_projects

    (tmp_path / "project.conf").write_text("name: acme-os\n")
    _capture(tmp_path, [(100, "acme-os", "pkgs/zlib.bst")])
    assert not needs_element_projects(str(tmp_path / "invocations.jsonl"), str(tmp_path))
    _capture(tmp_path, [(100, "acme-os", "pkgs/zlib.bst"), (200, "acme-base", "pkgs/zlib.bst")])
    assert needs_element_projects(str(tmp_path / "invocations.jsonl"), str(tmp_path))


def test_the_invocation_record_carries_the_project(tmp_path):
    path = tmp_path / "inv.jsonl"
    record_invocation(str(path), 7, "pkgs/zlib.bst", project="acme-base")
    record_invocation(str(path), 8, "buildstream-build")

    entries = [json.loads(line) for line in path.read_text().splitlines()]

    assert entries[0]["project"] == "acme-base" and "project" not in entries[1]
