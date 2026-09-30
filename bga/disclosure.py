"""UX-1060: what every exported value path discloses, per bundle member.

`docs/design/anonymized-bundle.md` sections 3 and 6.11. Each bundle
member has a treatment (keep, transform, drop); a transformed member has
a policy keyed by its contract version, or by its layout path when it has
none. A policy names every value path with one of the eight classes,
including map keys that are data and array items:

    name        a literal schema key
    {A}         a map key that is data, of that class
    {B:vocab}   a map key checked against a vocabulary
    []          an array item

A class B path names a vocabulary: the values it may carry verbatim, and
the fallback for one it may not (a `b-` pseudonym, or `None`: refuse).
`gaps` walks a document and returns every path the policy does not name,
every class B value its vocabulary refuses, and the whole member for a
contract version with no policy. Transforming values is `UX-1062`'s.
"""

import re
from collections.abc import Iterator
from typing import Any, NamedTuple, Optional

from .sources import KEYING_BY_KIND

KEEP, TRANSFORM, DROP = "keep", "transform", "drop"

CLASSES = {
    "A": "project identifier: pseudonym, keyed and structure-preserving",
    "B": "public vocabulary: kept only when the value is on its allowlist",
    "C": "measurement: kept",
    "D": "host fact: hostname pseudonymized, the rest kept",
    "E": "content hash: re-keyed by HMAC",
    "F": "free text: rebuilt from a grammar, or dropped",
    "G": "secret: dropped, never pseudonymized",
    "H": "time: shifted to epoch 0",
}


