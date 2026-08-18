"""UX-92: what the cache actually did.

Round 6 established that *every* real CI build is incremental, which
makes the cache the dominant efficiency mechanism - and `bga` treated it
as a footnote. `UX-55` taught the report to stop miscounting cached
elements as coverage gaps; that was the whole cache story.

The gap this closes is not cosmetic. Occupancy, the efficiency score and
the certified floors all describe *the work the build did*. A build with
terrible cache behaviour does less-cached work, does it efficiently, and
scores well - so the single largest real-world BuildStream efficiency
failure mode, a volatile cache key near the root converting every
incremental build into a near-full one, is invisible to every signal the
tool publishes. Stage 1 is the accounting; `compare` adds the churn
detection that names the culprit.

Nothing here is derived or modelled: BuildStream's own closing Pipeline
Summary says how many elements it built and how many it skipped, and the
run's own spans say where the time went. Every field is None rather than
0 when the capture does not record it, on this codebase's standing rule
that "not measured" and "measured as none" are different facts.
"""
from typing import Dict, List, Optional, Set

# A hit ratio at or above this is not worth a line of report: the cache
# is doing its job. `UX-65`'s bar, one domain over - below this share is
# not an opportunity, it is how caching works.
HEALTHY_HIT_RATIO = 0.5

# Below this, an "incremental" build is not incremental in any useful
# sense and the report should say so rather than reporting its scheduling
# efficiency as though that were the interesting fact.
POOR_HIT_RATIO = 0.2

# Pull/push time above this share of wall clock is worth naming: the
# build spent it moving artifacts rather than making them.
TRANSFER_SHARE_NOTABLE = 0.1


def _queue(run_context, name: str) -> dict:
    return ((getattr(run_context, 'queue_summary', None) or {}).get(name)) or {}


def _ratio(hits: Optional[int], misses: Optional[int]) -> Optional[float]:
    """Hits over the population that *could* have hit.

    None when either side is unrecorded, and None (not 1.0) for an empty
    population: a queue that processed nothing did not achieve a perfect
    hit ratio, it has no hit ratio.
    """
    if not isinstance(hits, int) or not isinstance(misses, int):
        return None
    total = hits + misses
    return hits / total if total > 0 else None


def _closure(graph, targets: Set[str]) -> Set[str]:
    """Every element the given targets depend on, transitively, plus the
    targets themselves.

    Walks `dependencies` unfiltered - `runtime`-only edges included.
    That differs from the critical-path walk (`P4-11` excludes them,
    correctly, because they do not gate a build *start*), and the
    difference is deliberate: this answers "what does shipping this
    target require", and a runtime dependency is required. An element
    excluded here would be an element whose cache state nobody accounts
    for.
    """
    predecessors: Dict[str, List[str]] = {}
    for dep in getattr(graph, 'dependencies', None) or []:
        predecessors.setdefault(dep.successor, []).append(dep.predecessor)

    seen: Set[str] = set()
    stack = list(targets)
    while stack:
        uid = stack.pop()
        if uid in seen:
            continue
        seen.add(uid)
        stack.extend(predecessors.get(uid, []))
    return seen


def _transfer_us(tasks) -> Dict[str, int]:
    """Wall-clock in each transfer resource, from the run's own spans.

    Summed over task duration rather than over a resource timeline, so
    two concurrent pulls count twice - the question this answers is
    "how much pulling did this build do", not "how long was the pull
    window".
    """
    totals: Dict[str, int] = {}
    for task in tasks or []:
        resource = getattr(task, 'primary_resource', None)
        if resource is None:
            continue
        name = getattr(resource, 'value', resource)
        if name in ('DOWNLOAD', 'UPLOAD'):
            totals[name] = totals.get(name, 0) + (task.finish_us - task.start_us)
    return totals


def compute_cache_accounting(
    run_context, graph=None, tasks=None, total_duration_us: Optional[int] = None,
) -> dict:
    """UX-92 stage 1: the cache's own report card for one run.

    Returns `{}` when the capture records no Pipeline Summary at all -
    there is nothing to account, and an empty block is honest where a
    block of Nones invites a consumer to render zeros.
    """
    build = _queue(run_context, 'build')
    fetch = _queue(run_context, 'fetch')
    if not build and not fetch:
        return {}

    built = build.get('processed')
    cached = build.get('skipped')
    accounting = {
        'built_elements': built if isinstance(built, int) else None,
        'cached_elements': cached if isinstance(cached, int) else None,
        'hit_ratio': _ratio(cached, built),
        'fetch': {
            'fetched': fetch.get('processed') if isinstance(fetch.get('processed'), int) else None,
            'already_present': fetch.get('skipped') if isinstance(fetch.get('skipped'), int) else None,
            'hit_ratio': _ratio(fetch.get('skipped'), fetch.get('processed')),
        },
    }

    transfer = _transfer_us(tasks)
    if transfer:
        accounting['transfer_us'] = transfer
        if total_duration_us:
            accounting['transfer_share'] = sum(transfer.values()) / total_duration_us

    # The requested target's own closure, which is the number a build
    # owner actually asked about: a project-wide 72% means little when
    # the thing being shipped rebuilt entirely.
    targets = {e.uid for e in (getattr(graph, 'elements', None) or []) if getattr(e, 'requested_target', False)}
    if targets and graph is not None:
        closure = _closure(graph, targets)
        built_uids = {
            task.task_key.element_uid for task in (tasks or [])
            if getattr(task.task_key, 'task_kind', None) is not None
            and getattr(task.task_key.task_kind, 'value', '') == 'BUILD'
        }
        in_closure_built = closure & built_uids
        accounting['target_closure'] = {
            'targets': sorted(targets),
            'elements': len(closure),
            'built': len(in_closure_built),
            # Cached is the remainder rather than a second measurement:
            # an element in the closure that produced no BUILD task in
            # this run did not build, and `UX-55` established that is
            # what "cached" means in a capture.
            'cached': len(closure) - len(in_closure_built),
            'hit_ratio': (
                (len(closure) - len(in_closure_built)) / len(closure) if closure else None
            ),
        }
    return accounting


