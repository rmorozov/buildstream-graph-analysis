#!/usr/bin/env bash
# Populates every examples/**/files/runtime/bin/ (any depth, not just one
# level - 04-critical-path-optimization/optimized/ is a full, separate
# BuildStream project nested inside its own example directory, needing
# its own runtime just like every top-level example) with a real shell
# (and common utilities) for that project's manual.bst elements to run
# commands with. BuildStream's sandbox is assembled purely from staged
# dependencies - nothing from the host is bound in - so something has to
# actually provide /bin/sh; this stages a static busybox (installed via
# the `busybox-static` package) rather than committing a binary to the
# repo. Not needed for `bst show`/graph-only work, only for a real `bst
# build`. See examples/README.md.
set -euo pipefail

BB="$(command -v busybox)"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while IFS= read -r -d '' bin_dir; do
    for applet in sh sleep true env cat; do
        cp "$BB" "${bin_dir}/${applet}"
    done
done < <(find "$HERE" -type d -path '*/files/runtime/bin' -print0)
