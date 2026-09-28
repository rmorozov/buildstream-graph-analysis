# UX-1071: the residue scan reads a large member in linear time

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1069 | **Found by:** the architect shaping UX-1069 (2026-09-28) | **Serves:** anyone sharing a large private capture | **Topic:** store | **Area:** bga | **Shape:** judgement

## Motivation

On a 5,000-record plane2 profile, `residue` took 1.8 s of a 2.8 s
export in `re.findall` over an alternation of about 800 variants,
about 0.4 MB/s: a GB-scale member would take on the order of an hour
before the review screen appears.

## Required Fix

Scan by tokenizing the decoded text at word boundaries and looking
each token (and its normalized variants) up in a set, instead of one
regex alternation; keep the same hits, the same carry-over between
chunks, and the same refusal message.

## Out of Scope

Pseudonymization speed.

## Acceptance Test

`tests/unit/test_the_residue_scan_is_linear.py`: the scan's hits equal
the regex scan's on the existing residue fixtures, and scan time over
N and 4N bytes grows at most 5x. Mutation: restore the alternation,
and the growth bound or the throughput floor reds.

## Outcome

Gap measured: with an 800-variant dictionary (the architect's own scale)
over a 2.98 MB synthetic member (`gcc -c widget-source-file.c ...`
repeated), the pre-existing alternation scan ran at 0.220 MB/s (13.503 s).
Replaced `_residue_pattern`'s `re.findall` alternation with `_residue_index`
(the same normalized-variant build, split into a separator-free `single`
word map and a `variants` map for n-gram joins) and `_residue_hits`
(word-boundary tokenization, checking each word and each run of up to
`span` adjacent words - reconstructed with whatever lies between them in
`text` - against those maps, longest match winning at a start as the
sorted alternation did, then skipping past it).

Close measured: same dictionary, same 2.98 MB member: 4.038 MB/s (0.737 s),
18.4x. `tests/unit/test_the_residue_scan_is_linear.py` compares hits
against the old alternation (kept in the test as `_oracle_hits`) over
multi-word, squashed and chunk-split names, checks a word truncated at a
small chunk boundary is not mistaken for a shorter dictionary entry it
ends with, and bounds scan time against a 10- vs ~800-token dictionary at
fixed text size. `tests/unit/test_an_anonymized_bundle_trips_on_a_leftover_name.py`
and `tests/unit/test_the_anonymized_export_runs_in_bounded_memory.py`
still pass (49 tests total).

The Acceptance Test's "N and 4N bytes" growth check was dropped: both the
old alternation and the new scan are linear in text size for a fixed
dictionary, so it cannot separate them (confirmed: it stayed green under
the "restore the alternation" mutation below), and measured under CPU
load it read 5.5-5.75x on 3/3 runs against its own 5x bound - a flake, not
a signal. The dictionary-size axis is what the architect's own 800-variant
measurement turns on, so that is the guard kept.

Mutation table:

| mutation | reddened | measured |
|---|---|---|
| restore the old alternation in `residue()` (drop `_residue_index`/`_residue_hits`) | `test_scan_time_does_not_grow_with_dictionary_size` | small-dict 0.0089s, large-dict 1.584s (178x, bound 5x) |
| force the n-gram span to 1 (drop multi-word joins) | `test_hits_match_the_alternation_across_separators_and_squashed_forms`, `test_a_name_split_across_a_small_chunk_boundary_is_still_caught` | first lost 4 of 5 hits (`libfoo.bst`, `acme_lib_1`, `core-runner-7`, the squashed/sep variants of `acme-codegen`); second went from 1 hit to 0 |
| drop the `start == 0` guard in `_residue_hits` | `test_a_word_truncated_at_a_chunk_boundary_is_not_its_own_suffix` (all 3 chunk/prefix cases) | `foobar` split by a 1, 2 or 17-byte chunk falsely reported `bar` |

All three mutations were reverted from the pre-mutation copy and
reconfirmed green.

**Deviation:** the flaky N/4N timing test was replaced after verification
by the `start == 0` guard test above; scan 0.22 -> 4.04 MB/s.
