#!/usr/bin/env python3
"""UX-703: `mutmut` over the modules a diff touched, weekly.

`falsify` mutates one guard by hand. This asks the reverse question of
the whole tree in one CI run: which touched module changes with no
guard going red. Not a score - a survivor is a filing, and the run
never blocks (`quality.yml`'s weekly schedule).

Per touched module (`bga/`, `tools/`, `.py`, not a test): the tests
`dev_touching.naming(*dev_touching.select([module]))` names, `mutmut`
run against just that module with those tests, survivors appended as a
ledger row.

`mutmut` needs a full working copy under `mutants/` to import anything
real - a guard reads paths relative to its own file's parents, so a
copy missing a directory a guard reads fails for a reason that is not
the mutation. `source_paths` below is therefore the whole tree, with
`only_mutate` narrowing what actually gets mutated to the one module.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import dev_touching as dt

LEDGER = REPO / "docs" / "audits" / "mutation.md"
PYPROJECT = REPO / "pyproject.toml"
MUTANTS_DIR = REPO / "mutants"
CACHE = REPO / ".mutmut-cache"

# Everything a copied test run might read via a REPO-relative path -
# `parents[N]` computed from a file now one directory deeper. Cheap:
# the whole tree is 26 MB (`du -sh --exclude=.git .`, this container).
SOURCE_PATHS = (".claude", ".github", "bga", "docs", "examples", "tests", "tools")
ALSO_COPY = (".pymarkdown.json", "CLAUDE.md", "README.md", "REVIEW.md",
             "CHANGELOG.md")

_RESULT_RE = re.compile(r"^\s*(\S+): (\S.*\S|\S)\s*$")
_TRAMPOLINE_RE = re.compile(r"^def (x_\w+__mutmut_\d+)\(", re.MULTILINE)
#: A mutant `mutmut` calls "killed" is the only status a guard is known
#: to have caught. `timeout` is deliberately *not* included: a browser
#: guard's timeout margin is wide and machine-dependent (`UX-551`), so
#: a slow run's timeout is noise, not a catch - filing it costs
#: nothing, since a survivor is a filing, never a failure.
_CAUGHT = {"killed"}


def touched_modules(since):
    """`.py` files under `bga/` or `tools/` the diff touched, not a test."""
    changed = dt.changed_files(base=since)
    return sorted(
        p for p in changed
        if p.endswith(".py")
        and p.split("/")[0] in ("bga", "tools")
        and not pathlib.Path(p).name.startswith("test_")
        and (REPO / p).exists())


def _verdict_lines(results_text):
    """Yield `(mutant_id, verdict)` for every line `mutmut results` prints."""
    for line in results_text.splitlines():
        match = _RESULT_RE.match(line)
        if match:
            yield match.group(1), match.group(2)


def classify(results_text):
    """`mutmut results --all true`'s text -> counts by verdict.

    `_CAUGHT` decides which verdicts count as caught; `"caught"` and
    `"survivors"` are the two totals derived from it, alongside each
    raw verdict's own count (`killed`, `survived`, `timeout`, `no
    tests`, ...).
    """
    counts = {}
    for _, verdict in _verdict_lines(results_text):
        counts[verdict] = counts.get(verdict, 0) + 1
    total = sum(counts.values())
    counts["caught"] = sum(n for verdict, n in counts.items()
                            if verdict in _CAUGHT)
    counts["survivors"] = total - counts["caught"]
    return counts


def guards_for(module):
    """The tests naming `module` - the census floor excluded (`UX-645`).

    The census runs the same 11 files under every module; a mutant of
    one module tells nothing about whether those files would catch it
    versus any other module, so they are not "the guard that should
    have caught it" for this one.
    """
    selected, why = dt.select([module])
    return dt.naming(selected, why)


def _mutmut_config(module, guards):
    return (
        "\n\n[tool.mutmut]\n"
        f"source_paths = {json.dumps(list(SOURCE_PATHS))}\n"
        f"only_mutate = {json.dumps([module])}\n"
        f"pytest_add_cli_args_test_selection = {json.dumps(guards)}\n"
        "use_git_change_detection = false\n"
        f"also_copy = {json.dumps(list(ALSO_COPY))}\n")


def _clean():
    shutil.rmtree(MUTANTS_DIR, ignore_errors=True)
    CACHE.unlink(missing_ok=True)


def _run(argv, **kw):
    return subprocess.run(argv, cwd=REPO, text=True, capture_output=True, **kw)


def run_module(module, max_children):
    """One module's mutation run. `{module, guards, survivors, counts}`.

    `survivors`: `(mutant, status)` for every mutant no guard is known
    to have killed. The full mutant set comes from the *generated*
    file under `mutants/`, not from `mutmut results` alone - when no
    selected guard covers the module at all, `mutmut` prints "Stopping
    early, because we could not find any test case for any mutant" and
    never gives any of them a verdict. A mutant with no verdict is a
    mutant no guard is known to have caught, which is this task's
    question, so it counts as a survivor rather than vanishing from the
    ledger. `counts`: `classify`'s verdict totals for the same run.
    """
    guards = guards_for(module)
    if not guards:
        return {"module": module, "guards": [], "survivors": []}

    dotted = module[:-3].replace("/", ".")
    original = PYPROJECT.read_text(encoding="utf-8")
    PYPROJECT.write_text(original + _mutmut_config(module, guards),
                          encoding="utf-8")
    _clean()
    try:
        _run([sys.executable, "-m", "mutmut", "run",
              "--max-children", str(max_children)])
        generated = (MUTANTS_DIR / module).read_text(encoding="utf-8")
        all_ids = {f"{dotted}.{name}"
                   for name in _TRAMPOLINE_RE.findall(generated)}
        results = _run([sys.executable, "-m", "mutmut", "results", "--all",
                        "true"])
    finally:
        PYPROJECT.write_text(original, encoding="utf-8")
        _clean()

    counts = classify(results.stdout)
    status = {mid: verdict for mid, verdict in _verdict_lines(results.stdout)
              if mid in all_ids}
    survivors = [(mutant, status.get(mutant, "no verdict"))
                 for mutant in sorted(all_ids)
                 if status.get(mutant) not in _CAUGHT]
    return {"module": module, "guards": guards, "survivors": survivors,
            "counts": counts}


_FUNC_RE = re.compile(r"^(.*)__mutmut_\d+$")


def _function(mutant):
    """A mutant's function, `__mutmut_N` stripped - the grouping key.

    One row per mutant would repeat the same finding once per mutation
    site inside an untested function (37, for one `main()` here); the
    fact worth filing is "this function", not which of its N sites.
    """
    match = _FUNC_RE.match(mutant)
    return match.group(1) if match else mutant


def render_row(run):
    if not run["guards"]:
        return (f"| `{run['module']}` | - | no test names this module "
                f"(`test-touching` finding) |\n")
    if not run["survivors"]:
        return ""
    guard_list = ", ".join(f"`{g}`" for g in run["guards"])
    grouped = {}
    for mutant, status in run["survivors"]:
        key = (_function(mutant), status)
        grouped.setdefault(key, []).append(mutant)
    rows = ""
    for (func, status), mutants in sorted(grouped.items()):
        example = mutants[0]
        count = f" x{len(mutants)}" if len(mutants) > 1 else ""
        rows += (f"| `{run['module']}` | `{func}` ({status}{count}, "
                 f"e.g. `{example}`) | {guard_list} |\n")
    return rows


def write_ledger(date, runs, dry_run=False):
    total_survivors = sum(len(r["survivors"]) for r in runs)
    body = f"\n## {date}\n\n"
    body += "| module | mutant | the guard that should have caught it |\n"
    body += "|---|---|---|\n"
    rows = "".join(render_row(r) for r in runs)
    if not rows:
        rows = "| - | - | every touched module's mutants were killed |\n"
    body += rows
    body += (f"\n{total_survivors} survivor(s) over {len(runs)} touched "
             f"module(s).\n")
    if dry_run:
        print(body)
        return
    if not LEDGER.exists():
        LEDGER.write_text(
            "# UX-703: the weekly mutation ledger\n\n"
            "One section per run. A survivor is a filing, not a "
            "failure - see the task file for the loop that produces "
            "this.\n", encoding="utf-8")
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(body)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", default=None,
                         help="diff base (default: 7 days ago on HEAD)")
    parser.add_argument("--module", action="append", default=None,
                         help="mutate this module instead of computing the "
                              "touched set (repeatable)")
    parser.add_argument("--max-children", type=int,
                         default=os.cpu_count() or 2)
    parser.add_argument("--dry-run", action="store_true",
                         help="print the touched modules and their guards, "
                              "run nothing")
    parser.add_argument("--write", action="store_true",
                         help="append the ledger section to "
                              "docs/audits/mutation.md")
    parser.add_argument("--date", default=None,
                         help="the ledger section's heading (default: today, "
                              "UTC)")
    args = parser.parse_args(argv)

    if args.module:
        modules = args.module
    else:
        since = args.since
        if since is None:
            found = _run(["git", "rev-list", "-1", "--before=7 days ago",
                          "HEAD"])
            since = found.stdout.strip() or None
        modules = touched_modules(since) if since else []

    if not modules:
        print("no touched module in range; nothing to mutate", file=sys.stderr)
        return 0

    if args.dry_run and not args.write:
        for module in modules:
            guards = guards_for(module)
            print(f"{module}\n    <- {guards or '(no guard names it)'}")
        return 0

    runs = [run_module(module, args.max_children) for module in modules]
    date = args.date or __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).date().isoformat()
    write_ledger(date, runs, dry_run=not args.write)
    return 0


if __name__ == "__main__":
    sys.exit(main())
