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
    r"|git +(log|grep|show|diff|status|ls-remote))\b"
)


def _record(line):
    """One transcript line, or `None` when it will not parse.

    `UX-711`: a session measuring **itself** reads a transcript still
    being appended to, so the last line is half written. Every reader
    below goes through here; skipping that line costs the final
    response and is what makes the figure obtainable from inside the
    run it describes.
    """
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _tool_text(block):
    """The argv-ish text of one `tool_use` block: what it ran or wrote."""
    args = block.get("input") or {}
    if not isinstance(args, dict):
        return block.get("name", ""), ""
    parts = [str(args.get(key, "")) for key in ("command", "file_path", "path", "pattern", "new_string")]
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
            record = _record(line)
            if record is None:
                continue
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
                tools[key] += [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
    return [(tools[key], usage[key]) for key in order]


def _stamps(path):
    out = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            parsed = _record(line)
            if parsed is None:
                continue
            stamp = parsed.get("timestamp")
            if stamp:
                out.append(stamp)
    return out


def _parse_ts(stamp):
    return datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _fresh(usage):
    """What newly entered the context in one response - the tool's quantity."""
    return usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)


def split(path):
    """The per-phase table for one transcript, and the track's totals."""
    rows = responses(path)
    by_phase = collections.defaultdict(lambda: [0, 0])  # turns, tokens
    ambiguous = [0, 0]
    peak = 0
    for index, (tools, usage) in enumerate(rows):
        found = phases_of(tools)
        cost = _fresh(usage)
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
        span = _parse_ts(max(stamps)) - _parse_ts(min(stamps))
        wall = round(span.total_seconds())
    return {
        "phases": by_phase,
        "responses": len(rows),
        "wall": wall,
        "peak_context": peak,
        "cache_read": sum(u.get("cache_read_input_tokens", 0) for _, u in rows),
        "ambiguous_turns": ambiguous[0],
        "ambiguous_tokens": ambiguous[1],
    }


