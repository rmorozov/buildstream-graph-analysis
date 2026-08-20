"""UX-100: are the elements the right size?

Element granularity is BuildStream's oldest tuning question and every
answer today is folklore. The tool measures every ingredient of both
failure directions - the toll (`UX-99`), critical-path share (Plane 1),
internal parallelism (Plane 2), invalidation blast (`UX-92`) - and drew
no conclusion from any of them, which is the same measure-but-don't-say
gap `UX-82` closed for graph shape.

The threshold is derived from the measured toll distribution, never
chosen. These tests cover both what that means when the distribution can
decide and what it must do when it cannot.
"""
from bga.correlate import _merge_candidates, _split_candidates


class _Edge:
    def __init__(self, predecessor, successor, dependency_type="build"):
        self.predecessor = predecessor
        self.successor = successor
        self.dependency_type = dependency_type


def _cache_logs(*payers):
    return {'sandbox_tax': {'top_payers': [
        {'element': element, 'toll_us': toll, 'total_us': total,
         'toll_share': toll / total}
        for element, toll, total in payers
    ]}}


# --- the criterion -----------------------------------------------------
#
# Deriving a cut from the measured distribution was tried first and the
# real data refuses to supply one: on the freedesktop-sdk tree, 23
# elements have a median toll share of 0.0 and a MAD of 0.0, because
# BuildStream times these phases to the second. `median + k*MAD`
# collapses to the median and every element clears it. The criterion is
# the direction's own sentence instead - elements paying more toll than
# they spend building - which is a definition with nothing to tune.


# --- merge candidates ---------------------------------------------------

def test_siblings_paying_an_outlying_toll_are_a_merge_candidate():
    """The too-fine signature: several elements with the same parents,
    each spending more of its time on staging than this project's own
    distribution calls normal."""
    cache_logs = _cache_logs(
        ("tiny-a.bst", 3_000_000, 5_000_000),   # 60% toll: more setup than build
        ("tiny-b.bst", 3_000_000, 5_000_000),   # 60%
        ("big.bst", 2_000_000, 200_000_000),    # 1%
        ("other.bst", 1_000_000, 100_000_000),  # 1%
        ("more.bst", 1_000_000, 100_000_000),   # 1%
    )
    edges = [
        _Edge("base.bst", "tiny-a.bst"), _Edge("base.bst", "tiny-b.bst"),
        _Edge("base.bst", "big.bst"), _Edge("base.bst", "other.bst"),
        _Edge("base.bst", "more.bst"),
    ]
    findings = _merge_candidates(edges, cache_logs, None, None)
    assert [f['id'] for f in findings] == ['merge-candidate']
    assert findings[0]['elements'] == ['tiny-a.bst', 'tiny-b.bst']
    # Merging two deletes one staging, not two: one still happens.
    assert findings[0]['deleted_toll_us'] == 3_000_000
    assert 'merges their cache granularity' in findings[0]['title']


def test_elements_with_different_parents_are_not_siblings():
    """A merge only makes sense where the graph would not notice. Two
    elements with different parents cannot become one without changing
    what depends on what."""
    cache_logs = _cache_logs(
        ("tiny-a.bst", 3_000_000, 5_000_000),
        ("tiny-b.bst", 3_000_000, 5_000_000),
        ("big.bst", 2_000_000, 200_000_000),
        ("other.bst", 1_000_000, 100_000_000),
        ("more.bst", 1_000_000, 100_000_000),
    )
    edges = [
        _Edge("base-x.bst", "tiny-a.bst"), _Edge("base-y.bst", "tiny-b.bst"),
        _Edge("base.bst", "big.bst"), _Edge("base.bst", "other.bst"),
        _Edge("base.bst", "more.bst"),
    ]
    assert [f['id'] for f in _merge_candidates(edges, cache_logs, None, None)] == [
        'merge-not-indicated'
    ]


