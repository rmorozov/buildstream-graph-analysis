# No internal dependencies. In the fixture's synthetic log this element's
# FETCH phase is deliberately rendered as a bare CACHED line with no
# preceding START, to exercise a real gap in tools/bst_log_to_chrome_trace.py:
# a status line with no matching START is silently dropped, so this one
# phase never appears in the resulting trace. See build_model.DROPPED_TASKS.
kind: cmake
sources:
- kind: git
  url: upstream:net-stack/libcrypto.git
  track: main
variables:
  cmake-local: -DBUILD_SHARED_LIBS=ON
