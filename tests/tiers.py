"""UX-238: which tier each test file is in, measured rather than guessed.

Google's small/medium/large/enormous, adapted to what this suite
actually does. **The measured duration is the rule**; the descriptions
below say what tends to be slow, not what decides:

* **small** - pure Python over in-memory fixtures. No subprocess, no
  node, no real tool. The **default**: a file not listed below is
  small, which is right for 164 of 224 files.
* **medium** - spawns a process (the `bga` CLI, a node harness) or
  writes a run directory. Seconds, not milliseconds.
* **large** - builds scale fixtures, streams traces, drives real
  process trees. Tens of seconds each.
* **enormous** - needs a real `bst`/`bwrap` build. That tier already
  existed as the `bst` marker and keeps its name; `bst-tests` in CI is
  the job that runs it.

Measured with `pytest tests/ --durations=0`, summed per file over
setup+call+teardown, on the container that produced round 29:

```text
3102 passed, 3 skipped in 373.14s
160 files    18.2s   small    (5% of the time, 73% of the files)
 53 files   184.0s   medium
  7 files   159.0s   large    (43% of the time, 3% of the files)
```

Re-measured 2026-08-25 (round 39), after CI killed the small tier at
its 90s budget:

```text
small tier before   130.4s   24 files at or above the medium floor,
                             one of them 61.7s on its own
small tier after     16.4s   the same 2,431 tests, none of them moved
                             out of the suite - only out of the tier
```

The drift is the mechanism working as designed and nobody reading it:
a file joins `small` by default, so twenty-four of them crossed the
floor one at a time and only the aggregate budget could see it. It saw
it.

Re-measured 2026-08-27 (round 47, `UX-336`), and the same drift had
happened again — fourteen files over the medium floor, one of them
above the *large* one:

```text
small tier before   81.7s test time, 33s wall at -n auto   103 files
small tier after    35.5s test time, 11s wall at -n auto    89 files
```

The whole suite moved with it, and the parallelism is the larger half:

```text
full suite, single process   642s   4,131 passed, 18 skipped
full suite, -n auto          194s   4,131 passed, 18 skipped   3.3x
skip census                  identical between the two, reason for reason
```

`-n auto` is how every tier runs now (`make`'s `PYTEST_XDIST`). The
tiers still matter: they are what `make test-small` selects, and 11s is
a different kind of loop from 33s.

**The lists are the exceptions, not the taxonomy.** Adding a test file
costs nothing here unless it is slow, and a slow one that is not listed
is caught by the small tier's own wall-clock budget rather than by
review - see `test_the_tiers_are_a_partition.py`.

A file moves tier when its *measurement* moves, not when it feels
slower. Re-measure with the command above before editing either list.
"""

# Above this, a file is `large`. Below `MEDIUM_CEILING_S`, it is small.
LARGE_FLOOR_S = 15.0
MEDIUM_FLOOR_S = 1.0

# Wall-clock budget for the whole small tier, with headroom. Measured
# at 18.2s of test time; the budget is generous because it is a
# backstop against a *large* file landing in the default tier (the
# smallest of those is 15.4s on its own), not a benchmark.
SMALL_TIER_BUDGET_S = 90.0

LARGE = (
    # UX-257's geometry instrument: a real Chrome over CDP, an exported
    # report per class, and every claim measured at three viewports. It
    # was never listed, so it sat in the default tier at 42.6s and then
    # at 61.7s once `UX-285` and `UX-286` added fourteen checks - which
    # is what finally blew the small tier's budget in CI. The file is
    # four times the large floor on its own.
    "tests/unit/test_the_page_has_geometry.py",                      #   61.7s
    "tests/unit/test_process_spine.py",                              #   35.8s
    "tests/unit/test_spine_ground_truth.py",                         #   26.9s
    "tests/unit/test_analysis_memory_shape.py",                      #   24.6s
    "tests/unit/test_trace_stream_and_census_scale.py",              #   19.4s
    "tests/unit/test_snapshot.py",                                   #   18.9s
    "tests/unit/test_cache_logs.py",                                 #   18.2s
    "tests/unit/test_doctor.py",                                     #   15.4s
    # UX-336, re-measured 2026-08-27: the drift the aggregate budget
    # hides, again. `UX-317`'s apparatus checks boot the exported page
    # once per claim and had reached the large floor while sitting in
    # the default tier - the same mechanism round 39 documented, three
    # rounds later.
    "tests/unit/test_apparatus_in_its_place.py",                     #   17.4s
    # UX-334's console net: four boots of a real Chromium - two fixture
    # runs, served and exported - and three positive controls that each
    # start a browser of their own to prove one channel of the
    # instrument can still hear. Measured at 13.8s with two controls and
    # 16.4s with the third, which is what moved it over the floor.
    "tests/unit/test_the_console_stays_clean.py",                    #   16.4s
)