def _response_stamps(path):
    """One timestamp per response, in `responses()`'s own order."""
    order, stamp = [], {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            record = _record(line)
            if record is None:
                continue
            message = record.get("message")
            if record.get("type") != "assistant" or not isinstance(message, dict):
                continue
            key = message.get("id")
            if key not in stamp:
                order.append(key)
                stamp[key] = record.get("timestamp")
    return [stamp[key] for key in order]


def rebuilds(path, floor=30000):
    """Responses over `floor` whose previous response called no tool -
    a wake re-entering the whole live context, not a turn that read one.
    The first response has no previous one at all, the purest case."""
    rows = responses(path)
    stamps = _response_stamps(path)
    total = sum(_fresh(usage) for _, usage in rows)
    found = []
    for index in range(len(rows)):
        cost = _fresh(rows[index][1])
        no_tool_before = index == 0 or not rows[index - 1][0]
        if cost > floor and no_tool_before:
            found.append({"timestamp": stamps[index], "cost": cost})
    tokens = sum(item["cost"] for item in found)
    return {
        "count": len(found),
        "tokens": tokens,
        "share": tokens / total if total else 0.0,
        "total": total,
        "rebuilds": found,
    }


def _round_boundaries(spec):
    """`name=ISO-timestamp` pairs from `--rounds`, earliest first."""
    pairs = []
    for item in spec.split(","):
        name, _, stamp = item.partition("=")
        pairs.append((name, _parse_ts(stamp)))
    return sorted(pairs, key=lambda pair: pair[1])


def round_totals(path, rounds_spec, floor=30000):
    """Responses, tokens and rebuilds per named round boundary."""
    boundaries = _round_boundaries(rounds_spec)
    rows = responses(path)
    stamps = _response_stamps(path)
    totals = {name: {"responses": 0, "tokens": 0, "rebuilds": 0} for name, _ in boundaries}
    for index, (_tools, usage) in enumerate(rows):
        stamp = stamps[index]
        owner = boundaries[0][0]
        if stamp:
            when = _parse_ts(stamp)
            for name, start in boundaries:
                if start <= when:
                    owner = name
        totals[owner]["responses"] += 1
        totals[owner]["tokens"] += _fresh(usage)
        if _fresh(usage) > floor and (index == 0 or not rows[index - 1][0]):
            totals[owner]["rebuilds"] += 1
    return totals


def report_rebuilds(path, floor=30000, rounds_spec=None):
    data = rebuilds(path, floor)
    lines = [
        f"{os.path.basename(path)}  rebuilds {data['count']}  "
        f"tokens {data['tokens']}  share {100.0 * data['share']:.1f}%"
    ]
    for item in data["rebuilds"]:
        lines.append(f"  {item['timestamp']}  {item['cost']}")
    if rounds_spec:
        lines.append("round      responses     tokens  rebuilds")
        for name, _ in _round_boundaries(rounds_spec):
            row = round_totals(path, rounds_spec, floor)[name]
            lines.append(f"{name:<10} {row['responses']:9d} {row['tokens']:10d} {row['rebuilds']:9d}")
    return "\n".join(lines)


def report(path, verbose=False):
    data = split(path)
    total = sum(count for _, count in data["phases"].values()) or 1
    lines = [
        f"{os.path.basename(path)}  {data['wall']}s  {data['responses']} responses",
        "phase      turns     tokens      %",
    ]
    for phase in PHASES:
        if phase not in data["phases"]:
            continue
        turns, tokens = data["phases"][phase]
        lines.append(f"{phase:<9} {turns:6d} {tokens:10d} {100.0 * tokens / total:6.1f}")
    lines.append(f"{'TOTAL':<9} {data['responses']:6d} {total:10d} {100.0:6.1f}")
    lines.append(f"context high-water {data['peak_context']}, cache re-reads {data['cache_read']}")
    dollars = cost_of(path)
    lines.append("priced: " + ("— (a model with no row in PRICES)" if dollars is None else f"${dollars:.2f}"))
    if verbose:
        lines.append(f"turns in two phases: {data['ambiguous_turns']} ({data['ambiguous_tokens']} tokens)")
    return "\n".join(lines)


def implementer_transcripts(root):
    """Every subagent transcript whose opening message is a track brief.

    The brief is the harness's, not the agent's - a track is what it was
    told to be, so this reads the first record and nothing later.
    """
    found = []
    root = pathlib.Path(root)
    paths = sorted(root.rglob("subagents/*.jsonl")) + sorted(root.rglob("tasks/*.output"))
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            first = handle.readline()
        if not first.strip():
            continue
        try:
            record = _record(first)
            if record is None:
                continue
        except json.JSONDecodeError:
            continue  # a `tasks/*.output` that is a Bash run's own stdout
        if not isinstance(record, dict):
            continue
        message = record.get("message") or {}
        text = message.get("content")
        text = text if isinstance(text, str) else json.dumps(text)
        if re.search(
            r"running (ONE|one) [Tt][Rr][Aa][Cc][Kk]"
            r"|Implement \*\*UX-\d+\*\* only",
            text,
        ):
            item = re.search(r"UX-\d+", text)
            found.append((str(path), item.group(0) if item else "?"))
    return found


_MODEL_WORD = re.compile(r"[a-zA-Z]+")

#: `UX-1351`: dollars per million tokens, from Claude Code 2.1.296's own
#: billing table - input, output, 5-minute write, 1-hour write, cache read.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50, 0.125, 0.20, 0.01),
    "claude-sonnet-5-5": (2.0, 10.0, 2.5, 4.0, 0.10),
    "claude-sonnet-5": (2.0, 10.0, 2.5, 4.0, 0.20),
    "claude-opus-5-5": (4.0, 20.0, 5.0, 8.0, 0.20),
    "claude-opus-5": (5.0, 25.0, 6.25, 10.0, 0.50),
    "claude-fable-5-1": (10.0, 50.0, 12.5, 20.0, 0.25),
    "claude-fable-5": (10.0, 50.0, 12.5, 20.0, 1.0),
}

