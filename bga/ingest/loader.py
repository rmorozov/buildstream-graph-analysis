"""
Trace ingestion module.

Handles loading and parsing of trace data from various formats.
Currently supports Chrome JSON trace format.
"""

import json
import logging
from pathlib import Path
from typing import List

from .models import (
    DependencyEdge,
    Element,
    Graph,
    PhaseSpan,
    Resource,
    RunContext,
    TaskKey,
    TaskKind,
    TaskSpan,
    Trace,
)
from ..exceptions import IngestionError

logger = logging.getLogger(__name__)


def load_run_context(path: Path) -> RunContext:
    """
    Load run context from a JSON file.
    
    Expected schema: run-context/v9 (Part 32.1)
    """
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise IngestionError(f"Malformed JSON in run context file {path}: {e}")

    wall_clock = data.get('wall_clock', {})

    logger.info("Loaded run context from %s", path)

    return RunContext(
        trace_epsilon_us=data.get('trace_epsilon_us', 50000),
        wall_start_us=wall_clock.get('start_us'),
        wall_end_us=wall_clock.get('end_us'),
        host=data.get('host'),
        resource_capacities=data.get('resource_capacities', {}),
        max_jobs=data.get('max_jobs'),
        cpu_accounting=data.get('cpu_accounting'),
        native_max_jobs=data.get('native_max_jobs'),
        native_max_jobs_source=data.get('native_max_jobs_source'),
        host_cpu_count=data.get('host_cpu_count'),
        cpu_budget=data.get('cpu_budget'),
        memory_budget_mb=data.get('memory_budget_mb'),
        estimated_job_memory_mb=data.get('estimated_job_memory_mb'),
        exclusive_resources=data.get('exclusive_resources', []),
        pipeline_overhead=data.get('pipeline_overhead', []),
        run_identity=data.get('run_identity'),
        build_outcome=data.get('build_outcome'),
        queue_summary=data.get('queue_summary'),
    )


def _parse_resource(resource_str: str) -> Resource:
    """Parse a resource string into a Resource enum."""
    # Map common resource names to our enum
    resource_map = {
        'CPU': Resource.PROCESS,
        'PROCESS': Resource.PROCESS,
        'DOWNLOAD': Resource.DOWNLOAD,
        'FETCH': Resource.DOWNLOAD,
        'UPLOAD': Resource.UPLOAD,
        'PUSH': Resource.UPLOAD,
        'CACHE': Resource.CACHE,
    }
    
    if isinstance(resource_str, str):
        upper_name = resource_str.upper()
        if upper_name in resource_map:
            return resource_map[upper_name]
        try:
            return Resource(upper_name)
        except ValueError:
            pass
    
    return Resource.OTHER


def load_trace(path: Path) -> Trace:
    """
    Load trace from a JSON file.
    
    Expected schema: trace/v9 (Part 32.3)
    Also supports Chrome trace format with conversion.
    """
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise IngestionError(f"Malformed JSON in trace file {path}: {e}")

    spans = []
    phases = []
    
    # Check if this is trace/v9 format or Chrome trace format
    if 'spans' in data:
        # trace/v9 format
        for span_data in data.get('spans', []):
            task_key = TaskKey.from_string(span_data['task_key'])
            resources = [_parse_resource(r) for r in span_data.get('resources', [])]
            primary_resource = _parse_resource(span_data['primary_resource']) if span_data.get('primary_resource') else None
            
            spans.append(TaskSpan(
                task_key=task_key,
                ts_us=span_data['ts_us'],
                dur_us=span_data['dur_us'],
                resources=resources,
                primary_resource=primary_resource,
            ))
        
        for phase_data in data.get('phases', []):
            phases.append(PhaseSpan(
                name=phase_data['name'],
                ts_us=phase_data['ts_us'],
                dur_us=phase_data['dur_us'],
            ))
    
    elif 'tasks' in data:
        # Simplified tasks array format (common in tests)
        for task_data in data.get('tasks', []):
            key = task_data.get('key')
            element_uid = task_data.get('element_uid')
            
            if not key and not element_uid:
                continue
            
            # Build task key from either explicit 'key' or from element_uid + other fields
            if key:
                try:
                    task_key = TaskKey.from_string(key)
                except ValueError:
                    task_key = TaskKey(
                        element_uid=key,
                        task_kind=TaskKind.BUILD,
                        phase='default',
                        attempt=0,
                    )
            else:
                # Construct from element_uid and optional kind/phase/attempt fields
                task_kind_str = task_data.get('kind', 'BUILD')
                phase_str = task_data.get('phase', 'EXECUTION')
                attempt = task_data.get('attempt', 1)
                
                try:
                    task_kind = TaskKind(task_kind_str)
                except ValueError:
                    task_kind = TaskKind.BUILD
                
                task_key = TaskKey(
                    element_uid=element_uid,
                    task_kind=task_kind,
                    phase=phase_str,
                    attempt=attempt,
                )
            
            start_time = task_data.get('start_us', task_data.get('start_time_us', 0))
            finish_time = task_data.get('finish_us', task_data.get('finish_time_us', 0))
            duration = task_data.get('duration_us', finish_time - start_time)
            
            # Parse resource profile
            resources = []
            resource_profile = task_data.get('resource_profile', {})
            if isinstance(resource_profile, dict):
                for res_name in resource_profile.keys():
                    resources.append(_parse_resource(res_name))
            
            primary_resource = None
            if resources:
                primary_resource = resources[0]
            
            spans.append(TaskSpan(
                task_key=task_key,
                ts_us=start_time,
                dur_us=duration,
                resources=resources,
                primary_resource=primary_resource,
            ))
    
    elif 'traceEvents' in data:
        # Chrome trace format - convert to our model
        for event in data['traceEvents']:
            if event.get('ph') == 'X':  # Complete event
                name = event.get('name', '')
                ts = int(event.get('ts', 0))  # Chrome uses microseconds
                dur = int(event.get('dur', 0))
                
                # Parse task key from name or args
                task_key_str = event.get('args', {}).get('task_key', name)
                try:
                    task_key = TaskKey.from_string(task_key_str)
                except ValueError:
                    # Create a synthetic task key
                    task_key = TaskKey(
                        element_uid=name,
                        task_kind=TaskKind.OTHER,
                        phase='default',
                        attempt=0,
                    )
                
                resources = []
                resource_str = event.get('args', {}).get('resources', [])
                if isinstance(resource_str, list):
                    resources = [_parse_resource(r) for r in resource_str]
                elif isinstance(resource_str, str):
                    resources = [_parse_resource(resource_str)]
                
                primary_resource = None
                pr_str = event.get('args', {}).get('primary_resource')
                if pr_str:
                    primary_resource = _parse_resource(pr_str)
                
                spans.append(TaskSpan(
                    task_key=task_key,
                    ts_us=ts,
                    dur_us=dur,
                    resources=resources,
                    primary_resource=primary_resource,
                ))
            
            elif event.get('ph') == 'P':  # Phase/interval event
                name = event.get('name', '')
                ts = int(event.get('ts', 0))
                dur = int(event.get('dur', 0))
                
                phases.append(PhaseSpan(
                    name=name,
                    ts_us=ts,
                    dur_us=dur,
                ))
    
    logger.info("Loaded trace from %s: %d spans, %d phases", path, len(spans), len(phases))
    return Trace(spans=spans, phases=phases, run_identity_hash=data.get('run_identity_hash'))


