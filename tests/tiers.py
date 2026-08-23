"""UX-238: which tier each test file is in, measured rather than guessed.

Google's small/medium/large/enormous, adapted to what this suite
actually does. **The measured duration is the rule**; the descriptions
below say what tends to be slow, not what decides:

* **small** - pure Python over in-memory fixtures. No subprocess, no
  node, no real tool. The **default**: a file not listed below is
  small, which is right for 160 of 220 files.
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
    "tests/unit/test_process_spine.py",                              #   35.8s
    "tests/unit/test_spine_ground_truth.py",                         #   26.9s
    "tests/unit/test_analysis_memory_shape.py",                      #   24.6s
    "tests/unit/test_trace_stream_and_census_scale.py",              #   19.4s
    "tests/unit/test_snapshot.py",                                   #   18.9s
    "tests/unit/test_cache_logs.py",                                 #   18.2s
    "tests/unit/test_doctor.py",                                     #   15.4s
)

MEDIUM = (
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
)