#: Haiku 5.5 bills a response whose whole prompt passes 100K tokens on a
#: second card, five times the first; no other model here has one.
LONG_PROMPT = {"claude-haiku-5-5": (100_000, (0.50, 2.50, 0.625, 1.0, 0.05))}


def _base_model(raw):
    """`claude-opus-5-5[1m]` and `claude-opus-5-5-20260101` -> `claude-opus-5-5`."""
    raw = (raw or "").split("[")[0]
    return re.sub(r"-\d{8}$", "", raw)


def price(usage, model):
    """One response's dollars, or `None` for a model with no row in `PRICES`."""
    base = _base_model(model)
    if base not in PRICES:
        return None
    rates = PRICES[base]
    fresh = usage.get("input_tokens", 0)
    written = usage.get("cache_creation_input_tokens", 0)
    read = usage.get("cache_read_input_tokens", 0)
    if base in LONG_PROMPT and fresh + written + read > LONG_PROMPT[base][0]:
        rates = LONG_PROMPT[base][1]
    split_ = usage.get("cache_creation") or {}
    hour = split_.get("ephemeral_1h_input_tokens", 0)
    five = written - hour if split_ else written
    dollars = (
        fresh * rates[0]
        + usage.get("output_tokens", 0) * rates[1]
        + five * rates[2]
        + hour * rates[3]
        + read * rates[4]
    )
    total = dollars / 1e6
    # An advisor's consult is billed inside the executor's response, at its own model.
    for step in usage.get("iterations") or ():
        if step.get("type") == "advisor_message":
            consult = price(step, step.get("model"))
            if consult is None:
                return None
            total += consult
    return total


def _models(path):
    """`message.model` per response, in `responses()`'s own order."""
    order, model = [], {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            record = _record(line)
            if record is None:
                continue
            message = record.get("message")
            if record.get("type") != "assistant" or not isinstance(message, dict):
                continue
            key = message.get("id")
            if key not in model:
                order.append(key)
                model[key] = message.get("model")
    return [model[key] for key in order]


def cost_of(path):
    """A transcript's dollars, summed per response at that response's model, or `None`
    when any response names an unpriced model - a partial sum reads as the whole."""
    total = 0.0
    for (_tools, usage), model in zip(responses(path), _models(path)):
        dollars = price(usage, model)
        if dollars is None:
            return None
        total += dollars
    return total


def _agent_and_model(path):
    """`attributionAgent` and `message.model`, from the records - never
    from frontmatter, which can name a model the run did not use."""
    agent = model = None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            record = _record(line)
            if record is None:
                continue
            if agent is None and record.get("attributionAgent"):
                agent = record["attributionAgent"]
            message = record.get("message")
            if model is None and isinstance(message, dict) and message.get("model"):
                model = message["model"]
            if agent and model:
                break
    return agent, model


def _model_short(raw):
    """The bare model family: `claude-sonnet-5` -> `sonnet`."""
    words = [word for word in _MODEL_WORD.findall(raw or "") if word != "claude"]
    return words[0] if words else (raw or "?")


def _model_cell(raw):
    """`UX-1351`: family and version, `claude-sonnet-5-5` -> `sonnet-5-5`; the
    family alone pooled Sonnet 5 with 5.5."""
    base = _base_model(raw)
    return base.removeprefix("claude-") if base.startswith("claude-") else _model_short(raw)


def ledger_row(path, round_, task, outcome, friction):
    """One `agent-runs.md` row, derived from the transcript."""
    rows = responses(path)
    agent, model = _agent_and_model(path)
    tokens = sum(_fresh(usage) for _, usage in rows)
    calls = sum(len(tools) for tools, _ in rows)
    stamps = _stamps(path)
    wall = 0.0
    if stamps:
        wall = (_parse_ts(max(stamps)) - _parse_ts(min(stamps))).total_seconds() / 60
    wall_text = f"{wall:.1f}".removesuffix(".0")
    dollars = cost_of(path)
    cost = "—" if dollars is None else f"${dollars:.2f}"
    return (
        f"| {round_} | {agent} | {_model_cell(model)} | {task} | "
        f"{round(tokens / 1000)}k | {calls} | {wall_text} m | {cost} | "
        f"{outcome} | {friction} |"
    )


#: `UX-666`: the ledger the rows go into. A round appends here; the
#: summary sentence below the table is derived from the row count, never
#: typed - `test_a_counted_figure_is_derived.py` reads it back.
LEDGER = pathlib.Path(__file__).resolve().parents[1] / "docs/audits/agent-runs.md"

_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_UNITS = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
)


