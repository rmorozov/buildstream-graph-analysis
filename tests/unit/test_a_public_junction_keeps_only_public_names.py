"""UX-1065: a declared public junction keeps its public names.

`subproj-junction.bst:libfoo.bst` is tagged in a public checkout;
`forked.bst` is added after the tag, in a fork. Only the first survives
an anonymized export.
"""

import json
import pathlib
import shutil
import subprocess
import tarfile

from bga import bundle, run_store

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "macro_micro"
SUBPROJ = REPO / "tests" / "fixtures" / "bst_show_project" / "subproj"
STAMP = "20260902T101112Z"
KEY = bytes(range(32))
JUNCTION = "subproj-junction.bst"
LIBFOO = f"{JUNCTION}:libfoo.bst"
FORKED = f"{JUNCTION}:forked.bst"


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _public_checkout(tmp_path) -> str:
    """A copy of the subproj fixture, tagged, then forked past that tag."""
    checkout = tmp_path / "public-checkout"
    shutil.copytree(SUBPROJ, checkout)
    _git(checkout, "init", "-q")
    _git(checkout, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(checkout, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "public")
    _git(checkout, "tag", "v1")
    (checkout / "elements" / "forked.bst").write_text("kind: import\nsources: []\n", encoding="utf-8")
    _git(checkout, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(checkout, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "fork")
    return str(checkout)


def _snapshot(project: pathlib.Path) -> str:
    snapshot = pathlib.Path(run_store.runs_dir(str(project))) / STAMP
    (snapshot / "run").mkdir(parents=True)
    for name in ("graph.json", "trace.json", "run-context.json"):
        shutil.copyfile(FIXTURE / "run" / name, snapshot / "run" / name)
    shutil.copyfile(FIXTURE / "plane2.json", snapshot / "plane2.json")
    graph = json.loads((snapshot / "run" / "graph.json").read_text(encoding="utf-8"))
    graph["elements"][0]["uid"] = LIBFOO
    graph["elements"][1]["uid"] = FORKED
    (snapshot / "run" / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
    return str(snapshot)


def _export(project, checkout=None, tmp_path=None):
    from bga import anonymize

    if checkout is not None:
        run_store.write_config(str(project), {"public_junctions": {JUNCTION: {"checkout": checkout, "tag": "v1"}}})
    snapshot = _snapshot(project)
    pmap = anonymize.PseudonymMap(str(tmp_path / "anon" / "map.json"))
    destination = str(tmp_path / "out.tar.gz")
    path, manifest = bundle.export_anonymized(snapshot, KEY, pmap, destination, approve=lambda screen: True)
    with tarfile.open(path, mode="r:gz") as archive:
        text = "\n".join(archive.extractfile(i).read().decode("utf-8") for i in archive.getmembers() if i.isfile())
    return manifest, text


def test_the_tagged_name_passes_and_the_forked_one_does_not(tmp_path):
    checkout = _public_checkout(tmp_path)
    project = tmp_path / "project"
    manifest, text = _export(project, checkout, tmp_path)
    assert LIBFOO in text
    assert FORKED not in text and "forked" not in text
    assert f"{JUNCTION}:e-" in text  # the junction is public; the fork's own name is not
    assert manifest["public_junctions"] == [{"junction": JUNCTION, "tag": "v1", "names_passed": 1}]


def test_nothing_declared_pseudonymizes_both(tmp_path):
    project = tmp_path / "project"
    manifest, text = _export(project, None, tmp_path)
    assert LIBFOO not in text and "libfoo" not in text
    assert FORKED not in text and "forked" not in text
    assert "public_junctions" not in manifest
