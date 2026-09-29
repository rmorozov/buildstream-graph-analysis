"""UX-1066: the three raw logs travel tokenized, not dropped.

On `with_timeline`: the timeline renders from the anonymized bundle, no
planted original survives in any member (the inflated `plane2.log.gz`
included), and the residue scan reads inside a gzipped member.
"""

import gzip
import io
import json
import pathlib
import shutil
import tarfile

import pytest

from bga import anonymize, bundle, disclosure
from tests.unit.test_an_anonymized_bundle_trips_on_a_leftover_name import KEY, _snapshot, _source
from tools.bga_timeline import render

FIXTURE = "with_timeline"
PRIVATE_DIR, PRIVATE_FILE, PRIVATE_MACRO, PRIVATE_TOOL = "acmecorp-vault", "secretwidget", "ACMEPRIVATE", "acme-codegen"
CONTEXT_TOKEN = "zephyrbuilder"


def _uids() -> list:
    graph = json.loads(_source(FIXTURE, "graph.json").read_text(encoding="utf-8"))
    return [e["uid"] for e in graph["elements"]][:3]


def _raw_logs(snapshot: pathlib.Path) -> None:
    shutil.copyfile(_source(FIXTURE, "build.log"), snapshot / "build.log")
    with open(snapshot / "build.log", "a", encoding="utf-8") as out:
        out.write(f"[wrapper][2026-08-21 17:09:00,000] INFO: fetching /home/{PRIVATE_DIR}/{PRIVATE_FILE}.tar\n")
    (snapshot / "capture-context.txt").write_text(f"host {CONTEXT_TOKEN} kernel 6.1\n", encoding="utf-8")
    lines = []
    for n, uid in enumerate(_uids()):
        tail = f"element={uid} inv=inv-{1000 + n} src=spine"
        cmd = f"/opt/{PRIVATE_TOOL}/bin/{PRIVATE_TOOL} -D{PRIVATE_MACRO}=1 -c /home/{PRIVATE_DIR}/{PRIVATE_FILE}.c"
        lines.append(f"START pid={1000 + n} ppid=1 ts={1787331690 + n}.000000 {tail} cmd={cmd}\n")
        lines.append(f"END pid={1000 + n} ppid=1 ts={1787331691 + n}.000000 {tail} exit=0 cmd={cmd}\n")
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as out:
        out.write("".join(lines))


def _export(tmp_path):
    snapshot = pathlib.Path(_snapshot(tmp_path / "project", FIXTURE))
    _raw_logs(snapshot)
    pmap = anonymize.PseudonymMap(str(tmp_path / "anon" / "map.json"))
    return bundle.export_anonymized(str(snapshot), KEY, pmap, str(tmp_path / "out.tar.gz"), approve=lambda screen: True)


def _decoded(path: str) -> dict:
    out = {}
    with tarfile.open(path, mode="r:gz") as archive:
        for info in archive.getmembers():
            data = archive.extractfile(info).read()
            out[info.name] = (gzip.decompress(data) if info.name.endswith(".gz") else data).decode("utf-8")
    return out


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    path, manifest = _export(tmp_path_factory.mktemp("raw"))
    return path, manifest, _decoded(path)


def test_the_raw_logs_are_transformed_not_dropped():
    assert {disclosure.TREATMENTS[m] for m in disclosure.LINE_MEMBERS} == {disclosure.TRANSFORM}


def test_no_planted_original_survives_in_any_member(exported):
    _path, manifest, members = exported
    shipped = {m["path"] for m in manifest["members"]}
    assert shipped >= disclosure.LINE_MEMBERS, shipped
    planted = [PRIVATE_DIR, PRIVATE_FILE, PRIVATE_MACRO, PRIVATE_TOOL, CONTEXT_TOKEN, *_uids()]
    leaks = [f"{name}: {token}" for name, text in members.items() for token in planted if token in text]
    assert leaks == []
    assert any(name.endswith("plane2.log.gz") for name in members)


def test_the_log_keeps_its_shape_and_the_planes_still_join(exported):
    _path, _manifest, members = exported
    log = next(text for name, text in members.items() if name.endswith("plane2.log.gz")).splitlines()
    assert [line.split()[0] for line in log] == ["START", "END"] * 3
    assert log[0].split()[1:4] == ["pid=1000", "ppid=1", "ts=1787331690.000000"]
    names = [next(w for w in line.split() if w.startswith("element=")).partition("=")[2] for line in log]
    assert len(set(names)) == 3
    assert all(" cmd=b-" in line and "<dropped>" in line for line in log), log[0]
    build = next(text for name, text in members.items() if name.endswith("build.log"))
    assert all(name in build for name in names), "a plane2.log.gz element is not the one build.log names"


def test_the_timeline_renders_from_the_anonymized_bundle(exported, tmp_path):
    path, _manifest, _members = exported
    target, _ = bundle.load(path, str(tmp_path / "loaded"))
    result = render(target, str(tmp_path / "t.pftrace"), quiet=True)
    assert result["planes"] == ["1", "2"], result
    assert result["tracks"] > 0
    assert (tmp_path / "t.pftrace").stat().st_size > 0


def _archive(tmp_path, text: str) -> str:
    target = tmp_path / "a.tar.gz"
    body = gzip.compress(text.encode("utf-8"))
    with tarfile.open(target, mode="w:gz") as archive:
        info = tarfile.TarInfo("plane2.log.gz")
        info.size = len(body)
        archive.addfile(info, io.BytesIO(body))
    return str(target)


def test_the_residue_scan_reads_inside_a_gzipped_member(tmp_path):
    archive = _archive(tmp_path, f"START pid=1 cmd=cc /home/{PRIVATE_DIR}/x.c\n")
    assert bundle.residue(archive, {PRIVATE_DIR}) == [f"plane2.log.gz: {PRIVATE_DIR}"]


def test_a_command_is_rebuilt_never_kept(tmp_path):
    pmap = anonymize.PseudonymMap(str(tmp_path / "map.json"))
    line = f"START pid=1 ts=5.0 cmd=/opt/{PRIVATE_TOOL}/bin/{PRIVATE_TOOL} -D{PRIVATE_MACRO}=1\n"
    out = anonymize.tokenize_line(line, KEY, pmap, disclosure.VOCABULARIES["binary"].allowed)
    assert PRIVATE_TOOL not in out and PRIVATE_MACRO not in out and out.startswith("START pid=1 ts=5.0 cmd=")
