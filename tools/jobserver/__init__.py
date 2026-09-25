"""UX-901: the jobserver, behind an import boundary.

Everything that acts on a sandbox - the token pool, the wrapper
ledger it writes to - lives under this package so it can later move
into a separate project of BuildStream helpers without a call-site
hunt. `tools/bst_native_build_tracer.py` is its only caller; nothing
here imports the tracer or `bga`, and nothing outside this package
reaches a name not listed below - including a submodule (`.pool`,
`.ledger`) reached directly instead of through here.

Not a plugin system: bga gains no second one for anything else this
way, and nothing here is discovered or loaded dynamically - the
tracer imports these names directly, by name.
"""
from . import pool as _pool
from .ledger import (
    JOBSERVER_SERIES_CAP,
    admission_wait_by_element,
    jobserver_auth_style,
    read_jobserver_decisions,
    read_jobserver_ledger,
    report_block,
    summarize_jobserver_leaks,
    summarize_jobserver_ledger,
    summarize_jobserver_tokens_by_element,
    tokens_by_element,
)
from .pool import (
    JOBSERVER_POOL_INTERVAL_S,
    AdmissionBroker,
    Broker,
    PoolController,
    close_jobserver,
    create_jobserver_proxies,
    open_admission_pool,
    open_jobserver,
    read_mem_available_bytes,
    read_plan_peak_rss,
    read_plan_slack,
)


def bind_cpu_sampler(reader) -> None:
    """UX-901: `PoolController` samples `/proc/stat` through the
    tracer's own reader - bound here (never imported) so this package
    never reaches back into the tracer for it."""
    _pool.cpu_sampler = reader


def bind_pid_to_element_reader(reader) -> None:
    """UX-901: `Broker`'s live refresh reads the raw log's pid map
    through the tracer's own reader - same reach-back as
    `bind_cpu_sampler`."""
    _pool.pid_to_element_reader = reader


__all__ = [
    "AdmissionBroker",
    "Broker",
    "JOBSERVER_POOL_INTERVAL_S",
    "JOBSERVER_SERIES_CAP",
    "PoolController",
    "admission_wait_by_element",
    "bind_cpu_sampler",
    "bind_pid_to_element_reader",
    "close_jobserver",
    "create_jobserver_proxies",
    "jobserver_auth_style",
    "open_admission_pool",
    "open_jobserver",
    "read_jobserver_decisions",
    "read_jobserver_ledger",
    "read_mem_available_bytes",
    "read_plan_peak_rss",
    "read_plan_slack",
    "report_block",
    "summarize_jobserver_ledger",
    "summarize_jobserver_leaks",
    "summarize_jobserver_tokens_by_element",
    "tokens_by_element",
]