def test_a_large_share_of_a_tiny_element_is_arithmetic_not_a_finding():
    """`UX-99` ranks toll payers by seconds rather than by share for this
    reason, and the same floor applies here: 90% of 0.4s is not a
    finding."""
    cache_logs = _cache_logs(
        ("tiny-a.bst", 400_000, 440_000),   # 91% of 0.44s
        ("tiny-b.bst", 400_000, 440_000),
        ("big.bst", 2_000_000, 200_000_000),
        ("other.bst", 1_000_000, 100_000_000),
        ("more.bst", 1_000_000, 100_000_000),
    )
    edges = [_Edge("base.bst", name) for name in
             ("tiny-a.bst", "tiny-b.bst", "big.bst", "other.bst", "more.bst")]
    assert [f['id'] for f in _merge_candidates(edges, cache_logs, None, None)] == [
        'merge-not-indicated'
    ]


def test_nothing_firing_says_how_far_from_the_line_the_project_is():
    """The useful form of "no finding": on freedesktop-sdk the largest
    toll share is 16.7%, on a 6-second element, against the 50% that
    would make a merge worth its cache cost. Silence would leave a
    reader unable to tell that from a check that did not run."""
    cache_logs = _cache_logs(
        ("a.bst", 0, 5_000_000), ("b.bst", 0, 5_000_000),
        ("c.bst", 0, 5_000_000), ("d.bst", 1_000_000, 6_000_000),
    )
    edges = [_Edge("base.bst", name) for name in ("a.bst", "b.bst", "c.bst", "d.bst")]
    findings = _merge_candidates(edges, cache_logs, None, None)
    assert [f['id'] for f in findings] == ['merge-not-indicated']
    assert "largest tax share is 17%" in findings[0]['title']
    assert "toll" not in findings[0]['title'], (
        "UX-138/UX-154: one concept, one name - the rendered text says "
        "sandbox tax everywhere, including here")


def test_no_plane3_report_means_no_merge_half_at_all():
    """The toll is the whole basis for calling an element too small."""
    assert _merge_candidates([], None, None, None) == []


# --- split candidates ---------------------------------------------------

def _analysis(path, durations, horizon):
    return {
        'signals': {'critical_path': path, 'element_durations': durations},
        'floors': {'t_infinity_observed': horizon},
    }


def test_a_dominant_element_with_real_internal_parallelism_is_named():
    """The too-coarse signature, measured on the real capture:
    `cmake-stage1.bst` holds 44% of the critical path and runs 7.50
    concurrent work processes inside one element."""
    analysis = _analysis(["big.bst", "small.bst"],
                         {"big.bst": 44, "small.bst": 5}, 100)
    native = {'per_element_parallelism': [
        {'element': 'big.bst', 'mean_work_concurrency': 7.5, 'work_process_count': 4586},
        {'element': 'small.bst', 'mean_work_concurrency': 6.0, 'work_process_count': 10},
    ]}
    findings = _split_candidates(analysis, native)
    assert [f['elements'] for f in findings] == [['big.bst']]
    assert findings[0]['severity'] == 'info'
    # The hedge is carried on the finding, in `rationale` rather than
    # `title`: it is identical for every candidate, so the renderer says
    # it once for the group instead of once per element.
    assert 'a split\'s shape is a human decision' in findings[0]['rationale']
    assert 'big.bst' in findings[0]['title']


def test_a_serial_element_is_not_a_split_candidate():
    """Splitting buys nothing that raising its job count would not - and
    an element already running one process at a time has no internal
    parallelism to expose."""
    analysis = _analysis(["big.bst"], {"big.bst": 90}, 100)
    native = {'per_element_parallelism': [
        {'element': 'big.bst', 'mean_work_concurrency': 1.0, 'work_process_count': 900},
    ]}
    assert _split_candidates(analysis, native) == []


def test_a_parallel_element_off_the_critical_path_is_not_one_either():
    analysis = _analysis(["other.bst"], {"big.bst": 90, "other.bst": 90}, 100)
    native = {'per_element_parallelism': [
        {'element': 'big.bst', 'mean_work_concurrency': 8.0, 'work_process_count': 900},
    ]}
    assert _split_candidates(analysis, native) == []


# --- UX-120: the projection is a floor, and says so -----------------------

