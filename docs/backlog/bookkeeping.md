# Bookkeeping ledger

One line per bookkeeping finding - a stale figure, a doc naming a
retired flag - never a task file (`UX-998`). `tools/dev_bookkeeping.py`
is the only writer: `--add` appends, `--sweep` lists the open lines
oldest first with the sweeps each survived, `--mark` resolves one.
`merge=union` in `.gitattributes` lets parallel filers append without
colliding.

Format:

    - r<filed> · <status> · <class> · `<path>[:<line>]` · <what drifted> · `<command>`

`status` is `open`, `swept r<N> UX-<id>`, `promoted r<N> UX-<id>`, or
`dropped r<N> <reason>`. `class` is `[a-z][a-z0-9-]*`; a new one needs
`--new-class`. No line stays open past three sweeps - `--sweep`
promotes it to a row or drops it with a reason. The key that catches a
duplicate finding is derived, never written:
`sha1("<path> · <what>")[:7]`.

## Findings
