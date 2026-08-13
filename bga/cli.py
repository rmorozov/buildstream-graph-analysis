#!/usr/bin/env python3
"""
BuildStream Build Efficiency Analyzer (bga) - Command Line Interface

This module provides the CLI entry point for analyzing BuildStream build traces.
It implements all commands documented in docs/cli.md.

Usage:
    bga analyze <run_directory> [options]
    bga --version
    bga --help

Examples:
    bga analyze /path/to/run-12345
    bga analyze /path/to/run-12345 --format json --output report.json
    bga analyze /path/to/run-12345 --capacity 16 --replay --heuristic lpt
    bga analyze /path/to/run-12345 --diagnostics --format json | jq '.floors'
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .analyzer import BuildEfficiencyAnalyzer, AnalysisResult


def format_text(result: AnalysisResult) -> str:
    """
    Format analysis results as human-readable text.
    
    Args:
        result: The AnalysisResult object from the analyzer
        
    Returns:
        Formatted string suitable for terminal display
    """
    lines = []
    lines.append("=" * 60)
    lines.append("Build Efficiency Report")
    lines.append("=" * 60)
    lines.append(f"Run: {result.run_id}")
    lines.append(f"Total Duration: {result.total_duration_us / 1e6:.1f}s")
    lines.append("")
    
    # Certified Floors (Parts 14-17)
    lines.append("Certified Floors:")
    floors = result.floors
    t_inf = floors.get('t_infinity_observed') or floors.get('t_infinity_observed_us', 0)
    lb_val = floors.get('lb') or floors.get('lb_us', 0)
    headroom = floors.get('certified_headroom') or floors.get('certified_headroom_us', 0)
    lines.append(f"  T∞ (observed critical path): {t_inf / 1e6:.2f}s")
    lines.append(f"  LB (resource lower bound):   {lb_val / 1e6:.2f}s")
    lines.append(f"  Certified Headroom:          {headroom / 1e6:.2f}s")
    t_replay = floors.get('t_c') or floors.get('t_replay_us')
    if t_replay is not None:
        lines.append(f"  T_C (replay makespan):       {t_replay / 1e6:.2f}s")
    lines.append("")
    
    # Attribution (Part 11-12)
    if hasattr(result, 'attribution') and result.attribution:
        lines.append("Attribution Breakdown:")
        total = result.total_duration_us
        for category, duration_us in result.attribution.items():
            pct = (duration_us / total * 100) if total > 0 else 0
            lines.append(f"  {category.replace('_', ' ').title():25s} {duration_us / 1e6:8.2f}s ({pct:5.1f}%)")
        lines.append("")
    
    # Critical Path (Part 14.1)
    if hasattr(result, 'critical_path') and result.critical_path:
        lines.append(f"Critical Path Length: {len(result.critical_path)} elements")
        if len(result.critical_path) <= 5:
            cp_str = " → ".join([t.task_key.element_name for t in result.critical_path])
            lines.append(f"  Path: {cp_str}")
        lines.append("")
    
    # Occupancy Stats (Part 4)
    if hasattr(result, 'occupancy_stats') and result.occupancy_stats:
        lines.append("Occupancy Statistics:")
        lines.append(f"  Max Parallelism: {result.occupancy_stats.get('max_parallelism', 0):.1f}x")
        lines.append(f"  Avg Parallelism: {result.occupancy_stats.get('avg_parallelism', 0):.1f}x")
        lines.append("")
    
    # Diagnostics (Part 20-29, M5)
    if hasattr(result, 'signals') and result.signals:
        lines.append("Advanced Diagnostics:")
        if 'blast_radius' in result.signals:
            br_data = result.signals['blast_radius']
            # Handle both dict format and dataclass format
            if isinstance(br_data, dict) and br_data:
                max_blast = max((v.get('downstream_count', 0) if isinstance(v, dict) else getattr(v, 'blast_count', 0)) for v in br_data.values())
                lines.append(f"  Max Blast Radius: {max_blast} downstream elements")
            elif isinstance(br_data, list) and br_data:
                max_blast = max((br.blast_count for br in br_data if hasattr(br, 'blast_count')), default=0)
                lines.append(f"  Max Blast Radius: {max_blast} downstream elements")
        if 'criticality_probability' in result.signals:
            cp_data = result.signals['criticality_probability']
            # Handle both dict format and dataclass format
            high_crit = 0
            if isinstance(cp_data, dict):
                high_crit = sum(1 for v in cp_data.values() if (isinstance(v, dict) and v.get('probability', 0) > 0.5) or (hasattr(v, 'probability') and v.probability > 0.5))
            elif isinstance(cp_data, list):
                high_crit = sum(1 for cp in cp_data if getattr(cp, 'probability', 0) > 0.5)
            lines.append(f"  High Criticality Elements: {high_crit} (>50% probability)")
        lines.append("")
    
    # Structural Analysis (M6)
    if hasattr(result, 'structural_metrics') and result.structural_metrics:
        lines.append("Structural Analysis:")
        sm = result.structural_metrics
        if 'bottlenecks' in sm and sm['bottlenecks']:
            lines.append(f"  Bottlenecks Identified: {len(sm['bottlenecks'])}")
        if 'parallelism_profile' in sm:
            pp = sm['parallelism_profile']
            lines.append(f"  Parallelism Profile: min={pp.get('min_parallelism', 0):.1f}x, max={pp.get('max_parallelism', 0):.1f}x")
        lines.append("")
    
    lines.append("=" * 60)
    return "\n".join(lines)


def format_json(result: AnalysisResult) -> str:
    """
    Format analysis results as JSON.
    
    Args:
        result: The AnalysisResult object from the analyzer
        
    Returns:
        JSON string suitable for machine processing
    """
    data = {
        'run_id': result.run_id,
        'total_duration_us': result.total_duration_us,
        'floors': result.floors,
    }
    
    if hasattr(result, 'attribution') and result.attribution:
        data['attribution'] = result.attribution
    
    if hasattr(result, 'critical_path') and result.critical_path:
        data['critical_path'] = [
            {
                'element': t.task_key.element_name,
                'kind': t.task_key.kind.value,
                'start_us': t.start_us,
                'dur_us': t.dur_us,
            }
            for t in result.critical_path
        ]
    
    # occupancy field - check both occupancy (AnalysisResult field) and occupancy_stats (legacy name)
    if hasattr(result, 'occupancy') and result.occupancy:
        data['occupancy'] = result.occupancy
    elif hasattr(result, 'occupancy_stats'):
        data['occupancy'] = result.occupancy_stats
    
    if hasattr(result, 'signals') and result.signals:
        # Convert dataclasses to dicts for JSON serialization
        signals_data = {}
        for key, value in result.signals.items():
            if isinstance(value, list) and value:
                if hasattr(value[0], '__dict__'):
                    signals_data[key] = [v.__dict__ if hasattr(v, '__dict__') else v for v in value]
                else:
                    signals_data[key] = value
            elif hasattr(value, '__dict__'):
                signals_data[key] = value.__dict__
            else:
                signals_data[key] = value
        data['signals'] = signals_data
    
    if hasattr(result, 'structural_metrics') and result.structural_metrics:
        data['structural'] = result.structural_metrics
    
    return json.dumps(data, indent=2, default=str)


def format_csv(result: AnalysisResult) -> str:
    """
    Format attribution results as CSV.
    
    Args:
        result: The AnalysisResult object from the analyzer
        
    Returns:
        CSV string with attribution breakdown
    """
    lines = ["category,duration_us,duration_s,percent"]
    total = result.total_duration_us
    
    if hasattr(result, 'attribution') and result.attribution:
        for category, duration_us in result.attribution.items():
            pct = (duration_us / total * 100) if total > 0 else 0
            lines.append(f"{category},{duration_us},{duration_us / 1e6:.6f},{pct:.2f}")
    
    return "\n".join(lines)


def cmd_analyze(args: argparse.Namespace) -> int:
    """
    Execute the analyze command.
    
    This is the main entry point for the `bga analyze` subcommand.
    It orchestrates the full analysis pipeline including:
    1. Data ingestion (run-context/v9, graph/v9, trace/v9)
    2. Timestamp normalization and ordering validation
    3. Occupancy computation
    4. Graph analysis and critical path
    5. Blame chain attribution
    6. Replay scheduling (if requested)
    7. Diagnostics (if requested)
    8. Structural analysis (M6)
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    run_dir = Path(args.directory)
    
    if not run_dir.exists():
        print(f"Error: Directory does not exist: {run_dir}", file=sys.stderr)
        return 1
    
    if not run_dir.is_dir():
        print(f"Error: Not a directory: {run_dir}", file=sys.stderr)
        return 1
    
    try:
        # Initialize analyzer with configuration from args
        analyzer = BuildEfficiencyAnalyzer(
            capacity=args.capacity,
            run_replay=args.replay,
            replay_heuristic=args.heuristic,
            run_diagnostics=args.diagnostics,
            verbose=args.verbose,
        )
        
        # Run full analysis pipeline
        result = analyzer.analyze(run_dir)
        
        # Format output based on requested format
        if args.format == 'json':
            output = format_json(result)
        elif args.format == 'csv':
            output = format_csv(result)
        else:
            output = format_text(result)
        
        # Write to file or stdout
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(output)
            if args.verbose:
                print(f"Report written to: {output_path}", file=sys.stderr)
        else:
            print(output)
        
        return 0
        
    except ValueError as e:
        # Cycle detection and other validation errors - exit code 3 per docs/cli.md
        if 'cycle' in str(e).lower():
            print(f"Error: Graph contains a cycle - {e}", file=sys.stderr)
            return 3
        else:
            print(f"Error: {e}", file=sys.stderr)
            return 2
    except json.JSONDecodeError as e:
        print(f"Error: Malformed JSON in input file - {e}", file=sys.stderr)
        return 2
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 2


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser with full inline documentation.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog='bga',
        description='BuildStream Build Efficiency Analyzer - Analyze build traces for efficiency metrics',
        epilog='See docs/cli.md for detailed usage examples and workflows.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
        help='Show program version and exit'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze subcommand
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze a BuildStream run directory',
        description='Analyze a directory containing BuildStream run artifacts (run-context/v9, graph/v9, trace/v9)',
    )
    
    analyze_parser.add_argument(
        'directory',
        type=str,
        help='Path to the BuildStream run directory (e.g., ~/.buildstream/cache/artifacts/run-<uuid>)'
    )
    
    analyze_parser.add_argument(
        '-f', '--format',
        type=str,
        choices=['text', 'json', 'csv'],
        default='text',
        help='Output format: text (human-readable), json (machine-readable), csv (attribution data). Default: text'
    )
    
    analyze_parser.add_argument(
        '-o', '--output',
        type=str,
        help='Write output to file instead of stdout'
    )
    
    analyze_parser.add_argument(
        '-c', '--capacity',
        type=int,
        default=None,
        metavar='N',
        help='Override system resource capacity (affects LB and replay calculations). Default: auto-detect from run-context'
    )
    
    analyze_parser.add_argument(
        '-r', '--replay',
        action='store_true',
        help='Run deterministic replay scheduler to compute optimal makespan (T_C)'
    )
    
    analyze_parser.add_argument(
        '--heuristic',
        type=str,
        choices=['lpt', 'spt', 'fifo', 'depth'],
        default='lpt',
        help='Scheduling heuristic for replay. Options: lpt (Longest Processing Time), spt (Shortest Processing Time), fifo (First In First Out), depth (Dependency Depth). Default: lpt'
    )
    
    analyze_parser.add_argument(
        '-d', '--diagnostics',
        action='store_true',
        help='Enable advanced diagnostics (blast radius, criticality probability, wall-clock shares). Adds computation time.'
    )
    
    analyze_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging for debugging'
    )
    
    analyze_parser.set_defaults(func=cmd_analyze)
    
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """
    Main entry point for the bga CLI.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
