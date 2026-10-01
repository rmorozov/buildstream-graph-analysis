"""UX-1063: analysis commutes with anonymization.

`analyze(anon(x))` against `anon(analyze(x))` under a fixed key, in three
tiers: every measurement exactly, a name through the export's own map;
every tie-broken list exactly, since each break is on graph.json position;
the `LISTED` outputs as sets. Prose, a string holding a name, is not compared.
"""

import json
import math
import pathlib
import re
import shutil

import pytest

from bga import anonymize, bundle, findings, run_store
from bga.analyzer import analyze_run
from bga.report import format_json
from tests.fixtures import topologies

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = sorted(p for p in (REPO / "tests" / "fixtures" / "golden").iterdir() if p.is_dir())
#: Chosen so each tie below reorders; `test_the_key_reorders_each_tie` holds it.
KEY = bytes(range(1, 33))
STAMP = "20260902T101112Z"
RUN_FILES = ("graph.json", "trace.json", "run-context.json", "sources.json")
PROSE = "<prose>"

#: A tie with no name-independent order, or an order only for display:
#: compared as a multiset. Path steps are keys; `[]` is any list index.
LISTED = {
    # the element card's capped list, selected by graph order, shown by name.
    ".elements.fan_in.*.direct",
    ".elements.fan_in.*.dependents",
    # structural levels (structural/analyzer.py:379), each level by name.
    ".parallelism.levels[].elements",
    # consolidation `elements` and consumers, display order.
    ".consolidation_candidates[].elements",
    ".consolidation_candidates[].shared_consumers",
}

#: Name tie-breaks kept, whose output no capture here reaches: a list, not a path.
NAMED_ONLY = {
    "attribution/blame_chain.py:469,1462": "the smallest task key, spec 7.1/36.4",
    "sources.py:414": "a source's identity, after its measured cost and blast",
    "blast.py:308-314,346-358": "`bga blast`, each depth by name: display",
    "sources.py:333-357": "display",
    "utilisation/envelope.py:111-135": "display",
}

#: Not a measurement of the build: the export withholds the capture date (its
#: origin shifts to 0, which `_run_instance` reads as none) and these restate it.
NOT_COMPARED = {
    ".run_instance.started_at",
    ".run_instance.started_at_us",
    # the document's own leaf count, the two keys above among them.
    ".document_shape",
    # title, detail and evidence, each compared, plus the run's id and date.
    ".findings[].copy_text",
}

#: An absolute wall-clock instant: compared through the export's shift.
ABSOLUTE = {".occupancy.horizon_start_us", ".occupancy.horizon_end_us"}

#: Each topology and the uids its tie is between (the second precondition).
TOPOLOGIES = {
    "diamond": (topologies.diamond, ("b.bst", "c.bst")),
    "shared_base_wide": (topologies.shared_base_wide, tuple(f"mod{i}.bst" for i in range(6))),
    "fan_in": (topologies.fan_in, tuple(f"pred{i}.bst" for i in range(4))),
}


def _snapshot(project: pathlib.Path, run: pathlib.Path) -> pathlib.Path:
    """`run` as a store snapshot, so both sides are analyzed from a store."""
    snapshot = pathlib.Path(run_store.runs_dir(str(project))) / STAMP / "run"
    snapshot.mkdir(parents=True)
    for name in RUN_FILES:
        if (run / name).is_file():
            shutil.copyfile(run / name, snapshot / name)
    return snapshot


def _analysis(run: pathlib.Path) -> dict:
    return json.loads(format_json(analyze_run(run)))


