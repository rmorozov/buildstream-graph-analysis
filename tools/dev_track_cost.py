"""UX-525: where an implementer track's tokens go, by phase.

Round 75 recorded three tracks as three totals and no split. This reads
the transcript the harness already writes - one JSONL per subagent -
and attributes its tokens to the phase each turn was doing.

    python3 tools/dev_track_cost.py --list
    python3 tools/dev_track_cost.py <transcript.jsonl> ...

**The quantity.** `input_tokens + cache_creation_input_tokens` per API
response: what newly entered the context there. Summed, it is the
context the track ended with, to 0.2% - so it is the whole cost of the
track and not a sample of it. `cache_read_input_tokens` is excluded and
printed separately: it is the same prefix re-read every turn, so it
counts turns, not work. `output_tokens` is not summed - this transcript
under-reports it, and the agent's own output re-enters the next
response's `cache_creation` anyway, where this counts it once.

**The attribution.** One response is several JSONL records sharing a
`message.id` and one `usage`; counting records multiplies it. A
response's cost is charged to the *previous* response's phase, because
what entered the context is that turn's tool results and its own text.
The phase comes from tool argv, never from prose; a turn touching two
phases is charged to the higher, and `-v` prints how many that was.
"""
import argparse
import collections
import datetime
import json
import os
import pathlib
import re
import sys

#: Highest precedence first. A turn that both writes an Outcome and
#: commits is an Outcome turn: the write is the tokens, the commit is
#: one line. `brief` is the harness's opening prompt, charged to no
#: phase because the track did not choose it.
PHASES = ("brief", "outcome", "close", "falsify", "test", "edit", "read", "other")

_PYTEST = re.compile(r"\bpytest\b|\bmake +test")
_MUTATE = re.compile(r"write_text\(|\.replace\(|sed +-i|\bcp +[-\w./$]")
_CLOSE = re.compile(r"\bgit +(commit|add)\b|dev_close_task\.py|\bmake +(lint|check-clean)\b")
_WRITE = re.compile(r"write_text\(|sed +-i|<<'|<<\"|\btee\b|>>? *[\w./]")
_TASK_FILE = re.compile(r"docs/backlog/scenarios/UX-\d+[\w-]*\.md")
_READ = re.compile(
    r"\b(cat|head|tail|grep|rg|ls|wc|find|awk|sed +-n"
    r"|git +(log|grep|show|diff|status|ls-remote))\b")


def _tool_text(block):
    """The argv-ish text of one `tool_use` block: what it ran or wrote."""
    args = block.get("input") or {}
    if not isinstance(args, dict):
        return block.get("name", ""), ""
    parts = [str(args.get(key, "")) for key in
             ("command", "file_path", "path", "pattern", "new_string")]
    return block.get("name", ""), " ".join(part for part in parts if part)


def phases_of(tools):
    """Every phase one response's tool calls belong to."""
    found = set()
    for block in tools:
        name, text = _tool_text(block)
        if name in ("Read", "Grep", "Glob"):
            found.add("read")
        elif name in ("Edit", "Write", "NotebookEdit"):
            found.add("outcome" if _TASK_FILE.search(text) else "edit")
        elif name != "Bash":
            found.add("other")
        elif _PYTEST.search(text) and _MUTATE.search(text):
            found.add("falsify")
        elif _PYTEST.search(text):
            found.add("test")
        elif _CLOSE.search(text):
            found.add("close")
        elif _TASK_FILE.search(text) and _WRITE.search(text):
            found.add("outcome")
        elif _WRITE.search(text):
            found.add("edit")
        elif _READ.search(text):
            found.add("read")
        else:
            found.add("other")
    return found or {"other"}


def rank(found):
    """The one phase a multi-phase turn is charged to."""
    return min(found, key=PHASES.index)


