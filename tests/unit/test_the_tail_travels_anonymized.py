"""UX-1103: `tail.json` travels in an anonymized bundle, its call argv rebuilt.

`tail/v1` (UX-1078) is a capture-layout row, and #298's export refuses a
row with no treatment. Its timings are class C; a call's argv names
elements, so it is rebuilt by the command grammar, never kept verbatim.
"""
import ast
import json
import pathlib
import tarfile

from bga import anonymize, bundle, disclosure, run_store, schemas
from tests.unit.test_an_anonymized_bundle_trips_on_a_leftover_name import CAPTURES, KEY, _snapshot, _source

REPO = pathlib.Path(__file__).resolve().parents[2]
WRITERS = sorted([*(REPO / "bga").rglob("*.py"), *(REPO / "tools").glob("*.py")])


def _tail(verb: str) -> dict:
    return schemas.stamp({
        "producer": None, "build_wall_us": 9_000_000, "complete": True,
        "phases": [{"name": "analyze", "wall_us": 1_500_000, "peak_rss_bytes": 4096,
                    "calls": [{"verb": verb, "wall_us": 700_000, "exit": 0}]}]},
        schemas.TAIL)


def _export(tmp_path, verb: str) -> dict:
    fixture = CAPTURES[0]
    snapshot = pathlib.Path(_snapshot(tmp_path / "project", fixture))
    (snapshot / run_store.TAIL_NAME).write_text(json.dumps(_tail(verb)), encoding="utf-8")
    pmap = anonymize.PseudonymMap(str(tmp_path / "anon" / "map.json"))
    path, _ = bundle.export_anonymized(str(snapshot), KEY, pmap, str(tmp_path / "out.tar.gz"),
                                       approve=lambda screen: True)
    with tarfile.open(path, mode="r:gz") as archive:
        member = next(i for i in archive.getmembers() if i.name.endswith(run_store.TAIL_NAME))
        return json.loads(archive.extractfile(member).read().decode("utf-8"))


def _uid() -> str:
    graph = json.loads(_source(CAPTURES[0], "graph.json").read_text(encoding="utf-8"))
    return graph["elements"][0]["uid"]


def test_the_tail_has_a_treatment_and_a_policy():
    assert disclosure.TREATMENTS["tail.json"] == disclosure.TRANSFORM
    assert disclosure.gaps("tail.json", schemas.TAIL, [_tail("bst show x.bst")]) == []


def test_a_calls_element_name_does_not_travel(tmp_path):
    uid = _uid()
    carried = _export(tmp_path, f"bst artifact list-contents {uid}")
    text = json.dumps(carried)
    assert uid not in text, text
    phase = carried["phases"][0]
    assert (phase["name"], phase["wall_us"], carried["build_wall_us"]) == (
        "analyze", 1_500_000, 9_000_000)
    assert phase["calls"][0]["verb"].split()[0] == "bst"


def test_every_phase_the_snapshot_names_is_on_the_vocabulary():
    allowed = disclosure.VOCABULARIES["tail_phase"]
    named = set()
    for path in WRITERS:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "timed"
                    and node.args and isinstance(node.args[0], ast.Constant)):
                named.add(node.args[0].value)
    assert named, "no progress.timed(...) phase found; the walk reads nothing"
    assert sorted(n for n in named if not allowed.admits(n)) == []
