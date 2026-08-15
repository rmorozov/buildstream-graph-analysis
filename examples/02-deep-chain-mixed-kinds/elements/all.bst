# Real build target - depth-4 chain (base -> stage1 -> stage2 -> stage3)
# as a build dependency, plus a runtime-only dependency reached through a
# junction (kind diversity: import, manual, compose, junction, all in one
# real build - not just `bst show` as in tests/fixtures/bst_show_project).
#
# `kind: import` here, not `stack` (BuildStream real constraint,
# confirmed via a real CI failure: stack elements require every
# dependency to be both build and runtime, so a stack can't mix a
# build-only and a runtime-only dep the way this target deliberately
# does - same typed-dependency pattern as
# tests/fixtures/bst_show_project's app.bst).
kind: import
sources:
- kind: local
  path: files/final
depends:
- filename: stage3.bst
  type: build
- filename: junction.bst:libfoo.bst
  type: runtime
