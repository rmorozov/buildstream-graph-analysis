#!/bin/bash
# UX-1371: make a project-thread session load this repository's workflow.
# The session starts above the checkouts, so `.claude/agents`, `skills`
# and `settings.json` hooks do not load. This links the agents and
# skills into the user's ~/.claude, points the user's hooks at
# `.claude/hooks/dispatch_by_repo.py`, and (without --links-only)
# unshallows the clone and installs the lock and the editable package.
#
#   bash /home/*/buildstream-graph-analysis/tools/dev_cloud_setup.sh
#   bash tools/dev_cloud_setup.sh [--links-only] [REPO...]
#
# The cloud environment's setup script runs it; with no REPO it takes
# this checkout and a sibling bga-bench. Every REPO's hooks fire for a
# call made inside it; the first REPO owns the agents and skills.
set -euo pipefail

links_only=0
if [[ "${1:-}" == "--links-only" ]]; then links_only=1; shift; fi
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repos=()
# Absolute, or the links and the hooks' allowlist resolve against another cwd.
for repo in "$@"; do repos+=("$(cd "$repo" && pwd)"); done
if [[ ${#repos[@]} -eq 0 ]]; then
    repos=("$here")
    # The project's second checkout clones beside this one, wherever home is.
    [[ -d "$here/../bga-bench/.git" ]] && repos+=("$(cd "$here/../bga-bench" && pwd)")
fi
owner="${repos[0]}"
user_dir="${HOME}/.claude"
mkdir -p "$user_dir/agents" "$user_dir/skills"

for agent in "$owner"/.claude/agents/*.md; do
    ln -sfn "$agent" "$user_dir/agents/$(basename "$agent")"
done
for skill in "$owner"/.claude/skills/*/; do
    ln -sfn "${skill%/}" "$user_dir/skills/$(basename "$skill")"
done

python3 - "$user_dir/settings.json" "$here/.claude/hooks/dispatch_by_repo.py" "${repos[@]}" <<'EOF'
import json, pathlib, shlex, sys
path, dispatcher, repos = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
settings = json.loads(path.read_text()) if path.is_file() else {}
hooks = settings.setdefault("hooks", {})
def entry(event, extra=()):
    command = " ".join(shlex.quote(a) for a in ["python3", dispatcher, event, *extra])
    return {"hooks": [{"type": "command", "command": command}]}
wanted = {
    "PreToolUse": entry("PreToolUse", repos),
    "PostToolUse": entry("PostToolUse", repos),
    "SessionStart": dict(entry("SessionStart", repos[:1]), matcher="startup"),
}
for event, group in wanted.items():
    kept = [g for g in hooks.get(event, []) if dispatcher not in json.dumps(g)]
    hooks[event] = [*kept, group]
path.write_text(json.dumps(settings, indent=2) + "\n")
EOF

[[ $links_only -eq 1 ]] && exit 0
for repo in "${repos[@]}"; do
    if [[ "$(git -C "$repo" rev-parse --is-shallow-repository)" == "true" ]]; then
        # Setup runs before git credentials exist; a shallow clone must not stop the installs.
        git -C "$repo" fetch --unshallow --quiet origin || echo "unshallow skipped: $repo" >&2
    fi
done
# Debian's argcomplete and PyYAML refuse an uninstall, so the lock goes in over them.
python3 -m pip install --quiet --ignore-installed -r "$owner/requirements.lock"
python3 -m pip install --quiet --no-deps -e "$owner"
python3 "$owner/tools/dev_env_check.py"
