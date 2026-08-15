"""P3-09: per-module unit tests for bga/replay/scheduler.py.

Deterministic replay scheduler basic correctness and capacity-sweep
monotonicity (Part 18/19), on small hand-built NormalizedTask lists -
no run-dir/JSON fixture needed.
"""
from bga.ingest.models import NormalizedTask, Resource, RunContext, TaskKey, TaskKind
from bga.replay.scheduler import ReplayScheduler


def _task(uid, dur_us, dependencies=()):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=0, start_us=0, finish_us=dur_us,
        dependencies=list(dependencies), resources=[Resource.PROCESS],
    )


def test_dependency_chain_is_scheduled_in_order():
    """a -> b -> c, each 1000us, ample capacity - the dependency chain
    alone forces full serialization regardless of capacity."""
    a = _task("a.bst", 1000)
    b = _task("b.bst", 2000, dependencies=[str(a.task_key)])
    c = _task("c.bst", 3000, dependencies=[str(b.task_key)])
    scheduler = ReplayScheduler([a, b, c])

    result = scheduler.replay(capacities={"PROCESS": 4})
    by_key = {t.task_key: t for t in result.scheduled_tasks}

    assert by_key[str(a.task_key)].start_us == 0
    assert by_key[str(a.task_key)].finish_us == 1000
    assert by_key[str(b.task_key)].start_us == 1000
    assert by_key[str(b.task_key)].finish_us == 3000
    assert by_key[str(c.task_key)].start_us == 3000
    assert by_key[str(c.task_key)].finish_us == 6000
    assert result.makespan_us == 6000


def test_independent_tasks_serialize_under_capacity_one():
    """3 independent (no dependency) tasks, 1000us each, capacity 1 -
    must fully serialize: makespan == sum of durations."""
    tasks = [_task(f"t{i}.bst", 1000) for i in range(3)]
    scheduler = ReplayScheduler(tasks)

    result = scheduler.replay(capacities={"PROCESS": 1})
    assert result.makespan_us == 3000


def test_independent_tasks_parallelize_under_sufficient_capacity():
    """Same 3 independent tasks, capacity 3 - full parallelism,
    makespan == the single longest task's duration."""
    tasks = [_task(f"t{i}.bst", 1000) for i in range(3)]
    scheduler = ReplayScheduler(tasks)

    result = scheduler.replay(capacities={"PROCESS": 3})
    assert result.makespan_us == 1000


def test_default_capacities_use_real_run_context_resource_capacities():
    """P2-09: ReplayScheduler's own default-capacity fallback previously
    read nonexistent run_context.builders/fetchers/pushers attributes
    (RunContext has never defined them - only the real resource_capacities
    field), always silently falling back to the hardcoded 4/2/2 regardless
    of the run's actual capacities. 5 independent 1000us tasks, a real
    run_context declaring resource_capacities={"PROCESS": 5}, no explicit
    capacities passed to .replay() - must use the real capacity 5 (full
    parallelism, makespan == 1000), not the stale hardcoded default of 4
    (which would force the 5th task to wait, makespan == 2000)."""
    tasks = [_task(f"t{i}.bst", 1000) for i in range(5)]
    run_context = RunContext(resource_capacities={"PROCESS": 5})
    scheduler = ReplayScheduler(tasks, run_context)

    result = scheduler.replay()

    assert result.makespan_us == 1000


def test_default_capacities_fall_back_to_hardcoded_defaults_without_run_context():
    """Regression: no run_context at all - unaffected, still falls back
    to the hardcoded default (PROCESS capacity 4), same as before P2-09."""
    tasks = [_task(f"t{i}.bst", 1000) for i in range(5)]
    scheduler = ReplayScheduler(tasks, run_context=None)

    result = scheduler.replay()

    assert result.makespan_us == 2000


def test_capacity_sweep_is_monotonic_and_hits_expected_endpoints():
    """5 independent 1000us tasks - makespan must never increase as
    PROCESS capacity increases (Part 19), and must range from the fully
    serial endpoint (5000us at capacity 1) down to the fully parallel
    endpoint (1000us at capacity 5)."""
    tasks = [_task(f"t{i}.bst", 1000) for i in range(5)]
    scheduler = ReplayScheduler(tasks)

    sweep = scheduler.capacity_sweep("PROCESS", min_capacity=1, max_capacity=5)

    assert sweep.is_monotonic("PROCESS")
    assert sweep.monotonicity_violations == []
    makespans = [s["makespan_us"] for s in sweep.sweeps]
    assert makespans[0] == 5000  # capacity 1: fully serial
    assert makespans[-1] == 1000  # capacity 5: fully parallel
    assert makespans == sorted(makespans, reverse=True)


def test_capacity_sweep_first_sample_normalized_improvement_is_not_nan():
    """Regression guard for the P1-14-adjacent NaN bug: the first sweep
    sample has no prior makespan to compare against, so
    normalized_improvement must be a real number (0), never NaN."""
    tasks = [_task(f"t{i}.bst", 1000) for i in range(3)]
    scheduler = ReplayScheduler(tasks)

    sweep = scheduler.capacity_sweep("PROCESS", min_capacity=1, max_capacity=3)
    first = sweep.sweeps[0]["normalized_improvement"]
    assert first == 0
    assert first == first  # NaN != NaN; this fails if it were ever NaN again


