"""
Trace ingestion module.

Handles loading and parsing of trace data from various formats.
Currently supports Chrome JSON trace format.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def load_run_context(path: Path) -> RunContext:
    """
    Load run context from a JSON file.
    
    Expected schema: run-context/v9 (Part 32.1)
    """
    with open(path, 'r') as f:
        data = json.load(f)
    
    wall_clock = data.get('wall_clock', {})
    
    return RunContext(
        trace_epsilon_us=data.get('trace_epsilon_us', 50000),
        wall_start_us=wall_clock.get('start_us'),
        wall_end_us=wall_clock.get('end_us'),
        host=data.get('host'),
        resource_capacities=data.get('resource_capacities', {}),
        max_jobs=data.get('max_jobs'),
        cpu_accounting=data.get('cpu_accounting'),
    )


def _parse_resource(resource_str: str) -> Resource:
    """Parse a resource string into a Resource enum."""
    try:
        return Resource(resource_str.upper())
    except ValueError:
        return Resource.OTHER


def load_trace(path: Path) -> Trace:
    """
    Load trace from a JSON file.
    
    Expected schema: trace/v9 (Part 32.3)
    Also supports Chrome trace format with conversion.
    """
    with open(path, 'r') as f:
        data = json.load(f)
    
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
    
    return Trace(spans=spans, phases=phases)


def load_graph(path: Path) -> Graph:
    """
    Load dependency graph from a JSON file.
    
    Expected schema: graph/v9 (Part 32.2)
    """
    with open(path, 'r') as f:
        data = json.load(f)
    
    elements = []
    dependencies = []
    
    for elem_data in data.get('elements', []):
        # Support both explicit uid and key-based identification
        uid = elem_data.get('uid', elem_data.get('key'))
        if uid is None:
            raise ValueError("Element must have either 'uid' or 'key' field")
        
        elements.append(Element(
            uid=uid,
            cache_key=elem_data.get('cache_key'),
            requested_target=elem_data.get('requested_target', False),
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
    
    return Graph(elements=elements, dependencies=dependencies)


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