class Vocabulary(NamedTuple):
    allowed: Any  # a frozenset of values, or a compiled pattern
    fallback: Optional[str]  # "b-" pseudonym prefix, or None: refuse

    def admits(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        if isinstance(self.allowed, re.Pattern):
            return self.allowed.fullmatch(value) is not None
        return value in self.allowed


_BINARIES = frozenset(
    [
        "sh",
        "bash",
        "dash",
        "env",
        "make",
        "gmake",
        "cmake",
        "ctest",
        "cpack",
        "ninja",
        "meson",
        "samu",
        "cc",
        "c++",
        "gcc",
        "g++",
        "cpp",
        "clang",
        "clang++",
        "cc1",
        "cc1plus",
        "cc1obj",
        "lto1",
        "lto-wrapper",
        "collect2",
        "as",
        "ld",
        "ld.bfd",
        "ld.gold",
        "ld.lld",
        "lld",
        "ar",
        "ranlib",
        "nm",
        "strip",
        "objcopy",
        "objdump",
        "readelf",
        "python",
        "python3",
        "perl",
        "install",
        "cp",
        "mv",
        "rm",
        "ln",
        "mkdir",
        "rmdir",
        "chmod",
        "cat",
        "sed",
        "awk",
        "gawk",
        "grep",
        "egrep",
        "fgrep",
        "tr",
        "sort",
        "uniq",
        "head",
        "tail",
        "cut",
        "find",
        "xargs",
        "touch",
        "tar",
        "gzip",
        "xz",
        "bzip2",
        "patch",
        "diff",
        "cmp",
        "wc",
        "date",
        "basename",
        "dirname",
        "mktemp",
        "expr",
        "test",
        "true",
        "false",
        "uname",
        "pkg-config",
        "pkgconf",
        "libtool",
        "autoconf",
        "automake",
        "autoreconf",
        "aclocal",
        "m4",
        "configure",
        "config.status",
        "bison",
        "flex",
        "yacc",
        "lex",
        "rustc",
        "cargo",
        "go",
        "javac",
        "java",
        "bst",
        "bwrap",
        "buildbox-run",
        "buildbox-casd",
    ]
)
_TOOLS = frozenset(
    [
        "bst",
        "bwrap",
        "buildbox-run",
        "buildbox-casd",
        "cc",
        "c++",
        "gcc",
        "g++",
        "clang",
        "clang++",
        "ld",
        "make",
        "cmake",
        "ninja",
        "meson",
        "python3",
    ]
)
_TOOL = "|".join(sorted(map(re.escape, _TOOLS), key=len, reverse=True))
_DISTRO = r"\((?:Ubuntu|Debian|GCC|Red Hat|Fedora|SUSE|Alpine|Arch Linux)[^()]*\)"
_ELEMENT_KINDS = frozenset(
    [
        "import",
        "manual",
        "stack",
        "compose",
        "filter",
        "junction",
        "link",
        "script",
        "autotools",
        "cmake",
        "make",
        "meson",
        "pip",
        "distutils",
        "setuptools",
        "qmake",
        "makemaker",
        "modulebuild",
    ]
)

VOCABULARIES = {
    "binary": Vocabulary(_BINARIES, "b-"),
    "tool": Vocabulary(_TOOLS, "b-"),
    "toolchain": Vocabulary(re.compile(rf"(?:(?:{_TOOL})(?: {_DISTRO})? |bubblewrap )?\d[\w.~+-]*"), "b-"),
    "element_kind": Vocabulary(_ELEMENT_KINDS, None),
    "source_kind": Vocabulary(frozenset(KEYING_BY_KIND), None),
    # "url" is written by no producer; the `one_source_many_elements` fixture holds it.
    "keying": Vocabulary(frozenset(KEYING_BY_KIND.values()) | {"unknown", "url"}, None),
    "dependency_type": Vocabulary(frozenset({"build", "runtime", "all"}), None),
    "status": Vocabulary(frozenset({"SUCCESS", "FAILURE", "SKIPPED"}), None),
    "resource": Vocabulary(frozenset({"PROCESS", "DOWNLOAD", "UPLOAD", "CACHE", "OTHER"}), None),
    "action": Vocabulary(frozenset({"build", "fetch", "pull", "push", "track", "source-push"}), None),
    "tail_phase": Vocabulary(
        frozenset(
            {
                "before the build",
                "run directory",
                "Plane 2 report",
                "raw log gzip",
                "analyze",
                "element slice",
                "compare",
                "store size",
                "timeline",
            }
        ),
        None,
    ),
    "tail_stage": Vocabulary(frozenset({"before", "after"}), None),
    "phase": Vocabulary(
        frozenset(
            {"cache_cleanup", "Loading elements", "Resolving elements", "Initializing remote caches", "Query cache"}
        ),
        None,
    ),
    "provenance": Vocabulary(
        frozenset(
            {
                "cas_walk",
                "not_walked",
                "absent",
                "budget_exceeded",
                "operator_declared",
                "parsed_from_invocation",
                "resolved_from_graph",
                "log_timestamp",
                "file_mtime",
                "env:BGA_REQUESTED_AT",
                "gitlab_ci:CI_PIPELINE_CREATED_AT",
                "no_request_instant",
                "no_start_instant",
                "request_after_start",
                "start_not_an_instant",
            }
        ),
        None,
    ),
    "schema": Vocabulary(re.compile(r"[a-z0-9-]+/v\d+"), None),
    "producer": Vocabulary(frozenset({"bga"}), None),
    "version": Vocabulary(re.compile(r"\d+(?:\.\d+)*(?:[.+-][\w.]+)?"), None),
    "clock": Vocabulary(frozenset({"CLOCK_MONOTONIC"}), None),
    "coverage": Vocabulary(frozenset({"spine+hook", "spine-only", "hook-only"}), None),
    "spine_policy": Vocabulary(frozenset({"off", "auto", "on", "always"}), None),
    "parallelism_finding": Vocabulary(frozenset({"pinned_to_one_job", "underachieved_requested_jobs"}), None),
    "jobserver_auth": Vocabulary(frozenset({"fd", "fifo"}), None),
    "jobserver_mode": Vocabulary(frozenset({"off", "auto", "n"}), None),
    "artifact_weight_source": Vocabulary(frozenset({"cas_walk", "ref_absent", "incomplete", "budget_exceeded"}), None),
}

_PER_ELEMENT = "{A}"

POLICIES = {
    "graph/v9": {
        "run_identity_hash": "E",
        "elements[].uid": "A",
        "elements[].cache_key": "E",
        "elements[].element_kind": "B:element_kind",
        "elements[].max_jobs": "C",
        "elements[].notparallel": "C",
        "elements[].requested_target": "C",
        "dependencies[].predecessor": "A",
        "dependencies[].successor": "A",
        "dependencies[].dependency_type": "B:dependency_type",
        "foundation[]": "A",
    },
    "trace/v9": {
        "run_identity_hash": "E",
        "spans[].task_key": "A",
        "spans[].ts_us": "H",
        "spans[].dur_us": "C",
        "spans[].status": "B:status",
        "spans[].primary_resource": "B:resource",
        "spans[].resources[]": "B:resource",
        "phases[].name": "B:phase",
        "phases[].ts_us": "H",
        "phases[].dur_us": "C",
    },
    "run-context/v9": {
        "host": "D",
        "host_cpu_count": "C",
        "host_memory_mb": "C",
        "host_manifest.schema": "B:schema",
        "host_manifest.cpu_count": "D",
        "host_manifest.cpu_model": "D",
        "host_manifest.distro_id": "D",
        "host_manifest.kernel_release": "D",
        "host_manifest.memory_bytes": "D",
        "host_manifest.memory_mb": "D",
        "host_manifest.toolchain.{B:tool}": "B:toolchain",
        "max_jobs": "C",
        "native_max_jobs": "C",
        "native_max_jobs_source": "B:provenance",
        "trace_epsilon_us": "C",
        "cpu_accounting.effective_cpus": "C",
        "cpu_budget": "C",
        "memory_budget_mb": "C",
        "estimated_job_memory_mb": "C",
        "jobserver_env[].name": "F",
        "jobserver_env[].prefix": "F",
        "jobserver.mode": "B:jobserver_mode",
        "jobserver.ceiling": "C",
        "jobserver.seed": "C",
        "jobserver.auth": "B:jobserver_auth",
        "jobserver.project_max_jobs": "C",
        "build_class.type": "A",
        "build_class.variant.{A}": "A",
        "artifact_weights.cachedir": "A",
        "artifact_weights.project": "A",
        "artifact_weights.run_unique_bytes": "C",
        "artifact_weights.walk_dirs_read": "C",
        "artifact_weights.elements.{A}.files_bytes": "C",
        "artifact_weights.elements.{A}.buildtree_bytes": "C",
        "artifact_weights.elements.{A}.source": "B:artifact_weight_source",
        "project_refs_provenance.path": "A",
        "project_refs_provenance.sha256": "E",
        "build_outcome.failed_count": "C",
        "build_outcome.failed_elements[]": "A",
        "build_outcome.interrupted": "C",
        "build_outcome.suspended.suspended_seconds": "C",
        "cache_capacity.cache_used_bytes": "C",
        "cache_capacity.cache_used_source": "B:provenance",
        "cache_capacity.cachedir": "A",
        "cache_capacity.config_path": "A",
        "cache_capacity.low_watermark_declared": "C",
        "cache_capacity.quota_bytes": "C",
        "cache_capacity.quota_declared": "C",
        "cache_capacity.reserved_bytes": "C",
        "cache_capacity.reserved_declared": "C",
        "cache_capacity.volume_free_bytes": "C",
        "cache_capacity.volume_total_bytes": "C",
        "pipeline_overhead[].phase": "B:phase",
        "pipeline_overhead[].elapsed_us": "C",
        "producer.tool": "B:producer",
        "producer.version": "B:version",
        "producer.contracts[]": "B:schema",
        "queue_seam.absent_reason": "B:provenance",
        "queue_seam.queue_wait_us": "C",
        "queue_seam.requested_at_source": "B:provenance",
        "queue_seam.requested_at_us": "H",
        "queue_seam.started_at_source": "B:provenance",
        "queue_seam.started_at_us": "H",
        "queue_summary.{B:action}.failed": "C",
        "queue_summary.{B:action}.processed": "C",
        "queue_summary.{B:action}.skipped": "C",
        "resource_capacities.{B:resource}": "C",
        "run_identity.manifest_hash": "E",
        "run_identity.project_git_commit": "E",
        "run_identity.project_identity": "A",
        "run_identity.project_refs_sha256": "E",
        "run_identity.scheduler.builders": "C",
        "run_identity.scheduler.fetchers": "C",
        "run_identity.scheduler.native_max_jobs": "C",
        "run_identity.scheduler.pushers": "C",
        "run_identity.targets[]": "A",
        "timestamp_agreement.note": "F",
        "timestamp_agreement.tasks_compared": "C",
        "timestamp_agreement.tasks_shorter_than_bst": "C",
        "timestamp_agreement.worst_excess_s": "C",
        "timestamp_agreement.worst_shortfall_s": "C",
        "timestamp_agreement.shorter_than_bst[].action": "B:action",
        "timestamp_agreement.shorter_than_bst[].bst_elapsed_s": "C",
        "timestamp_agreement.shorter_than_bst[].element": "A",
        "timestamp_agreement.shorter_than_bst[].shortfall_s": "C",
        "timestamp_agreement.shorter_than_bst[].span_s": "C",
        "wall_clock.start_us": "H",
        "wall_clock.end_us": "H",
        "wall_clock.start_us_source": "B:provenance",
    },
    "sources/v1": {
        "schema": "B:schema",
        "elements.{A}[].kind": "B:source_kind",
        "elements.{A}[].identity": "A",
        "elements.{A}[].declared": "A",
        "elements.{A}[].keying": "B:keying",
        "elements.{A}[].staged_at": "A",
        "unreadable.{A}[]": "F",
        "source_kind_map.{A}": "B:source_kind",
    },
    "host-samples/v1": {
        "schema": "B:schema",
        "available": "C",
        "clock": "B:clock",
        "interval_s": "C",
        "wall_at_start": "H",
        "monotonic_at_start": "H",
        "t": "H",
        **dict.fromkeys(
            (
                "cached_kb",
                "cores",
                "cpu_busy_cores",
                "load1",
                "mem_available_kb",
                "mem_free_kb",
                "mem_total_kb",
                "net_rx_bytes",
                "net_tx_bytes",
                "pgmajfault",
                "pswpin",
                "pswpout",
                "swap_free_kb",
                "swap_total_kb",
            ),
            "C",
        ),
    },
    "plane2/v3": {
        "schema": "B:schema",
        **dict.fromkeys(
            (
                "matched_count",
                "max_concurrency",
                "open_count",
                "process_count",
                "wall_span_s",
                "wrapped_command_exit_code",
            ),
            "C",
        ),
        "open_records_note": "F",
        "static_binary_disclaimer": "F",
        "by_binary.{B:binary}": "C",
        "by_element.{A}": "C",
        "commands_not_observed.available": "C",
        "commands_not_observed.note": "F",
        "commands_not_observed.elements_with_gap[]": "A",
        "commands_not_observed.per_element.{A}.named[]": "B:binary",
        "commands_not_observed.per_element.{A}.observed[]": "B:binary",
        "commands_not_observed.per_element.{A}.named_not_observed[]": "B:binary",
        "commands_not_observed.per_element.{A}.commands_not_read": "C",
        f"binary_cost.{_PER_ELEMENT}.available": "C",
        f"binary_cost.{_PER_ELEMENT}.measured_cpu_us": "C",
        f"binary_cost.{_PER_ELEMENT}.by_count[].binary": "B:binary",
        f"binary_cost.{_PER_ELEMENT}.by_count[].count": "C",
        **{f"binary_cost.{_PER_ELEMENT}.by_cpu[].{key}": "C" for key in ("count", "cpu_share", "cpu_us", "wall_s")},
        f"binary_cost.{_PER_ELEMENT}.by_cpu[].binary": "B:binary",
        f"binary_cost.{_PER_ELEMENT}.single_process_costs[].binary": "B:binary",
        f"binary_cost.{_PER_ELEMENT}.single_process_costs[].cpu_us": "C",
        f"binary_cost.{_PER_ELEMENT}.single_process_costs[].wall_s": "C",
        f"binary_cost.{_PER_ELEMENT}.binaries[].binary": "B:binary",
        **{f"binary_cost.{_PER_ELEMENT}.binaries[].{key}": "C" for key in ("count", "cpu_us", "wall_s")},
        "configure_phase.available": "C",
        "configure_phase.configure_cpu_us": "C",
        "configure_phase.configure_share": "C",
        "configure_phase.total_cpu_us": "C",
        "configure_phase.note": "F",
        **{
            f"configure_phase.per_element.{_PER_ELEMENT}.{key}": "C"
            for key in (
                "build_cpu_us",
                "build_processes",
                "configure_cpu_us",
                "configure_processes",
                "configure_share",
                "coverage",
                "measured",
                "unmeasured",
            )
        },
        **{
            f"cpu_time.{key}": "C"
            for key in (
                "available",
                "measured_processes",
                "spine_sourced_processes",
                "total_cpu_us",
                "unmeasured_processes",
            )
        },
        "cpu_time.note": "F",
        **{
            f"cpu_time.per_element.{_PER_ELEMENT}.{key}": "C"
            for key in (
                "children_cpu_us",
                "coverage",
                "cpu_per_wall_second",
                "cpu_us",
                "measured",
                "unmeasured",
                "wall_span_s",
            )
        },
        "declared_vs_used.available": "C",
        "declared_vs_used.note": "F",
        **{
            f"declared_vs_used.opens_coverage.{key}": "C"
            for key in ("elements_considered", "elements_fully_covered", "processes", "hook_covered_processes")
        },
        **{
            f"declared_vs_used.{block}[].{key}": "A"
            for block in ("unused_candidates", "used", "aggregating_dependencies")
            for key in ("element", "dependency")
        },
        **{
            f"declared_vs_used.{block}[].{key}": "C"
            for block in ("unused_candidates", "used", "aggregating_dependencies")
            for key in ("opened_files", "staged_files")
        },
        "declared_vs_used.unused_candidates[].evidence": "F",
        "declared_vs_used.aggregating_dependencies[].reason": "F",
        "declared_vs_used.uncovered_elements[].element": "A",
        "declared_vs_used.uncovered_elements[].reason": "F",
        "declared_vs_used.skipped[].element": "A",
        "declared_vs_used.skipped[].dependency": "A",
        "declared_vs_used.skipped[].reason": "F",
        **{
            f"element_attribution.{key}": "C"
            for key in (
                "attributed_share",
                "largest_bucket_processes",
                "recognized_processes",
                "reliable",
                "tagged_processes",
                "unattributed_processes",
            )
        },
        "element_attribution.largest_bucket": "A",
        "element_attribution.unresolved_bucket": "A",
        "element_attribution.recognized_elements[]": "A",
        "element_attribution.note": "F",
        "invocation_correlation.ambiguous[]": "C",
        "invocation_correlation.unmatched[]": "C",
        "invocation_correlation.certain": "C",
        "invocation_correlation.elements_in_plane1": "C",
        "invocation_correlation.intervals_used": "C",
        "invocation_correlation.relabelled_processes": "C",
        "invocation_correlation.resolved.{C}": "A",
        **{
            f"opens_captured.{_PER_ELEMENT}.{key}": "C"
            for key in ("dropped", "paths", "processes", "windows", "relative", "dirfd")
        },
        "peak_memory.available": "C",
        "peak_memory.note": "F",
        **{f"peak_memory.per_element.{_PER_ELEMENT}.{key}": "C" for key in ("measured", "peak_rss_kb", "unmeasured")},
        "per_element_parallelism[].element": "A",
        "per_element_parallelism[].findings[]": "B:parallelism_finding",
        "per_element_parallelism[].unclassified_binaries.{B:binary}": "C",
        **{
            f"per_element_parallelism[].{key}": "C"
            for key in (
                "achieved_vs_requested",
                "mean_work_concurrency",
                "peak_work_concurrency",
                "requested_jobs",
                "resolved_jobs",
                "jobs_denominator",
                "work_process_count",
                "work_process_lifetime_s",
                "work_span_s",
            )
        },
        "redundant_operations[].elements[]": "A",
        "redundant_operations[].worst_element": "A",
        "redundant_operations[].example_cmd": "F",
        "redundant_operations[].signature": "F",
        **{
            f"redundant_operations[].{key}": "C"
            for key in ("max_element_duration_s", "occurrence_count", "total_duration_s")
        },
        "redundant_operations_coverage.excluded_element_command_blocks": "C",
        "redundant_operations_coverage.excluded_unresolved_only": "C",
        "redundant_operations_coverage.findings_cap": "C",
        "redundant_operations_coverage.omitted_beyond_cap": "C",
        "redundant_operations_coverage.total_findings": "C",
        "redundant_operations_coverage.display_floor_seconds": "C",
        "redundant_operations_coverage.note": "F",
        "resource_pressure.available": "C",
        "resource_pressure.note": "F",
        "resource_pressure.measured": "C",
        "resource_pressure.unmeasured": "C",
        **{
            f"resource_pressure.per_element.{_PER_ELEMENT}.{key}": "C"
            for key in (
                "read_bytes",
                "written_bytes",
                "major_faults",
                "minor_faults",
                "voluntary_switches",
                "involuntary_switches",
                "measured",
                "unmeasured",
                "coverage",
            )
        },
        "process_outcomes.available": "C",
        "process_outcomes.note": "F",
        "process_outcomes.unknown": "C",
        "process_outcomes.exited_zero": "C",
        "process_outcomes.exited_nonzero": "C",
        "process_outcomes.killed": "C",
        "process_outcomes.killed_by_signal.{C}": "C",
        f"process_outcomes.per_element.{_PER_ELEMENT}.killed": "C",
        f"process_outcomes.per_element.{_PER_ELEMENT}.exited_nonzero": "C",
        f"process_outcomes.per_element.{_PER_ELEMENT}.statuses.{{C}}": "C",
        "spine_policy.policy": "B:spine_policy",
        "spine_policy.sandboxes": "C",
        "spine_policy.spine_traced": "C",
        "static_census.note": "F",
        "static_census.static_executables[]": "A",
        "static_census.elements_at_risk[]": "A",
        "static_census.elements_unassessable[]": "A",
        f"static_census.per_element.{_PER_ELEMENT}.dynamic_executables": "C",
        f"static_census.per_element.{_PER_ELEMENT}.static_count": "C",
        f"static_census.per_element.{_PER_ELEMENT}.assessable": "C",
        f"static_census.per_element.{_PER_ELEMENT}.unassessable_because[]": "A",
        f"static_census.per_element.{_PER_ELEMENT}.own_static[]": "A",
        f"static_census.per_element.{_PER_ELEMENT}.static_executables[]": "A",
        f"static_census.per_element.{_PER_ELEMENT}.staged_by_dependencies.{{A}}[]": "A",
        "stream_coverage.by_coverage.{B:coverage}": "C",
        **{
            f"stream_coverage.{key}": "C"
            for key in (
                "cpu_disagreement_count",
                "cpu_from_spine_only",
                "cpu_reconciled_processes",
                "exec_chains_collapsed",
                "fork_only_exits",
                "opens_coverage",
                "opens_covered_processes",
                "processes",
                "unmatched_ends",
            )
        },
        "stream_coverage.note": "F",
        **{
            f"stream_coverage.cpu_aggregate.{key}": "C"
            for key in ("processes", "spine_cpu_us", "hook_cpu_us", "delta_us", "delta_pct")
        },
        "stream_coverage.cpu_disagreements[].pid": "C",
        "stream_coverage.cpu_disagreements[].element": "A",
        "stream_coverage.cpu_disagreements[].cmd": "F",
        **{f"stream_coverage.cpu_disagreements[].{key}": "C" for key in ("spine_cpu_us", "hook_cpu_us", "delta_us")},
    },
    "plane2-resource.json": {
        "cores_busy": "C",
        "peak_rss_bytes": "C",
    },
    "tail/v1": {
        "schema": "B:schema",
        "producer.tool": "B:producer",
        "producer.version": "B:version",
        "producer.contracts[]": "B:schema",
        "build_wall_us": "C",
        "complete": "C",
        "phases[].name": "B:tail_phase",
        "phases[].wall_us": "C",
        "phases[].peak_rss_bytes": "C",
        "phases[].stage": "B:tail_stage",
        # A call's argv names elements and paths: rebuilt by 6.2's command grammar.
        "phases[].calls[].verb": "F",
        "phases[].calls[].wall_us": "C",
        "phases[].calls[].exit": "C",
    },
    "element-slice.json": {
        "elements[].element_uid": "A",
        "elements[].duration_us": "C",
        "elements[].share_of_path": "C",
        "elements[].on_critical_path": "C",
        "elements_considered": "C",
        "bounded_at": "C",
    },
}

#: `{snapshot-relative member: treatment}`, stage 4 of the design.
TREATMENTS = {
    "run/graph.json": TRANSFORM,
    "run/trace.json": TRANSFORM,
    "run/run-context.json": TRANSFORM,
    "run/sources.json": TRANSFORM,
    "run/chrome_trace.json": DROP,
    "plane2.json": TRANSFORM,
    "plane2-resource.json": TRANSFORM,
    "host-samples.jsonl": TRANSFORM,
    "element-slice.json": TRANSFORM,
    "tail.json": TRANSFORM,
    "analyze.json": DROP,
    "plane2.log.gz": TRANSFORM,
    "build.log": TRANSFORM,
    "capture-context.txt": TRANSFORM,
    ".size": DROP,
}

#: The transformed members that are text, not JSON: rewritten line by line
#: (`anonymize.tokenize_line`), a `.gz` one inflated and deflated again.
LINE_MEMBERS = frozenset({"plane2.log.gz", "build.log", "capture-context.txt"})


class Gap(NamedTuple):
    path: str  # "" is the whole member
    reason: str

    def __str__(self) -> str:
        return f"{self.path or '<member>'}: {self.reason}"


def layout_members() -> dict:
    """`{snapshot-relative member: contract}`, from `CAPTURE_LAYOUT`."""
    from .run_store import CAPTURE_LAYOUT, RUNS_DIRNAME, STORE_DIRNAME

    prefix = f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/"
    return {
        path[len(prefix) :]: contract
        for path, _presence, contract, _what in CAPTURE_LAYOUT
        if path.startswith(prefix) and not path.endswith("/")
    }


def policy_key(member: str, contract: Optional[str]) -> str:
    """The policy a member is read under: its contract, else its layout path."""
    return contract or member


def _parse(pattern: str) -> list[str]:
    steps = []
    for part in pattern.split("."):
        # A `{...}` placeholder may itself be followed by `[]`.
        name, arrays = part, 0
        while name.endswith("[]"):
            name, arrays = name[:-2], arrays + 1
        steps.append(name)
        steps.extend(["[]"] * arrays)
    return steps


def compile_policy(policy: dict) -> dict:
    """The patterns as a trie: `{step: subtrie}`, and `"."` for a value class."""
    trie: dict = {}
    for pattern, klass in policy.items():
        node = trie
        for step in _parse(pattern):
            node = node.setdefault(step, {})
        node["."] = klass
    return trie


def _vocabulary(klass: str) -> Optional[Vocabulary]:
    return VOCABULARIES[klass[2:]] if klass.startswith("B:") else None


def _refused(klass: str, value: Any) -> bool:
    vocab = _vocabulary(klass)
    return vocab is not None and value is not None and vocab.fallback is None and not vocab.admits(value)


#: A class-C *key* names a number (a pid, a signal, an exit status), not a
#: measurement of its own - `_refused` only checks a `B:` vocabulary, so a
#: class-C key otherwise accepted any string verbatim.
_INTEGER_KEY_RE = re.compile(r"-?\d+")


def _key_refused(klass: str, key: Any) -> bool:
    """A map key's class, checked separately from `_refused`'s leaf values:
    a class-C key must itself look like the number it claims to be, fail-
    closed against anything else smuggled in as a key."""
    if klass == "C":
        return not (isinstance(key, str) and _INTEGER_KEY_RE.fullmatch(key))
    return _refused(klass, key)


class Step(NamedTuple):
    node: Optional[dict]  # None: the policy does not name the key
    path: str
    name: str  # the literal key, or its `{...}` placeholder
    gaps: list


def step(node: dict, key: str, path: str) -> Step:
    """Where `key` of a map at `node` leads, and the gaps the key alone makes."""
    where = f"{path}.{key}" if path else str(key)
    if key in node and not key.startswith(("{", "[", ".")):
        return Step(node[key], where, key, [])
    placeholder = next((k for k in node if k.startswith("{")), None)
    if placeholder is None:
        return Step(None, where, key, [Gap(where, "not named by the policy")])
    refused = _key_refused(placeholder[1:-1], key)
    return Step(
        node[placeholder], where, placeholder, [Gap(where, f"key {key!r} is not on its allowlist")] if refused else []
    )


def _walk_map(node: dict, value: dict, path: str) -> Iterator[Gap]:
    if not any(not k.startswith(("[", ".")) for k in node):
        yield Gap(path, "a map where the policy names none")
        return
    for key, item in value.items():
        where = step(node, key, path)
        yield from where.gaps
        if where.node is not None:
            yield from walk(where.node, item, where.path)


def walk(node: dict, value: Any, path: str) -> Iterator[Gap]:
    """Every gap in `value`, read at `node` of a compiled policy."""
    if value is None:
        return  # an absent value discloses nothing, at a leaf or a block
    if isinstance(value, dict):
        yield from _walk_map(node, value, path)
    elif isinstance(value, list):
        if "[]" not in node:
            yield Gap(path, "an array where the policy names none")
            return
        for item in value:
            yield from walk(node["[]"], item, path + "[]")
    elif "." not in node:
        yield Gap(path, "a value where the policy names none")
    elif _refused(node["."], value):
        yield Gap(path, f"value {value!r} is not on its allowlist")


def gaps(member: str, contract: Optional[str], documents: list) -> list[Gap]:
    """Every path in `documents` (one, or one per `.jsonl` line) the policy
    for `member` under `contract` does not name, and every refused value."""
    policy = POLICIES.get(policy_key(member, contract))
    if policy is None:
        return [Gap("", f"{policy_key(member, contract)!r} has no disclosure policy")]
    trie = compile_policy(policy)
    found: list[Gap] = []
    for document in documents:
        for gap in walk(trie, document, ""):
            if gap not in found:
                found.append(gap)
    return found
