#!/bin/sh
# UX-905 (`pairs`: off/auto; `cap3`: the same at max-jobs 3, 8-of-40 scaled)
# and UX-895 (`overhead`: none/capture/trace/spine/all) on one quiet host: three
# interleaved repeats, cold caches every build, bst's own `max-jobs` default
# (min(cpus, 8)) unless `cap3`. `mem` is host used-memory peak over the
# build's start, sampled 1/s from /proc/meminfo. One `::notice::` per arm
# at exit - GitHub keeps ten per step, a line per build would not fit.
set -eu
MODE=$1
PROJ=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-$PWD/arms}
mkdir -p "$OUT/xdg"
export XDG_CONFIG_HOME="$OUT/xdg"
printf 'cache:\n  quota: 20G\n  reserved-disk-space: 2G\n' > "$XDG_CONFIG_HOME/buildstream2.conf"
[ "$MODE" != cap3 ] || printf 'build:\n  max-jobs: 3\n' >> "$XDG_CONFIG_HOME/buildstream2.conf"
OLDPWD_REPO=$(cd "$PROJ/../.." && pwd)
cd "$PROJ"

summary() {
    for arm in $(cut -d' ' -f1 "$OUT/builds.txt" 2>/dev/null | sort -u); do
        echo "::notice title=$MODE $arm::$(grep "^$arm " "$OUT/builds.txt" | cut -d' ' -f2- | paste -sd';' -)"
    done
}
trap summary EXIT

traced() {  # a capture whose hook never ran is not an arm (bwrap shim shadowed)
    python3 -c 'import json, sys; sys.exit(not json.load(open(sys.argv[1])).get("process_count"))' "$1"
}

peak() {
    python3 -c 'import json, sys
r = json.load(open(sys.argv[1]))
print(next((e.get("peak_work_concurrency") for e in r.get("per_element_parallelism") or []
            if e.get("element") == "giant.bst"), "?"))' "$1" 2>/dev/null || echo "?"
}

busy() {  # host-wide busy CPU seconds: the sandbox's work is not bst's rusage
    awk '/^cpu /{print ($2+$3+$4+$7+$8)/100}' /proc/stat
}

shares() {  # UX-847's two shares and the pool mode, off the Plane 2 ledger
    python3 -c 'import json, sys
from bga.correlate import compute_jobserver_shares
r = json.load(open(sys.argv[1])); pool = r.get("jobserver_pool") or {}
if not r.get("jobserver"): print("jobserver -"); sys.exit()
i, s = compute_jobserver_shares(r.get("jobserver_ledger") or [], pool.get("capacity"))
print("pool %s idle %.2f starved %.2f" % (pool.get("mode"), i, s))' "$1"
}

used_mb() {
    awk '/^MemTotal:/{t=$2} /^MemAvailable:/{a=$2} END{print int((t-a)/1024)}' /proc/meminfo
}

spined() {  # the spine alone reports how processes ended
    python3 -c 'import json, sys; sys.exit(not json.load(open(sys.argv[1])).get("process_outcomes"))' "$1"
}

build() {  # build <arm> <repeat> <plane2 path or -> -- <command...>
    arm=$1 i=$2 plane2=$3; shift 4
    rm -rf ~/.cache/buildstream ~/.local/share/buildstream .bga
    m0=$(used_mb); b0=$(busy)
    (while :; do used_mb; sleep 1; done) > "$OUT/mem" & sampler=$!
    /usr/bin/time -f '%e' -o "$OUT/time" "$@" > "$OUT/$arm-$i.log" 2>&1 \
        || { kill $sampler; tail -40 "$OUT/$arm-$i.log"; exit 1; }
    b1=$(busy); kill $sampler; read -r wall < "$OUT/time"
    mem=$(( $(sort -n "$OUT/mem" | tail -1) - m0 ))
    [ "$plane2" = - ] || plane2=$(ls $plane2 2>/dev/null | tail -1)
    [ "$plane2" = - ] || traced "$plane2" || { echo "::error title=$arm::Plane 2 traced 0 processes"; exit 1; }
    case $arm in spine|all) spined "$plane2" || { echo "::error title=$arm::no process outcomes"; exit 1; } ;; esac
    p=$([ "$plane2" = - ] && echo - || peak "$plane2")
    cpu=$(python3 -c "print(f'{$b1 - $b0:.0f}')")
    js=$([ "$plane2" = - ] && echo - || (cd "$OLDPWD_REPO" && shares "$plane2"))
    echo "$arm wall ${wall}s cpu ${cpu}s mem ${mem}M giant-peak $p $js" | tee -a "$OUT/builds.txt"
}

for i in 1 2 3; do
    case $MODE in
    pairs|cap3)
        for m in off auto; do
            build "$m" "$i" "$OUT/$m-$i.json" -- bga capture run --run-dir "$OUT/run-$m-$i" \
                --jobserver "$m" . "$OUT/$m-$i.json" -- bst build all.bst
        done ;;
    overhead)
        build none "$i" - -- bst build all.bst
        build capture "$i" ".bga/runs/*/plane2.json" -- bga snapshot --no-trace-opens -- bst build all.bst
        build trace "$i" ".bga/runs/*/plane2.json" -- bga snapshot --trace-opens -- bst build all.bst
        build spine "$i" ".bga/runs/*/plane2.json" -- bga snapshot --no-trace-opens --trace-spine on -- bst build all.bst
        build all "$i" ".bga/runs/*/plane2.json" -- bga snapshot --trace-opens --trace-spine on -- bst build all.bst ;;
    diag)  # one small auto capture, its report's shape printed whole
        build diag 1 "$OUT/diag.json" -- bga capture run --run-dir "$OUT/run-diag" --jobserver auto \
            . "$OUT/diag.json" -- bst --option giant_lines 1800 build all.bst
        tail -60 "$OUT/diag-1.log"
        python3 -c 'import json, sys
r = json.load(open(sys.argv[1]))
print("keys", sorted(r))
for k in ("per_element_parallelism", "jobserver_decisions", "jobserver_pool"):
    print(k, json.dumps(r.get(k))[:1500])' "$OUT/diag.json"
        find "$OUT/run-diag" -maxdepth 2 | head -40
        exit 0 ;;
    *) echo "usage: $0 pairs|cap3|overhead|diag" >&2; exit 2 ;;
    esac
done
