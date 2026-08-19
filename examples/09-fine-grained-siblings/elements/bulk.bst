# UX-120: a staged tree whose cost is its *file count*. BuildStream
# stages dependencies by hardlink, so a normal 8k-file sysroot stages in
# under a second and its toll rounds to zero against BuildStream's own
# second-resolution phase timing. 60k files is what it takes for the toll
# to become measurable at all.
kind: import
sources:
- kind: local
  path: files/bulk
