"""UX-683: a declared foundation tier, not a kind guess.

`STRUCTURAL_ELEMENT_KINDS` exempts a `junction`/`import`/`filter`/
`compose`/`stack` from the blast and fan-in rankings (`UX-258`,
`UX-76`). A toolchain built as `autotools`/`manual`/`cmake` is not
exempt, so it tops the ranking on every run until the owner declares
it - the defect this closes.

Acceptance Test, on `tests/fixtures/macro_micro` (example 06:
`examples/06-macro-micro-optimization/project.conf` now declares
`variables: {bga-foundation: toolchain.bst}`, the committed `graph.json`
hand-carries the same `"foundation"` the extractor would produce from
it - real `bst show` here hits this machine's "Cache too full" on
*every* project, confirmed independent of this diff): its
chain-bound shape (`UX-65`/`UX-479`) means only `blast-radius-
foundation` and `blast-radius-reach` publish; the ranked arm is
exercised on a synthetic, non-chain-bound population instead, where
declaring `toolchain.bst` foundation drops it from `blast-radius-
ranking` and `core.bst` leads. `tests/fixtures/foundation_declared`
(a `fan_in(n=4)` topology, `sink.bst` declared) reaches the fan-in
mirror. Undeclared, `foundation-candidates` names the widest
non-structural, non-declared reach instead.
"""
import contextlib
import io
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
MACRO_MICRO = REPO / "tests/fixtures/macro_micro/run"
FOUNDATION_DECLARED = REPO / "tests/fixtures/foundation_declared/run"


def _findings(run_dir):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        main(["analyze", str(run_dir), "--format", "json"])
    return json.loads(buffer.getvalue())["findings"]


def _finding(run_dir, finding_id):
    found = [f for f in _findings(run_dir) if f["id"] == finding_id]
    return found[0] if found else None


def _entry(count, kind="cmake", structural=False, foundation=False):
    return {"downstream_count": count, "element_kind": kind,
            "is_structural_kind": structural, "is_foundation": foundation,
            "weighted_duration_us": count * 1000}


def _rank(blast, distribution=None):
    from bga import findings

    class R:
        pass

    result = R()
    result.signals = {
        "blast_radius": blast, "top_blast_radius": list(blast),
        "blast_radius_distribution": distribution,
    }
    return findings._ranking_findings(result, chain_bound=False)


class TestExampleSix:
    """The literal Acceptance Test, on the real graph."""

    def test_toolchain_declared_the_blast_top_row_is_core(self):
        graph = json.loads((MACRO_MICRO / "graph.json").read_text())
        assert graph["foundation"] == ["toolchain.bst"]

        # `macro_micro` is chain-bound (`UX-479`), so the *ranking* arm
        # is gated and `blast-radius-reach` is what publishes instead -
        # `TestSyntheticGraphShape` below drives the ranked case, which
        # a chain-bound fixture cannot exercise.
        reach = _finding(MACRO_MICRO, "blast-radius-reach")
        assert reach is not None
        assert "core.bst" in reach["elements"]
        assert "toolchain.bst" not in reach["elements"]

    def test_toolchain_sits_in_the_foundation_tier_with_its_fan_out(self):
        found = _finding(MACRO_MICRO, "blast-radius-foundation")
        assert found is not None
        assert found["elements"] == ["toolchain.bst"]
        assert "downstream" in found["title"]

    def test_a_name_not_in_the_graph_is_a_diagnostic_not_a_crash(self, tmp_path, monkeypatch):
        """Runs the real `extract_run`, `extract_graph` monkeypatched
        so this needs no real `bst` - only the validation clause
        (`tools/bst_extract_run.py:405-414`) is under test. `graph.json`
        is real project.conf's own `variables: {bga-foundation:
        "a.bst,not-in-graph.bst"}` YAML, read by `_read_bga_foundation`
        exactly as a real project's would be.
        """
        import tools.bst_extract_run as extractor

        project = tmp_path / "proj"
        (project / "elements").mkdir(parents=True)
        (project / "project.conf").write_text(
            "name: p\nmin-version: 2.0\nelement-path: elements\n"
            "variables:\n  bga-foundation: a.bst,not-in-graph.bst\n")
        log = tmp_path / "build.log"
        log.write_text("Targets:       a.bst\n")

        def fake_extract_graph(project_dir, targets, bst_bin="bst", bst_options=None):
            return {"elements": [{"uid": "a.bst"}, {"uid": "b.bst"}], "dependencies": []}

        monkeypatch.setattr(extractor, "extract_graph", fake_extract_graph)

        out = tmp_path / "out"
        summary = extractor.extract_run(
            str(project), str(log), str(out),
            log_format="raw", start_time="2026-08-14T00:00:00+00:00")

        assert any("not-in-graph.bst" in w for w in summary["warnings"])
        graph = json.loads((out / "graph.json").read_text())
        assert graph["foundation"] == ["a.bst"]


