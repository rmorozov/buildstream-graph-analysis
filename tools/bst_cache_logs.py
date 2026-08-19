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


def _is_empty_command(command: str) -> bool:
    """Whether this echo is a command at all.

    BuildStream writes a `+ sh -c -e $'\\n'` line for an element whose
    command block is empty, and on the real freedesktop-sdk log tree
    eight elements share one - which the repeated-operation report
    happily called an operation repeated across eight elements. It is
    not an operation; it is the absence of one.
    """
    body = command.strip()
    if body.startswith("$'") and body.endswith("'"):
        body = body[2:-1]
    return not body.replace('\\n', '').replace('\\t', '').strip()


# UX-99: the one build phase that is the element's own work. Everything
# else BuildStream times inside a build log is the toll it pays to run
# that work in a sandbox - staging dependencies, integrating them,
# staging sources, caching the artifact afterwards.
WORK_PHASE = 'Running commands'

# BuildStream times to the second, so a toll of "0.0s" means "under a
# second", not "free". On a project that stages a 270 MB sysroot into 90
# sandboxes the toll is minutes; on `examples/06` every overhead phase
# rounds to zero. Published so a reader can tell a real zero from a
# rounded one rather than having to know this.
LOG_RESOLUTION_US = 1_000_000


def _phase_family(name: str) -> str:
    """`Staging dependencies at: /` -> `Staging dependencies`.

    BuildStream puts the staging path in the activity name, so the same
    phase reads as a different one per element whenever the path differs.
    Only the aggregate is grouped by family; each element keeps the exact
    string its own log carried.
    """
    return name.split(' at:', 1)[0].strip()


