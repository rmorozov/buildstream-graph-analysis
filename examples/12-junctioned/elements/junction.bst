# The local junction into sub/ - never itself joins the jobserver mode
# (kind: junction has no build or native-parallelism concept of its
# own; Decomposition's second input class).
kind: junction
sources:
- kind: local
  path: sub
