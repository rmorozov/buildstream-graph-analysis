"""UX-896: what the cache was configured to hold, and what it sits on.

`cache_effectiveness` reads the cache's *behaviour*. Nothing read its
*capacity*, so a cache too small to hold a project's artifacts looked
like a cache with volatile keys - and the advice that follows differs.

Three facts, from the cheapest exact source BuildStream 2.8.0 has:

- the **quota**, from BuildStream's own user configuration
  (`cache: quota`, default `infinity`), beside `reserved-disk-space`
  and `low-watermark`, resolved as `utils._parse_size` resolves it;
- the **volume** the cache sits on, from `shutil.disk_usage(cachedir)`;
- the cache's **used size**, an opt-in walk of `<cachedir>/cas`.

Per-element artifact size is not here, and that absence is measured
rather than forgotten. `%{artifact-cas-digest}` is the only `bst show`
key naming an artifact's storage and its `size_bytes` is the serialized
root `Directory` proto, not the artifact's weight - a proxy for the
thing it names. `bst artifact list-contents --long` enumerates every
file and deduplicates nothing. `UX-907` carries the question.

Every field is `None` when unread, and `infinity` is a declared quota
with no byte value rather than a quota of zero.
"""
import os
import shutil
import time
from collections.abc import Mapping
from typing import Optional

# BuildStream's own suffixes, 1024-based (`utils._parse_size`).
_UNITS = ("", "K", "M", "G", "T")

# `_context.py` reads these two filenames from `$XDG_CONFIG_HOME`, in
# this order, before falling back to its built-in defaults.
_CONFIG_NAMES = ("buildstream2.conf", "buildstream.conf")

# The walk of `<cachedir>/cas` stops here rather than holding up an
# extraction on a cache with millions of blobs. Exceeding it is a named
# outcome, not a smaller number: a truncated sum is not a cache size.
WALK_BUDGET_S = 30.0


