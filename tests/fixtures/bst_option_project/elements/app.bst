kind: manual
(?):
- variant == "b":
    depends:
    - base-b.bst
config:
  install-commands:
  - "true %{variant}"