def count_word(n):
    """`37` -> `thirty-seven`, `101` -> `one hundred and one`. Built, not
    tabled: the guard that reads the sentence back carries a table, and
    two tables drift. The hundredth row (`UX-794`) is where a table ended."""
    if n >= 1000:
        raise ValueError(f"count_word stops at 999, not {n}")
    if n >= 100:
        hundreds, rest = divmod(n, 100)
        head = f"{_UNITS[hundreds]} hundred"
        return f"{head} and {count_word(rest)}" if rest else head
    if n < 20:
        return _UNITS[n]
    tens, unit = divmod(n, 10)
    return _TENS[tens] + (f"-{_UNITS[unit]}" if unit else "")


def append_row(row, ledger=LEDGER):
    """`UX-666`: the row after the table's last, count sentence re-derived."""
    lines = ledger.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("|---"))
    body = [i for i, line in enumerate(lines[start + 1 :], start + 1) if line.startswith("| ")]
    lines.insert(body[-1] + 1, row)
    said = count_word(len(body) + 1)
    text = re.sub(r"What the [a-z -]+ rows already say", f"What the {said} rows already say", "\n".join(lines) + "\n")
    ledger.write_text(text, encoding="utf-8")
    return said


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("transcripts", nargs="*")
    parser.add_argument(
        "--root", default=os.path.expanduser("~/.claude/projects"), help="Where the harness writes agent transcripts."
    )
    parser.add_argument("--list", action="store_true", help="Name the implementer transcripts under --root.")
    parser.add_argument("--session", help="Count and price one session's rebuilds.")
    parser.add_argument("--floor", type=int, default=30000, help="Fresh-token floor for a rebuild.")
    parser.add_argument("--rounds", help="name=ISO-timestamp,... round boundaries.")
    parser.add_argument("--ledger", help="Print one agent-runs.md row for a transcript.")
    parser.add_argument("--round", dest="round_", help="The round cell for --ledger.")
    parser.add_argument("--task", default="", help="The task cell for --ledger.")
    parser.add_argument("--outcome", default="", help="The outcome cell for --ledger.")
    parser.add_argument("--friction", default="", help="The friction cell for --ledger.")
    parser.add_argument(
        "--append",
        action="store_true",
        help="With --ledger: write the row into "
        "docs/audits/agent-runs.md and re-derive its "
        "count sentence, instead of printing it.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    if args.list:
        for path, item in implementer_transcripts(args.root):
            print(f"{item:<8} {path}")
        return 0
    if args.session:
        print(report_rebuilds(args.session, args.floor, args.rounds))
        return 0
    if args.ledger:
        row = ledger_row(args.ledger, args.round_, args.task, args.outcome, args.friction)
        if args.append:
            said = append_row(row)
            print(f"appended to {LEDGER}; the summary now says {said}")
        else:
            print(row)
        return 0
    if not args.transcripts:
        parser.error("give a transcript path, or --list")
    for path in args.transcripts:
        print(report(path, args.verbose))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