def config_path(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """The user configuration BuildStream would read, or None.

    `$BST_USER_CONFIG` first - `bga capture` passes it to `bst` and a CI
    runner sets it - then `$XDG_CONFIG_HOME`, which BuildStream itself
    defaults to `~/.config` before looking.
    """
    env = os.environ if env is None else env
    explicit = env.get("BST_USER_CONFIG")
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    config_home = env.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config")
    for name in _CONFIG_NAMES:
        candidate = os.path.join(config_home, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def parse_size(declared, volume_total_bytes: Optional[int] = None) -> Optional[int]:
    """A BuildStream size string in bytes, or None.

    None for `infinity`, for a percentage with no volume to take it of,
    and for anything that does not parse - all four are "no byte value
    was stated", which is not a size of zero.
    """
    if not isinstance(declared, str):
        return None
    text = declared.strip()
    if not text or text == "infinity":
        return None
    number, unit = text[:-1], text[-1]
    if unit not in "KMGT%":
        number, unit = text, ""
    try:
        value = float(number)
    except ValueError:
        return None
    if unit == "%":
        if volume_total_bytes is None or not 0 <= value <= 100:
            return None
        return int(volume_total_bytes * value / 100)
    return int(value * 1024 ** _UNITS.index(unit))


def parse_percentage(declared) -> Optional[float]:
    """`"80%"` as `0.8`, or None. BuildStream's `low-watermark` is a
    ratio of the effective quota (`_context.py`), not a size, so it
    parses on its own rather than through `parse_size`."""
    if not isinstance(declared, str):
        return None
    text = declared.strip().rstrip("%")
    try:
        value = float(text)
    except ValueError:
        return None
    return value / 100 if 0 <= value <= 100 else None


def read_config(path: Optional[str] = None, env: Optional[Mapping[str, str]] = None) -> dict:
    """`cachedir` and the `cache:` block, as the file declares them.

    Values are returned verbatim; nothing is resolved here, because
    resolving a percentage needs the volume the path turns out to be on.
    `{}` when there is no readable configuration - a host running
    BuildStream's defaults declares nothing, which is a fact about the
    host rather than a missing file.
    """
    path = config_path(env) if path is None else path
    if not path or not os.path.isfile(path):
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except (OSError, ValueError, yaml.YAMLError):
        return {}
    if not isinstance(data, dict):
        return {}
    cache = data.get("cache")
    cache = cache if isinstance(cache, dict) else {}
    return {
        "config_path": path,
        "cachedir": _expand(data.get("cachedir"), env),
        "quota_declared": _as_text(cache.get("quota")),
        "reserved_declared": _as_text(cache.get("reserved-disk-space")),
        "low_watermark_declared": _as_text(cache.get("low-watermark")),
    }


def _as_text(value) -> Optional[str]:
    """A declared size as the string BuildStream would parse. YAML reads
    a bare `64` as an int, and `infinity` stays the word it is."""
    if value is None:
        return None
    return str(value)


def _expand(value, env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """`${XDG_CACHE_HOME}/buildstream` with the variable BuildStream
    would have substituted. Returns None rather than a path still
    carrying a `${...}` nobody resolved."""
    if not isinstance(value, str):
        return None
    env = os.environ if env is None else env
    cache_home = env.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache")
    expanded = value.replace("${XDG_CACHE_HOME}", cache_home)
    return None if "${" in expanded else expanded


def default_cachedir(env: Optional[Mapping[str, str]] = None) -> str:
    """Where BuildStream keeps its cache when the configuration is
    silent: `$XDG_CACHE_HOME/buildstream` (`data/userconfig.yaml`)."""
    env = os.environ if env is None else env
    cache_home = env.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache")
    return os.path.join(cache_home, "buildstream")


def cas_size_bytes(cachedir: str, budget_s: float = WALK_BUDGET_S) -> tuple:
    """`(bytes, source)` for the CAS under `cachedir`.

    `st_blocks * 512` rather than `st_size`, because the question is
    what the cache occupies on the volume the quota is enforced against,
    and a sparse or tail-packed blob does not occupy its apparent
    length. `st_nlink > 1` blobs are counted once: CAS hardlinks one
    object into several trees and counting it twice would report a cache
    larger than its own volume.

    The source is `cas_walk` on a complete walk, `budget_exceeded` when
    the walk ran out of time (bytes None - a truncated sum is not a
    cache size), and `absent` when there is no CAS to walk.
    """
    root = os.path.join(cachedir, "cas")
    if not os.path.isdir(root):
        return None, "absent"
    deadline = time.monotonic() + budget_s
    total, seen = 0, set()
    stack = [root]
    while stack:
        if time.monotonic() > deadline:
            return None, "budget_exceeded"
        try:
            entries = list(os.scandir(stack.pop()))
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                    continue
                stat = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            if stat.st_nlink > 1:
                if stat.st_ino in seen:
                    continue
                seen.add(stat.st_ino)
            total += stat.st_blocks * 512
    return total, "cas_walk"


def collect(env: Optional[Mapping[str, str]] = None, with_usage: bool = False,
            config: Optional[dict] = None) -> dict:
    """The capacity block for the machine this is running on.

    `with_usage` is off by default because the walk is the only part
    that costs anything; off, `cache_used_bytes` is absent and
    `cache_used_source` says `not_walked`, so "nobody looked" stays
    distinguishable from "looked and found nothing".
    """
    env = os.environ if env is None else env
    config = read_config(env=env) if config is None else config
    cachedir = config.get("cachedir") or default_cachedir(env)
    # No `schema` key: this is an additive `run-context/v9` extension,
    # not a published contract of its own - `host/v2` carries one
    # because `compare` classifies on it, and nothing classifies on this.
    block = {
        "config_path": config.get("config_path"),
        "cachedir": cachedir,
        "quota_declared": config.get("quota_declared"),
        "reserved_declared": config.get("reserved_declared"),
        "low_watermark_declared": config.get("low_watermark_declared"),
        "volume_total_bytes": None,
        "volume_free_bytes": None,
        "quota_bytes": None,
        "reserved_bytes": None,
        "cache_used_bytes": None,
        "cache_used_source": "not_walked",
    }
    try:
        usage = shutil.disk_usage(cachedir)
    except OSError:
        usage = None
    if usage is not None:
        block["volume_total_bytes"] = usage.total
        block["volume_free_bytes"] = usage.free
    block["quota_bytes"] = parse_size(
        block["quota_declared"], block["volume_total_bytes"])
    block["reserved_bytes"] = parse_size(
        block["reserved_declared"], block["volume_total_bytes"])
    if with_usage:
        used, source = cas_size_bytes(cachedir)
        block["cache_used_bytes"] = used
        block["cache_used_source"] = source
    return block
