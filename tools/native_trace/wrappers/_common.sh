# UX-846: sourced by every wrapper in this directory - "a tool that
# will not read the pipe holds tokens instead". `bga_run_wrapped
# <threads|dashj> "$@"` is the one entry point: find the real tool past
# this directory on PATH, read MAKEFLAGS for a jobserver auth, acquire
# up to $BST_TRACE_WRAPPER_CAP tokens non-blockingly (bounded 50ms),
# run the tool with that width plus its own implicit token, and return
# exactly the tokens read - via a trap, so a killed *child* still
# leaves the wrapper (the parent, running the tool as a foreground job
# rather than exec'ing into it) to give them back. A wrapper killed
# itself leaks until UX-852's audit.

bga_self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
bga_tool=$(basename -- "$0")
bga_held=0
bga_wfd=

# UX-846 (post-merge incident): `$0`'s directory is the *invoked* path's
# directory, not necessarily the wrapper directory on `PATH` - a symlink,
# a relative path, or a copy elsewhere all break that assumption. Without
# this, `bga_find_real` picked the wrapper itself back up as "real",
# `"$real" --help` re-entered it, and the loop had no bound: 32,000
# processes, a container restart. `bga_resolve` follows symlinks with
# `readlink -f` where it exists; a candidate is also skipped if its own
# first 3 lines carry this item's own marker (a copy, not a symlink).
bga_resolve() {
    readlink -f -- "$1" 2>/dev/null || printf '%s\n' "$1"
}

bga_find_real() {
    self_resolved=$(bga_resolve "$0")
    old_ifs=$IFS
    IFS=:
    set -- $PATH
    IFS=$old_ifs
    for dir in "$@"; do
        [ -n "$dir" ] || continue
        [ "$dir" = "$bga_self_dir" ] && continue
        candidate="$dir/$bga_tool"
        [ -x "$candidate" ] || continue
        [ "$(bga_resolve "$candidate")" = "$self_resolved" ] && continue
        head -3 -- "$candidate" 2>/dev/null | grep -q "UX-846" && continue
        printf '%s\n' "$candidate"
        return 0
    done
    return 1
}

bga_ledger() {
    [ -n "${BST_TRACE_JOBSERVER_LEDGER:-}" ] || return 0
    printf '{"event":"%s","tool":"%s","pid":%s,"tokens":%s,"t":%s}\n' \
        "$1" "$bga_tool" "$$" "$bga_held" "$(date +%s.%N)" \
        >>"$BST_TRACE_JOBSERVER_LEDGER" 2>/dev/null || :
}

bga_release() {
    i=0
    while [ "$i" -lt "$bga_held" ]; do
        printf '+' >&"${bga_wfd:-9}" 2>/dev/null || :
        i=$((i + 1))
    done
    bga_ledger release
}

# `flag_style` is `threads` (--threads=N) or `dashj` (-j N).
bga_run_wrapped() {
    flag_style=$1
    shift

    # UX-846 (post-merge incident): the last line, independent of
    # whatever `bga_find_real` above concludes - if this process is
    # already inside a wrapper invocation for the *same* tool name, it
    # is a repeat by construction and must never recurse again,
    # regardless of the cause. Exported before `bga_find_real` or
    # `--help` ever run, so every process in the chain carries it.
    if [ "${BGA_WRAPPER_TOOL:-}" = "$bga_tool" ]; then
        echo "bga: $bga_tool: wrapper re-entered itself" >&2
        exit 127
    fi
    export BGA_WRAPPER_TOOL="$bga_tool"

    real=$(bga_find_real) || {
        echo "bga: $bga_tool: no real tool found on PATH past $bga_self_dir" >&2
        exit 127
    }

    auth=
    for flag in ${MAKEFLAGS:-}; do
        case "$flag" in
            --jobserver-auth=*) auth=${flag#--jobserver-auth=} ;;
        esac
    done

    if [ -z "$auth" ]; then
        exec "$real" "$@"
    fi

    # UX-846: the same fact the capture's pass-through policy probed
    # before the build, checked again here - belt and braces against a
    # tool that ended up on this PATH despite speaking the protocol.
    if "$real" --help 2>&1 | grep -qi jobserver; then
        exec "$real" "$@"
    fi

    # A redirection failure here is fatal to a POSIX `exec` (no command)
    # rather than something `||` can catch - accepted, since a jobserver
    # auth string this wrapper cannot open is already a broken build.
    #
    # `/dev/fd/$r`, not `exec 9<&"$r"`: dash's IO-number lexer only
    # recognises a *single*-digit fd immediately before `<&`/`>&` -
    # `exec 9<&"$r"` with a real two-digit inherited fd (11, common
    # once bwrap and the trace hook have their own open) fails outright
    # with "Bad fd number", silently discarding the whole pool. A path
    # under `/dev/fd/` is an ordinary filename argument to the parser,
    # so the digit-count limit never applies (measured: `exec
    # 15<>/dev/null` fails the same way `dash` here; `exec
    # 9<>/dev/fd/15` does not).
    case "$auth" in
        fifo:*)
            fifo_path=${auth#fifo:}
            exec 9<>"$fifo_path"
            bga_wfd=9
            ;;
        *)
            r=${auth%%,*}
            w=${auth#*,}
            exec 9<>/dev/fd/"$r"
            if [ "$w" != "$r" ]; then
                exec 8>/dev/fd/"$w"
                bga_wfd=8
            else
                bga_wfd=9
            fi
            ;;
    esac

    cap=${BST_TRACE_WRAPPER_CAP:-$(nproc 2>/dev/null || echo 1)}
    # One `dd`, not one fork per token: `count=$cap` non-blocking
    # single-byte reads in dd's own loop, bounded by `timeout` rather
    # than a shell loop polling `date` - measured, the per-fork shell
    # loop this replaced needed 2-3 extra forks per token and missed
    # its own 50ms budget under a loaded machine. `dd` still exits
    # non-zero on a short read (EAGAIN before `count` is reached) -
    # expected, not an error, so `|| :` under `set -e`.
    #
    # `BGA_WRAPPER_ACQUIRE_MS` (default 50): the budget is production's
    # own choice, not a test's - a guard asserting an exact token count
    # must not also be a scheduling bet under `make test`'s own xdist
    # contention. `timeout` takes seconds; `ms / 1000` and `ms % 1000`,
    # zero-padded to 3 digits, is exact for any integer millisecond
    # count (no float parsing, no locale-dependent decimal point).
    acquire_ms=${BGA_WRAPPER_ACQUIRE_MS:-50}
    acquire_budget=$(printf '%d.%03d' "$((acquire_ms / 1000))" "$((acquire_ms % 1000))")
    if command -v timeout >/dev/null 2>&1; then
        out=$(timeout "$acquire_budget" dd bs=1 count="$cap" iflag=nonblock 2>/dev/null <&9) || :
    else
        out=$(dd bs=1 count="$cap" iflag=nonblock 2>/dev/null <&9) || :
    fi
    bga_held=${#out}
    bga_ledger acquire
    trap bga_release EXIT INT TERM HUP

    width=$((bga_held + 1))
    case "$flag_style" in
        dashj) "$real" -j "$width" "$@" ;;
        *) "$real" "--threads=$width" "$@" ;;
    esac
}
