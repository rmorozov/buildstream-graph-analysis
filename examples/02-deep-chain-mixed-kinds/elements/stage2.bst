# Depth 3 of the chain (stage1.bst -> stage2.bst) - deliberately a
# different kind (`compose`, not `manual`) from its neighbors, for
# element-kind heuristic coverage (P4-12): composes stage1's staged
# output rather than running its own commands.
kind: compose
depends:
- filename: stage1.bst
  type: build
