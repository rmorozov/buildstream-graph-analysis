"""End-to-end tests for BuildStream Build Efficiency Analyzer (bga)"""
import json
import tempfile
from pathlib import Path
from bga import BuildEfficiencyAnalyzer, analyze_run


def create_test_run_data(tmpdir: Path) -> Path:
    """Create minimal valid v9 run-context, graph, and trace data."""
    run_dir = tmpdir / "test_run"
    run_dir.mkdir()
    
    # Create run-context.json (using underscore variant for compatibility)
    run_context = {
        "version": 9,
        "run_id": "test-run-001",
        "project": "test-project",
        "trace_epsilon_us": 50000,
        "wall_clock": {
            "start_us": 0,
            "end_us": 60000000
        },
        "host": "test-host",
        "resource_capacities": {"cpu": 4},
        "max_jobs": 4
    }
    with open(run_dir / "run_context.json", "w") as f:
        json.dump(run_context, f)
    
    # Create graph.json - simple linear dependency chain
    graph = {
        "version": 9,
        "elements": [
            {"key": "elem-c", "type": "BUILD", "dependencies": []},
            {"key": "elem-b", "type": "BUILD", "dependencies": ["elem-c"]},
            {"key": "elem-a", "type": "BUILD", "dependencies": ["elem-b"]}
        ]
    }
    with open(run_dir / "graph.json", "w") as f:
        json.dump(graph, f)
    
    # Create trace.json - timeline with dependencies
    # elem-c: 0-100ms
    # elem-b: ready at 100ms, starts 150ms, ends 250ms
    # elem-a: ready at 250ms, starts 350ms, ends 450ms
    trace = {
        "version": 9,
        "tasks": [
            {
                "key": "elem-c",
                "start_time_us": 0,
                "finish_time_us": 100000,
                "duration_us": 100000,
                "resource_profile": {"cpu": 1}
            },
            {
                "key": "elem-b",
                "ready_time_us": 100000,
                "start_time_us": 150000,
                "finish_time_us": 250000,
                "duration_us": 100000,
                "resource_profile": {"cpu": 1}
            },
            {
                "key": "elem-a",
                "ready_time_us": 250000,
                "start_time_us": 350000,
                "finish_time_us": 450000,
                "duration_us": 100000,
                "resource_profile": {"cpu": 1}
            }
        ]
    }
    with open(run_dir / "trace.json", "w") as f:
        json.dump(trace, f)
    
    return run_dir


def test_basic_analysis():
    """Test basic end-to-end analysis flow."""
    print("Running test_basic_analysis...")
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = create_test_run_data(Path(tmpdir))
        
        # Run analysis
        result = analyze_run(run_dir)
        
        # Verify floors exist
        assert result.floors is not None
        assert "t_infinity_observed" in result.floors
        assert "lb" in result.floors
        assert "certified_headroom" in result.floors
        
        # Verify critical path in signals
        assert result.signals is not None
        assert "critical_path" in result.signals
        assert len(result.signals["critical_path"]) > 0
        
        # Verify attribution
        assert result.attribution is not None
        assert "execution_on_chain_us" in result.attribution
        assert "dependency_wait_us" in result.attribution
        
        print(f"  ✓ Floors: {result.floors}")
        print(f"  ✓ Critical path length: {len(result.signals['critical_path'])}")
        print(f"  ✓ Attribution: {result.attribution}")
        print("  PASSED\n")


def test_blame_chain():
    """Test blame chain computation for linear dependency."""
    print("Running test_blame_chain...")
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = create_test_run_data(Path(tmpdir))
        
        analyzer = BuildEfficiencyAnalyzer(run_dir)
        analyzer.load()
        analyzer.normalize()
        analyzer.analyze()
        
        # Get attribution results which include blame chain data
        assert analyzer.analysis_result.attribution is not None
        
        # Verify execution_on_chain and dependency_wait are present
        assert "execution_on_chain_us" in analyzer.analysis_result.attribution
        assert "dependency_wait_us" in analyzer.analysis_result.attribution
        
        print(f"  ✓ Execution on chain: {analyzer.analysis_result.attribution['execution_on_chain_us']} µs")
        print(f"  ✓ Dependency wait: {analyzer.analysis_result.attribution['dependency_wait_us']} µs")
        print("  PASSED\n")