class _Case:
    """One capture, exported, loaded and analyzed both ways."""

    def __init__(self, run: pathlib.Path, tmp_path: pathlib.Path):
        pmap = anonymize.PseudonymMap(str(tmp_path / "anon" / "map.json"))
        self.run = _snapshot(tmp_path / "project", run)
        path, _manifest = bundle.export_anonymized(
            str(self.run.parent), KEY, pmap, str(tmp_path / "out.tar.gz"), approve=lambda screen: True
        )
        target, _ = bundle.load(path, str(tmp_path / "far"))
        self.anon_run = pathlib.Path(target) / "run"
        self.places = {"real": (self.run, tmp_path / "project"), "anon": (self.anon_run, tmp_path / "far")}
        self.graph = json.loads((run / "graph.json").read_text(encoding="utf-8"))
        self.anon_graph = json.loads((self.anon_run / "graph.json").read_text(encoding="utf-8"))
        self.pmap = pmap
        self.names = {e["uid"]: anonymize.pseudonymize_identifier(e["uid"], KEY, pmap) for e in self.graph["elements"]}
        with open(pmap.path, encoding="utf-8") as handle:
            saved = json.load(handle)
        self.hashes = {
            original.split("\0", 1)[1]: pseudonym
            for pseudonym, original in saved.items()
            if original.startswith("hash\0")
        }
        self.shift = _start(self.run) - _start(self.anon_run)
        self.real = _analysis(self.run)
        self.anon = _analysis(self.anon_run)

    def placed(self, side: str, value: str) -> str:
        """Where `bga analyze` was pointed is not the capture: both sides' paths neutral."""
        run, root = self.places[side]
        value = value.replace(str(run), "<run>")
        token = findings.run_token(str(run))
        return (value.replace(token, "<run>") if token != str(run) else value).replace(str(root), "<project>")

    def translate(self, value: str) -> str:
        """`anon` of one output string: a name or task key through the map, prose marked."""
        value = self.placed("real", value)
        if value in self.names:
            return self.names[value]
        if value in self.hashes:
            return self.hashes[value]
        if "|" in value and value.split("|")[0] in self.names:
            return anonymize.pseudonymize_identifier(value, KEY, self.pmap)
        return PROSE if _holds(value, set(self.names) | set(self.hashes)) else value

    def untouched(self, value: str) -> str:
        value = self.placed("anon", value)
        known = set(self.names.values()) | set(self.hashes.values())
        if value in known or ("|" in value and value.split("|")[0] in known):
            return value
        return PROSE if _holds(value, known) else value


def _start(run: pathlib.Path) -> int:
    context = json.loads((run / "run-context.json").read_text(encoding="utf-8"))
    return context["wall_clock"]["start_us"]


def _holds(value: str, names) -> bool:
    return any(re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", value) for n in names)


def _map(node, leaf):
    if isinstance(node, dict):
        return {leaf(k): _map(v, leaf) for k, v in node.items()}
    if isinstance(node, list):
        return [_map(v, leaf) for v in node]
    return leaf(node) if isinstance(node, str) else node


def _pattern(path: str) -> str:
    return re.sub(r"\[\d+\]", "[]", path)


def _matches(listed: str, shape: str) -> bool:
    return re.fullmatch(re.escape(listed).replace(r"\*", r".+"), shape) is not None


def _listed(path: str) -> bool:
    return any(_matches(p, _pattern(path)) for p in LISTED)


def _canon(item) -> str:
    return json.dumps(item, sort_keys=True)


def _differences(real, anon, shift: int, path=""):
    """Every place `real` (already translated) and `anon` disagree."""
    shape = _pattern(path)
    if shape in NOT_COMPARED:
        return []
    if shape in ABSOLUTE and isinstance(real, int):
        real -= shift
    if isinstance(real, dict) and isinstance(anon, dict):
        out = [
            f"{path}.{k}: only one side"
            for k in sorted(set(real) ^ set(anon))
            if _pattern(f"{path}.{k}") not in NOT_COMPARED
        ]
        for key in sorted(set(real) & set(anon)):
            out += _differences(real[key], anon[key], shift, f"{path}.{key}")
        return out
    if isinstance(real, list) and isinstance(anon, list):
        if _listed(path):
            same = sorted(map(_canon, real)) == sorted(map(_canon, anon))
            return [] if same else [f"{path}: differ as sets"]
        if len(real) != len(anon):
            return [f"{path}: {len(real)} items against {len(anon)}"]
        return [d for i, (r, a) in enumerate(zip(real, anon)) for d in _differences(r, a, shift, f"{path}[{i}]")]
    numbers = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (real, anon))
    if numbers and math.isclose(real, anon, rel_tol=1e-12):
        return []
    if real != anon:
        return [f"{path}: {_canon(real)[-120:]} against {_canon(anon)[-120:]}"]
    return []


