"""Run the canned question library against a real trace.

    python tools/dev_perfetto_queries.py /tmp/two.pftrace

`test_the_questions_ask_what_the_trace_answers.py` checks the library's
vocabulary against the emitter's statically, everywhere. It cannot say
whether a question **returns anything**: `graph-levels` answered
nothing for every capture here, in silence, because `extract_arg`
returns null rather than failing (`UX-312`, one level out).

Answering that needs Perfetto's own reader and a two-plane capture.
Round 69 found the reader had never been present on any machine this
project had run on, so the fourteen shipped questions the library then
held had never executed - `UX-432`'s Outcome has the run. `--fetch`
downloads the pinned reader when `PATH` and `BGA_TRACE_PROCESSOR` have
none, into `--fetch-into`, and prints where: that friction is what kept
the gate skipping.
"""
import argparse
import csv
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tests import trace_processor              # noqa: E402  (UX-321's one gate)

QUESTIONS_JS = REPO / "bga/viewer/questions.js"

#: Pinned, because an unpinned reader makes two runs incomparable - the
#: same reason `gen-synthetic` takes a seed. Perfetto publishes its
#: prebuilts here; `get.perfetto.dev` is a redirector to the same bucket
#: and is blocked by some proxies, so the bucket is named directly.
READER_VERSION = "v57.2"
READER_URL = ("https://commondatastorage.googleapis.com/perfetto-luci-artifacts/"
              f"{READER_VERSION}/linux-amd64/trace_processor_shell")

#: Lines the shell writes around the result set.
NOISE = re.compile(r"^(Loading trace|\[\d|column \d+ =)")


def questions():
    """The library, as data, read by running the module it lives in.

    The same trick `test_the_questions_ask_what_the_trace_answers` uses:
    the library is JavaScript, so JavaScript reads it. A regex over the
    source would be a second parser to keep true.
    """
    node = shutil.which("node")
    if node is None:
        raise SystemExit("node is not installed, and it is what reads "
                         "bga/viewer/questions.js")
    script = ('const { QUESTIONS } = await import("./bga/viewer/questions.js");'
              'console.log(JSON.stringify(QUESTIONS));')
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=REPO, timeout=60)
    if done.returncode != 0:
        raise SystemExit(f"could not read the question library: {done.stderr}")
    return json.loads(done.stdout)


def fetch(into):
    """Download the pinned reader, returning its path."""
    into = pathlib.Path(into)
    into.mkdir(parents=True, exist_ok=True)
    binary = into / f"trace_processor_shell-{READER_VERSION}"
    if binary.exists() and os.access(binary, os.X_OK):
        return binary
    print(f"fetching {READER_URL}", file=sys.stderr)
    with urllib.request.urlopen(READER_URL, timeout=600) as response:
        binary.write_bytes(response.read())
    binary.chmod(0o755)
    return binary


def reader(fetch_if_missing, into):
    """The reader to use, or `None` with the reason already printed."""
    found = trace_processor.shell()
    if found:
        return pathlib.Path(found)
    if fetch_if_missing:
        return fetch(into)
    print(f"{trace_processor.REASON}. Re-run with --fetch to download "
          f"the pinned {READER_VERSION} reader, or set BGA_TRACE_PROCESSOR.",
          file=sys.stderr)
    return None


def ask(shell, trace, sql, workdir):
    """`(rows, error)` - the shell takes a file, never stdin."""
    path = workdir / "_ask.sql"
    path.write_text(sql, encoding="utf-8")
    done = subprocess.run([str(shell), "-q", str(path), str(trace)],
                          capture_output=True, text=True, timeout=900)
    if done.returncode != 0:
        lines = [ln for ln in (done.stderr or "").splitlines() if ln.strip()]
        return None, (lines[-1] if lines else f"exit {done.returncode}")
    body = [ln for ln in (done.stdout or "").splitlines()
            if ln.strip() and not NOISE.search(ln)]
    if not body:
        return [], None
    reader_ = csv.reader(io.StringIO("\n".join(body)))
    header = next(reader_)
    return [dict(zip(header, row)) for row in reader_ if row], None