def load_graph(path: Path) -> Graph:
    """
    Load dependency graph from a JSON file.

    Expected schema: graph/v9 (Part 32.2)
    """
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise IngestionError(f"Malformed JSON in graph file {path}: {e}")

    elements = []
    dependencies = []

    for elem_data in data.get('elements', []):
        # Support both explicit uid and key-based identification
        uid = elem_data.get('uid', elem_data.get('key'))
        if uid is None:
            raise IngestionError("Element must have either 'uid' or 'key' field")
        
        elements.append(Element(
            uid=uid,
            cache_key=elem_data.get('cache_key'),
            requested_target=elem_data.get('requested_target', False),
            element_kind=elem_data.get('element_kind'),
            max_jobs=elem_data.get('max_jobs'),
            notparallel=elem_data.get('notparallel'),
        ))
    
    # Support both explicit dependencies list and inline dependencies
    if 'dependencies' in data:
        for dep_data in data['dependencies']:
            dependencies.append(DependencyEdge(
                predecessor=dep_data['predecessor'],
                successor=dep_data['successor'],
                dependency_type=dep_data.get('dependency_type', 'build'),
            ))
    else:
        # Extract dependencies from element definitions
        for elem_data in data.get('elements', []):
            elem_uid = elem_data.get('uid', elem_data.get('key'))
            for dep_key in elem_data.get('dependencies', []):
                dependencies.append(DependencyEdge(
                    predecessor=dep_key,
                    successor=elem_uid,
                    dependency_type='build',
                ))
    
    logger.info(
        "Loaded graph from %s: %d elements, %d dependencies",
        path, len(elements), len(dependencies),
    )
    return Graph(elements=elements, dependencies=dependencies, run_identity_hash=data.get('run_identity_hash'))


def load_chrome_trace(path: Path) -> Trace:
    """
    Load a Chrome trace format file directly.
    
    This is a convenience function for the common case where
    BuildStream outputs Chrome trace format.
    """
    return load_trace(path)


def load_all(run_dir: Path) -> tuple[RunContext, Graph, Trace]:
    """
    Load all input files from a run directory.
    
    Expected structure:
        run_dir/
            run-context.json  (or run_context.json for legacy)
            graph.json
            trace.json
    
    Supports both hyphenated and underscored filenames for compatibility.
    """
    # Support both naming conventions: run-context.json and run_context.json
    run_context_path = run_dir / 'run-context.json'
    if not run_context_path.exists():
        run_context_path = run_dir / 'run_context.json'
    
    run_context = load_run_context(run_context_path)
    graph = load_graph(run_dir / 'graph.json')
    trace = load_trace(run_dir / 'trace.json')

    return run_context, graph, trace


def load_historical_runs(run_dirs: List[Path]) -> List[tuple[RunContext, Graph, Trace]]:
    """
    Load one or more prior runs' trace/graph data (Part 15.2 - the
    duration-source hierarchy for the advisory cold structural floor
    needs historical execution data to resolve cold durations from).

    Each directory is loaded independently via load_all; a directory
    that fails to load (missing/malformed files) raises, same as load_all -
    callers that want best-effort loading across many historical runs
    should catch per-directory rather than relying on this function to
    skip failures silently.
    """
    return [load_all(run_dir) for run_dir in run_dirs]
