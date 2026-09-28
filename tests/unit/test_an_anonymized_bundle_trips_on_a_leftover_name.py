"""UX-1062: a bundle exports anonymized, and refuses a leftover name.

Every fixture capture under `tests/fixtures/` is packed by
`bundle.export_anonymized` and read back decoded: no uid, hostname,
source path or target name of the fixture survives, and the bundle
loads. The refusals are each driven by one planted fault.
"""
import json
import os
import pathlib
import re
import shutil
import tarfile

import pytest

from bga import anonymize, bundle, run_store

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures"
STAMP = "20260902T101112Z"
KEY = bytes(range(32))
RUN_FILES = ("graph.json", "trace.json", "run-context.json", "sources.json")
BESIDE_FILES = ("plane2.json", "host-samples.jsonl")
CANONICAL_S = 946684800  # 2000-01-01T00:00:00Z


def _captures() -> list[str]:
    found = set()
    for graph in FIXTURES.rglob("graph.json"):
        root = graph.parent.parent if graph.parent.name == "run" else graph.parent
        found.add(root.relative_to(FIXTURES).as_posix())
    return sorted(found)


CAPTURES = _captures()


def _source(fixture: str, name: str) -> pathlib.Path:
    root = FIXTURES / fixture
    return next((p for p in (root / "run" / name, root / name) if p.is_file()), root / name)


def _snapshot(project: pathlib.Path, fixture: str, edit=None) -> str:
    snapshot = pathlib.Path(run_store.runs_dir(str(project))) / STAMP
    (snapshot / "run").mkdir(parents=True)
    for name in RUN_FILES + BESIDE_FILES:
        source = _source(fixture, name)
        if source.is_file():
            target = snapshot / ("run" if name in RUN_FILES else "") / name
            shutil.copyfile(source, target)
    for name, change in (edit or {}).items():
        target = snapshot / ("run" if name in RUN_FILES else "") / name
        document = json.loads(target.read_text(encoding="utf-8"))
        change(document)
        target.write_text(json.dumps(document), encoding="utf-8")
    return str(snapshot)


def _export(tmp_path, fixture, edit=None, approve=lambda screen: True):
    project = tmp_path / "project"
    snapshot = _snapshot(project, fixture, edit)
    pmap = anonymize.PseudonymMap(str(tmp_path / "anon" / "map.json"))
    destination = str(tmp_path / "out.tar.gz")
    path, manifest = bundle.export_anonymized(snapshot, KEY, pmap, destination, approve=approve)
    return path, manifest, pmap


def _decoded(path: str) -> dict:
    with tarfile.open(path, mode="r:gz") as archive:
        return {info.name: archive.extractfile(info).read().decode("utf-8")
                for info in archive.getmembers()}


def _names(fixture: str) -> set:
    """What the fixture must not leak: uids, hostname, source paths, targets."""
    names = set()
    graph = json.loads(_source(fixture, "graph.json").read_text(encoding="utf-8"))
    names.update(e["uid"] for e in graph.get("elements", []))
    context = json.loads(_source(fixture, "run-context.json").read_text(encoding="utf-8"))
    names.update(filter(None, [context.get("host")]))
    names.update((context.get("run_identity") or {}).get("targets") or [])
    sources = _source(fixture, "sources.json")
    if sources.is_file():
        for entries in json.loads(sources.read_text(encoding="utf-8"))["elements"].values():
            names.update(filter(None, (s.get(k) for s in entries for k in ("identity", "declared"))))
    return names


def _found(names, text: str) -> list:
    return sorted(n for n in names if re.search(
        rf"(?<![A-Za-z0-9]){re.escape(n)}(?![A-Za-z0-9])", text))


