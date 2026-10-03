"""UX-904: N variant builds priced against one junctioned invocation, over synthetic runs."""

import copy
import json
from pathlib import Path

import pytest

from bga import schemas
from bga.junction_cost import project, run_view

S = 1_000_000
EDGES = [("base", "lib"), ("lib", "app"), ("base", "tool")]


def _run(run_id, variant, keys, durations, phases, build_type="night"):
    return {
        "run_id": run_id,
        "build_class": {"type": build_type, "variant": {"arch": variant}},
        "phases": [{"phase": name, "elapsed_us": us} for name, us in phases],
        "keys": dict(keys),
        "edges": list(EDGES),
        "durations": dict(durations),
    }


def _pair():
    a = _run(
        "a",
        "x86_64",
        {"base": "k-base", "lib": "k-lib", "app": "k-app-x86", "tool": "k-tool-x86"},
        {"base": 10 * S, "lib": 20 * S, "app": 30 * S, "tool": 5 * S},
        [("Loading elements", 1 * S), ("Resolving elements", 2 * S)],
    )
    b = _run(
        "b",
        "aarch64",
        {"base": "k-base", "lib": "k-lib", "app": "k-app-arm", "tool": "k-tool-arm"},
        {"base": 12 * S, "lib": 18 * S, "app": 40 * S, "tool": 6 * S},
        [("Loading elements", 3 * S), ("Resolving elements", 5 * S)],
    )
    return a, b


def _validates(document):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(document, schemas.schema(schemas.JUNCTION_COST))


def test_a_known_overlap_is_projected_with_its_figures():
    document = project(_pair())
    _validates(document)
    projected = document["projected"]
    assert document["refusals"] == []
    assert [row["cache_key"] for row in projected["shared"]] == ["k-base", "k-lib"]
    assert projected["shared_closed_downward"] is True
    assert projected["shared_work_saving_us"] == (10 + 12 - 12 + 20 + 18 - 20) * S
    assert projected["pipeline_saving_us"] == (1 + 2) * S
    assert projected["saving_us"] == 31 * S
    assert projected["separate_floors_us"] == [60 * S, 70 * S]
    assert projected["union_floor_us"] == (12 + 20 + 40) * S
    assert projected["one_invocation_lower_bound_us"] == (3 + 5 + 72) * S
    assert projected["junction_staging_us"] is None
    ids = {row["id"] for row in document["assumptions"]}
    assert {"pipeline_once", "shared_by_key", "unlimited_capacity", "junction_staging"} <= ids


def test_doubling_one_runs_pipeline_grows_the_saving_by_exactly_that():
    a, b = _pair()
    before = project([a, b])["projected"]
    doubled = copy.deepcopy(a)
    for phase in doubled["phases"]:
        phase["elapsed_us"] *= 2
    after = project([doubled, b])["projected"]
    assert after["pipeline_saving_us"] - before["pipeline_saving_us"] == 3 * S
    assert after["saving_us"] - before["saving_us"] == 3 * S


def test_an_element_moved_out_of_the_overlap_drops_the_set_and_the_saving():
    a, b = _pair()
    before = project([a, b])["projected"]
    b["keys"]["lib"] = "k-lib-arm"
    after = project([a, b])["projected"]
    assert [row["cache_key"] for row in after["shared"]] == ["k-base"]
    assert after["shared_work_saving_us"] == before["shared_work_saving_us"] - 18 * S
    assert after["saving_us"] < before["saving_us"]


def test_disjoint_keys_save_no_work_and_say_so():
    a, b = _pair()
    b["keys"] = {uid: f"{key}-arm" for uid, key in b["keys"].items()}
    document = project([a, b])
    _validates(document)
    projected = document["projected"]
    assert projected["shared"] == []
    assert projected["shared_work_saving_us"] == 0
    assert projected["overlap"].startswith("No element is shared")


def test_different_types_are_refused_even_under_one_variant():
    a, b = _pair()
    b["build_class"] = {"type": "review", "variant": dict(a["build_class"]["variant"])}
    document = project([a, b])
    _validates(document)
    assert [refusal["check"] for refusal in document["refusals"]] == ["different_types"]
    assert document["projected"] is None


def test_a_single_run_is_refused():
    document = project(_pair()[:1])
    _validates(document)
    assert [refusal["check"] for refusal in document["refusals"]] == ["single_run"]


def test_runs_with_no_cache_keys_are_refused():
    a, b = _pair()
    b["keys"] = dict.fromkeys(b["keys"])
    document = project([a, b])
    _validates(document)
    assert [refusal["check"] for refusal in document["refusals"]] == ["no_cache_keys"]
    assert document["refusals"][0]["runs"] == ["b"]


def test_a_captured_run_reaches_the_projection():
    from bga.analyzer import BuildEfficiencyAnalyzer

    run = Path(__file__).parents[1] / "fixtures" / "macro_micro" / "run"
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.load(run)
    view = run_view(analyzer.analyze(run), analyzer.graph)
    twin = {**view, "run_id": f"{view['run_id']}-twin"}
    document = json.loads(json.dumps(project([view, twin]), default=str))
    _validates(document)
    projected = document["projected"]
    assert len(projected["shared"]) == len(view["keys"]) > 0
    assert projected["union_floor_us"] == projected["separate_floors_us"][0] > 0
    assert projected["pipeline_saving_us"] == sum(int(p["elapsed_us"]) for p in view["phases"]) > 0


def test_the_same_run_twice_is_refused():
    a, _ = _pair()
    document = project([a, copy.deepcopy(a)])
    _validates(document)
    assert [refusal["check"] for refusal in document["refusals"]] == ["same_run"]
    assert document["projected"] is None


def test_an_empty_run_id_is_labelled_not_left_blank():
    from bga.junction_cost import render

    a, b = _pair()
    a["run_id"] = ""
    lines = render(project([a, b]))
    assert not any(line.startswith("  : ") for line in lines)
    assert any(line.startswith("  (no run id): ") for line in lines)
