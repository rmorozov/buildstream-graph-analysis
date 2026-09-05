"""UX-82: the tool measured every fact of the macro fix and never stated it.

On `examples/06`'s baseline, `bga` had all of it: a ten-element critical
path with `lib-a..lib-f` six links of it, and `correlate` reporting **each
of the five chain edges** as "opened no file staged by …". Five
disconnected, deliberately-hedged rows, ranked last by design (`UX-68`) —
and the one conclusion they jointly support, *these six elements form a
chain whose every internal edge is unread; fan them out*, was never
drawn. It was the biggest win in the project: measured that round at
27.9s → 25.0s, −10.1%.
"""
import json

from bga.analyzer import BuildEfficiencyAnalyzer
from bga.correlate import correlate, format_correlation

D = 4_000_000


def _write_run(tmp_path, name, elements, deps, spans, builders=4):
    run_dir = tmp_path / name
    run_dir.mkdir()
    identity = {"manifest_hash": f"fixture-{name}", "targets": list(elements)}
    end = max(start + dur for _, start, dur in spans)
    (run_dir / "run-context.json").write_text(json.dumps({
        "trace_epsilon_us": 1000,
        "resource_capacities": {"PROCESS": builders},
        "run_identity": identity,
        "wall_clock": {"start_us": 0, "end_us": end},
    }))
    (run_dir / "graph.json").write_text(json.dumps({
        "elements": [{"uid": uid, "requested_target": True} for uid in elements],
        "dependencies": [
            {"predecessor": a, "successor": b, "dependency_type": "build"}
            for a, b in deps
        ],
        "run_identity_hash": identity["manifest_hash"],
    }))
    (run_dir / "trace.json").write_text(json.dumps({
        "run_identity_hash": identity["manifest_hash"],
        "spans": [
            {"task_key": f"{uid}|BUILD|BUILD|0", "ts_us": start, "dur_us": dur,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"}
            for uid, start, dur in spans
        ],
        "phases": [],
    }))
    return run_dir


LIBS = [f"lib-{c}.bst" for c in "abcdef"]


def _chained_libs(tmp_path):
    """`examples/06`'s baseline shape: six libraries chained instead of
    fanned out, every internal edge decorative."""
    elements = ["base.bst"] + LIBS
    # Every library really depends on `base`; the chain edges on top of
    # that are the decoration. Removing them must leave the libraries
    # depending on `base`, not on nothing - which is what makes the
    # projection a fan-out onto the available builders rather than a
    # free-for-all.
    deps = [("base.bst", uid) for uid in LIBS] + list(zip(LIBS, LIBS[1:]))
    spans = [("base.bst", 0, D)] + [
        (uid, D + i * D, D) for i, uid in enumerate(LIBS)
    ]
    return _write_run(tmp_path, "baseline", elements, deps, spans)


def _analysis_and_parts(run_dir):
    from bga.report.json import format_json

    analyzer = BuildEfficiencyAnalyzer()
    result = analyzer.analyze(run_dir)
    return (
        json.loads(format_json(result)),
        analyzer.normalized_tasks,
        analyzer.run_context,
    )


def _native(unused, elements=LIBS):
    return {
        "by_element": dict.fromkeys(elements, 1),
        "per_element_parallelism": [],
        "cpu_time": {"per_element": {}},
        "element_attribution": {"reliable": True, "unattributed_processes": 0},
        "declared_vs_used": {"unused_candidates": unused},
    }


def _every_chain_edge_unread():
    return [
        {"element": successor, "dependency": predecessor}
        for predecessor, successor in zip(LIBS, LIBS[1:])
    ]


def test_the_chain_becomes_one_finding_not_five_rows(tmp_path):
    analysis, tasks, context = _analysis_and_parts(_chained_libs(tmp_path))

    result = correlate(
        analysis, _native(_every_chain_edge_unread()), tasks=tasks, run_context=context,
    )

    assert len(result["restructuring"]) == 1
    finding = result["restructuring"][0]
    assert finding["id"] == "unread-gating-chain"
    assert finding["elements"] == LIBS
    assert len(finding["edges"]) == 5


def test_the_projection_replays_the_run_without_those_edges(tmp_path):
    """The prize, replayed rather than guessed. Six 4s libraries chained
    behind a 4s base take 28s; fanned out onto 4 builders they take 12s,
    which the replay - same durations, same capacity - finds on its own."""
    analysis, tasks, context = _analysis_and_parts(_chained_libs(tmp_path))

    finding = correlate(
        analysis, _native(_every_chain_edge_unread()), tasks=tasks, run_context=context,
    )["restructuring"][0]
    projection = finding["projection"]

    assert projection["replayed_baseline_us"] == 28 * 1_000_000
    assert projection["projected_us"] == 12 * 1_000_000
    assert projection["saving_us"] == 16 * 1_000_000


def test_the_finding_is_rendered_above_the_per_element_rows(tmp_path):
    analysis, tasks, context = _analysis_and_parts(_chained_libs(tmp_path))

    text = format_correlation(correlate(
        analysis, _native(_every_chain_edge_unread()), tasks=tasks, run_context=context,
    ))

    assert "Restructuring opportunity" in text
    assert "lib-a.bst -> lib-b.bst" in text
    assert text.index("Restructuring opportunity") < text.index("What to do next")


def test_the_hedge_survives_the_synthesis(tmp_path):
    """`UX-68`'s caveat is not weakened by aggregating five instances of
    it - the finding recommends *checking* the edges, with the prize
    attached, and says the projection is not a re-capture."""
    analysis, tasks, context = _analysis_and_parts(_chained_libs(tmp_path))

    text = format_correlation(correlate(
        analysis, _native(_every_chain_edge_unread()), tasks=tasks, run_context=context,
    ))

    assert "evidence, not a verdict" in text
    assert "not a re-capture" in text


def test_an_edge_that_was_read_is_not_in_any_finding(tmp_path):
    """`examples/07`'s `user.bst` case: a genuinely-consumed edge must
    never be proposed for removal."""
    analysis, tasks, context = _analysis_and_parts(_chained_libs(tmp_path))

    result = correlate(
        analysis,
        _native([{"element": "lib-c.bst", "dependency": "lib-b.bst"}]),
        tasks=tasks, run_context=context,
    )

    finding = result["restructuring"][0]
    assert finding["edges"] == [["lib-b.bst", "lib-c.bst"]]
    assert "lib-a.bst" not in finding["elements"]


def test_an_unread_edge_off_the_critical_path_is_not_a_restructuring_finding(tmp_path):
    """An unread edge that holds nothing up is a true observation and not
    a restructuring opportunity; it stays a per-element row."""
    elements = ["base.bst", "slow.bst", "fast.bst", "leaf.bst"]
    deps = [("base.bst", "slow.bst"), ("base.bst", "fast.bst"),
            ("fast.bst", "leaf.bst")]
    spans = [("base.bst", 0, D), ("slow.bst", D, 10 * D),
             ("fast.bst", D, D), ("leaf.bst", 2 * D, D)]
    run_dir = _write_run(tmp_path, "offpath", elements, deps, spans)
    analysis, tasks, context = _analysis_and_parts(run_dir)

    result = correlate(
        analysis,
        _native([{"element": "leaf.bst", "dependency": "fast.bst"}],
                elements=["fast.bst", "leaf.bst"]),
        tasks=tasks, run_context=context,
    )

    assert result["restructuring"] == []


def test_without_the_run_the_finding_still_names_the_chain(tmp_path):
    """`correlate` is a library over two finished artifacts; the tasks
    are an optional extra the CLI happens to have. Losing them must cost
    the projection, not the finding."""
    analysis, _tasks, _context = _analysis_and_parts(_chained_libs(tmp_path))

    finding = correlate(
        analysis, _native(_every_chain_edge_unread()),
    )["restructuring"][0]

    assert finding["elements"] == LIBS
    assert finding["projection"] is None
