# UX-801: `bst show` writes the CAS, and two files still run it in the ambient HOME

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-775 (the isolation and its counting guard), UX-760 | **Found by:** round 110, the gate's bst tier on a shared machine | **Serves:** R8 reading a red gate on a machine whose disk casd cannot size | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

```console
$ python3 -m pytest tests/unit/test_bst_show_to_graph.py -q -x
E   RuntimeError: bst show failed (exit 255) ... Cache too full
$ grep -iE "quota|space" ~/.cache/buildstream/logs/_casd/$(ls -t ~/.cache/buildstream/logs/_casd | head -1) | tail -2
[ERROR] Cleanup operation failed: disk usage (257919074623) is above maximum quota (257025515316) and no inactive blobs are available for deletion
[ERROR] Out of space error in `merklize()` for path ".../examples/06-macro-micro-optimization/files/toolchain" ... "Insufficient storage quota"
$ printf 'cache:\n  quota: 3G\n  reserved-disk-space: 500M\n' > ~/.config/buildstream.conf
$ python3 -m pytest tests/unit/test_bst_show_to_graph.py tests/unit/test_element_kind_heuristics.py -q
33 passed in 2.86s
```

`bst show` merklizes the project's local files into the CAS, so it
writes the cache; `tests/unit/test_a_generated_project_builds.py:213`
lists `test_bst_show_to_graph.py` and `test_element_kind_heuristics.py`
under `_NOT_CAS_WRITING`, and they run `bst` with the ambient `HOME`.
With no quota configured, casd sizes its quota from the filesystem, and
on this container the filesystem's used space reads above that quota
(252 GB total, 12 GB available, 26 GB used by `df`): every capture is
refused. The isolated config's `quota: 3G` never asks the disk.

## Required Fix

In `tests/unit/test_a_generated_project_builds.py` the two files leave
`_NOT_CAS_WRITING`, and in `tests/unit/test_bst_show_to_graph.py` and
`tests/unit/test_element_kind_heuristics.py` every `bst` call runs under
`_bst_env.bst_env(tmp_path / "home")`; the exclusion set's docstring
states that `bst show` writes the CAS. `UX-775`'s verifier named the
mutation this guard cannot see — a file mislabelled into the set — so
the set's entries carry the command each file runs and a guard reads
each entry's file for a `bst` call whose subcommand writes the CAS
(`show`, `build`, `artifact`): red when one does.

## Out of Scope

- The machine-local `~/.config/buildstream.conf` — a workaround on
  one box, not the tree's.

## Acceptance Test

Both files green with `HOME` pointed at an empty directory and no
`~/.config/buildstream.conf`; mutation: `test_bst_show_to_graph.py`
returned to `_NOT_CAS_WRITING` — red, naming the file and `show`.

## Outcome

_Not started._