MEDIUM = (
    # Re-measured 2026-08-25 (round 39). Twenty-four files had drifted
    # over the medium floor while staying in the default tier: the
    # budget is an aggregate, so each one was invisible on its own and
    # together they were 114s of the small tier's 130s. Every line below
    # carries what it measured at.
    # UX-296's big-run fixture: a million process records written to
    # disk, and four subprocess startups measured against it.
    # Round 48, measured on landing rather than after the drift: both
    # of these are subprocess-heavy by construction, and `UX-336`'s
    # lesson is that a file joins `small` by *default* - so the tier is
    # chosen when the file is written, not when the budget notices.
    # The small tier went 23.6s -> 46.2s with these two in it.
    "tests/unit/test_one_bad_row_costs_one_section.py",         #   11.3s
    "tests/unit/test_every_emitted_contract_is_answerable.py",  #    9.0s
    "tests/unit/test_the_view_parses_nothing.py",               #    7.6s
    # Round 50, tiered on landing for the same reason: four `bga analyze`
    # subprocesses, three of them `--format json --explain`.
    "tests/unit/test_the_readme_block_is_the_real_output.py",   #    1.2s
    # `UX-330`'s walk: a seed planted once, then ten `bga` subprocesses
    # run against it - the whole point is that it is not in-process.
    "tests/unit/test_the_stranger_has_a_seed.py",               #    5.6s
    # UX-298's emitter: a 40,000-process trace written twice, once for
    # the ceiling and once for the bytes-before-close clause.
    "tests/unit/test_the_timeline_speaks_perfetto.py",           #    6.0s
    "tests/unit/test_any_element_can_be_inspected.py",          #   12.3s
    "tests/unit/test_one_table_many_views.py",                  #    8.1s
    "tests/unit/test_the_report_has_chapters.py",               #    4.9s
    "tests/unit/test_a_table_cell_obeys_the_value_rule.py",     #    3.2s
    "tests/unit/test_a_control_says_what_it_does.py",           #    2.7s
    "tests/unit/test_every_table_has_its_own_state_key.py",     #    1.5s
    "tests/unit/test_findings_carry_their_evidence.py",         #    1.5s
    "tests/unit/test_the_structural_block_is_reachable.py",     #    1.5s
    "tests/unit/test_dev_run_script.py",                        #    1.4s
    "tests/unit/test_focused_graphs_not_a_dag_viewer.py",       #    1.4s
    "tests/unit/test_a_value_shows_what_it_is.py",              #    1.4s
    "tests/unit/test_element_kind_heuristics.py",               #    1.4s
    "tests/unit/test_logging_and_exceptions.py",                #    1.3s
    "tests/unit/test_capture_diagnostics.py",                   #    1.3s
    "tests/unit/test_correlate.py",                             #    1.2s
    "tests/unit/test_focus_and_the_working_set.py",             #    1.2s
    "tests/unit/test_the_tiers_are_a_partition.py",             #    1.2s
    "tests/unit/test_ci_comment.py",                            #    1.1s
    "tests/unit/test_open_window_flush.py",                     #    1.1s
    "tests/unit/test_focus_is_an_investigation.py",             #    1.1s
    "tests/test_golden.py",                                     #    1.1s
    "tests/unit/test_why_is_this_ranked_first.py",              #    1.0s
    "tests/unit/test_the_jump_box_offers_what_it_knows.py",     #    1.0s
    "tests/unit/test_the_capacity_answer_is_published.py",      #    1.3s
    "tests/unit/test_comparison_refuses_on_contract_movement.py",       #    2.1s
    "tests/unit/test_report_stays_readable_at_scale.py",             #   12.8s
    "tests/unit/test_marginal_efficiency_gate.py",                   #   11.3s
    "tests/unit/test_build_root_override_join.py",                   #    9.9s
    "tests/unit/test_dual_plane_capture.py",                         #    9.8s
    "tests/unit/test_six_seams_round_21_found.py",                   #    7.7s
    "tests/unit/test_stream_merge.py",                               #    7.6s
    "tests/unit/test_the_viewer_renders_the_schema.py",              #    6.6s
    "tests/unit/test_the_perfetto_handoff.py",                       #    6.4s
    "tests/unit/test_docs_links_and_commands.py",                    #    6.2s
    "tests/unit/test_output_schemas.py",                             #    5.7s
    "tests/unit/test_grace_window_drains.py",                        #    5.3s
    "tests/unit/test_bst_extract_run.py",                            #    5.0s
    "tests/unit/test_blast_ranking_discriminates.py",                #    4.8s
    "tests/unit/test_cli_subcommands.py",                            #    4.6s
    "tests/unit/test_bst_extract_run_strict.py",                     #    4.5s
    "tests/unit/test_why_bga_believes_what_it_believes.py",          #    4.3s
    "tests/unit/test_publish_the_join.py",                           #    4.1s
    "tests/unit/test_a_report_you_can_navigate.py",                  #    3.8s
    "tests/unit/test_native_build_tracer.py",                        #    3.6s
    "tests/unit/test_diagnostics_performance.py",                    #    3.2s
    "tests/unit/test_the_minutes_inside_analyze.py",                 #    2.8s
    "tests/unit/test_bst_run_context.py",                            #    2.7s
    "tests/unit/test_compare_mismatch_refusal.py",                   #    2.6s
    "tests/unit/test_the_views_that_draw.py",                        #    2.5s
    "tests/unit/test_compare.py",                                    #    2.2s
    "tests/unit/test_shared_source_blast.py",                        #    2.2s
    "tests/unit/test_the_report_you_can_attach.py",                  #    2.2s
    "tests/unit/test_the_order_the_page_has.py",                     #    2.1s
    "tests/unit/test_the_numbers_have_a_sentence.py",                #    2.1s
    "tests/unit/test_copy_a_finding.py",                             #    1.8s
    "tests/test_cli.py",                                             #    1.8s
    "tests/unit/test_granularity.py",                                #    1.8s
    "tests/unit/test_efficiency_gate_exit_codes.py",                 #    1.7s
    "tests/unit/test_determinism.py",                                #    1.7s
    "tests/unit/test_bst_show_to_graph.py",                          #    1.7s
    "tests/unit/test_what_if_you_could_choose_the_fixes.py",         #    1.7s
    "tests/unit/test_efficiency_gate_signal.py",                     #    1.7s
    "tests/unit/test_a_clone_without_the_archive.py",                #    1.6s
    "tests/unit/test_bst_checkout_cost.py",                          #    1.6s
    "tests/unit/test_host_manifest_and_cross_host.py",               #    1.6s
    "tests/unit/test_one_timeline_both_planes.py",                   #    1.5s
    "tests/unit/test_a_link_that_shows_what_i_was_looking_at.py",    #    1.5s
    "tests/unit/test_progress_never_touches_the_pipe.py",            #    1.4s
    "tests/unit/test_cli_exit_codes.py",                             #    1.4s
    "tests/unit/test_one_click_from_investigation.py",               #    1.4s
    "tests/unit/test_a_capture_that_slept.py",                       #    1.3s
    "tests/unit/test_tables_you_can_interrogate.py",                 #    1.3s
    "tests/unit/test_the_page_that_answers_why.py",                  #    1.3s
    "tests/unit/test_graph_performance.py",                          #    1.2s
    "tests/unit/test_the_first_screen_is_a_decision.py",             #    1.2s
    "tests/unit/test_every_element_is_one_object.py",                #    1.2s
    "tests/unit/test_the_next_step_is_a_command.py",                 #    1.1s
    "tests/unit/test_blast_query_and_kinds.py",                      #    1.1s
    # UX-336, re-measured 2026-08-27 on the small tier alone. Thirteen
    # more files had crossed the medium floor since round 39 and were
    # invisible for the same reason: each is small, the budget is an
    # aggregate. Together they were 46.2s of the small tier's 81.7s.
    "tests/unit/test_emphasis_is_a_budget.py",                       #   12.4s
    "tests/unit/test_the_documented_invocations_parse.py",           #    5.6s
    "tests/unit/test_the_chain_folds_and_clicks_are_counted.py",     #    4.8s
    "tests/unit/test_the_fold_says_how_deep_it_goes.py",             #    4.4s
    "tests/unit/test_the_shape_before_the_rows.py",                  #    3.6s
    "tests/unit/test_a_drawing_is_graded.py",                        #    3.1s
    "tests/unit/test_the_mapping_is_law.py",                         #    2.2s
    "tests/unit/test_the_page_conforms_to_its_sections.py",          #    2.1s
    "tests/unit/test_a_guard_reads_only_what_a_clone_has.py",        #    2.1s
    "tests/unit/test_the_printed_sentences_are_contracts.py",        #    1.6s
    "tests/unit/test_a_capture_that_cannot_start.py",                #    1.5s
    "tests/unit/test_the_handoff_does_not_carry_the_trace.py",       #    1.3s
    "tests/unit/test_buttons_that_know_why.py",                      #    1.0s
)
