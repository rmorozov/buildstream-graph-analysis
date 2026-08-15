# Depth 4 of the chain (stage2.bst -> stage3.bst). Back to real work.
kind: manual
depends:
- filename: stage2.bst
  type: build
- filename: runtime.bst
  type: build
config:
  install-commands:
  - "sleep 2"