def an_element(shell, trace, workdir):
    """An element this trace really has, for the questions that take one.

    `UX-369`'s rule, applied to the harness: a query filled with some
    other capture's element proves nothing about this one.

    **One that waited, and among those the longest-running.** Two of the
    four questions taking an element ask what it waited for, so an
    element with no incoming edge answers them empty however
    interesting it is otherwise. Both wrong picks were made here before
    this rule was: `min(element)` chose `all.bst`, the target; longest
    duration alone chose `toolchain.bst`, the root, which is the source
    of every flow in the capture and the sink of none. **An empty result
    must mean the trace cannot answer, never that the harness asked
    about the one element with no answer.**

    `--element` overrides, and the chosen element is printed, because a
    heuristic that picks silently is one nobody can check.
    """
    rows, error = ask(shell, trace, """
select extract_arg(s.arg_set_id, 'debug.element') as element,
       max(case when f.slice_in is not null then 1 else 0 end) as waits,
       sum(s.dur) as total
from slice s left join flow f on f.slice_in = s.id
where s.category glob '*bst-builder*'
  and extract_arg(s.arg_set_id, 'debug.element') is not null
group by element
order by waits desc, total desc limit 1;""", workdir)
    if error or not rows:
        return None
    return rows[0].get("element")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("trace", help="a .pftrace written by `bga timeline`")
    parser.add_argument("--element", help="fill {element} with this rather "
                                          "than one read from the trace")
    parser.add_argument("--fetch", action="store_true",
                        help="download the pinned reader if none is found")
    parser.add_argument("--fetch-into",
                        default=str(pathlib.Path.home() / ".cache/bga"),
                        help="where --fetch puts the reader")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    trace = pathlib.Path(args.trace)
    if not trace.is_file():
        raise SystemExit(f"no such trace: {trace}")
    shell = reader(args.fetch, args.fetch_into)
    if shell is None:
        return 2

    workdir = pathlib.Path(args.fetch_into)
    workdir.mkdir(parents=True, exist_ok=True)
    element = args.element or an_element(shell, trace, workdir)
    library = questions()

    results, empty, broken = [], [], []
    for question in library:
        sql = question["sql"].replace("{element}", element or "")
        rows, error = ask(shell, trace, sql, workdir)
        results.append({"id": question["id"], "plane": question.get("plane"),
                        "rows": None if error else len(rows), "error": error,
                        "first": (rows or [None])[0] if not error else None})
        if error:
            broken.append(question["id"])
        elif not rows:
            empty.append(question["id"])

    if args.format == "json":
        print(json.dumps({"trace": str(trace), "bytes": trace.stat().st_size,
                          "reader": str(shell), "element": element,
                          "questions": len(library), "empty": empty,
                          "errors": broken, "results": results}, indent=2))
    else:
        print(f"trace   {trace} ({trace.stat().st_size:,} B)")
        print(f"reader  {shell}")
        print(f"element {element}")
        print()
        for row in results:
            if row["error"]:
                print(f"  {row['id']:20s} {str(row['plane']):12s} "
                      f"ERROR  {row['error'][:60]}")
                continue
            mark = "  <-- EMPTY" if not row["rows"] else ""
            print(f"  {row['id']:20s} {str(row['plane']):12s} "
                  f"{row['rows']:5d} row(s){mark}")
        print()
        print(f"empty:  {len(empty)}/{len(library)}  {empty}")
        print(f"errors: {len(broken)}/{len(library)}  {broken}")

    # An empty answer is a finding, not a crash: `graph-levels` is
    # legitimately empty on a capture with no `analyze.json`, and the
    # point of this tool is to say so rather than to decide.
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
