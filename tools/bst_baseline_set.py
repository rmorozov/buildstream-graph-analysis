#!/usr/bin/env python3
"""UX-96: assemble a baseline set from published capture refs, in one
command.

`UX-81` made the data exist - one immutable ref per capture, named with
the tuple that has to match for two runs to be comparable
(`captures/fdsdk/<commit>-<mode>-b<builders>j<max_jobs>-<run_id>`). It
did not make the data *usable*. Round 11 built a three-run baseline set
by hand: one `git ls-remote` to discover the refs, three `git archive`
extractions, two manual untars (the older refs predate the uncompressed
`run/`), and a five-path `bga compare` assembled by hand. That is the
workflow every CI owner is now expected to run on every candidate build.

What this adds beyond convenience - and the reason it is a tool rather
than a shell snippet in a document:

**It checks the set's own homogeneity.** The three captures round 11
compared were produced by three different `bga` revisions. Each one
recorded that fact in its own `capture-context.txt`, and nothing read
it. A baseline set assembled from drifting capture tooling silently
widens or biases the band - which is the same unlike-things comparison
`bga compare` refuses everywhere else, arriving through the back door.
So the config tuple is verified and a `bga`-revision difference is
reported, every time, whether or not anyone asked.

**It untars where it has to.** Two of the three real refs carry only
`capture.tar.gz`; the newest also has an uncompressed `run/`. A helper
that handled only the current layout would work today and fail on the
history it exists to read.
"""

HELP = """Fetch published capture refs and build a baseline set from them.

A single baseline run cannot say whether a delta is noise. This assembles
several comparable runs into the set `compare --baseline-run` judges against.

Full background: docs/guides/ci-comment.md
"""
import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from typing import Dict, List, Optional

# `captures/fdsdk/<short-ref>-<mode>-b<builders>j<max_jobs>-<run_id>`.
# The run id is GitHub's, and it increases monotonically, so it is the
# ordering key - no commit dates to fetch and no clock to trust.
_REF_RE = re.compile(
    r'^captures/(?P<project>[^/]+)/'
    r'(?P<commit>[0-9a-f]+)-(?P<mode>[a-z]+)-'
    r'b(?P<builders>\d+)j(?P<max_jobs>\d+)-(?P<run_id>\d+)$'
)

# The fields of `capture-context.txt` that must agree across a baseline
# set, mapped to **what an absent value means**, and the reason each one
# is here:
#   - a different commit is a different project state;
#   - a different mode is a different *kind* of build (UX-86);
#   - different builders/max_jobs is a different machine shape;
#   - a different target is a different build entirely, and the ref name
#     does not carry it (UX-96 added it to `capture-context.txt`);
#   - a capture taken with the ptrace spine is a different *measurement*
#     of the same build - more processes, more wall clock - so mixing one
#     into a band of hook-only captures widens the band with tooling
#     rather than with noise (UX-108).
#
# UX-114: absence used to be skipped for every field, and that skip
# failed in practice. `captures/fdsdk/953683fb-incremental-b4j4-32223468993`
# records `trace_spine=true`; the four refs beneath it predate the field
# and record nothing. `{absent, absent, absent, absent, 'true'}` filtered
# to truthy values is one distinct value, so the spine capture joined a
# four-run hook-only band with no warning at all, and `bga baseline -n 5`
# exited 0.
#
# The repair is per-field, because absence does not mean one thing:
#   - `None` - absence is genuinely ambiguous. The field is compared
#     across the captures that record it, and partial coverage is
#     *warned* about rather than passed over, so "they agree" and "two of
#     them never said" stop looking identical. `target` is this case: the
#     four older refs did not record it, and they were in fact building
#     the same target as the fifth.
#   - a string - absence has a known meaning, because the capture
#     workflow's own default is that value and a ref published before the
#     field existed was taken under it. Absent then *participates* in the
#     comparison and mismatches against a differing value, which is what
#     makes the spine capture visible.
#
# `bga compare` already refuses across commit and mode; this refuses
# before the fetch, where the error is cheap and legible.
HOMOGENEOUS_FIELDS = {
    'fdsdk_ref': None,
    'capture_mode': None,
    'builders': None,
    'max_jobs': None,
    'target': None,
    # `real-project-capture.yml`: `TRACE_SPINE: ${{ ... || 'false' }}`
    # and `TRACE_OPENS: ${{ ... || 'true' }}` - the scheduled default
    # instrumentation, and therefore what an absent field was taken
    # under.
    'trace_spine': 'false',
    'trace_opens': 'true',
}