def sandbox_tax(records: List[dict]) -> dict:
    """UX-99: how much of this project's element time was the sandbox
    rather than the build.

    Three buckets, not two, and the third is the point of doing it this
    way: `work` is `Running commands`, `toll` is every other timed
    activity, and `unaccounted` is whatever the enclosing `Build`
    activity's own total does not hand to either. Folding the
    unaccounted remainder into the toll would inflate exactly the number
    this exists to report, so it is published beside it instead.

    Two limits, both in the payload rather than only here:

    - **One-second resolution.** A per-element toll below a second reads
      as 0.0s. The aggregate over many elements is still meaningful -
      rounding down 90 times understates the toll, it does not invent
      one - so this is a floor, and says so.
    - **These logs accumulate across builds.** The share is over every
      build log in the tree; if the tree holds three builds, it is that
      population's share, not one build's. Filter with `--project`, or
      scan a tree from one build (the capture workflow publishes one).
    """
    builds = [r for r in records if r['action'] == 'build' and r['total_us']]
    if not builds:
        return {}

    by_family: Dict[str, int] = {}
    work_us = toll_us = total_us = 0
    payers = []
    for record in builds:
        element_work = element_toll = 0
        for phase in record['phases']:
            duration = phase['duration_us'] or 0
            if phase['name'] == WORK_PHASE:
                element_work += duration
            else:
                element_toll += duration
                by_family[_phase_family(phase['name'])] = (
                    by_family.get(_phase_family(phase['name']), 0) + duration
                )
        work_us += element_work
        toll_us += element_toll
        total_us += record['total_us']
        payers.append({
            'element': record['element'],
            'cache_key': record['cache_key'],
            'started_at': record['started_at'],
            'total_us': record['total_us'],
            'work_us': element_work,
            'toll_us': element_toll,
            'toll_share': element_toll / record['total_us'],
        })

    return {
        # Logs, not distinct elements: these accumulate across builds, so
        # `core.bst` appears once per build it took part in. Counted the
        # way it is summed, so the two numbers agree.
        'build_logs': len(builds),
        'build_logs_without_a_total': sum(
            1 for r in records if r['action'] == 'build' and not r['total_us']
        ),
        'total_us': total_us,
        'work_us': work_us,
        'toll_us': toll_us,
        'toll_share': toll_us / total_us if total_us else None,
        'unaccounted_us': total_us - work_us - toll_us,
        'by_phase': [
            {'phase': name, 'duration_us': duration}
            for name, duration in sorted(by_family.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        # Ranked by toll seconds, not by share: a 90% toll on a 0.4s
        # element is arithmetic, a 40s toll on a 90s one is a finding.
        'top_payers': sorted(payers, key=lambda p: (-p['toll_us'], p['element'])),
        'resolution_us': LOG_RESOLUTION_US,
        'caveat': (
            "BuildStream times these activities to the second, so a toll under a "
            "second reads as 0.0s and this total is a floor rather than a "
            "measurement. It is also taken over every build log in the tree, "
            "which accumulates across builds - filter with --project, or scan a "
            "tree from one build."
        ),
    }


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
        # UX-99: the toll/work split, per element, unfiltered by
        # `PHASE_SHARE_FLOOR` - the floor decides which phases are worth
        # a *row*, and a toll that is small is still part of the split.
        work_us = sum(
            p['duration_us'] or 0 for p in record['phases'] if p['name'] == WORK_PHASE
        )
        toll_us = sum(
            p['duration_us'] or 0 for p in record['phases'] if p['name'] != WORK_PHASE
        )
        rows.append({
            'element': record['element'],
            'cache_key': record['cache_key'],
            'started_at': record['started_at'],
            'total_us': total,
            'work_us': work_us,
            'toll_us': toll_us,
            'toll_share': toll_us / total,
            'phases': sorted(phases, key=lambda p: -p['duration_us']),
            'commands': record['commands'],
            'self_timed': record['self_timed'],
            'unaccounted_us': total - sum(p['duration_us'] for p in record['phases']),
        })
    return sorted(rows, key=lambda r: (-r['total_us'], r['element']))


# UX-102: the self-reported phases that are the *native build system*
# configuring itself, as distinct from UX-99's toll, which is
# BuildStream staging around it. `Configuring` and `Generating` are what
# cmake prints; `Build files` is the line it prints when writing them.
CONFIGURE_SELF_TIMED = frozenset({'Configuring', 'Generating', 'Build files'})

# A configure share at or above this is worth a project-wide finding.
# Below it the remedies (config caches, merged elements) cost more
# attention than they return, and a report that names every 3% is a
# report nobody reads.
CONFIGURE_SHARE_NOTABLE = 0.10


def configure_tax(records: List[dict]) -> dict:
    """UX-102: how much of each element's time the native build system
    spent working out how to build, rather than building.

    **This is a different quantity from `sandbox_tax`, and the pair only
    makes sense if the difference is kept in view.** The toll is
    BuildStream's - staging, integrating, caching - and it is measured by
    BuildStream's own clock. The configure tax is cmake's or autotools',
    it happens *inside* `Running commands`, and here it is measured by
    the tool itself: cmake prints `-- Configuring done (0.8s)` and this
    reads that line. So the toll is timed to the second and the configure
    tax to the millisecond, by two different clocks, and they are
    reported side by side rather than added.

    The known gap, stated because it bounds every number here: **only
    tools that report their own timing are counted.** cmake does;
    autotools' `configure` does not print a total, and neither does
    meson. On an autotools-heavy project this returns a *floor of zero*
    for elements that may be majority-configure - which is exactly
    backwards from where the prize is, and is why `UX-102` pairs this
    with the Plane 2 view (`bga cache-logs --native-report`), where the
    measurement is the traced process tree rather than a self-report.
    """
    builds = [r for r in records if r['action'] == 'build' and r['total_us']]
    rows = []
    total_us = configure_us = 0
    for record in builds:
        element_configure = sum(
            timed['duration_us'] for timed in record['self_timed']
            if timed['what'] in CONFIGURE_SELF_TIMED
        )
        total_us += record['total_us']
        configure_us += element_configure
        if element_configure:
            rows.append({
                'element': record['element'],
                'cache_key': record['cache_key'],
                'started_at': record['started_at'],
                'total_us': record['total_us'],
                'configure_us': element_configure,
                'configure_share': element_configure / record['total_us'],
                'source': 'plane3-self-reported',
            })
    if not builds:
        return {}
    return {
        'build_logs': len(builds),
        'elements_reporting': len(rows),
        'total_us': total_us,
        'configure_us': configure_us,
        'configure_share': configure_us / total_us if total_us else None,
        'top_payers': sorted(rows, key=lambda r: (-r['configure_us'], r['element'])),
        'caveat': (
            "Counted only where the build tool reports its own configure timing - "
            "cmake does, autotools' configure and meson do not. On a project "
            "built with those, this is a floor of zero rather than a measurement, "
            "and the Plane 2 view (--native-report) is the one to read."
        ),
    }


def join_configure_views(plane3: dict, native_report: Optional[dict]) -> dict:
    """UX-102: the configure tax as both planes measured it, per element.

    A quantity computed twice is a free test (`UX-53`'s lesson), and
    these two are computed from different evidence entirely: Plane 3
    reads what cmake said about itself, Plane 2 sums kernel `getrusage`
    over the process tree below the configure command. They are also
    *different quantities* - Plane 3's self-report is wall time, Plane
    2's is CPU time - so this reports them side by side and never adds
    them, and the ratio it publishes is a ratio to look at, not a
    tolerance to pass.

    What the pair is actually good for is disagreement in *direction*:
    an element Plane 3 says spends nothing configuring, while Plane 2
    finds a large configure subtree under it, is an autotools element
    whose `configure` does not report itself - and that is the case the
    self-report is blind to and the prize is largest in.
    """
    plane2 = ((native_report or {}).get('configure_phase') or {})
    if not plane2.get('available'):
        return {}
    plane3_by_element = {
        row['element']: row for row in (plane3.get('top_payers') or [])
    }
    rows = []
    for element, entry in plane2['per_element'].items():
        plane3_row = plane3_by_element.get(element)
        rows.append({
            'element': element,
            'plane2_configure_cpu_us': entry['configure_cpu_us'],
            'plane2_configure_share': entry['configure_share'],
            'plane2_coverage': entry['coverage'],
            'plane3_configure_us': (plane3_row or {}).get('configure_us'),
            'plane3_configure_share': (plane3_row or {}).get('configure_share'),
            # The case worth naming: Plane 2 found a configure subtree
            # and Plane 3 heard nothing about it.
            'self_report_missing': bool(
                entry['configure_cpu_us'] and not (plane3_row or {}).get('configure_us')
            ),
        })
    return {
        'elements': sorted(rows, key=lambda r: (-r['plane2_configure_cpu_us'], r['element'])),
        'elements_without_a_self_report': sum(1 for r in rows if r['self_report_missing']),
        'note': (
            "Plane 3 is the build tool's own self-reported wall time; Plane 2 is "
            "kernel CPU time over the traced process tree below the configure "
            "command. Different clocks and different quantities - shown together, "
            "never summed. An element with Plane 2 configure CPU and no Plane 3 "
            "self-report is a build system that does not report itself (autotools, "
            "meson), which is where this measurement earns its keep."
        ),
    }


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
            if _is_empty_command(command):
                continue
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


def _plane3_findings(plane3_configure: dict, views: dict) -> List[dict]:
    """UX-102 item 3: one project-wide finding, with an id, naming the
    top payers and the size of the prize.

    Shaped like `bga`'s own findings (`id`/`severity`/`title`/`evidence`)
    because a consumer should not have to learn a second shape, but built
    here rather than in `bga/findings.py`: that module analyses a run
    directory and has no access to Plane 3's logs or Plane 2's trace.

    The remedy is one hedged sentence, deliberately. Config caches,
    merged elements and generated-config reuse are all real answers and
    which one applies is a fact about the project, not about this
    measurement - the tool names the prize, not the patch.
    """
    share = plane3_configure.get('configure_share')
    plane2_share = None
    if views.get('elements'):
        configure_cpu = sum(r['plane2_configure_cpu_us'] for r in views['elements'])
        if configure_cpu:
            plane2_share = configure_cpu
    if not share and not plane2_share:
        return []
    if (share or 0) < CONFIGURE_SHARE_NOTABLE and not plane2_share:
        return []

    payers = [r['element'] for r in (plane3_configure.get('top_payers') or [])[:4]]
    if views.get('elements'):
        payers = payers or [r['element'] for r in views['elements'][:4] if r['plane2_configure_cpu_us']]
    prize = (
        f"{plane3_configure['configure_us'] / 1e6:.1f}s self-reported"
        if plane3_configure.get('configure_us') else None
    )
    if plane2_share:
        measured = f"{plane2_share / 1e6:.1f} CPU s traced"
        prize = f"{prize}, {measured}" if prize else measured
    return [{
        'id': 'configure-tax',
        'severity': 'info' if (share or 0) < CONFIGURE_SHARE_NOTABLE else 'medium',
        'title': (
            f"Configuring cost {prize} across this log tree"
            + (f" ({share * 100:.1f}% of element time)" if share else "")
            + (f" - paid most by {', '.join(payers)}" if payers else "")
            + ". Elements that configure independently re-answer the same "
            "questions; config caches, merged elements or reusing a generated "
            "config are the usual remedies, and which applies is a fact about "
            "the project rather than about this measurement"
        ),
        'evidence': {
            'plane3_configure_us': plane3_configure.get('configure_us'),
            'plane3_configure_share': share,
            'plane2_configure_cpu_us': plane2_share,
            'elements_without_a_self_report': views.get('elements_without_a_self_report'),
            'top_payers': payers,
        },
    }]


# UX-101: a ranking over fewer builds than this is a list, not a trend.
# Below it the tax figures are printed with the count and explicitly
# called weak evidence rather than withheld - a three-build tree is what
# most developers have, and it does say something.
TAX_WINDOW_STRONG_BUILDS = 5


def developer_tax(records: List[dict], dependencies: Optional[List[dict]] = None) -> dict:
    """UX-101: which element costs the most wall-clock across the whole
    log tree, and why it keeps rebuilding.

    Every other ranking in `bga` is about one build - the critical path
    of *that* run, the realizable saving in *that* capture. The question
    a team lead has is longitudinal: an element that is fourth on today's
    critical path but rebuilds in most builds taxes the team more than
    today's first, which rebuilds monthly. `tax = rebuild count x mean
    rebuild cost`, which is just the total, and the total is what ranks.

    **The logs carry no session id.** Measured rather than assumed: a
    log's header timestamp equals its own filename stamp - `all/…-build.
    20260818-160457.log` opens with `at 16:04:57` - so it is the *task's*
    start, not the build's. Nothing in the tree says which logs belonged
    to one `bst build`. So this never claims a build count it cannot
    know: the window is first-to-last log, the population is build logs,
    and `builds_lower_bound` is the largest per-element count, labelled
    for what it is.

    **Cause annotation.** For each rebuild after an element's first, its
    key either changed or did not:

    - unchanged: `UX-93`'s case - the artifact was not retained, which is
      a question about the cache rather than the project;
    - changed, and no dependency's key changed across the same interval:
      the change starts here;
    - changed, and a dependency's did too: rooted upstream, and the
      dependency is named.

    The third case needs the graph, which these logs do not contain -
    pass `dependencies` (from a run directory's `graph.json`) to get it.
    Without them the first two are still exact, and the payload says
    which of the three it could distinguish rather than quietly folding
    the third into the second.
    """
    builds = [r for r in records if r['action'] == 'build' and r['total_us']]
    if not builds:
        return {}

    by_element: Dict[str, List[dict]] = {}
    for record in builds:
        by_element.setdefault(record['element'], []).append(record)
    for history in by_element.values():
        history.sort(key=lambda r: (r['started_us'] or 0, r['path']))

    predecessors: Dict[str, List[str]] = {}
    for dependency in dependencies or []:
        predecessors.setdefault(dependency['successor'], []).append(
            dependency['predecessor'],
        )

    def _key_changed_between(element: str, start_us, end_us) -> bool:
        """Whether `element`'s cache key changed across (start_us, end_us]."""
        history = by_element.get(element) or []
        keys = [
            record['cache_key'] for record in history
            if start_us is not None and record['started_us'] is not None
            and start_us < record['started_us'] <= (end_us or 0)
        ]
        if not keys:
            return False
        before = [
            record['cache_key'] for record in history
            if record['started_us'] is not None and record['started_us'] <= start_us
        ]
        return bool(before) and keys[-1] != before[-1]

    rows = []
    for element, history in by_element.items():
        total_us = sum(record['total_us'] for record in history)
        causes = {'unchanged_key': 0, 'own_key_changed': 0, 'rooted_upstream': 0}
        roots: Dict[str, int] = {}
        for previous, current in zip(history, history[1:]):
            if current['cache_key'] == previous['cache_key']:
                causes['unchanged_key'] += 1
                continue
            upstream = [
                name for name in predecessors.get(element, [])
                if _key_changed_between(
                    name, previous['started_us'], current['started_us'],
                )
            ]
            if upstream:
                causes['rooted_upstream'] += 1
                for name in upstream:
                    roots[name] = roots.get(name, 0) + current['total_us']
            else:
                causes['own_key_changed'] += 1
        rows.append({
            'element': element,
            'build_count': len(history),
            'total_us': total_us,
            'mean_us': total_us / len(history),
            'distinct_keys': len({record['cache_key'] for record in history}),
            'causes': causes,
            'upstream_roots': sorted(
                ({'element': name, 'downstream_us': cost} for name, cost in roots.items()),
                key=lambda entry: (-entry['downstream_us'], entry['element']),
            ),
        })
    rows.sort(key=lambda row: (-row['total_us'], row['element']))

    starts = [r['started_us'] for r in builds if r['started_us']]
    builds_lower_bound = max((row['build_count'] for row in rows), default=0)
    return {
        'build_logs': len(builds),
        'builds_lower_bound': builds_lower_bound,
        'window_start': min((r['started_at'] for r in builds if r['started_at']), default=None),
        'window_end': max((r['started_at'] for r in builds if r['started_at']), default=None),
        'window_us': (max(starts) - min(starts)) if len(starts) > 1 else 0,
        'weak_window': builds_lower_bound < TAX_WINDOW_STRONG_BUILDS,
        'causes_available': ['unchanged_key', 'own_key_changed'] + (
            ['rooted_upstream'] if dependencies else []
        ),
        'ranking': rows,
        'caveat': (
            "Ranked by total build seconds across every build log in the tree. "
            "These logs carry no session id - a log's header is its own task's "
            "start, not its build's - so the number of builds is a lower bound "
            "taken from the most-rebuilt element, never a count. One-second "
            "resolution, no scheduler context, and nothing here may feed a "
            "certified floor."
        ),
    }


def build_report(
    records: List[dict], native_report: Optional[dict] = None,
    dependencies: Optional[List[dict]] = None,
) -> dict:
    projects = sorted({r['project'] for r in records if r['project']})
    builds = [r for r in records if r['action'] == 'build']
    plane3_configure = configure_tax(records)
    views = join_configure_views(plane3_configure, native_report)
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
        'sandbox_tax': sandbox_tax(records),
        'developer_tax': developer_tax(records, dependencies),
        'configure_tax': plane3_configure,
        'configure_views': views,
        'findings': _plane3_findings(plane3_configure, views),
        'repeated_operations': repeated_operations(records),
    }


_ELEMENT_COLUMN_CHARS = 28


def _elide_element(name: str, width: int = _ELEMENT_COLUMN_CHARS) -> str:
    """Fit an element name to the ranking column without hiding which
    element it is. A fixed slice truncates the *head*, and on a real
    project that turns `components/_private/cmake-stage1.bst` and
    `components/_private/git-minimal.bst` into `components/_private/cmake-st`
    and `components/_private/git-mini` - two names that differ only past
    the cut, with nothing saying they were cut at all. The tail is the
    distinguishing part, so the head is what gives way."""
    if len(name) <= width:
        return name
    return "…" + name[-(width - 1):]


def _pct(share: float) -> str:
    """A share, rendered so a nonzero quantity never reads as zero. A
    1.0s toll on a 594.0s element is 0.17%, and printing that as `0%`
    beside a real number says the toll was not paid at all."""
    if share <= 0:
        return "0%"
    pct = share * 100
    return f"{pct:.0f}%" if pct >= 1 else "<1%"


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
                    f"({_pct(phase['share'])})"
                )
            for timed in row['self_timed']:
                lines.append(
                    f"    {timed['what'] + ' (self-reported)':<32s} "
                    f"{timed['duration_us'] / 1e6:7.1f}s"
                )
        if len(rows) > _ELEMENTS_SHOWN:
            lines.append(f"  (+{len(rows) - _ELEMENTS_SHOWN} more element(s), see --format json)")
    lines.append('')

    tax = report.get('sandbox_tax') or {}
    if tax.get('total_us'):
        # UX-99: the headline the direction asked for, then who paid it.
        toll_s = tax['toll_us'] / 1e6
        lines.append(
            f"Sandbox tax: {toll_s:.1f}s of {tax['total_us'] / 1e6:.1f}s element time "
            f"({tax['toll_share'] * 100:.1f}%) across {tax['build_logs']} build log(s) "
            f"went to staging, integrating and caching rather than to the build itself"
        )
        if not tax['toll_us']:
            lines.append(
                "  Every overhead phase rounded to zero at BuildStream's one-second "
                "resolution - which is a real answer on a small project, and the "
                "reason this is a floor rather than a measurement"
            )
        for phase in tax['by_phase']:
            if not phase['duration_us']:
                continue
            lines.append(
                f"    {phase['phase']:<32s} {phase['duration_us'] / 1e6:7.1f}s"
            )
        payers = [p for p in tax['top_payers'] if p['toll_us']][:_TAX_PAYERS_SHOWN]
        if payers:
            lines.append('  Who paid it (by toll seconds, not by share):')
            for payer in payers:
                lines.append(
                    f"    {_elide_element(payer['element'], 32):<32s} "
                    f"{payer['toll_us'] / 1e6:7.1f}s toll "
                    f"of {payer['total_us'] / 1e6:.1f}s ({_pct(payer['toll_share'])})"
                )
        if tax['unaccounted_us']:
            lines.append(
                f"  ({tax['unaccounted_us'] / 1e6:.1f}s of the enclosing Build activity "
                f"is in neither bucket - reported rather than folded into the toll)"
            )
        lines.append('')

    tax = report.get('configure_tax') or {}
    views = report.get('configure_views') or {}
    if tax.get('configure_us') or views.get('elements'):
        # UX-102: the configure tax, one plane or two.
        if tax.get('configure_us'):
            lines.append(
                f"Configure tax (Plane 3, self-reported): "
                f"{tax['configure_us'] / 1e6:.1f}s of {tax['total_us'] / 1e6:.1f}s "
                f"element time ({(tax['configure_share'] or 0) * 100:.1f}%), reported by "
                f"{tax['elements_reporting']} of {tax['build_logs']} build log(s)"
            )
        else:
            lines.append(
                "Configure tax (Plane 3, self-reported): nothing reported - no build "
                "tool in this tree printed its own configure timing"
            )
        if views.get('elements'):
            lines.append('  Both planes, per element (wall vs CPU - shown, never summed):')
            lines.append(
                f"    {'element':<28s} {'Plane 3 wall':>13s} {'Plane 2 CPU':>12s}  coverage"
            )
            for row in views['elements'][:_TAX_PAYERS_SHOWN]:
                plane3 = (
                    f"{row['plane3_configure_us'] / 1e6:.2f}s"
                    if row['plane3_configure_us'] else 'not reported'
                )
                lines.append(
                    f"    {row['element']:<28s} {plane3:>13s} "
                    f"{row['plane2_configure_cpu_us'] / 1e6:>11.2f}s "
                    f"{row['plane2_coverage'] * 100:>8.0f}%"
                )
            missing = views['elements_without_a_self_report']
            if missing:
                lines.append(
                    f"    {missing} element(s) have traced configure work and no "
                    f"self-report - an autotools or meson build system, and the case "
                    f"the self-report alone is blind to"
                )
        lines.append(f"  ({tax.get('caveat') or views.get('note')})")
        lines.append('')

    tax = report.get('developer_tax') or {}
    if tax.get('ranking'):
        # UX-101: the longitudinal ranking, which is a different question
        # from any single build's critical path.
        window = (
            f"{tax['window_start']} .. {tax['window_end']}"
            if tax['window_start'] and tax['window_end'] else 'an unrecorded window'
        )
        lines.append(
            f"Developer tax across {tax['build_logs']} build log(s) over {window} "
            f"(at least {tax['builds_lower_bound']} build(s))"
            + (
                " - WEAK EVIDENCE at this few builds, printed with the count rather "
                "than withheld" if tax['weak_window'] else ""
            )
        )
        shown = tax['ranking'][:_TAX_ELEMENTS_SHOWN]
        # The `cause` column needs `--graph` *and* an element that
        # rebuilt more than once. An empty column on every other run
        # reads as "no cause found" rather than "no cause could be
        # looked for".
        any_cause = any(
            any(count for count in row['causes'].values()) for row in shown
        )
        lines.append(
            f"  {'element':<28s} {'builds':>6s} {'total':>9s} {'mean':>8s}"
            + ("  cause" if any_cause else "")
        )
        for row in shown:
            causes = row['causes']
            parts = [
                f"{count}x {name.replace('_', ' ')}"
                for name, count in causes.items() if count
            ]
            lines.append(
                (f"  {_elide_element(row['element']):<28s} {row['build_count']:>6d} "
                 f"{row['total_us'] / 1e6:>8.1f}s {row['mean_us'] / 1e6:>7.1f}s"
                 + ("  " + ", ".join(parts) if parts else "")).rstrip()
            )
            for root in row['upstream_roots'][:2]:
                lines.append(
                    f"      rooted at {root['element']} "
                    f"({root['downstream_us'] / 1e6:.1f}s of this element's rebuilds)"
                )
        if len(tax['ranking']) > _TAX_ELEMENTS_SHOWN:
            lines.append(
                f"  (+{len(tax['ranking']) - _TAX_ELEMENTS_SHOWN} more element(s), "
                f"see --format json)"
            )
        if 'rooted_upstream' not in tax['causes_available']:
            lines.append(
                "  No graph supplied, so a rebuild caused by an upstream key change "
                "is counted under `own key changed` - pass --graph RUN/graph.json to "
                "separate them"
            )
        lines.append(f"  ({tax['caveat']})")
        lines.append('')

    for finding in report.get('findings') or []:
        lines.append(f"[{finding['severity']}] {finding['id']}: {finding['title']}")
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
_TAX_PAYERS_SHOWN = 8
_TAX_ELEMENTS_SHOWN = 10
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


