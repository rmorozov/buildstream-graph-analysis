# Depth 2 of the chain (base.bst -> stage1.bst). Real work, not
# instantaneous, so the chain has measurable per-stage duration.
kind: manual
depends:
- filename: base.bst
  type: build
- filename: runtime.bst
  type: build
config:
  install-commands:
  - "sleep 2"
