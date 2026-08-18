#!/usr/bin/env python3
"""UX-91: BuildStream's own persisted per-element logs, as a third data
plane.

Everything `bga` reads today has to be *decided on before the build*:
Plane 1 needs the wrapped log, Plane 2 needs the tracer running. But
BuildStream already writes a per-element log for every task it runs, to
`~/.cache/buildstream/logs/<project>/<element>/<key>-<action>.<stamp>.log`,
on every developer machine and every CI runner, for free, and keeps them
across builds. Nothing read them. They are the only source that can
answer a question about a build *nobody captured* - which is most
builds.

## What these logs actually contain (measured, not assumed)

Measured against real bst 2.7.0 logs rather than designed against the
task description, and the measurement bounds the design:

- **Phase timings are real and per-activity.** Each `SUCCESS` line's
  `[HH:MM:SS]` prefix is that activity's own duration, not time since
  session start (the same per-activity behaviour `UX-06` found in the
  console format, which corrupts a *timeline* but is exactly right for a
  *duration*). A build log yields `Staging dependencies`, `Integrating
  sandbox`, `Staging sources`, `Running commands`, `Caching artifact`,
  and the enclosing `Build` total.

- **There are no timestamps inside `Running commands`.** Verified on a
  real 136-line log: 14 timestamped lines, all of them phase
  START/SUCCESS/STATUS, and none between the first echoed command and
  the phase's own `SUCCESS`. So a *configure-vs-compile time split*
  cannot be read out of these logs, however much one would like it.
  What is available is the command *boundaries* (`+ sh -c -e ...`) and
  whatever a tool reports about itself - cmake prints
  `-- Configuring done (0.8s)`, and that is a real number this parser
  keeps because cmake measured it, not because we inferred it.

- **Absolute start is available at one-second resolution**, from the
  header (`BuildStream 2.7.0 - Tuesday, 18-08-2026 at 11:53:22`) and
  redundantly from the filename stamp - confirmed to agree. Enough to
  order elements and see overlap; not enough for a certified floor,
  which is why this never feeds one.

## What this refuses to do

The floors and every certified quantity keep requiring a real capture:
these logs carry no `--builders`, no `--max-jobs`, no scheduler context,
and their resolution is a second. This tool reports what the logs say
and labels its own provenance; it does not synthesize a run directory
that would then be indistinguishable from a captured one.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

# `[HH:MM:SS] STATE   [cachekey] element.bst: Activity` - the cache key
# is absent on some lines (the sandbox's own `Running commands`), so it
# is optional rather than assumed.
_EVENT_RE = re.compile(
    r'^\[(?P<elapsed>[0-9]{2}:[0-9]{2}:[0-9]{2}|--:--:--)\]\s+'
    r'(?P<state>[A-Z]+)\s+'
    r'(?:\[(?P<key>[0-9a-f]+)\]\s+)?'
    # Non-greedy up to the first colon *followed by whitespace*, not to
    # the first colon. A junction-qualified element is
    # `subproj-junction.bst:libfoo.bst` - the colon inside it has no
    # space after it, so this skips past it and splits at the real
    # separator. Found by running the parser over logs a real `bst
    # build` had just written: `[^:]+` matched nothing at all on those
    # lines, so every junction element parsed as nameless.
    r'(?P<element>.+?):\s+'
    r'(?P<activity>.*)$'
)
_HEADER_RE = re.compile(
    r'^BuildStream\s+(?P<version>\S+)\s+-\s+\w+,\s+'
    r'(?P<date>[0-9]{2}-[0-9]{2}-[0-9]{4})\s+at\s+(?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2})'
)
# `<cachekey>-<action>.<YYYYMMDD>-<HHMMSS>.log`
_FILENAME_RE = re.compile(
    r'^(?P<key>[0-9a-f]+)-(?P<action>[a-z-]+)\.'
    r'(?P<stamp>[0-9]{8}-[0-9]{6})\.log$'
)
_COMMAND_PREFIX = '+ sh -c -e '
# cmake's own self-reported timings - a real measurement the tool made,
# kept because it is one, not because a duration was inferred for it.
_SELF_TIMED_RE = re.compile(r'^--\s+(?P<what>Configuring|Generating|Build files)\b.*?\((?P<secs>[0-9.]+)s\)')


def _elapsed_us(text: str) -> Optional[int]:
    if text == '--:--:--':
        return None
    hours, minutes, seconds = (int(p) for p in text.split(':'))
    return ((hours * 3600) + (minutes * 60) + seconds) * 1_000_000


def parse_element_log(path: str, project_root: Optional[str] = None) -> Optional[dict]:
    """One persisted element log -> one record, or None if the file is
    not one (the `_casd/` sibling directory holds daemon logs in a
    different format, and a truncated log is not worth guessing at).
    """
    name = os.path.basename(path)
    match = _FILENAME_RE.match(name)
    if not match:
        return None

    with open(path, 'r', encoding='utf-8', errors='replace') as handle:
        lines = handle.read().splitlines()
    if not lines:
        return None

    header = _HEADER_RE.match(lines[0])
    started_us = None
    started_at = None
    version = None
    if header:
        version = header.group('version')
        started_at = f"{header.group('date')} {header.group('time')}"
        # BuildStream writes this header in the *runner's local* time and
        # records no offset, so `started_us` is that wall time read as
        # UTC. It is therefore only comparable against other logs from
        # the same machine - which is exactly what it is used for
        # (ordering elements within one build) and never for anything
        # that leaves it. The literal string is kept beside it so a
        # consumer can see what was actually written.
        stamp = datetime.strptime(started_at, '%d-%m-%Y %H:%M:%S').replace(
            tzinfo=timezone.utc,
        )
        started_us = int(stamp.timestamp() * 1_000_000)

    phases: List[dict] = []
    commands: List[str] = []
    self_timed: List[dict] = []
    element = None
    outcome = None
    total_us = None
    action = match.group('action')
    # The enclosing activity is the action itself, capitalized -
    # `Build`/`Fetch`. Its duration is the element's total, so it is
    # reported as `total_us` rather than mixed in with the phases it
    # contains, which would double-count.
    enclosing = action.replace('-', ' ').title()

    pending_command: Optional[List[str]] = None
    for line in lines:
        # A shell command echo continues across lines when it ends in a
        # backslash, and BuildStream echoes it verbatim. Joining them
        # matters for the frequency analysis: truncating at the first
        # line makes two genuinely different `cmake` invocations look
        # identical, which is precisely the kind of false match that
        # would make a repeated-operation report worthless.
        if pending_command is not None:
            pending_command.append(line.strip())
            if not line.rstrip().endswith('\\'):
                commands.append(' '.join(pending_command).strip())
                pending_command = None
            continue
        if line.startswith(_COMMAND_PREFIX):
            body = line[len(_COMMAND_PREFIX):]
            if body.rstrip().endswith('\\'):
                pending_command = [body.strip()]
            elif body.strip():
                commands.append(body.strip())
            continue
        timed = _SELF_TIMED_RE.match(line.strip())
        if timed:
            self_timed.append({
                'what': timed.group('what'),
                'duration_us': int(float(timed.group('secs')) * 1_000_000),
                'source': 'the tool reported this itself',
            })
            continue
        event = _EVENT_RE.match(line)
        if not event:
            continue
        if element is None:
            element = event.group('element').strip()
        if event.group('state') not in ('SUCCESS', 'FAILURE'):
            continue
        # A STATUS line names a *different* element (a dependency being
        # staged); only this log's own element's activities are its own.
        if event.group('element').strip() != element:
            continue
        duration_us = _elapsed_us(event.group('elapsed'))
        activity = event.group('activity').strip()
        if activity == enclosing:
            total_us = duration_us
            outcome = event.group('state')
            continue
        phases.append({
            'name': activity,
            'duration_us': duration_us,
            'outcome': event.group('state'),
        })

    return {
        'path': os.path.relpath(path, project_root) if project_root else path,
        'element': element,
        'cache_key': match.group('key'),
        'action': action,
        'buildstream_version': version,
        'started_at': started_at,
        'started_us': started_us,
        'total_us': total_us,
        'outcome': outcome,
        'phases': phases,
        'commands': commands,
        'self_timed': self_timed,
    }


def scan_log_tree(root: str, project: Optional[str] = None) -> List[dict]:
    """Every element log under `root`, newest last.

    `root` is BuildStream's own `logs/` directory. Its immediate children
    are project names; `_casd` is one of them and is not a project, so it
    is skipped by the filename check rather than by name - a future
    sibling directory needs no new special case.

    Sorted by (element, action, started_us, path) rather than by
    directory order, so two runs over the same tree produce identical
    output on any filesystem.
    """
    records: List[dict] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in sorted(filenames):
            record = parse_element_log(os.path.join(dirpath, filename))
            if record is None:
                continue
            relative = os.path.relpath(dirpath, root)
            parts = relative.split(os.sep)
            record['project'] = parts[0] if parts and parts[0] != '.' else None
            if project and record['project'] != project:
                continue
            records.append(record)
    return sorted(
        records,
        key=lambda r: (r['element'] or '', r['action'], r['started_us'] or 0, r['path']),
    )


# A command whose text is identical across this many distinct elements
# is worth reporting. Two is not a pattern - almost every cmake project
# runs `cmake --build`, and a report that says so is noise. `UX-72`'s
# materiality discipline, applied to a population instead of a duration.
REPEATED_MIN_ELEMENTS = 3

# Only phases at or above this share of an element's own total are worth
# a row. BuildStream reports at one-second resolution, so most staging
# phases are a flat 0 and listing them says nothing.
PHASE_SHARE_FLOOR = 0.05


def _normalize_command(command: str) -> str:
    """Collapse whitespace so two echoes of the same command that the
    log wrapped differently compare equal.

    Deliberately *not* stripping paths or arguments: two elements
    running `cmake` in their own build directories are doing the same
    kind of work, but saying they run "the same operation" would be a
    claim this data cannot support - the sandbox paths differ because
    the elements differ. Exact text, whitespace-normalized, keeps the
    report to matches a reader can verify by eye.
    """
    return ' '.join(command.split())


def phase_breakdown(records: List[dict]) -> List[dict]:
    """Per element: where its own time went, by BuildStream phase.

    Only `build` records: a `fetch` log has a single enclosing activity
    and no phases, so including them adds rows that are all "100%
    Fetch".
    """
    rows = []
    for record in records:
        if record['action'] != 'build' or not record['total_us']:
            continue
        total = record['total_us']
        phases = [
            {
                'name': phase['name'],
                'duration_us': phase['duration_us'],
                'share': phase['duration_us'] / total,
            }
            for phase in record['phases']
            if phase['duration_us'] and phase['duration_us'] / total >= PHASE_SHARE_FLOOR
        ]
        # `Running commands` is almost always the whole of it, and the
        # interesting element is the one where it is not - an element
        # whose time went to `Caching artifact` is a different problem
        # from one that spent it compiling, and nothing in `bga` could
        # previously tell them apart.
        rows.append({
            'element': record['element'],
            'cache_key': record['cache_key'],
            'started_at': record['started_at'],
            'total_us': total,
            'phases': sorted(phases, key=lambda p: -p['duration_us']),
            'commands': record['commands'],
            'self_timed': record['self_timed'],
            'unaccounted_us': total - sum(p['duration_us'] for p in record['phases']),
        })
    return sorted(rows, key=lambda r: (-r['total_us'], r['element']))


def repeated_operations(records: List[dict]) -> List[dict]:
    """Commands whose exact text recurs across distinct elements.

    A no-tracer approximation of `UX-23`'s redundancy detector, and
    weaker than it in a way worth stating: Plane 2 measures what each
    process *cost*, so it can say a shared operation is worth 20 seconds.
    These logs carry no per-command timing at all, so this can only say
    an operation recurs and in how many elements. It is a pointer at
    something to measure, not a measurement.
    """
    by_command: Dict[str, set] = {}
    for record in records:
        if record['action'] != 'build':
            continue
        for command in record['commands']:
            by_command.setdefault(_normalize_command(command), set()).add(
                record['element'],
            )
    findings = [
        {
            'command': command,
            'element_count': len(elements),
            'elements': sorted(elements),
        }
        for command, elements in by_command.items()
        if len(elements) >= REPEATED_MIN_ELEMENTS
    ]
    return sorted(findings, key=lambda f: (-f['element_count'], f['command']))


def build_report(records: List[dict]) -> dict:
    projects = sorted({r['project'] for r in records if r['project']})
    builds = [r for r in records if r['action'] == 'build']
    return {
        'provenance': {
            'source': "BuildStream's own persisted element logs",
            'projects': projects,
            'logs_read': len(records),
            'build_logs': len(builds),
            # Said in the payload, not only in the docs: a consumer that
            # reads this must not mistake it for a capture.
            'caveat': (
                "Phase durations are BuildStream's own per-activity elapsed values "
                "at one-second resolution. These logs carry no --builders, no "
                "--max-jobs and no scheduler context, and no timestamps inside "
                "'Running commands' - so there is no configure-vs-compile time "
                "split here, and nothing in this report may feed a certified floor."
            ),
        },
        'phase_breakdown': phase_breakdown(records),
        'repeated_operations': repeated_operations(records),
    }


def format_report_text(report: dict) -> str:
    provenance = report['provenance']
    lines = [
        '=' * 60,
        'Cached Build Logs (Plane 3)',
        '=' * 60,
        f"Read {provenance['logs_read']} log(s), {provenance['build_logs']} of them "
        f"builds, from {', '.join(provenance['projects']) or 'no project'}",
        '',
    ]

    rows = report['phase_breakdown']
    if not rows:
        lines.append('No build logs with a recorded duration.')
    else:
        lines.append('Where each element spent its own time:')
        for row in rows[:_ELEMENTS_SHOWN]:
            # The key and the timestamp are not decoration. These logs
            # accumulate across builds - that is the whole reason they
            # can answer a longitudinal question - so the same element
            # appears once per build it took part in, and without them
            # two real builds of `core.bst` read as one row printed
            # twice.
            lines.append(
                f"  {row['element']} [{row['cache_key']}] "
                f"{row['started_at'] or 'unknown time'} "
                f"({row['total_us'] / 1e6:.1f}s)"
            )
            for phase in row['phases']:
                lines.append(
                    f"    {phase['name']:<32s} {phase['duration_us'] / 1e6:7.1f}s "
                    f"({phase['share'] * 100:.0f}%)"
                )
            for timed in row['self_timed']:
                lines.append(
                    f"    {timed['what'] + ' (self-reported)':<32s} "
                    f"{timed['duration_us'] / 1e6:7.1f}s"
                )
        if len(rows) > _ELEMENTS_SHOWN:
            lines.append(f"  (+{len(rows) - _ELEMENTS_SHOWN} more element(s), see --format json)")
    lines.append('')

    repeated = report['repeated_operations']
    if repeated:
        lines.append(
            f'Operations repeated across {REPEATED_MIN_ELEMENTS}+ elements '
            f'(a pointer, not a measurement - these logs carry no per-command timing):'
        )
        for finding in repeated[:_REPEATED_SHOWN]:
            shown = ", ".join(finding['elements'][:4])
            more = (
                f" (+{finding['element_count'] - 4} more)"
                if finding['element_count'] > 4 else ""
            )
            lines.append(f"  {finding['element_count']}x  {finding['command'][:100]}")
            lines.append(f"        in {shown}{more}")
        if len(repeated) > _REPEATED_SHOWN:
            lines.append(f"  (+{len(repeated) - _REPEATED_SHOWN} more, see --format json)")
        lines.append('')

    lines.append(f"({provenance['caveat']})")
    lines.append('=' * 60)
    return '\n'.join(lines)


_ELEMENTS_SHOWN = 10
_REPEATED_SHOWN = 8


def default_log_root() -> str:
    """BuildStream's own default log directory.

    `XDG_CACHE_HOME` is honoured because BuildStream honours it; a user
    who moved their cache should not have to pass a path this tool could
    have worked out.
    """
    base = os.environ.get('XDG_CACHE_HOME') or os.path.join(
        os.path.expanduser('~'), '.cache',
    )
    return os.path.join(base, 'buildstream', 'logs')


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'log_root', nargs='?', default=None,
        help='BuildStream\'s logs directory. Defaults to '
             '$XDG_CACHE_HOME/buildstream/logs (or ~/.cache/buildstream/logs).',
    )
    parser.add_argument('--project', default=None, help='Only this project\'s logs.')
    parser.add_argument('-f', '--format', choices=['text', 'json'], default='text')
    parser.add_argument('-o', '--output', default=None, help='Write here instead of stdout.')
    args = parser.parse_args(argv)

    root = args.log_root or default_log_root()
    if not os.path.isdir(root):
        print(
            f"Error: no BuildStream log directory at {root}. Point this at one "
            f"explicitly, or run a build first - these logs are written by "
            f"BuildStream itself, not by bga.",
            file=sys.stderr,
        )
        return 1

    records = scan_log_tree(root, project=args.project)
    if not records:
        print(
            f"Error: no element logs found under {root}"
            + (f" for project {args.project!r}" if args.project else "")
            + ". Nothing to report on.",
            file=sys.stderr,
        )
        return 1

    report = build_report(records)
    output = (
        json.dumps(report, indent=2) if args.format == 'json'
        else format_report_text(report)
    )
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as handle:
            handle.write(output + '\n')
    else:
        print(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