def project_name_from_dir(project_dir: str) -> Optional[str]:
    """The `name:` a BuildStream project declares, or `None`.

    `UX-127`: the thing a user *has* is a project directory; the thing
    this tool wanted was the project's **name** - BuildStream's log-tree
    directory name - discoverable only by listing the cache yourself.
    Three audit rounds passed `--project
    macro-micro-optimization-example-optimized`, a value obtained by
    `ls`-ing `~/.cache/buildstream/logs`, which is exactly the folklore
    step Plane 3 exists to not need.

    Read from `project.conf` directly rather than through BuildStream,
    for the same reason `read_declared_build_deps` does: this has to work
    against a project directory without loading a plugin, and the name is
    a plain top-level key.
    """
    conf = os.path.join(project_dir, 'project.conf')
    try:
        with open(conf, 'r', encoding='utf-8', errors='replace') as handle:
            for line in handle:
                if line.startswith('name:'):
                    return line.split(':', 1)[1].strip() or None
    except OSError:
        return None
    return None


def is_project_dir(path: str) -> bool:
    return os.path.isfile(os.path.join(path, 'project.conf'))


def summarize_log_tree(root: str) -> List[dict]:
    """What the log tree holds, per project: counts and time span.

    `UX-127` item 2. Discovery is the tool's job - a user should not have
    to `ls` a cache directory to find out what is in it.
    """
    projects: Dict[str, dict] = {}
    for record in scan_log_tree(root):
        name = record.get('project') or '(unknown)'
        entry = projects.setdefault(name, {
            'project': name, 'logs': 0, 'elements': set(),
            'first_us': None, 'last_us': None,
        })
        entry['logs'] += 1
        entry['elements'].add(record.get('element'))
        started = record.get('started_us')
        if started is not None:
            if entry['first_us'] is None or started < entry['first_us']:
                entry['first_us'] = started
            if entry['last_us'] is None or started > entry['last_us']:
                entry['last_us'] = started
    return sorted(
        ({**entry, 'elements': len(entry['elements'])} for entry in projects.values()),
        key=lambda e: (-e['logs'], e['project']),
    )