@pytest.mark.parametrize("fixture", CAPTURES)
def test_no_fixture_name_survives_and_the_bundle_loads(fixture, tmp_path):
    path, manifest, _pmap = _export(tmp_path, fixture)
    decoded = _decoded(path)
    names = _names(fixture)
    assert names, fixture
    assert _found(names, "\n".join([*decoded, *decoded.values()])) == []
    target, loaded = bundle.load(path, str(tmp_path / "far"))
    assert loaded["stamp"] == manifest["stamp"] != STAMP
    assert os.path.isfile(os.path.join(target, "run", "graph.json"))


def test_the_capture_list_is_every_fixture_with_a_graph():
    assert len(CAPTURES) >= 14 and "macro_micro" in CAPTURES, CAPTURES


def _private_tool(document):
    document["by_binary"]["acme-codegen"] = 3


def _private_toolchain(document):
    document["host_manifest"]["toolchain"]["acme-codegen"] = "acme-codegen 4.2.1"


def test_a_private_tool_exports_as_a_b_pseudonym(tmp_path):
    path, _manifest, pmap = _export(tmp_path, "macro_micro", {
        "plane2.json": _private_tool, "run-context.json": _private_toolchain})
    decoded = _decoded(path)
    assert "acme" not in "\n".join(decoded.values()).lower()
    by_binary = json.loads(decoded["capture/plane2.json"])["by_binary"]
    private = [b for b in by_binary if b.startswith("b-")]
    assert [pmap.resolve(b) for b in private] == ["binary\0acme-codegen"]
    toolchain = json.loads(decoded["capture/run/run-context.json"])["host_manifest"]["toolchain"]
    assert {k: v for k, v in toolchain.items() if k.startswith("b-")} == {
        private[0]: f"{private[0]} 4.2.1"}


def _plant(uid):
    def change(document):
        document["host_manifest"]["cpu_model"] = f"Xeon {uid} edition"
    return change


def test_a_uid_planted_in_a_kept_string_trips_the_residue_scan(tmp_path):
    with pytest.raises(bundle.BundleError, match=r"residue scan.*\n.*run-context.json: lib-a"):
        _export(tmp_path, "macro_micro", {"run-context.json": _plant("lib-a.bst")})
    assert not (tmp_path / "out.tar.gz").exists()
    assert not (tmp_path / "anon" / "map.json").exists()


def test_a_layout_row_with_no_treatment_refuses(tmp_path, monkeypatch):
    row = (f"{run_store.STORE_DIRNAME}/{run_store.RUNS_DIRNAME}/<stamp>/notes.txt",
           run_store.CONDITIONAL, None, "a member added with no treatment")
    monkeypatch.setattr(run_store, "CAPTURE_LAYOUT", run_store.CAPTURE_LAYOUT + (row,))
    with pytest.raises(bundle.BundleError, match="notes.txt"):
        _export(tmp_path, "macro_micro")
    assert not (tmp_path / "out.tar.gz").exists()


def test_an_unnamed_path_refuses_the_whole_export(tmp_path):
    def codename(document):
        document["codename"] = "falcon"
    with pytest.raises(bundle.BundleError, match="run/graph.json: codename"):
        _export(tmp_path, "macro_micro", {"graph.json": codename})
    assert not (tmp_path / "out.tar.gz").exists()


def test_nothing_is_written_until_the_owner_approves(tmp_path):
    screens = []

    def refuse(screen):
        screens.append(screen)
        return False
    with pytest.raises(bundle.BundleError, match="did not approve"):
        _export(tmp_path, "macro_micro", approve=refuse)
    assert not (tmp_path / "out.tar.gz").exists()
    assert not (tmp_path / "anon" / "map.json").exists()
    [screen] = screens
    assert len(screen.splitlines()) <= 24
    assert "kept verbatim" in screen and "cmake" in screen and "residue scan: clean" in screen