def compute_cache_churn(
    baseline_elements, candidate_elements, dependencies,
    candidate_built: Set[str], candidate_durations: Dict[str, int],
) -> dict:
    """UX-92 stage 2: which rebuilds in the candidate were not earned.

    BuildStream's cache key is a hash over an element's own definition
    *and* its dependencies' keys, so it is exactly the "did anything
    that affects this element change" question already computed for us.
    Two facts fall out of comparing the two runs' keys:

    **Churn** - an element the candidate rebuilt whose key is *identical*
    to the baseline's. Nothing about it or anything it depends on
    changed, and it built anyway. Its output is the artifact that already
    existed, so the time is waste by definition rather than by judgement.

    **Invalidation roots** - among elements whose key *did* change, the
    ones all of whose dependencies' keys are unchanged. The change
    originated there; everything downstream of it is explained rather
    than suspicious. This is the shape of the failure mode the task was
    filed for: one volatile key near the root (a timestamp leaking into
    an artifact, an over-broad `project.conf` variable) turning every
    incremental build into a near-full one. Naming the root is the whole
    value - a list of the 200 elements it invalidated is a symptom.

    Elements absent from either side are skipped rather than guessed at:
    an element the baseline never had cannot have churned.
    """
    baseline_keys = {e.uid: e.cache_key for e in baseline_elements if e.cache_key}
    candidate_keys = {e.uid: e.cache_key for e in candidate_elements if e.cache_key}
    comparable = set(baseline_keys) & set(candidate_keys)
    if not comparable:
        return {}

    unchanged = {uid for uid in comparable if baseline_keys[uid] == candidate_keys[uid]}
    changed = comparable - unchanged

    churned = sorted(unchanged & candidate_built)
    wasted_us = sum(candidate_durations.get(uid, 0) for uid in churned)

    predecessors: Dict[str, List[str]] = {}
    for dep in dependencies or []:
        predecessors.setdefault(dep.successor, []).append(dep.predecessor)

    successors: Dict[str, List[str]] = {}
    for dep in dependencies or []:
        successors.setdefault(dep.predecessor, []).append(dep.successor)

    roots = []
    for uid in sorted(changed):
        upstream = [p for p in predecessors.get(uid, []) if p in comparable]
        if any(p in changed for p in upstream):
            continue  # explained by something above it
        # What this root cost: itself plus every element downstream of it
        # whose key also changed and which rebuilt. Bounded to `changed`
        # so an unrelated rebuild further down is not billed to this
        # root, and counted per root rather than summed across roots -
        # two roots can invalidate the same subtree and adding their
        # costs would double-count it.
        invalidated, stack = set(), [uid]
        while stack:
            node = stack.pop()
            if node in invalidated or node not in changed:
                continue
            invalidated.add(node)
            stack.extend(successors.get(node, []))
        rebuilt_downstream = (invalidated & candidate_built) - {uid}
        roots.append({
            'element_uid': uid,
            'baseline_cache_key': baseline_keys[uid],
            'candidate_cache_key': candidate_keys[uid],
            'rebuilt': uid in candidate_built,
            'duration_us': candidate_durations.get(uid, 0),
            'downstream_rebuilt': len(rebuilt_downstream),
            'downstream_us': sum(candidate_durations.get(d, 0) for d in rebuilt_downstream),
        })

    return {
        'comparable_elements': len(comparable),
        'unchanged_keys': len(unchanged),
        'changed_keys': len(changed),
        'churned_elements': churned,
        'churned_count': len(churned),
        'wasted_rebuild_us': wasted_us,
        # Sorted by what the invalidation cost downstream, so the
        # expensive root leads rather than the alphabetically first one.
        'invalidation_roots': sorted(
            roots,
            key=lambda r: (-(r['duration_us'] + r['downstream_us']), r['element_uid']),
        ),
    }
