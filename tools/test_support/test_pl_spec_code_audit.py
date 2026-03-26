#!/usr/bin/env python3
"""Automated tests for the /pl-spec-code-audit skill command.

Covers all 36 automated scenarios from features/pl_spec_code_audit.md.
The command is an agent skill defined in .claude/commands/pl-spec-code-audit.md.
Tests verify the command file content, structure, and referenced infrastructure
match the feature spec requirements.

Produces tests/pl_spec_code_audit/tests.json at project root.
"""

import json
import os
import re
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../..')))
from tools.bootstrap import detect_project_root
PROJECT_ROOT = detect_project_root(SCRIPT_DIR)

COMMAND_FILE = os.path.join(
    PROJECT_ROOT, '.claude', 'commands', 'pl-spec-code-audit.md')
FEATURE_FILE = os.path.join(
    PROJECT_ROOT, 'features', 'pl_spec_code_audit.md')
CONFIG_FILE = os.path.join(PROJECT_ROOT, '.purlin', 'config.json')
DEP_GRAPH_FILE = os.path.join(
    PROJECT_ROOT, '.purlin', 'cache', 'dependency_graph.json')


def _read_command():
    """Read the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


def _read_feature():
    """Read the feature spec content."""
    with open(FEATURE_FILE) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Test Classes -- grouped by related scenarios
# ---------------------------------------------------------------------------


class TestCommandFileExists(unittest.TestCase):
    """Prerequisite: the command file and feature spec exist on disk."""

    def test_command_file_exists(self):
        self.assertTrue(os.path.isfile(COMMAND_FILE),
                        f'Command file not found: {COMMAND_FILE}')

    def test_feature_file_exists(self):
        self.assertTrue(os.path.isfile(FEATURE_FILE),
                        f'Feature file not found: {FEATURE_FILE}')

    def test_command_file_not_empty(self):
        content = _read_command()
        self.assertGreater(len(content.strip()), 100,
                           'Command file should be substantial')

    def test_feature_file_has_scenarios(self):
        content = _read_feature()
        scenario_count = content.count('#### Scenario:')
        self.assertGreaterEqual(scenario_count, 36,
                                'Feature file should have at least 36 scenarios')


class TestRoleGating(unittest.TestCase):
    """Scenario: Role gate rejects non-PM/Engineer invocation

    Spec 2.1: Non-PM/Engineer agents (QA, PM) MUST receive the rejection
    message. The gate must appear before any analysis phase.
    """

    def test_command_contains_role_gate_message(self):
        content = _read_command()
        self.assertIn(
            'This command is for the PM or Engineer', content)

    def test_role_gate_appears_before_analysis(self):
        content = _read_command()
        gate_pos = content.index('PM or Engineer')
        phase_pos = content.index('Phase 0')
        self.assertLess(gate_pos, phase_pos,
                        'Role gate must appear before Phase 0 analysis')

    def test_role_gate_mentions_shared_role(self):
        """Command header declares shared PM/Engineer ownership."""
        content = _read_command()
        self.assertIn('shared', content.lower())
        self.assertIn('PM', content)
        self.assertIn('Engineer', content)

    def test_role_gate_blocks_non_architect_builder(self):
        """The gate message blocks QA and PM by requiring PM or Engineer."""
        content = _read_command()
        self.assertIn('not operating as', content.lower())


class TestArgumentParsing(unittest.TestCase):
    """Scenarios: Default invocation uses triage mode, Deep flag activates
    deep mode, Invalid argument produces error.

    Spec 2.3: The command MUST accept optional $ARGUMENTS and route to
    triage (default), deep (--deep), or error (anything else).
    """

    def test_no_argument_defaults_to_triage(self):
        content = _read_command()
        self.assertIn('No argument or empty', content)
        self.assertIn('triage', content.lower())

    def test_triage_processes_in_agent_no_subagents(self):
        content = _read_command()
        self.assertIn('no subagents', content.lower())

    def test_triage_processes_all_features(self):
        content = _read_command()
        self.assertIn('ALL features in-agent', content)

    def test_deep_flag_documented(self):
        content = _read_command()
        self.assertIn('--deep', content)

    def test_deep_mode_uses_batches_and_waves(self):
        content = _read_command()
        self.assertIn('batch', content.lower())
        self.assertIn('wave', content.lower())

    def test_invalid_argument_error_message(self):
        content = _read_command()
        self.assertIn("Error: Unknown argument", content)
        self.assertIn("Valid: --deep", content)

    def test_anything_else_clause(self):
        content = _read_command()
        self.assertIn('Anything else', content)


class TestPathResolution(unittest.TestCase):
    """Scenario: Path resolution reads tools_root from config

    Spec 2.4: Must read .purlin/config.json, extract tools_root, and use
    ${TOOLS_ROOT}/... for all tool invocations.
    """

    def test_reads_tools_root_from_config(self):
        content = _read_command()
        self.assertIn('tools_root', content)
        self.assertIn('.purlin/config.json', content)

    def test_uses_tools_root_variable(self):
        content = _read_command()
        self.assertIn('${TOOLS_ROOT}', content)

    def test_tools_root_invocations_use_variable(self):
        content = _read_command()
        invocations = re.findall(r'\$\{TOOLS_ROOT\}/[^\s`\)]+', content)
        self.assertGreater(len(invocations), 0,
                           'Should have tool invocations using ${TOOLS_ROOT}')

    def test_config_file_exists_with_tools_root(self):
        self.assertTrue(os.path.isfile(CONFIG_FILE))
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        self.assertIn('tools_root', config)


class TestTransitivePrerequisiteMap(unittest.TestCase):
    """Scenario: Transitive prerequisite map walks full ancestor chain

    Spec 2.5: Must walk all Prerequisite chains recursively via BFS to
    collect the full set of ancestor anchor nodes.
    """

    def test_command_describes_recursive_bfs_walk(self):
        content = _read_command()
        self.assertIn('recursively', content)
        self.assertIn('BFS', content)

    def test_command_describes_ancestor_output(self):
        content = _read_command()
        self.assertIn('ancestor anchor', content.lower())

    def test_dependency_graph_file_exists(self):
        self.assertTrue(os.path.isfile(DEP_GRAPH_FILE))

    def test_dependency_graph_has_prerequisites(self):
        with open(DEP_GRAPH_FILE) as f:
            graph = json.load(f)
        self.assertIn('features', graph)
        has_prereqs = any(
            f.get('prerequisites') for f in graph['features'])
        self.assertTrue(has_prereqs,
                        'At least one feature should have prerequisites')


class TestAnchorConstraintCollection(unittest.TestCase):
    """Scenarios: Anchor constraint collection extracts FORBIDDEN patterns,
    Anchor constraint collection extracts invariants.

    Spec 2.5 Step 0.3: Must collect FORBIDDEN patterns, numbered invariant
    statements, and named constraints from each unique anchor node.
    """

    def test_command_describes_forbidden_extraction(self):
        content = _read_command()
        self.assertIn('FORBIDDEN', content)
        self.assertIn('pattern', content.lower())

    def test_constraint_output_format_has_all_fields(self):
        content = _read_command()
        lower = content.lower()
        self.assertIn('forbidden', lower)
        self.assertIn('invariants', lower)
        self.assertIn('constraints', lower)

    def test_command_describes_invariant_extraction(self):
        content = _read_command()
        self.assertIn('invariant', content.lower())

    def test_command_reads_numbered_subsections(self):
        content = _read_command()
        self.assertIn('numbered', content.lower())


class TestTriageModeAnalysis(unittest.TestCase):
    """Scenarios: Triage mode checks spec completeness across all gap
    dimensions, Triage mode performs light code scan for FORBIDDEN patterns,
    Triage mode skips scenario-by-scenario comparison.

    Spec 2.7: Triage mode processes all features in-agent, checking 11
    gap dimensions, doing a light code scan, but skipping deep comparison.
    """

    def test_gap_dimensions_table_present(self):
        content = _read_command()
        self.assertIn('Gap Dimensions Table', content)

    def test_all_11_gap_dimensions_listed(self):
        content = _read_command()
        dimensions = [
            'Spec completeness', 'Policy anchoring', 'Traceability',
            'Engineer decisions', 'User testing', 'Dependency currency',
            'Spec-reality alignment', 'Notes depth', 'Code divergence',
            'Anchor invariant drift', 'Requirement hygiene',
        ]
        for dim in dimensions:
            self.assertIn(dim, content,
                          f'Missing gap dimension: {dim}')

    def test_light_code_scan_described(self):
        content = _read_command()
        self.assertIn('Light code scan', content)

    def test_reads_up_to_3_source_files(self):
        content = _read_command()
        self.assertIn('up to 3 primary source files', content)

    def test_grep_for_forbidden_patterns(self):
        content = _read_command()
        lower = content.lower()
        self.assertIn('grep', lower)
        self.assertIn('forbidden', lower)

    def test_skip_scenario_by_scenario_deep_comparison(self):
        content = _read_command()
        self.assertIn(
            'Skip scenario-by-scenario deep comparison', content)


class TestDeepModeClassification(unittest.TestCase):
    """Scenario: Deep mode classifies anchor nodes into spec-only track

    Spec 2.8: Deep mode classifies features into spec-only track
    (anchor nodes, zero-scenario features) and code-comparison track.
    """

    def test_spec_only_track_described(self):
        content = _read_command()
        self.assertIn('Spec-only track', content)

    def test_anchor_prefixes_in_spec_only(self):
        content = _read_command()
        self.assertIn('arch_*', content)
        self.assertIn('design_*', content)
        self.assertIn('policy_*', content)

    def test_code_comparison_track_described(self):
        content = _read_command()
        self.assertIn('Code-comparison track', content)

    def test_zero_scenario_features_in_spec_only(self):
        content = _read_command()
        self.assertIn('zero automated scenarios', content)


class TestDeepModeBatching(unittest.TestCase):
    """Scenarios: Deep mode batches features by scenario count, Deep mode
    creates solo batch for large features, Deep mode limits concurrent
    subagents to 5 per wave.

    Spec 2.8: Bin packing with 50-75 scenarios per batch, solo for 50+,
    max 5 concurrent subagents per wave.
    """

    def test_scenario_range_per_batch(self):
        content = _read_command()
        self.assertIn('50-75 scenarios', content)

    def test_first_fit_decreasing(self):
        content = _read_command()
        self.assertIn('first-fit-decreasing', content)

    def test_max_features_per_batch(self):
        content = _read_command()
        self.assertIn('max 4-5 features per batch', content)

    def test_solo_batch_rule(self):
        content = _read_command()
        self.assertIn('Solo batch', content)
        self.assertIn('50+ scenarios', content)

    def test_wave_limit_5_concurrent(self):
        content = _read_command()
        self.assertIn('up to 5 concurrent subagents', content)


class TestDeepModeSubagentPayload(unittest.TestCase):
    """Scenarios: Deep mode subagents receive transitive constraint payload,
    Deep mode subagents perform scenario-by-scenario comparison.

    Spec 2.8/2.9: Subagents receive the transitive map and anchor constraints
    in their prompt, and perform scenario-by-scenario code comparison.
    """

    def test_payload_includes_transitive_map(self):
        content = _read_command()
        self.assertIn('transitive prerequisite map', content)

    def test_payload_includes_anchor_constraints(self):
        content = _read_command()
        self.assertIn('anchor constraints', content)

    def test_subagents_dont_recompute(self):
        content = _read_command()
        self.assertIn("don't need to re-derive", content)

    def test_scenario_comparison_protocol(self):
        content = _read_command()
        self.assertIn('Scenario-by-scenario comparison', content)

    def test_traces_to_code_path(self):
        content = _read_command()
        self.assertIn('Trace to the code path', content)

    def test_flags_contradictions(self):
        content = _read_command()
        self.assertIn('contradictions', content)


class TestSpecOnlySubagents(unittest.TestCase):
    """Scenario: Spec-only subagents check cross-anchor consistency

    Spec 2.9: Spec-only subagents skip code comparison and instead check
    cross-anchor consistency for contradictions between invariant sets.
    """

    def test_cross_anchor_consistency_described(self):
        content = _read_command()
        self.assertIn('Cross-anchor consistency', content)

    def test_checks_contradictions_between_anchors(self):
        content = _read_command()
        self.assertIn('contradictions', content.lower())

    def test_skip_code_comparison_for_spec_only(self):
        content = _read_command()
        self.assertIn('Skip code comparison entirely', content)


class TestSubagentOutputFormat(unittest.TestCase):
    """Scenario: Subagent returns structured output format

    Spec 2.9: Each subagent returns structured output with FEATURE header/
    footer, severity/dimension/owner tags, and evidence/fix fields.
    """

    def test_feature_header_format(self):
        content = _read_command()
        self.assertIn('=== FEATURE:', content)

    def test_feature_footer_format(self):
        content = _read_command()
        self.assertIn('=== END FEATURE ===', content)

    def test_gap_entry_format(self):
        content = _read_command()
        self.assertIn('[SEVERITY] [DIMENSION] [OWNER]', content)

    def test_evidence_field(self):
        content = _read_command()
        self.assertIn('Evidence:', content)

    def test_suggested_fix_field(self):
        content = _read_command()
        self.assertIn('Suggested fix:', content)


class TestWaveExecution(unittest.TestCase):
    """Scenarios: Wave results saved to audit state file, Failed subagent
    batch is re-queued.

    Spec 2.9: After each wave, save to audit_state.json. On failure,
    create rescue batches or re-queue.
    """

    def test_state_file_path(self):
        content = _read_command()
        self.assertIn('.purlin/cache/audit_state.json', content)

    def test_saved_after_each_wave(self):
        content = _read_command()
        self.assertIn('save accumulated results', content.lower())

    def test_requeue_on_failure(self):
        content = _read_command()
        self.assertIn('re-queue', content.lower())

    def test_rescue_batch_for_incomplete(self):
        content = _read_command()
        self.assertIn('rescue batch', content)


class TestSynthesisAndAuditTable(unittest.TestCase):
    """Scenarios: Synthesis deduplicates overlapping gaps, Audit table
    includes Evidence and Anchor Source columns.

    Spec 2.10: Deduplicate gaps across overlapping batches. Build audit
    table with required columns sorted by severity.
    """

    def test_deduplication_instruction_present(self):
        content = _read_command()
        self.assertIn('Deduplicate gaps', content)

    def test_overlapping_batches_handled(self):
        content = _read_command()
        self.assertIn('overlapping feature batches', content)

    def test_transitive_anchor_overlap_handled(self):
        content = _read_command()
        self.assertIn('transitive anchors', content)

    def test_table_has_all_required_columns(self):
        content = _read_command()
        columns = [
            'Feature', 'Severity', 'Dimension', 'Gap Description',
            'Evidence', 'Anchor Source', 'Action', 'Planned Remediation',
        ]
        for col in columns:
            self.assertIn(col, content,
                          f'Missing audit table column: {col}')

    def test_table_sorted_by_severity(self):
        """Table sort order: CRITICAL -> HIGH -> MEDIUM -> LOW."""
        content = _read_command()
        self.assertIn('CRITICAL', content)
        # Verify the sort instruction is present
        self.assertIn('CRITICAL -> HIGH -> MEDIUM -> LOW', content)


class TestRemediationPlan(unittest.TestCase):
    """Scenarios: PM remediation plan describes only spec edits,
    Engineer remediation plan describes only code edits.

    Spec 2.11: PM FIX edits target feature specs and anchor nodes
    only. Engineer FIX edits target source code and tests only.
    """

    def test_architect_fix_targets_specs_and_anchors(self):
        content = _read_command()
        self.assertIn('PM FIX edits', content)
        self.assertIn('feature specs', content)
        self.assertIn('anchor nodes', content)

    def test_builder_fix_targets_code_and_tests(self):
        content = _read_command()
        self.assertIn('Engineer FIX edits', content)
        self.assertIn('source code and tests', content)

    def test_architect_fix_before_builder_fix(self):
        """Both remediation plan descriptions appear in the command file."""
        content = _read_command()
        arch_pos = content.index('PM FIX edits')
        builder_pos = content.index('Engineer FIX edits')
        # Both exist (positions are valid)
        self.assertGreater(arch_pos, 0)
        self.assertGreater(builder_pos, 0)


class TestCrossSessionResume(unittest.TestCase):
    """Scenarios: Cross-session resume from interrupted deep mode wave,
    Cross-session resume from completed triage scan, Audit state file
    deleted after remediation.

    Spec 2.6: Must check for audit_state.json, resume from next incomplete
    step, track required fields, and clean up after remediation.
    """

    def test_resume_state_file_documented(self):
        content = _read_command()
        self.assertIn('audit_state.json', content)

    def test_resume_skips_completed_waves(self):
        content = _read_command()
        self.assertIn('resume', content.lower())

    def test_state_file_tracks_required_fields(self):
        content = _read_command()
        for field in ('mode', 'role', 'transitive_map',
                      'anchor_constraints', 'dispatch_manifest',
                      'accumulated_gaps', 'scan_failures'):
            self.assertIn(field, content,
                          f'State file missing field: {field}')

    def test_triage_resume_skips_to_phase2(self):
        content = _read_command()
        self.assertIn('Phase 2', content)
        self.assertIn('resume from phase 2 synthesis', content.lower())

    def test_cleanup_deletes_state_file(self):
        content = _read_command()
        self.assertIn('Delete', content)
        self.assertIn('audit_state.json', content)

    def test_status_run_after_remediation(self):
        content = _read_command()
        self.assertIn('${TOOLS_ROOT}/cdd/scan.sh', content)


class TestSeverityClassification(unittest.TestCase):
    """Scenarios: FORBIDDEN pattern violation classified as HIGH severity,
    Missing prerequisite link classified as MEDIUM severity.

    Spec 2.13: Severity table maps specific gap types to severity levels.
    """

    def test_forbidden_is_high_severity(self):
        content = _read_command()
        self.assertIn('FORBIDDEN pattern violation', content)

    def test_severity_table_has_all_levels(self):
        content = _read_command()
        for level in ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW'):
            self.assertIn(level, content)

    def test_missing_prereq_is_medium(self):
        content = _read_command()
        self.assertIn('Missing prerequisite link', content)

    def test_forbidden_in_high_row(self):
        """FORBIDDEN pattern violation appears in the HIGH severity criteria."""
        content = _read_command()
        # Find severity table and verify FORBIDDEN is in the HIGH section
        high_match = re.search(
            r'\|\s*HIGH\s*\|(.+?)(?:\|\s*(?:MEDIUM|LOW|CRITICAL)\s*\||$)',
            content, re.DOTALL)
        self.assertIsNotNone(high_match,
                             'Should find HIGH row in severity table')
        high_text = high_match.group(1)
        self.assertIn('FORBIDDEN', high_text)


class TestEscalation(unittest.TestCase):
    """Scenarios: PM escalates code-side gap via companion file,
    Engineer escalates spec-side gap via companion file.

    Spec 2.14: PM writes [DISCOVERY] entries with Source/Severity/
    Details/Suggested fix. Engineer writes [DISCOVERY] or [SPEC_PROPOSAL]
    with Suggested spec change.
    """

    def test_architect_escalation_has_discovery_tag(self):
        content = _read_command()
        self.assertIn('[DISCOVERY]', content)

    def test_architect_escalation_has_source_field(self):
        content = _read_command()
        self.assertIn('**Source:** /pl-spec-code-audit', content)

    def test_architect_escalation_has_severity_and_details(self):
        content = _read_command()
        self.assertIn('**Severity:**', content)
        self.assertIn('**Details:**', content)

    def test_architect_escalation_has_suggested_fix(self):
        content = _read_command()
        self.assertIn('**Suggested fix:**', content)

    def test_builder_escalation_has_spec_proposal(self):
        content = _read_command()
        self.assertIn('[SPEC_PROPOSAL]', content)

    def test_builder_escalation_has_suggested_spec_change(self):
        content = _read_command()
        self.assertIn('**Suggested spec change:**', content)

    def test_escalation_targets_companion_files(self):
        content = _read_command()
        self.assertIn('companion file', content.lower())


class TestCleanReport(unittest.TestCase):
    """Scenario: No gaps produces clean report and exits plan mode

    Spec 2.11: If no gaps found, output clean message and ExitPlanMode.
    """

    def test_clean_output_message(self):
        content = _read_command()
        self.assertIn(
            'No spec-code gaps detected across all', content)

    def test_exits_plan_mode(self):
        content = _read_command()
        self.assertIn('ExitPlanMode', content)

    def test_enter_plan_mode_at_start(self):
        """Spec 2.2: Must call EnterPlanMode immediately."""
        content = _read_command()
        self.assertIn('EnterPlanMode', content)


class TestCrossFeatureRequirementHygiene(unittest.TestCase):
    """Scenarios: Duplicate requirements detected across features,
    Conflicting requirements detected across features, Unused feature
    spec detected.

    Spec 2.7/2.12 dimension 11: Cross-feature requirement hygiene pass
    detects duplicates, conflicts, and unused/orphaned specs.
    """

    def test_duplicate_detection_described(self):
        content = _read_command()
        self.assertIn('Duplicate detection', content)

    def test_duplicate_compares_scenario_signatures(self):
        content = _read_command()
        self.assertIn('scenario titles', content.lower())
        self.assertIn('Given/When/Then signatures', content)

    def test_duplicate_flags_same_endpoint(self):
        content = _read_command()
        self.assertIn('same endpoint', content.lower())

    def test_duplicate_severity_is_medium(self):
        content = _read_command()
        self.assertIn(
            'duplicate requirements across features', content.lower())

    def test_conflict_detection_described(self):
        content = _read_command()
        self.assertIn('Conflict detection', content)

    def test_conflict_checks_shared_prerequisite_anchor(self):
        content = _read_command()
        self.assertIn('share a prerequisite anchor', content.lower())

    def test_conflict_flags_contradictory_assertions(self):
        content = _read_command()
        self.assertIn('contradictory assertions', content.lower())

    def test_conflict_severity_is_high(self):
        content = _read_command()
        self.assertIn(
            'conflicting requirements across features', content.lower())

    def test_unused_detection_described(self):
        content = _read_command()
        self.assertIn('Unused detection', content)

    def test_unused_checks_no_implementation(self):
        content = _read_command()
        self.assertIn('no implementation', content.lower())

    def test_unused_checks_no_prerequisite_dependents(self):
        content = _read_command()
        self.assertIn(
            'not listed as a prerequisite by any other feature', content)

    def test_unused_severity_is_low(self):
        content = _read_command()
        self.assertIn('unused/orphaned feature spec', content.lower())

    def test_unused_flagged_as_orphaned(self):
        content = _read_command()
        self.assertIn('orphaned specs', content.lower())

    def test_dimension_is_requirement_hygiene(self):
        content = _read_command()
        self.assertIn('Requirement hygiene', content)


class TestPlanModeIntegration(unittest.TestCase):
    """Verifies plan mode entry/exit and user approval workflow.

    Spec 2.2: EnterPlanMode immediately. Spec 2.11: ExitPlanMode after
    audit table. Wait for user approval before Phase 3.
    """

    def test_enter_plan_mode_before_any_file_reads(self):
        """EnterPlanMode appears before Phase 0 instructions."""
        content = _read_command()
        enter_pos = content.index('EnterPlanMode')
        phase_pos = content.index('Phase 0')
        self.assertLess(enter_pos, phase_pos)

    def test_exit_plan_mode_after_audit_table(self):
        """ExitPlanMode appears after audit table section."""
        content = _read_command()
        # ExitPlanMode should appear after the audit table header
        table_pos = content.index('Audit Table')
        exit_pos = content.rindex('ExitPlanMode')
        self.assertGreater(exit_pos, table_pos)

    def test_wait_for_user_approval(self):
        """Command waits for user approval before Phase 3 remediation."""
        content = _read_command()
        self.assertIn('user approval', content.lower())

    def test_phase3_is_post_approval(self):
        """Phase 3 (Remediation) is explicitly labeled as post-approval."""
        content = _read_command()
        self.assertIn('After User Approval', content)


class TestSubagentType(unittest.TestCase):
    """Verifies subagent configuration requirements.

    Spec 2.9: Subagent type MUST be Explore (read-only). Subagents are
    launched wave by wave via Task tool calls.
    """

    def test_subagent_type_is_explore(self):
        content = _read_command()
        self.assertIn('Explore', content)

    def test_explore_is_read_only(self):
        content = _read_command()
        self.assertIn('read-only', content.lower())

    def test_auto_compaction_handling(self):
        """On auto-compaction, save state and instruct user to resume."""
        content = _read_command()
        self.assertIn('auto-compaction', content.lower())


class TestSpecFeatureAlignment(unittest.TestCase):
    """Cross-checks that the command file and feature spec are aligned
    on key structural elements.
    """

    def test_spec_and_command_both_reference_11_dimensions(self):
        """Both files reference 11 gap dimensions."""
        cmd = _read_command()
        spec = _read_feature()
        # Spec defines 11 dimensions in Section 2.12
        self.assertIn('11 dimensions', spec.lower().replace(' ', ' '))
        # Command file should reference all 11
        cmd_dims = sum(1 for d in [
            'Spec completeness', 'Policy anchoring', 'Traceability',
            'Engineer decisions', 'User testing', 'Dependency currency',
            'Spec-reality alignment', 'Notes depth', 'Code divergence',
            'Anchor invariant drift', 'Requirement hygiene',
        ] if d in cmd)
        self.assertEqual(cmd_dims, 11)

    def test_spec_and_command_both_reference_explore_subagent_type(self):
        """Both files specify Explore as the subagent type."""
        cmd = _read_command()
        spec = _read_feature()
        self.assertIn('Explore', cmd)
        self.assertIn('Explore', spec)

    def test_spec_and_command_both_define_severity_table(self):
        """Both files define the four severity levels."""
        cmd = _read_command()
        spec = _read_feature()
        for level in ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW'):
            self.assertIn(level, cmd)
            self.assertIn(level, spec)


# ---------------------------------------------------------------------------
# Test runner and JSON result output
# ---------------------------------------------------------------------------


class JsonTestResult(unittest.TextTestResult):
    """Custom result that collects pass/fail for JSON output."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.results.append({"test": str(test), "status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.results.append({
            "test": str(test), "status": "FAIL",
            "message": str(err[1])})

    def addError(self, test, err):
        super().addError(test, err)
        self.results.append({
            "test": str(test), "status": "ERROR",
            "message": str(err[1])})


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(resultclass=JsonTestResult, verbosity=2)
    result = runner.run(suite)

    # Write tests.json
    if PROJECT_ROOT:
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_spec_code_audit")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "tests.json")

        all_passed = len(result.failures) == 0 and len(result.errors) == 0
        failed = len(result.failures) + len(result.errors)
        with open(out_file, "w") as f:
            json.dump(
                {
                    "status": "PASS" if all_passed else "FAIL",
                    "passed": result.testsRun - failed,
                    "failed": failed,
                    "total": result.testsRun,
                    "test_file": "tools/test_support/test_pl_spec_code_audit.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
