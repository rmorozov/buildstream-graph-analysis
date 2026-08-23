"""UX-47: a narrow subcommand must not pay for stages it discards.

Every section subcommand was a thin alias over the full pipeline, so
`bga graph` computed attribution it never renders - the same cost as the
full `bga analyze`. At eleven elements that was unmeasurable; at 1202 it
was the whole runtime.

`P1-14`'s resolution - keep one shared pipeline rather than re-deriving
shared stages per subcommand - is not reopened here. The pipeline is
still one pipeline; it just skips stages the requested section does not
consume.

The load-bearing property is that output cannot change, so these tests
assert both halves: the stage really is skipped (otherwise the fix is a
no-op that happens to be fast for some other reason), *and* every
section renders exactly what it rendered before.
"""
import json

import pytest

from bga.report.json import format_json
from bga.report.text import format_text
from tests.fixtures import topologies


SECTIONS = ["graph", "floors", "utilisation", "diagnostics", None]


@pytest.fixture
def topology():
    return topologies.diamond()


def _analyzer(tmp_path, topology, name="run"):
    return topologies.build_analyzer(tmp_path, topology, name=name)


def test_graph_section_does_not_compute_attribution(tmp_path, topology, monkeypatch):
    """The specific waste this task is about. Asserted directly rather
    than inferred from a timing, so it cannot silently regress into
    "fast for some other reason"."""
    analyzer = _analyzer(tmp_path, topology)
    called = []
    monkeypatch.setattr(
        type(analyzer),
        "_compute_attribution",
        lambda self, graph_analysis: called.append(1) or {},
    )

    analyzer.analyze(section="graph")

    assert called == [], "bga graph must not enter _compute_attribution"


def test_full_analyze_still_computes_attribution(tmp_path, topology, monkeypatch):
    """The other half: gating must not quietly disable a stage for the
    full report."""
    analyzer = _analyzer(tmp_path, topology)
    called = []
    real = type(analyzer)._compute_attribution
    monkeypatch.setattr(
        type(analyzer),
        "_compute_attribution",
        lambda self, graph_analysis: called.append(1) or real(self, graph_analysis),
    )

    analyzer.analyze(section=None)

    assert called == [1]


@pytest.mark.parametrize(
    "section,skipped",
    [
        ("graph", "_compute_utilization"),
        ("graph", "_compute_diagnostics"),
        ("floors", "_compute_attribution"),
        ("floors", "_compute_structural_analysis"),
        ("utilisation", "_compute_attribution"),
        ("utilisation", "_compute_structural_analysis"),
        ("diagnostics", "_compute_attribution"),
    ],
)
def test_sections_skip_stages_they_do_not_render(
    tmp_path, topology, monkeypatch, section, skipped
):
    analyzer = _analyzer(tmp_path, topology)
    called = []
    monkeypatch.setattr(
        type(analyzer), skipped, lambda self, *a, **k: called.append(1) or {}
    )

    analyzer.analyze(section=section)

    assert called == [], f"bga {section} must not enter {skipped}"


@pytest.mark.parametrize("section", SECTIONS)
@pytest.mark.parametrize(
    "topology_name",
    ["diamond", "linear_chain", "fan_in", "independent_branches"],
)
def test_section_output_is_unchanged_by_gating(tmp_path, section, topology_name):
    """Gating a stage must never change what a section renders.

    Compared against the same section rendered from a *fully* analyzed
    result - which is what the pipeline produced before this change - so
    this is the real before/after comparison rather than a snapshot that
    could drift with it.
    """
    topology = getattr(topologies, topology_name)()

    gated = _analyzer(tmp_path, topology, name="gated").analyze(section=section)
    full = _analyzer(tmp_path, topology, name="full").analyze(section=None)

    # `UX-95`'s run-instance line names *which capture* a result came
    # from, and these two deliberately come from two directories. That
    # difference is the feature working, and it is not what this test is
    # about - so it is normalised out here rather than weakened there.
    #
    # `UX-218`'s next-step commands name the run for the same reason:
    # a command that did not would not be runnable. Both directories
    # are normalised to one token, so the *commands* are still
    # compared - only the path they point at is neutralised.
    directories = [str(tmp_path / "gated"), str(tmp_path / "full")]

    def _without_instance(rendered):
        for directory in directories:
            rendered = rendered.replace(directory, "<run>")
        return "\n".join(
            line for line in rendered.splitlines() if not line.startswith("Instance: ")
        )

    assert _without_instance(format_text(gated, section=section)) == _without_instance(
        format_text(full, section=section)
    )
    gated_json = json.loads(_without_instance(format_json(gated, section=section)))
    full_json = json.loads(_without_instance(format_json(full, section=section)))
    gated_json.pop("run_instance", None)
    full_json.pop("run_instance", None)
    assert gated_json == full_json


def test_default_analyze_signature_is_unchanged(tmp_path, topology):
    """Every programmatic caller passes no section and must keep getting
    the complete result."""
    result = _analyzer(tmp_path, topology).analyze()

    assert result.attribution
    assert result.floors
    assert result.structural
    assert result.confidence
