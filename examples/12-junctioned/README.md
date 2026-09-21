# 12-junctioned

`UX-869` (the FIFO under `bind_dst`) and `UX-871` (a junctioned
element's kind) were both real first-day defects on the user's own
junctioned project, and no example project in this repository had a
junction - so neither defect had a CI step to fail on. This project is
the smallest one that does: `elements/junction.bst` (`kind: junction`)
into `sub/`, a real second BuildStream project holding one `cmake`
element (`core.bst`, one trivial C file) and the stack that groups it;
the top project's own `all.bst` depends on `junction.bst:stack.bst`.

Same staged sysroot as `05`-`11` - `../stage_cpp_toolchain.sh` hardlink-
clones it into `sub/files/toolchain/` too (a junctioned subproject is a
real, separate project - `kind: local` sources resolve inside it, not
the parent).

```bash
../stage_cpp_toolchain.sh
bga snapshot --jobserver auto -- bst --builders 2 build all.bst
```

(run from inside `12-junctioned/`)

**Out of scope.** A remote junction (`kind: local` only, same as every
other example's junction). A second example forcing fifo-style
`--jobserver-auth` (`UX-869`'s own class). That paragraph used to say
the auto-detection picks `fd` here because this runner's own `make` is
GNU Make 4.3; since `UX-915` the sysroot carries a pinned 4.4.1, so the
style is the pin's, not the runner's, and crossing the switch on
purpose is `UX-916`'s own row rather than this project's.

## Real reading, this box, 2026-09-15

Fresh `HOME`/`XDG_CACHE_HOME`/`XDG_DATA_HOME`, a copy of this project
under the scratchpad, `bga snapshot --jobserver auto -- bst --builders
2 build all.bst` (`tests/unit/_bst_env.py`'s sized `XDG_CONFIG_HOME` -
this box's real free disk is small next to its nominal size, so
BuildStream's default percentage-of-total reserve alone refuses any
build here with "Cache too full" before a process runs, UX-755):

```text
exit=0 elapsed=13.9s
```

`plane2.json`'s `jobserver_decisions` for the junctioned cmake element,
named by its short spelling (`core.bst`, not `junction.bst:core.bst` -
the shim only ever derives the short spelling from bwrap's own `--dir`,
never the junction prefix):

```json
{"decision": "joined", "element": "core.bst", "kind": "cmake", "max_jobs": 4, "policy": "cmake_meson"}
```

`joined` with a real kind (`cmake`), not `unknown_kind` - `UX-871`'s
fix holds under a real build, not only the fixture
`tests/unit/test_the_kinds_read_carries_the_options.py` already covers.

`kinds_read.json`'s own diagnostic (`read_element_kinds_for_jobserver`,
called directly - the real file lives in a scratch directory removed
when the capture's own `with capture_scratch(...)` block exits, before
this process could read it back):

```json
{"argv": ["bst", "show", "--format", "%{name} %{kind}", "all.bst"], "count": 7, "junctions": 3, "collisions": 0}
```

`count: 7` is `{toolchain.bst, junction.bst:toolchain.bst, core.bst,
junction.bst:core.bst, stack.bst, junction.bst:stack.bst, all.bst}` -
every junctioned element stored under both spellings (`UX-871`),
`collisions: 0` - only one junction here, so no short spelling is ever
claimed twice.