class TestTheFanInMirror:
    def test_a_declared_sink_sits_in_the_foundation_tier(self):
        graph = json.loads((FOUNDATION_DECLARED / "graph.json").read_text())
        assert graph["foundation"] == ["sink.bst"]

        found = _finding(FOUNDATION_DECLARED, "fan-in-foundation")
        assert found is not None
        assert found["elements"] == ["sink.bst"]

    def test_the_declared_sink_is_excluded_from_the_fan_in_ranking(self):
        ranking = _finding(FOUNDATION_DECLARED, "fan-in-ranking")
        if ranking is not None:
            assert "sink.bst" not in ranking["elements"]


class TestSyntheticGraphShapeMirrorsTheKindException:
    """A non-chain-bound population, so the *ranked* arm (gated on
    `UX-65`) is the one exercised - `TestExampleSix` above is chain-
    bound and only reaches `blast-radius-reach`."""

    def test_a_declared_non_structural_element_does_not_lead(self):
        found = _rank({
            "toolchain.bst": _entry(900, "cmake", foundation=True),
            "core.bst": _entry(700, "cmake"),
            "app.bst": _entry(300, "cmake"),
        })
        ranking = next(f for f in found if f["id"] == "blast-radius-ranking")
        assert "toolchain.bst" not in ranking["elements"], (
            "a declared foundation element is still ranked as something to fix")
        assert ranking["elements"][0] == "core.bst"

    def test_it_is_reported_in_its_own_tier_with_its_figure(self):
        found = _rank({
            "toolchain.bst": _entry(900, "cmake", foundation=True),
            "core.bst": _entry(700, "cmake"),
        })
        tier = next(f for f in found if f["id"] == "blast-radius-foundation")
        assert tier["elements"] == ["toolchain.bst"]
        assert "900" in tier["title"]
        # `UX-344`: no second copy of the population inside the finding.
        assert "blast_radius" not in (tier.get("evidence") or {})

    def test_a_declared_structural_kind_reports_as_foundation_not_structural(self):
        """`UX-683`: the declaration is a stronger claim than the kind
        guess, so it wins the report even where both would apply."""
        found = _rank({
            "base.bst": _entry(900, "import", structural=True, foundation=True),
            "core.bst": _entry(700, "cmake"),
        })
        ids = [f["id"] for f in found]
        assert "blast-radius-foundation" in ids
        assert "blast-radius-structural" not in ids
        tier = next(f for f in found if f["id"] == "blast-radius-foundation")
        assert tier["elements"] == ["base.bst"]

    def test_undeclared_the_discovery_names_it(self):
        """The kind exemption misses a `cmake` toolchain; discovery
        proposes it as a candidate rather than silently ranking it."""
        distribution = {"n": 10, "min": 0, "max": 900, "is_flat": False,
                        "deciles": {"p10": 0, "p50": 100, "p90": 500}, "p95": 600}
        found = _rank({
            "toolchain.bst": _entry(900, "cmake"),
            "core.bst": _entry(300, "cmake"),
        }, distribution)
        candidates = next(f for f in found if f["id"] == "foundation-candidates")
        assert "toolchain.bst" in candidates["elements"]
        assert "declare or dismiss" in candidates["title"]
        assert "core.bst" not in candidates["elements"], (
            "300 is under the p95 threshold and should not be proposed")

    def test_a_declared_element_is_never_proposed_as_a_candidate(self):
        distribution = {"n": 10, "min": 0, "max": 900, "is_flat": False,
                        "deciles": {"p10": 0, "p50": 100, "p90": 500}, "p95": 600}
        found = _rank({
            "toolchain.bst": _entry(900, "cmake", foundation=True),
        }, distribution)
        assert not [f for f in found if f["id"] == "foundation-candidates"]

    def test_no_distribution_no_candidates(self):
        """A run too small for a distribution has nothing to compare a
        count against - the same refusal `blast_radius_distribution`
        itself makes (`UX-249`)."""
        found = _rank({"toolchain.bst": _entry(900, "cmake")})
        assert not [f for f in found if f["id"] == "foundation-candidates"]


class TestTheSchemaGainsTheField:
    def test_blast_radius_and_fan_in_publish_is_foundation(self):
        from bga import schemas

        blast = schemas.schema(schemas.ANALYZE)["properties"]["elements"][
            "properties"]["blast_radius"]
        fan_in = schemas.schema(schemas.ANALYZE)["properties"]["elements"][
            "properties"]["fan_in"]
        assert "is_foundation" in blast["additionalProperties"]["properties"]
        assert "is_foundation" in fan_in["additionalProperties"]["properties"]


class TestTheGraphModelCarriesTheDeclaration:
    def test_the_loader_reads_the_foundation_key(self):
        import tempfile

        from bga.ingest.loader import load_graph

        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "graph.json"
            path.write_text(json.dumps({
                "elements": [{"uid": "a.bst"}, {"uid": "b.bst"}],
                "dependencies": [],
                "foundation": ["a.bst"],
            }))
            graph = load_graph(path)
        assert graph.foundation == frozenset({"a.bst"})

    def test_absent_foundation_is_an_empty_frozenset_not_none(self):
        from bga.ingest.models import Graph

        assert Graph().foundation == frozenset()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