def responses(path):
    """`(tools, usage)` per API response, in order, counted once.

    One response is several records sharing a `message.id`, each
    carrying the same `usage`; the tool calls are spread across them.
    """
    order, tools, usage = [], {}, {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            message = record.get("message")
            if record.get("type") != "assistant" or not isinstance(message, dict):
                continue
            key = message.get("id")
            if key not in usage:
                order.append(key)
                usage[key] = message.get("usage") or {}
                tools[key] = []
            content = message.get("content")
            if isinstance(content, list):
                tools[key] += [b for b in content if isinstance(b, dict)
                               and b.get("type") == "tool_use"]
    return [(tools[key], usage[key]) for key in order]


def _stamps(path):
    out = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            stamp = json.loads(line).get("timestamp")
            if stamp:
                out.append(stamp)
    return out


def split(path):
    """The per-phase table for one transcript, and the track's totals."""
    rows = responses(path)
    by_phase = collections.defaultdict(lambda: [0, 0])  # turns, tokens
    ambiguous = [0, 0]
    peak = 0
    for index, (tools, usage) in enumerate(rows):
        found = phases_of(tools)
        cost = (usage.get("input_tokens", 0)
                + usage.get("cache_creation_input_tokens", 0))
        peak = max(peak, cost + usage.get("cache_read_input_tokens", 0))
        owner = "brief" if not index else rank(phases_of(rows[index - 1][0]))
        by_phase[owner][1] += cost
        by_phase[rank(found)][0] += 1
        if len(found) > 1:
            ambiguous[0] += 1
            ambiguous[1] += cost
    wall = 0
    stamps = _stamps(path)
    if stamps:
        span = (datetime.datetime.fromisoformat(max(stamps).replace("Z", "+00:00"))
                - datetime.datetime.fromisoformat(min(stamps).replace("Z", "+00:00")))
        wall = round(span.total_seconds())
    return {"phases": by_phase, "responses": len(rows), "wall": wall,
            "peak_context": peak,
            "cache_read": sum(u.get("cache_read_input_tokens", 0) for _, u in rows),
            "ambiguous_turns": ambiguous[0], "ambiguous_tokens": ambiguous[1]}


def report(path, verbose=False):
    data = split(path)
    total = sum(count for _, count in data["phases"].values()) or 1
    lines = [f"{os.path.basename(path)}  {data['wall']}s  "
             f"{data['responses']} responses",
             "phase      turns     tokens      %"]
    for phase in PHASES:
        if phase not in data["phases"]:
            continue
        turns, tokens = data["phases"][phase]
        lines.append("%-9s %6d %10d %6.1f"
                     % (phase, turns, tokens, 100.0 * tokens / total))
    lines.append("%-9s %6d %10d %6.1f"
                 % ("TOTAL", data["responses"], total, 100.0))
    lines.append(f"context high-water {data['peak_context']}, "
                 f"cache re-reads {data['cache_read']}")
    if verbose:
        lines.append(f"turns in two phases: {data['ambiguous_turns']} "
                     f"({data['ambiguous_tokens']} tokens)")
    return "\n".join(lines)


def implementer_transcripts(root):
    """Every subagent transcript whose opening message is a track brief.

    The brief is the harness's, not the agent's - a track is what it was
    told to be, so this reads the first record and nothing later.
    """
    found = []
    for path in sorted(pathlib.Path(root).rglob("subagents/*.jsonl")):
        with open(path, encoding="utf-8") as handle:
            first = handle.readline()
        if not first.strip():
            continue
        message = json.loads(first).get("message") or {}
        text = message.get("content")
        text = text if isinstance(text, str) else json.dumps(text)
        if re.search(r"running (ONE|one) [Tt][Rr][Aa][Cc][Kk]"
                     r"|Implement \*\*UX-\d+\*\* only", text):
            item = re.search(r"UX-\d+", text)
            found.append((str(path), item.group(0) if item else "?"))
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("transcripts", nargs="*")
    parser.add_argument("--root", default=os.path.expanduser("~/.claude/projects"),
                        help="Where the harness writes agent transcripts.")
    parser.add_argument("--list", action="store_true",
                        help="Name the implementer transcripts under --root.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    if args.list:
        for path, item in implementer_transcripts(args.root):
            print(f"{item:<8} {path}")
        return 0
    if not args.transcripts:
        parser.error("give a transcript path, or --list")
    for path in args.transcripts:
        print(report(path, args.verbose))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