def format_log_tree_listing(root: str, projects: List[dict]) -> str:
    lines = ['=' * 60, 'BuildStream log tree', '=' * 60, f"  {root}", '']
    if not projects:
        lines.append('  (no element logs - run a build first)')
        return '\n'.join(lines)
    lines.append(f"  {'project':<44} {'logs':>6} {'elements':>9}")
    for entry in projects:
        lines.append(f"  {entry['project']:<44} {entry['logs']:>6} {entry['elements']:>9}")
        if entry['first_us'] is not None and entry['last_us'] is not None:
            lines.append(
                f"      {_stamp(entry['first_us'])} .. {_stamp(entry['last_us'])}"
            )
    lines += ['', '  Report on one with `bga cache-logs PROJECT_DIR` (or --project NAME),',
              '  or on every project at once with --all.']
    return '\n'.join(lines)


def _stamp(micros: Optional[int]) -> str:
    if micros is None:
        return '(no timestamp)'
    return datetime.fromtimestamp(micros / 1e6, timezone.utc).strftime(
        '%Y-%m-%d %H:%M:%S UTC')


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'target', nargs='?', default=None, metavar='PROJECT_DIR|LOG_ROOT',
        help='UX-127: a BuildStream **project directory** (detected by its '
             'project.conf) - the obvious argument, and the one that does the '
             'right thing: the project name is read from it and the log root '
             'resolved automatically. A logs directory still works. With '
             'neither, this lists what the log tree holds.',
    )
    parser.add_argument('--project', default=None, help='Only this project\'s logs.')
    parser.add_argument(
        '--all', action='store_true',
        help='UX-127: report over every project in the log tree at once. This '
             'used to be what a bare invocation did, and "report on every project '
             'I ever built" is never one user\'s question - a bare invocation now '
             'lists the tree instead.',
    )
    parser.add_argument(
        '--list', action='store_true',
        help='List the projects the log tree holds, with log counts and time '
             'spans, and exit. The default when no target is given.',
    )
    parser.add_argument(
        '--graph', default=None,
        help="A run directory's `graph.json`. Lets the developer-tax cause "
             "annotation (UX-101) tell a rebuild caused by an upstream key change "
             "from one whose own definition changed - the logs alone carry no "
             "dependency edges.",
    )
    parser.add_argument(
        '--native-report', default=None,
        help="A Plane 2 report (`bga capture run`'s JSON) from the same build. "
             "Adds the traced configure measurement beside Plane 3's self-reported "
             "one (UX-102) - the two are different quantities and are shown side "
             "by side, never summed.",
    )
    parser.add_argument('-f', '--format', choices=['text', 'json'], default='text')
    parser.add_argument('-o', '--output', default=None, help='Write here instead of stdout.')
    args = parser.parse_args(argv)

    # UX-127: work out what the user actually handed us.
    project = args.project
    project_dir = None
    if args.target and is_project_dir(args.target):
        project_dir = args.target
        derived = project_name_from_dir(args.target)
        if not derived:
            print(
                f"Error: {args.target} looks like a BuildStream project but its "
                f"project.conf declares no `name:`, so there is no log-tree "
                f"directory to look for. Pass --project NAME.",
                file=sys.stderr,
            )
            return 1
        project = project or derived
        root = default_log_root()
    else:
        root = args.target or default_log_root()

    if not os.path.isdir(root):
        print(
            f"Error: no BuildStream log directory at {root}. Point this at one "
            f"explicitly, or run a build first - these logs are written by "
            f"BuildStream itself, not by bga.",
            file=sys.stderr,
        )
        return 1

    # UX-127 item 2: discovery is the tool's job. A bare invocation used to
    # report over every project the machine had ever built, which is never
    # one user's question; `--all` keeps that behaviour for anyone who
    # wants it.
    if args.list or (args.target is None and not args.project and not args.all):
        projects = summarize_log_tree(root)
        if args.format == 'json':
            payload = json.dumps({'log_root': root, 'projects': projects}, indent=2)
        else:
            payload = format_log_tree_listing(root, projects)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as handle:
                handle.write(payload + '\n')
        else:
            print(payload)
        return 0

    records = scan_log_tree(root, project=project)
    if not records:
        # UX-127 item 3: a redirect rather than a confidently wrong
        # "nothing to report". Handing this tool the obvious argument -
        # the project - used to produce that message about a project
        # whose logs sit two directories away.
        available = [entry['project'] for entry in summarize_log_tree(root)]
        lines = [f"Error: no element logs found under {root}"]
        if project:
            lines[0] += f" for project {project!r}"
            if project_dir:
                lines.append(
                    f"  {project_dir}/project.conf declares `name: {project}`, and "
                    f"that is the log-tree directory this looked for."
                )
            lines.append(
                "  The tree holds: "
                + (", ".join(available[:8]) + ("…" if len(available) > 8 else "")
                   if available else "nothing - no build has written logs here yet")
            )
            lines.append(
                "  `bga cache-logs --list` shows all of them with counts and spans."
            )
        else:
            lines.append("  Nothing to report on.")
        print("\n".join(lines), file=sys.stderr)
        return 1

    native_report = None
    if args.native_report:
        try:
            with open(args.native_report, 'r', encoding='utf-8') as handle:
                native_report = json.load(handle)
        except (OSError, ValueError) as error:
            print(
                f"Error: could not read the Plane 2 report at {args.native_report}: "
                f"{error}",
                file=sys.stderr,
            )
            return 1

    dependencies = None
    if args.graph:
        try:
            with open(args.graph, 'r', encoding='utf-8') as handle:
                dependencies = (json.load(handle) or {}).get('dependencies') or []
        except (OSError, ValueError) as error:
            print(f"Error: could not read the graph at {args.graph}: {error}",
                  file=sys.stderr)
            return 1

    report = build_report(
        records, native_report=native_report, dependencies=dependencies,
    )
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
