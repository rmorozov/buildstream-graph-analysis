# Real build target - depth-4 chain (base -> stage1 -> stage2 -> stage3)
# as a build dependency, plus a runtime-only dependency reached through a
# junction (kind diversity: import, manual, compose, stack, junction, all
# in one real build - not just `bst show` as in
# tests/fixtures/bst_show_project).
kind: stack
depends:
- filename: stage3.bst
  type: build
- filename: junction.bst:libfoo.bst
  type: runtime
