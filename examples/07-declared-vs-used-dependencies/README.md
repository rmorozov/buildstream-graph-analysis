# 07 — declared-vs-used dependencies

A deliberately minimal project that exists to test one thing in **both
directions**: `UX-46`'s detection of build dependencies an element
declares but never reads.

## Why it exists

`examples/06-macro-micro-optimization` cannot test this properly.
`UX-46` measured that project and found every one of its cross-element
build dependencies to be decorative — so its only evidence that the
detector does not simply flag everything was `toolchain.bst`. A detector
that reported *all* edges as unused would have looked identical there.

## The shape

`user.bst` and `unrelated.bst` declare **identical** dependencies
(`base.bst` + `toolchain.bst`) and differ in exactly one respect:

| element | source | expected verdict |
|---|---|---|
| `user.bst` | `#include <base.hpp>` — resolves to `base.bst`'s staged header | **used** |
| `unrelated.bst` | includes nothing from `base.bst` | **unused candidate** |

An over-eager detector flags both; an inert one flags neither; only a
correct one separates them.

## Running it

```bash
examples/stage_cpp_toolchain.sh      # stages the shared sysroot
python3 -m tools.bst_native_build_tracer run --trace-opens \
    examples/07-declared-vs-used-dependencies /tmp/07.json \
    -- bst --builders 4 --max-jobs 4 build all.bst
```

Real output from that command:

```
Declared build dependencies never read: 1 candidate(s) across 1 element(s); 4 edge(s) confirmed used
  unrelated.bst              never read: base.bst  (5 staged file(s))
```

and from its JSON, the discrimination stated numerically:

```
  user.bst      -> base.bst       (1/5 staged files opened)     <- used
  unrelated.bst -> base.bst       0 of 5 files were opened      <- candidate
```

`user.bst` opens exactly one of `base.bst`'s five staged files —
`/usr/include/base.hpp`, the one it includes.