# UX-96 round 76: which of the fields above the ref name actually
# carries. `<commit>-<mode>-b<builders>j<max_jobs>` is four of the seven,
# so a `--glob` can separate a set that differs on those and cannot
# separate one that differs on `target`, `trace_spine` or `trace_opens`.
# The refusal used to name narrowing the glob as the only remedy, and on
# the live refs it was the wrong one: seven published incrementals, all
# one tuple, one of them `trace_spine=true`.
NAMED_BY_THE_REF = ('fdsdk_ref', 'capture_mode', 'builders', 'max_jobs')

# Reported, never enforced. Capture tooling changing between runs is a
# real risk to a band and also a completely normal thing to happen in a
# repository under development - refusing would make the helper unusable
# in exactly the period it is most needed.
DRIFT_FIELD = 'bga_ref'


def list_capture_refs(remote: str, glob: str, cwd: Optional[str] = None) -> List[dict]:
    """Every published capture ref matching `glob`, newest first."""
    result = subprocess.run(
        ['git', 'ls-remote', '--heads', remote, glob],
        cwd=cwd, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git ls-remote failed: {result.stderr.strip()}")
    refs = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        sha, ref = parts
        name = ref[len('refs/heads/'):] if ref.startswith('refs/heads/') else ref
        match = _REF_RE.match(name)
        if not match:
            # A pointer ref (`captures/fdsdk-latest`) or something else
            # entirely. Skipped rather than guessed at: a moving pointer
            # in a baseline set would make the set change under it.
            continue
        refs.append({'sha': sha, 'ref': name, **match.groupdict()})
    return sorted(refs, key=lambda r: -int(r['run_id']))


def exclude_refs(refs: List[dict], patterns: List[str]) -> List[dict]:
    """Drop the refs a caller has named, before `-n` takes the newest N.

    A pattern is `fnmatch`ed against the full ref name and against the
    run id on its own, so both `32223468993` and `*-cold-*` work.
    """
    if not patterns:
        return refs
    return [
        ref for ref in refs
        if not any(fnmatch.fnmatch(ref['ref'], pattern)
                   or fnmatch.fnmatch(ref['run_id'], pattern)
                   for pattern in patterns)
    ]


def _parse_context(text: str) -> Dict[str, str]:
    context = {}
    for line in text.splitlines():
        if '=' in line:
            key, _, value = line.partition('=')
            context[key.strip()] = value.strip()
    return context


def fetch_run_directory(remote: str, ref: dict, dest: str, cwd: Optional[str] = None) -> dict:
    """Fetch one capture ref and materialise its `run/` at `dest`.

    Returns the ref's own `capture-context.txt` as a dict, which is what
    the homogeneity check reads.
    """
    fetch = subprocess.run(
        ['git', 'fetch', '-q', remote, ref['ref']], cwd=cwd, capture_output=True, text=True,
    )
    if fetch.returncode != 0:
        raise RuntimeError(f"git fetch {ref['ref']} failed: {fetch.stderr.strip()}")

    context_blob = subprocess.run(
        ['git', 'show', 'FETCH_HEAD:capture-context.txt'],
        cwd=cwd, capture_output=True, text=True,
    )
    context = _parse_context(context_blob.stdout) if context_blob.returncode == 0 else {}

    listing = subprocess.run(
        ['git', 'ls-tree', '--name-only', 'FETCH_HEAD'], cwd=cwd, capture_output=True, text=True,
    )
    entries = set(listing.stdout.split())

    os.makedirs(dest, exist_ok=True)
    if 'run' in entries:
        archive = subprocess.run(
            ['git', 'archive', '--format=tar', 'FETCH_HEAD', 'run'],
            cwd=cwd, capture_output=True,
        )
        if archive.returncode != 0:
            raise RuntimeError(f"git archive {ref['ref']} failed")
        staging = os.path.join(dest, '_staging.tar')
        with open(staging, 'wb') as handle:
            handle.write(archive.stdout)
        with tarfile.open(staging) as tar:
            tar.extractall(dest)
        os.remove(staging)
        run_dir = os.path.join(dest, 'run')
    elif 'capture.tar.gz' in entries:
        # The older layout. Two of the three real refs are this shape,
        # and a helper that only read the current one would fail on the
        # history it exists to read.
        blob = subprocess.run(
            ['git', 'show', 'FETCH_HEAD:capture.tar.gz'], cwd=cwd, capture_output=True,
        )
        tarball = os.path.join(dest, 'capture.tar.gz')
        with open(tarball, 'wb') as handle:
            handle.write(blob.stdout)
        with tarfile.open(tarball) as tar:
            tar.extractall(dest)
        os.remove(tarball)
        run_dir = _find_run_directory(dest)
    else:
        raise RuntimeError(
            f"{ref['ref']} carries neither run/ nor capture.tar.gz - not a capture ref"
        )

    if not run_dir or not os.path.isfile(os.path.join(run_dir, 'run-context.json')):
        raise RuntimeError(f"{ref['ref']} produced no usable run directory at {dest}")
    return {'ref': ref, 'run_dir': run_dir, 'context': context}


def _find_run_directory(root: str) -> Optional[str]:
    """The extracted `run/`, wherever the tarball happened to put it."""
    for current, directories, files in os.walk(root):
        if 'run-context.json' in files and 'graph.json' in files:
            return current
        directories.sort()
    return None


def check_homogeneity(members: List[dict]) -> dict:
    """What differs across the set, split by whether it invalidates the
    set or merely deserves saying.

    The split is the point. A different commit or mode makes these runs
    not a baseline set at all; a different `bga` revision makes them a
    baseline set assembled with drifting tooling, which is a fact a
    reader needs and not a reason to refuse.
    """
    mismatches = []
    coverage_gaps = []
    assumptions = []
    for field, absent_means in HOMOGENEOUS_FIELDS.items():
        recorded = {
            m['ref']['ref']: m['context'][field]
            for m in members if m['context'].get(field)
        }
        silent = sorted(
            m['ref']['ref'] for m in members if not m['context'].get(field)
        )
        values = set(recorded.values())

        if absent_means is not None and silent:
            # The default participates, so absent-vs-`true` is a mismatch
            # rather than a single value (UX-114).
            values.add(absent_means)
            # Recorded even when it changes nothing, because "we assumed"
            # and "it said so" are different claims and the reader is
            # entitled to know which one they are looking at. On the live
            # five-ref set this fires for every capture but one.
            assumption = {
                'field': field,
                'assumed': absent_means,
                'refs': silent,
                'message': (
                    f"{len(silent)} of {len(members)} capture(s) do not record "
                    f"{field}; taken as {field}={absent_means}, the capture "
                    f"workflow's default when those refs were published"
                ),
            }
        else:
            assumption = None

        if len(values) > 1:
            mismatch = {'field': field, 'values': sorted(values)}
            if absent_means is not None and silent:
                mismatch['assumed'] = absent_means
                mismatch['assumed_for'] = silent
            mismatches.append(mismatch)
            # The mismatch line already carries the assumption inline;
            # repeating it underneath is the same sentence twice.
            assumption = None
        if assumption is not None:
            assumptions.append(assumption)

        if absent_means is None and silent and recorded:
            # No default to fall back on, so this is neither a match nor
            # a mismatch - it is a hole, and saying so is the whole point
            # of UX-114's first clause.
            coverage_gaps.append({
                'field': field,
                'refs': silent,
                'recorded': sorted(values),
                'message': (
                    f"{len(silent)} of {len(members)} capture(s) do not record "
                    f"{field}, so the set was checked on {len(recorded)} of them. "
                    f"Absence has no defined meaning for this field - it is "
                    f"unverified, not verified-equal"
                ),
            })

    revisions = [
        (m['ref']['ref'], m['context'].get(DRIFT_FIELD)) for m in members
    ]
    distinct = {revision for _ref, revision in revisions if revision}
    drift = None
    if len(distinct) > 1:
        drift = {
            'field': DRIFT_FIELD,
            'revisions': sorted(distinct),
            'by_ref': dict(revisions),
            'message': (
                f"{len(distinct)} different {DRIFT_FIELD} values across this baseline "
                f"set - the captures were produced by different revisions of the "
                f"capture tooling, which can widen or bias the band. Reported, not "
                f"refused: this is normal in a repository under development, and "
                f"refusing would disable the helper exactly when it is most needed."
            ),
        }
    return {
        'mismatches': mismatches,
        'coverage_gaps': coverage_gaps,
        'assumptions': assumptions,
        'revision_drift': drift,
        'host_drift': _host_drift(members),
    }


def _host_drift(members: List[dict]) -> Optional[dict]:
    """UX-186 item 3: whether the set was captured on one machine.

    A warning rather than a refusal, unlike the mismatches above. A band
    assembled across machines is a real object somebody may deliberately
    want - "how much does the runner fleet vary" is a question - it just
    is not the object the band's arithmetic claims to be, and `UX-92`
    measured 33% spread on nominally identical runners to prove it.

    Read from each member's own `run-context.json`, since the capture
    context file records no host fields.
    """
    from bga import hostinfo

    manifests = []
    for member in members:
        context_path = os.path.join(member.get('run_dir') or '', 'run-context.json')
        try:
            with open(context_path, encoding='utf-8') as handle:
                manifests.append(json.load(handle).get('host_manifest'))
        except (OSError, ValueError):
            manifests.append(None)
    known = [manifest for manifest in manifests if manifest]
    if len(known) < 2 or hostinfo.homogeneous(manifests):
        return None
    models = sorted({str(manifest.get('cpu_model')) for manifest in known})
    counts = sorted({manifest.get('cpu_count') for manifest in known})
    return {
        'message': (
            f"this set spans {len(models)} CPU model(s) and {len(counts)} core "
            f"count(s) - a band over runs from different machines describes the "
            f"fleet, not the build (UX-92 measured 33% spread on one machine)"
        ),
        'cpu_models': models,
        'cpu_counts': [count for count in counts],
        'unknown': sum(1 for manifest in manifests if not manifest),
    }


def _name_refs(refs: List[str], limit: int = 3) -> str:
    """The runs a warning is about, named - the drift warning already
    names them, and a warning that says "2 captures" without saying which
    two sends the reader back to `git ls-remote`."""
    shown = ', '.join(ref.rsplit('-', 1)[-1] for ref in refs[:limit])
    return shown if len(refs) <= limit else f"{shown}, +{len(refs) - limit} more"


def trend_order(path: str) -> List[str]:
    """The run directories of a `--format json` set, oldest first.

    `UX-354`: the caller used to reach into the document -
    `[m["run_dir"] for m in reversed(json.load(f)["members"])]`, written
    out in a `python3 -c` inside a workflow step. Two key literals and
    the ordering rule, in the one file no guard in this repository
    reads, describing a document this module writes twenty lines above.

    The ordering is the part worth stating once: `bga baseline` returns
    **newest first**, because a reader asking "what is the baseline"
    wants the most recent run at the top, and a *trend* reads forwards
    in time. Nothing in a run directory records which build came before
    it, so the order is the caller's to supply - and this is the caller
    that knows.
    """
    with open(path, encoding='utf-8') as handle:
        document = json.load(handle)
    return [member['run_dir'] for member in reversed(document['members'])]


def refusal_remedy(mismatches: List[dict], members: List[dict]) -> str:
    """The sentence after the refusal: what the caller can actually do.

    Narrowing the glob only works for the four fields the ref name
    carries. For the other three it is advice that cannot be followed,
    so the odd captures are named and `--exclude` is.
    """
    invisible = [m['field'] for m in mismatches
                 if m['field'] not in NAMED_BY_THE_REF]
    if not invisible:
        return "Narrow --glob to one <commit>-<mode>-b<builders>j<max_jobs> tuple."
    verb = 'is' if len(invisible) == 1 else 'are'
    odd = _minority_refs(mismatches, members)
    remedy = (
        f"{', '.join(invisible)} {verb} not in the ref name, so no --glob "
        f"separates this set. Drop the odd capture(s) with --exclude "
        f"<run-id or ref glob>."
    )
    if odd:
        remedy += f" Here that is {_name_refs(odd)}."
    return remedy


def _minority_refs(mismatches: List[dict], members: List[dict]) -> List[str]:
    """The refs holding the least common value of a field the ref name
    cannot carry - a suggestion, not a verdict: the majority is not
    automatically the right population, and the caller decides."""
    odd = []
    for mismatch in mismatches:
        if mismatch['field'] in NAMED_BY_THE_REF:
            continue
        field = mismatch['field']
        assumed = mismatch.get('assumed')
        held = {}
        for member in members:
            value = member['context'].get(field) or assumed
            if value is None:
                continue
            held.setdefault(value, []).append(member['ref']['ref'])
        if len(held) < 2:
            continue
        smallest = min(held.values(), key=len)
        odd += [ref for ref in smallest if ref not in odd]
    return odd


def format_set_text(members: List[dict], homogeneity: dict, excluded: int = 0) -> str:
    lines = [
        '=' * 60,
        'Baseline Set',
        '=' * 60,
        f"{len(members)} capture(s), newest first:",
    ]
    if excluded:
        # A set narrowed by hand says so, in the set's own listing: a
        # band over a population the caller edited is a different
        # claim from a band over everything published.
        lines.insert(3, f"--exclude dropped {excluded} capture(s) before the newest "
                        f"{len(members)} were taken.")
    for member in members:
        ref = member['ref']
        lines.append(
            f"  {ref['ref']}"
        )
        lines.append(
            f"      {ref['commit']} {ref['mode']} "
            f"builders={ref['builders']} max_jobs={ref['max_jobs']}  "
            f"bga={(member['context'].get(DRIFT_FIELD) or 'unrecorded')[:8]}"
        )
    for mismatch in homogeneity['mismatches']:
        line = (
            f"  NOT COMPARABLE: {mismatch['field']} differs across the set "
            f"({', '.join(mismatch['values'])})"
        )
        if mismatch.get('assumed_for'):
            line += (
                f"; {len(mismatch['assumed_for'])} recorded nothing and were "
                f"taken as {mismatch['assumed']}"
            )
        lines.append(line)
        if mismatch.get('assumed_for'):
            lines.append(f"      {_name_refs(mismatch['assumed_for'])}")
    for gap in homogeneity.get('coverage_gaps') or []:
        lines.append(f"  UNVERIFIED: {gap['message']}")
        lines.append(f"      {_name_refs(gap['refs'])}")
    for assumption in homogeneity.get('assumptions') or []:
        lines.append(f"  ASSUMED: {assumption['message']}")
        lines.append(f"      {_name_refs(assumption['refs'])}")
    if homogeneity['revision_drift']:
        lines.append(f"  DRIFT: {homogeneity['revision_drift']['message']}")
    if homogeneity.get('host_drift'):
        lines.append(f"  HOSTS: {homogeneity['host_drift']['message']}")
    lines.append('=' * 60)
    return '\n'.join(lines)


def _CompactRawHelp(prog):
    """UX-158: one shared compact help layout, imported lazily so
    this module stays runnable on its own."""
    from bga.help_format import CompactRawHelp
    return CompactRawHelp(prog)

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=HELP, formatter_class=_CompactRawHelp,
    )
    parser.add_argument(
        '--remote', default='origin',
        help='Git remote (name or URL) the captures were published to. Default: origin.',
    )
    parser.add_argument(
        '--glob', default='captures/*/*-incremental-*',
        help="Ref glob selecting one comparable set, e.g. "
             "'captures/fdsdk/953683fb-incremental-b4j4-*'. The default takes every "
             "incremental capture, which is only a set if the project has one commit "
             "under capture - name the tuple explicitly for CI.",
    )
    parser.add_argument('-n', '--count', type=int, default=3,
                        help='How many of the newest captures to fetch. Default: 3.')
    parser.add_argument('--exclude', action='append', default=[], metavar='PATTERN',
                        help='Drop a capture before the newest N are taken. A run id '
                             '(32223468993) or a glob over the ref name '
                             "('*-cold-*'), repeatable. The remedy for a set that "
                             'differs on target, trace_spine or trace_opens, none of '
                             'which the ref name carries.')
    parser.add_argument('--workdir', default=None,
                        help='Where to materialise the run directories. Default: a '
                             'temporary directory, removed on exit.')
    parser.add_argument('--repo', default=None,
                        help='Git checkout to run git from. Default: the working directory.')
    parser.add_argument('--candidate', default=None,
                        help='A candidate run directory. Given one, this runs the band '
                             'compare against the fetched set and returns its exit code. '
                             'Takes a snapshot alias (`@last`, `@prev`, '
                             '`@<stamp-prefix>`) as well as a path (UX-145).')
    parser.add_argument('-f', '--format', choices=['text', 'json'], default='text')
    parser.add_argument('--band-k', default=None,
                        help='Passed through to `bga compare --band-k`.')
    parser.add_argument('compare_args', nargs='*',
                        help='Further arguments passed through to `bga compare`.')
    args = parser.parse_args(argv)

    # UX-145: the one run-directory argument outside `bga.cli`'s alias
    # threading, because this command dispatches straight to `tools/` and
    # never reaches that parser - the same gap `cache-logs` had for its
    # Plane 2 report (UX-134). Resolved through the same resolver, not a
    # copy of it, and before anything is fetched.
    if args.candidate:
        from bga.run_store import StoreError, resolve as resolve_run_alias
        try:
            args.candidate = resolve_run_alias(args.candidate)
        except StoreError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 2

    try:
        refs = list_capture_refs(args.remote, args.glob, cwd=args.repo)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    excluded = len(refs)
    refs = exclude_refs(refs, args.exclude)
    excluded -= len(refs)
    if not refs:
        print(
            f"Error: no capture refs matched {args.glob!r} on {args.remote}"
            + (f" after --exclude dropped {excluded}. " if excluded else ". ")
            + f"`git ls-remote --heads {args.remote} 'captures/*'` lists what exists.",
            file=sys.stderr,
        )
        return 1

    workdir = args.workdir or os.path.join(
        os.environ.get('TMPDIR', '/tmp'), f'bga-baseline-{os.getpid()}',
    )
    remove_workdir = args.workdir is None
    members = []
    try:
        for index, ref in enumerate(refs[:args.count]):
            try:
                members.append(fetch_run_directory(
                    args.remote, ref, os.path.join(workdir, f'{index:02d}-{ref["run_id"]}'),
                    cwd=args.repo,
                ))
            except RuntimeError as error:
                print(f"Error: {error}", file=sys.stderr)
                return 1

        homogeneity = check_homogeneity(members)
        if args.format == 'json':
            print(json.dumps({
                'members': [
                    {'ref': m['ref'], 'run_dir': m['run_dir'], 'context': m['context']}
                    for m in members
                ],
                'excluded': excluded,
                **homogeneity,
            }, indent=2))
        else:
            print(format_set_text(members, homogeneity, excluded))

        if homogeneity['mismatches']:
            print(
                "Refusing to compare against a set that is not internally comparable. "
                + refusal_remedy(homogeneity['mismatches'], members),
                file=sys.stderr,
            )
            return 6  # the same exit code `bga compare` uses for "not comparable"

        if not args.candidate:
            return 0

        # The newest member is the positional baseline, and **every**
        # member - that one included - supplies the band.
        #
        # Not a detail. `compute_band` reads only the `--baseline-run`
        # population and needs `MIN_BASELINE_RUNS` of them, so passing
        # "the rest" leaves a three-capture set one short and silently
        # falls back to the fixed 1% rule the band exists to replace.
        # Measured: with three real fdsdk refs and the rest-only shape,
        # `bga compare` reported "1 baseline run(s) supplied, 3
        # required". The positional baseline is the run being compared
        # *against*; the band is the noise model of the population it
        # came from, and it belongs in its own population.
        command = ['bga', 'compare', members[0]['run_dir'], args.candidate]
        for member in members:
            command += ['--baseline-run', member['run_dir']]
        if args.band_k:
            command += ['--band-k', str(args.band_k)]
        command += args.compare_args
        print(f"$ {' '.join(command)}")
        return subprocess.run(command).returncode
    finally:
        if remove_workdir and os.path.isdir(workdir):
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