#: A topology's own shift, real minus `bundle.CANONICAL_ORIGIN_US["wall"]`
#: (`UX-1062`) rather than 0 - this makes it a real one, not a stub at 0.
EPOCH_US = 1_790_000_000_000_000
TOPOLOGY_SHIFT = EPOCH_US - bundle.CANONICAL_ORIGIN_US["wall"]


def _topology(name: str, tmp_path: pathlib.Path) -> pathlib.Path:
    context, graph, trace = TOPOLOGIES[name][0]()
    for span in trace["spans"] + trace.get("phases", []):
        span["ts_us"] += EPOCH_US
    for end in ("start_us", "end_us"):
        context["wall_clock"][end] += EPOCH_US
    return topologies.write_run_dir(tmp_path, (context, graph, trace), name="capture")


CAPTURES = [pytest.param(("golden", p), id=f"golden/{p.name}") for p in GOLDEN] + [
    pytest.param(("topology", name), id=name) for name in TOPOLOGIES
]


@pytest.fixture(params=CAPTURES)
def case(request, tmp_path):
    kind, which = request.param
    run = which if kind == "golden" else _topology(which, tmp_path)
    return _Case(run, tmp_path)


def test_the_golden_fixtures_are_captures():
    assert GOLDEN and all((p / "graph.json").is_file() for p in GOLDEN), GOLDEN


def test_anonymization_keeps_the_graph_order(case):
    """The first precondition: the tie-break key survives the export."""
    assert [case.names[e["uid"]] for e in case.graph["elements"]] == [e["uid"] for e in case.anon_graph["elements"]]


@pytest.mark.parametrize("name", TOPOLOGIES)
def test_the_key_reorders_each_tie(name, tmp_path):
    """The second: under this key a name tie-break picks another last
    member - the one a cap drops - so the commutation below can see it."""
    tied = TOPOLOGIES[name][1]
    names = _Case(_topology(name, tmp_path), tmp_path).names
    by_pseudonym = sorted(tied, key=names.__getitem__)
    assert by_pseudonym[-1] != sorted(tied)[-1], (name, by_pseudonym)


def _shapes(node, path="") -> set:
    out = {_pattern(path)}
    items = (
        node.items()
        if isinstance(node, dict)
        else ((f"[{i}]", v) for i, v in enumerate(node))
        if isinstance(node, list)
        else ()
    )
    for step, value in items:
        out |= _shapes(value, path + (step if step.startswith("[") else f".{step}"))
    return out


def test_every_exemption_names_a_path_some_capture_has(tmp_path):
    """An exemption no output reaches is a list that could hide anything."""
    shapes = set()
    for index, param in enumerate(CAPTURES):
        kind, which = param.values[0]
        where = tmp_path / str(index)
        run = which if kind == "golden" else _topology(which, where)
        case = _Case(run, where)
        assert kind == "golden" or case.shift == TOPOLOGY_SHIFT, (which, case.shift)
        shapes |= _shapes(case.real)
    dead = sorted(p for p in NOT_COMPARED | ABSOLUTE if p not in shapes)
    dead += sorted(p for p in LISTED if not any(_matches(p, s) for s in shapes))
    assert not dead, dead


def test_analysis_commutes_with_anonymization(case):
    real = _map(case.real, case.translate)
    anon = _map(case.anon, case.untouched)
    found = _differences(real, anon, case.shift)
    assert not found, "\n".join(found[:40])