def _run_with_siblings(tmp_path):
    """Two sub-second siblings off one parent, each mostly staging.

    A real run directory rather than hand-built task objects, because the
    projection goes through the replay scheduler and a fake task list
    would be testing the fake.
    """
    import json

    elements = ["base.bst", "tiny-a.bst", "tiny-b.bst"]
    identity = {"manifest_hash": "granularity-fixture", "targets": elements}
    spans = [("base.bst", 0, 1_000_000),
             ("tiny-a.bst", 1_000_000, 5_000_000),
             ("tiny-b.bst", 1_000_000, 5_000_000)]
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run-context.json").write_text(json.dumps({
        "trace_epsilon_us": 1000,
        # One builder: with two, the two siblings already overlap and
        # shortening one changes no makespan at all - the projection is
        # then exactly 0 for a merge that would really delete a staging,
        # which is the same floor-not-estimate property this file's last
        # test is about, arriving from the other direction.
        "resource_capacities": {"PROCESS": 1},
        "run_identity": identity,
        "wall_clock": {"start_us": 0, "end_us": 6_000_000},
    }))
    (run_dir / "graph.json").write_text(json.dumps({
        "elements": [{"uid": uid, "requested_target": True} for uid in elements],
        "dependencies": [
            {"predecessor": "base.bst", "successor": "tiny-a.bst",
             "dependency_type": "build"},
            {"predecessor": "base.bst", "successor": "tiny-b.bst",
             "dependency_type": "build"},
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


def _merge_finding(tmp_path):
    from pathlib import Path

    from bga.analyzer import BuildEfficiencyAnalyzer

    analyzer = BuildEfficiencyAnalyzer()
    analyzer.load(Path(_run_with_siblings(tmp_path)))
    analyzer.analyze()
    cache_logs = _cache_logs(
        ("tiny-a.bst", 3_000_000, 5_000_000),
        ("tiny-b.bst", 3_000_000, 5_000_000),
    )
    findings = _merge_candidates(
        analyzer.graph.dependencies, cache_logs,
        analyzer.normalized_tasks, analyzer.run_context,
    )
    return next(f for f in findings if f['id'] == 'merge-candidate')


def test_the_projection_actually_replays_on_a_real_run(tmp_path):
    """The projection path was only ever exercised with `tasks=None`
    above, which returns `None` before reaching the scheduler - so the
    replay itself had no test at all."""
    finding = _merge_finding(tmp_path)

    assert finding['projection'] is not None
    assert finding['projection']['saving_us'] > 0


def test_the_projected_saving_is_published_as_a_floor(tmp_path):
    """UX-120 ran the loop the acceptance described - a purpose-built
    fixture of eight sub-second siblings sharing one staged sysroot - and
    the projection came back low. The replay shortens N tasks; a real
    merge leaves *one*, so the group's wave structure survives the
    projection and does not survive the merge.

    Publishing it as an unqualified estimate would make a number that is
    reliably too small look like a number that is roughly right.
    """
    finding = _merge_finding(tmp_path)

    assert finding['projection_is_a_floor'] is True
    assert "at least a replayed" in finding['title']
    assert "without collapsing them into one" in finding['title']


def test_no_user_facing_renderer_says_toll():
    """UX-154: UX-138's sweep stopped one file short, and the guard it
    claimed (`test_cache_logs.py`) was scoped to the cache-logs report
    only — so `bga correlate` went on alternating "sandbox tax" and
    "toll" inside one sentence, pinned by a test.

    Scoped to string *literals the code can print*, found by parsing
    rather than grepping: docstrings and comments recording UX-99's own
    history are exactly the places the word belongs. The JSON keys stay
    `toll_*` too - they are a published contract (`UX-75`), and renaming
    a field to tidy prose would break every consumer keyed on it.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    offenders = []
    for path in list((root / "bga").rglob("*.py")) + list((root / "tools").glob("*.py")):
        tree = ast.parse(path.read_text())
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                body = getattr(node, "body", None)
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    docstrings.add(id(body[0].value))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node) in docstrings:
                continue
            text = node.value
            # dict keys and field names are the published contract
            if text in ("toll", "toll_us", "toll_share", "toll_s"):
                continue
            if "toll" in text.replace("toll_us", "").replace("toll_share", ""):
                offenders.append(
                    f"{path.relative_to(root)}:{node.lineno}: {text.strip()[:80]}")
    assert offenders == [], (
        "user-facing 'toll' left after UX-138's sweep:\n  " + "\n  ".join(offenders))