# --- P1-34: `fifo` priority must be genuinely deterministic (not a
# per-process-randomized hash), and `depth` must be real, not an LPT
# duplicate ---

def test_fifo_tie_break_is_lexicographic_by_task_key():
    """Several independent same-duration tasks, capacity 1 (forces
    strict one-at-a-time ordering) - fifo must schedule them in
    task_key's own lexicographic order, regardless of construction/push
    order (pushed here in reverse - c, b, a)."""
    tasks = [_task(uid, 1000) for uid in ("c.bst", "b.bst", "a.bst")]
    scheduler = ReplayScheduler(tasks)

    result = scheduler.replay(capacities={"PROCESS": 1}, priority_rule="fifo")
    order = [t.task_key for t in sorted(result.scheduled_tasks, key=lambda t: t.start_us)]

    assert order == sorted(order)
    assert order[0].startswith("a.bst")
    assert order[1].startswith("b.bst")
    assert order[2].startswith("c.bst")


def test_fifo_is_deterministic_across_separate_processes():
    """The real bug (P1-34): a hash-derived priority is stable within
    one process (hash seed fixed per-process) but can differ across
    separate process invocations - exactly what a single-process-repeat
    determinism check (P1-35) cannot catch. Run the same fifo replay in
    two genuinely separate Python processes and compare."""
    import json
    import os
    import subprocess
    import sys

    script = (
        "from bga.ingest.models import NormalizedTask, Resource, TaskKey, TaskKind\n"
        "from bga.replay.scheduler import ReplayScheduler\n"
        "import json\n"
        "def _task(uid, dur_us):\n"
        "    return NormalizedTask(\n"
        "        task_key=TaskKey(uid, TaskKind.BUILD, 'BUILD', 0),\n"
        "        ready_us=0, start_us=0, finish_us=dur_us,\n"
        "        resources=[Resource.PROCESS],\n"
        "    )\n"
        "tasks = [_task(f't{i}.bst', 1000) for i in range(8)]\n"
        "scheduler = ReplayScheduler(tasks)\n"
        "result = scheduler.replay(capacities={'PROCESS': 1}, priority_rule='fifo')\n"
        "order = [t.task_key for t in sorted(result.scheduled_tasks, key=lambda t: t.start_us)]\n"
        "print(json.dumps({'makespan_us': result.makespan_us, 'order': order}))\n"
    )

    runs = []
    for seed in ("1", "2"):
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, check=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        )
        runs.append(json.loads(proc.stdout))

    assert runs[0] == runs[1]


def test_depth_rule_prioritizes_longer_remaining_chain_not_duration():
    """Two independent roots ready at t=0, same duration (so lpt/spt
    can't tell them apart) - one heads a 3-deep chain, the other a
    single task. Capacity 1 forces a strict choice: `depth` must pick
    the root of the longer chain first (real longest-remaining-path
    behavior), proving it's not silently identical to `lpt` (the
    original bug - both branches returned `-duration`)."""
    deep_root = _task("deep-root.bst", 1000)
    deep_mid = _task("deep-mid.bst", 1000, dependencies=[str(deep_root.task_key)])
    deep_leaf = _task("deep-leaf.bst", 1000, dependencies=[str(deep_mid.task_key)])
    shallow_root = _task("shallow-root.bst", 1000)

    scheduler = ReplayScheduler([deep_root, deep_mid, deep_leaf, shallow_root])
    result = scheduler.replay(capacities={"PROCESS": 1}, priority_rule="depth")

    first_scheduled = min(result.scheduled_tasks, key=lambda t: t.start_us)
    assert first_scheduled.task_key.startswith("deep-root.bst")


def test_depth_computation_tolerates_dependency_on_excluded_task():
    """Regression guard: a task's `dependencies` list can reference a
    task_key that isn't part of this scheduler's own task set at all
    (e.g. excluded upstream by P1-36's negative-duration guard, or a
    cyclic-graph input mid-way through cycle detection) - found via a
    real interaction with P1-36 that crashed
    tests/unit/test_cli_exit_codes.py::test_cyclic_graph_exits_three
    with an uncaught KeyError in the initial version of this fix.
    ReplayScheduler construction itself must never crash over this."""
    only_task = _task("b.bst", 1000, dependencies=["a.bst|BUILD|BUILD|0"])
    scheduler = ReplayScheduler([only_task])  # "a.bst" is not in the task list
    assert scheduler._task_depths.get(str(only_task.task_key)) == 0


def test_hash_is_never_called_in_replay_scheduler():
    """Structural regression guard (P1-34's own acceptance test): parse
    the module's AST and confirm no call to the builtin hash() exists
    anywhere in it - a hash-derived priority is the exact bug this task
    fixes, so this must stay true, not just true today."""
    import ast
    import inspect

    import bga.replay.scheduler as scheduler_module

    tree = ast.parse(inspect.getsource(scheduler_module))
    hash_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "hash"
    ]
    assert hash_calls == []
