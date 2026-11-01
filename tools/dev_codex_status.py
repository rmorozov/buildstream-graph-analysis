"""UX-1369: what Codex reviewed on a pull request, read from GitHub.

    python3 tools/dev_codex_status.py 338

A Codex code review counts as done on a sha when the Codex bot submitted
a review on it, or reacted +1 (no findings) after the request. The
summary comment's `codex-review-state:v1` marker is printed, never
trusted: on PR 338 it still read `running` after the review was submitted.
A finding is open until a reply answers it. The reviewed sha may trail
the head when nothing after it touches code (catch-ups, adopts, docs).
The security review is wanted only when the diff crosses a boundary in
`docs/design/threat-model.md`; its only reading is the marker, and not
started is reported, not failed.

Exit 1 names each problem; 0 means the PR may go to its owner. Reads
`GITHUB_TOKEN` (or `GH_TOKEN`) and `git diff` in this checkout.

holds: rules.md#some-claims-have-no-local-instrument-open-the-pr-first-7-marked-ready-the-round-pr-gets-one-codex-review-and-each-finding-is-answered-like-a-hold-procedure-codex-reviews-md
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

API = "https://api.github.com/repos/rmorozov/buildstream-graph-analysis"
BOT = "chatgpt-codex-connector[bot]"
MARKER = re.compile(r"codex-review-state:v1 (\{.*?\}) -->")
CODE_SUFFIXES = (".py", ".js", ".mjs", ".c", ".h", ".cc", ".sh", ".yml", ".yaml", ".toml", ".css", ".html", ".lock")
BOUNDARIES = (
    "tools/bga_view.py",
    "bga/viewer/",
    "bga/anonymize.py",
    "tools/native_trace/",
    "tools/jobserver/",
    ".github/workflows/",
)


def is_code(path):
    return not path.startswith("docs/") and path.endswith(CODE_SUFFIXES)


def crosses_boundary(paths):
    return sorted(p for p in paths if p.startswith(BOUNDARIES))


def reviewed_shas(reviews, reactions):
    """Shas Codex finished a code review on; `"+1"` when it said so only by reaction."""
    shas = [r["commit_id"] for r in reviews if r["user"]["login"] == BOT]
    if any(r["user"]["login"] == BOT and r["content"] == "+1" for r in reactions):
        shas.append("+1")
    return shas


def open_findings(comments):
    """Codex's inline findings with no reply in their thread."""
    answered = {c["in_reply_to_id"] for c in comments if c.get("in_reply_to_id")}
    return [
        c for c in comments if c["user"]["login"] == BOT and not c.get("in_reply_to_id") and c["id"] not in answered
    ]


def marker(issue_comments):
    for comment in reversed(issue_comments):
        found = MARKER.search(comment["body"]) if comment["user"]["login"] == BOT else None
        if found:
            return json.loads(found.group(1))
    return None


def verdict(head, shas, findings, changed_since):
    """Problems, then notes. `changed_since(sha)` lists paths from sha to head."""
    problems, notes = [], []
    if not shas:
        problems.append("no Codex code review on this PR - mark it ready, or comment `@codex review`")
    elif head not in shas and "+1" not in shas:
        last = shas[-1]
        moved = [p for p in changed_since(last) if is_code(p)]
        if moved:
            problems.append(f"code changed after the reviewed {last[:10]}: {', '.join(moved[:5])}")
        else:
            notes.append(f"reviewed {last[:10]}; nothing after it is code")
    for finding in findings:
        problems.append(f"open finding: {finding['path']}:{finding.get('line')} {finding['html_url']}")
    return problems, notes


def security_note(pr_paths, security_done):
    crossing = crosses_boundary(pr_paths)
    if crossing and not security_done:
        return f"security review wanted ({', '.join(crossing[:3])}) and not started - recorded as blocked"
    return None


def _get(path):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    request = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json"})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _paths(a, b):
    out = subprocess.run(["git", "diff", "--name-only", a, b], capture_output=True, text=True, check=True)
    return out.stdout.split()


def main(argv=None):
    parser = argparse.ArgumentParser(description="What Codex reviewed on a pull request.")
    parser.add_argument("pr", type=int)
    args = parser.parse_args(argv)
    pr = _get(f"/pulls/{args.pr}")
    head, base = pr["head"]["sha"], pr["base"]["sha"]
    reviews = _get(f"/pulls/{args.pr}/reviews?per_page=100")
    reactions = _get(f"/issues/{args.pr}/reactions?per_page=100")
    comments = _get(f"/pulls/{args.pr}/comments?per_page=100")
    issue_comments = _get(f"/issues/{args.pr}/comments?per_page=100")
    state = marker(issue_comments) or {}
    security_done = (state.get("security_review") or {}).get("status") == "completed"
    problems, notes = verdict(
        head, reviewed_shas(reviews, reactions), open_findings(comments), lambda sha: _paths(sha, head)
    )
    security = security_note(_paths(base, head), security_done)
    notes += [security] if security else []
    print(f"#{args.pr} head {head[:10]}; marker says {json.dumps(state, sort_keys=True)}")
    for line in notes:
        print("  note:", line)
    for line in problems:
        print("  FAIL:", line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
