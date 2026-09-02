# Raw figures: where round 75's three implementer tracks spent their tokens

`UX-525`. [Round 75](../round-75.md) recorded three tracks as
`943s · 996s · 1,174s` and `81k · 123k · 131k` — three totals, no split
and no stated definition. These are the same three runs, from the
transcripts the harness wrote, split by phase.

Regenerate with:

```bash
python3 tools/dev_track_cost.py --list
python3 tools/dev_track_cost.py -v <transcript.jsonl> ...
```

## Which run is which

The wall clocks identify them: the tool reads first-to-last record and
prints 943 s, 996 s and 1,174 s, matching round 75's three exactly.

| track | transcript | wall | tokens here | round 75 said |
|---|---|---|---|---|
| `UX-490` | `agent-aaa2b70126e746bcf` | 943 s | 78,583 | 81k |
| `UX-493` | `agent-aea8d7d7a33844ba6` | 996 s | 119,062 | 123k |
| `UX-492` | `agent-af3da166d3b53f87c` | 1,174 s | 126,187 | 131k |

Round 75 printed the three as an unordered list, so this is the first
time each number is attached to its track. The totals here sit 2.4k,
3.9k and 4.8k below the recorded ones — 3.1-3.8%. Round 75 stated no
definition, which is the gap `UX-525` was filed for; the definition
here is in the tool's docstring and the sum reproduces each track's
final context to 0.2%.

## The split

```text
agent-aaa2b70126e746bcf.jsonl  943s  65 responses     (UX-490)
phase      turns     tokens      %
brief          0       8679   11.0
close          3        846    1.1
test           9       4579    5.8
edit          28      32500   41.4
read          22      29656   37.7
other          3       2323    3.0
TOTAL         65      78583  100.0
context high-water 78455, cache re-reads 3354310
turns in two phases: 1 (350 tokens)

agent-aea8d7d7a33844ba6.jsonl  996s  90 responses     (UX-493)
phase      turns     tokens      %
brief          0       8914    7.5
outcome        2       3425    2.9
close         18      26606   22.3
falsify        6      10668    9.0
test          11       5933    5.0
edit          14      11956   10.0
read          35      50571   42.5
other          4        989    0.8
TOTAL         90     119062  100.0
context high-water 118884, cache re-reads 6381331
turns in two phases: 0 (0 tokens)

agent-af3da166d3b53f87c.jsonl  1174s  87 responses    (UX-492)
phase      turns     tokens      %
brief          0       8804    7.0
outcome        3       5292    4.2
close          3       1041    0.8
falsify       12       9781    7.8
test           6       3102    2.5
edit          13      17648   14.0
read          48      80382   63.7
other          2        137    0.1
TOTAL         87     126187  100.0
context high-water 126015, cache re-reads 6879152
turns in two phases: 0 (0 tokens)
```

## What the split says

**Reading is the track**: 37.7%, 42.5%, 63.7%. Not the task file — the
`brief` row is the whole opening prompt at 7-11% — but the `sed -n`,
`grep` and `cat` of source and docs that follow it. The single costliest
turn of the three was `ls docs/backlog/scenarios/ | grep -E …` at
**8,405 tokens**, a directory of 536 files listed to find five.

**Pytest output is real but second**: by a substring match over the
commands rather than the phase table, `pytest` and `make test` results
cost **7,868 / 15,585+3,166 / 11,699+1,184** tokens — **10.0%, 15.7%,
10.2%**. The filing named it as a suspect and it is one.

**But the selector is the smaller half of it.** Splitting that by which
command ran:

| track | `make test-touching` | direct `pytest` / `make test-*` |
|---|---|---|
| `UX-490` | 537 in 1 run | 7,331 in 10 runs |
| `UX-493` | 3,166 in 3 runs | 15,585 in 15 runs |
| `UX-492` | 1,184 in 2 runs | 11,699 in 16 runs |

So the lever `UX-525` expected first — a `make test-touching` that
prints one line unless red — has a ceiling of **0.7-2.7%** of a track,
and the tokens are in the ten-to-sixteen direct runs. The lever landed
anyway, because it is two lines of code and its own before/after is
measured; the honest ceiling is stated rather than the phase total
claimed for it.

**`other` is 0.1-3.0%** and no turn but one fell in two phases, so the
argv classifier is not carrying a large unclassified bucket.

**The close is not uniform**: 1.1%, 22.3%, 0.8%. `UX-493`'s eighteen
close turns are `make lint` and `dev_close_task.py` runs; the other two
tracks made three each. A track that closes badly costs a fifth of
itself doing it.