def test_replay_scheduler():
    """Test replay scheduler produces valid makespan."""
    print("Running test_replay_scheduler...")
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = create_test_run_data(Path(tmpdir))
        
        analyzer = BuildEfficiencyAnalyzer(run_dir)
        analyzer.load()
        analyzer.normalize()
        analyzer.analyze()
        
        # Verify replay result exists
        assert analyzer.replay_scheduler is not None
        
        # Verify T_C floor is computed
        assert "t_c_replay" in analyzer.analysis_result.floors
        
        print(f"  ✓ T_C floor: {analyzer.analysis_result.floors['t_c_replay']} µs")
        print("  PASSED\n")


def test_occupancy_computation():
    """Test occupancy step function computation."""
    print("Running test_occupancy_computation...")
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = create_test_run_data(Path(tmpdir))
        
        analyzer = BuildEfficiencyAnalyzer(run_dir)
        analyzer.load()
        analyzer.normalize()
        analyzer.analyze()
        
        # Verify occupancy result
        assert analyzer.analysis_result.occupancy is not None
        assert analyzer.analysis_result.occupancy['peak_concurrency'] > 0
        
        print(f"  ✓ Peak concurrency: {analyzer.analysis_result.occupancy['peak_concurrency']}")
        print("  PASSED\n")


def test_diagnostics():
    """Test advanced diagnostics computation."""
    print("Running test_diagnostics...")
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = create_test_run_data(Path(tmpdir))
        
        analyzer = BuildEfficiencyAnalyzer(run_dir)
        analyzer.load()
        analyzer.normalize()
        analyzer.analyze()
        
        # Verify signals are populated
        assert analyzer.analysis_result.signals is not None
        assert "wall_clock_shares" in analyzer.analysis_result.signals
        assert "blast_radius" in analyzer.analysis_result.signals
        
        print(f"  ✓ Wall clock shares computed: {len(analyzer.analysis_result.signals['wall_clock_shares'])} tasks")
        print(f"  ✓ Blast radius computed: {len(analyzer.analysis_result.signals['blast_radius'])} tasks")
        print("  PASSED\n")


def test_invariants():
    """Test that key invariants hold."""
    print("Running test_invariants...")
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = create_test_run_data(Path(tmpdir))
        
        analyzer = BuildEfficiencyAnalyzer(run_dir)
        analyzer.load()
        analyzer.normalize()
        analyzer.analyze()
        
        # H >= LB invariant
        total_work_us = analyzer.analysis_result.attribution.get('total_work_us', 0)
        lb = analyzer.analysis_result.floors["lb"]
        assert total_work_us >= lb, f"H ({total_work_us}) < LB ({lb})"
        
        # T_C >= LB invariant  
        t_c = analyzer.analysis_result.floors["t_c_replay"]
        assert t_c >= lb, f"T_C ({t_c}) < LB ({lb})"
        
        # Attribution sum equals H
        attr_sum = (
            analyzer.analysis_result.attribution.get("execution_on_chain_us", 0) +
            analyzer.analysis_result.attribution.get("dependency_wait_us", 0) +
            analyzer.analysis_result.attribution.get("resource_wait_us", 0) +
            analyzer.analysis_result.attribution.get("scheduler_wait_us", 0)
        )
        # Allow small floating point tolerance
        assert abs(attr_sum - total_work_us) < 1000, f"Attribution sum {attr_sum} != H {total_work_us}"
        
        print(f"  ✓ H >= LB: {total_work_us} >= {lb}")
        print(f"  ✓ T_C >= LB: {t_c} >= {lb}")
        print(f"  ✓ Σ attribution ≈ H: {attr_sum} ≈ {total_work_us}")
        print("  PASSED\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("BuildStream Build Efficiency Analyzer - End-to-End Tests")
    print("=" * 60 + "\n")
    
    tests = [
        test_basic_analysis,
        test_blame_chain,
        test_replay_scheduler,
        test_occupancy_computation,
        test_diagnostics,
        test_invariants,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}\n")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