def test_documents_are_rewritten_in_place_and_times_shift_to_zero(tmp_path):
    path, _manifest, pmap = _export(tmp_path, "macro_micro")
    decoded = _decoded(path)
    graph = json.loads(decoded["capture/run/graph.json"])
    original = json.loads(_source("macro_micro", "graph.json").read_text(encoding="utf-8"))
    assert [e["uid"] for e in graph["elements"]] == [
        anonymize.pseudonymize_identifier(e["uid"], KEY, pmap) for e in original["elements"]]
    trace = json.loads(decoded["capture/run/trace.json"])
    source = json.loads(_source("macro_micro", "trace.json").read_text(encoding="utf-8"))
    assert [s["dur_us"] for s in trace["spans"]] == [s["dur_us"] for s in source["spans"]]
    context = json.loads(decoded["capture/run/run-context.json"])
    wall = [context["wall_clock"]["start_us"], *(s["ts_us"] for s in trace["spans"])]
    assert min(wall) == bundle.CANONICAL_ORIGIN_US["wall"]
    real = json.loads(_source("macro_micro", "run-context.json").read_text(encoding="utf-8"))
    assert (context["wall_clock"]["end_us"] - context["wall_clock"]["start_us"]
            == real["wall_clock"]["end_us"] - real["wall_clock"]["start_us"])


def test_host_samples_shift_on_their_own_clock_and_keep_every_delta(tmp_path):
    path, _manifest, _pmap = _export(tmp_path, "host_cpu")
    lines = _decoded(path)["capture/host-samples.jsonl"].splitlines()
    shifted = [json.loads(line) for line in lines]
    real = [json.loads(line) for line in
            _source("host_cpu", "host-samples.jsonl").read_text(encoding="utf-8").splitlines()]
    header, first = shifted[0], shifted[1]
    assert 0 <= header["wall_at_start"] - CANONICAL_S < 1 and 0 <= header["monotonic_at_start"] < 1
    assert first["t"] - header["monotonic_at_start"] == pytest.approx(
        real[1]["t"] - real[0]["monotonic_at_start"], abs=1e-9)


def test_an_anonymized_analysis_still_has_a_start_at_the_canonical_origin(tmp_path):
    from bga.analyzer import analyze_run
    path, _manifest, _pmap = _export(tmp_path, "macro_micro")
    target, _loaded = bundle.load(path, str(tmp_path / "far"))
    instance = analyze_run(pathlib.Path(target) / "run").run_instance
    assert instance.get("started_at_us") == CANONICAL_S * 10**6
    assert instance.get("started_at") == "2000-01-01 00:00:00 UTC"


def _private_flags(document):
    for operation, argv0 in zip(document["redundant_operations"], ("/usr/bin/cc1plus", "acme-codegen")):
        operation["example_cmd"] = operation["signature"] = f"{argv0} --acme-license-server=foo -c"


def test_a_private_long_flag_travels_as_a_pseudonym_on_any_binary(tmp_path):
    """`-c` (compile-only, `_KEPT_FLAG`) is binary-independent, unlike
    `-O<n>` (UX-1084: only a compiler driver keeps that one)."""
    path, _manifest, pmap = _export(tmp_path, "macro_micro", {"plane2.json": _private_flags})
    decoded = _decoded(path)
    assert "acme" not in "\n".join(decoded.values()).lower()
    public, private = (op["example_cmd"].split() for op in
                       json.loads(decoded["capture/plane2.json"])["redundant_operations"][:2])
    assert public[0] == "cc1plus" and private[0].startswith("b-")
    for words in (public, private):
        flag = words[1].split("=")[0]
        assert flag.startswith("--m-") and words[2] == "-c"
        assert pmap.resolve(flag[2:]) == "macro\0acme-license-server"


def test_free_text_is_rebuilt_or_dropped(tmp_path):
    path, _manifest, _pmap = _export(tmp_path, "macro_micro")
    plane2 = json.loads(_decoded(path)["capture/plane2.json"])
    assert plane2["declared_vs_used"]["note"] is None
    first = plane2["redundant_operations"][0]
    assert first["example_cmd"] == first["signature"]
    assert first["example_cmd"].startswith("cmake -B")
    assert "-DCMAKE_INSTALL_PREFIX:PATH=/f-" in first["example_cmd"]
    assert "Makefiles" not in first["example_cmd"]
