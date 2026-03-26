#!/usr/bin/env python3
"""Tests for the /pl-spec-code-audit agent command.

Covers all 54 automated scenarios from features/pl_spec_code_audit.md.
The command is an agent skill defined in .claude/commands/pl-spec-code-audit.md.
Tests verify the command file content, structure, and referenced infrastructure.
"""
import json
import os
import re
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
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


class TestCommandFileExists(unittest.TestCase):
    """Prerequisite: the command file and feature spec exist."""

    def test_command_file_exists(self):
        self.assertTrue(os.path.isfile(COMMAND_FILE))

    def test_feature_file_exists(self):
        self.assertTrue(os.path.isfile(FEATURE_FILE))


class TestRoleGateRejectsNonArchitectBuilder(unittest.TestCase):
    """Scenario: Role gate rejects non-PM/Engineer invocation"""

    def test_command_contains_role_gate_message(self):
        content = _read_command()
        self.assertIn(
            'This command is for the PM or Engineer', content)

    def test_role_gate_appears_before_analysis(self):
        content = _read_command()
        gate_pos = content.index('PM or Engineer')
        phase_pos = content.index('Phase 0')
        self.assertLess(gate_pos, phase_pos)

    def test_role_gate_blocks_pm(self):
        """PM agents are blocked by the role gate (spec 2.1)."""
        content = _read_command()
        # The gate says "not operating as ... PM or ... Engineer"
        # which blocks QA and PM equally
        self.assertIn('not operating as', content.lower())
        self.assertIn('PM or', content)
        self.assertIn('Engineer', content)


class TestDefaultInvocationUsesTriageMode(unittest.TestCase):
    """Scenario: Default invocation uses triage mode"""

    def test_no_argument_defaults_to_triage(self):
        content = _read_command()
        self.assertIn('No argument or empty', content)
        self.assertIn('triage', content.lower())

    def test_triage_processes_in_agent(self):
        content = _read_command()
        self.assertIn('no subagents', content.lower())

    def test_triage_processes_all_features(self):
        content = _read_command()
        self.assertIn('ALL features in-agent', content)


class TestDeepFlagActivatesDeepMode(unittest.TestCase):
    """Scenario: Deep flag activates deep mode"""

    def test_deep_flag_documented(self):
        content = _read_command()
        self.assertIn('--deep', content)

    def test_deep_mode_uses_batches(self):
        content = _read_command()
        self.assertIn('batch', content.lower())

    def test_deep_mode_uses_waves(self):
        content = _read_command()
        self.assertIn('wave', content.lower())


class TestInvalidArgumentProducesError(unittest.TestCase):
    """Scenario: Invalid argument produces error"""

    def test_error_message_format(self):
        content = _read_command()
        self.assertIn("Error: Unknown argument", content)
        self.assertIn("Valid: --deep", content)

    def test_anything_else_aborts(self):
        content = _read_command()
        self.assertIn('Anything else', content)


class TestPathResolutionReadsToolsRoot(unittest.TestCase):
    """Scenario: Path resolution reads tools_root from config"""

    def test_reads_tools_root_from_config(self):
        content = _read_command()
        self.assertIn('tools_root', content)
        self.assertIn('.purlin/config.json', content)

    def test_uses_tools_root_variable(self):
        content = _read_command()
        self.assertIn('${TOOLS_ROOT}', content)

    def test_no_hardcoded_tools_path(self):
        content = _read_command()
        # After Path Resolution, tool invocations should use TOOLS_ROOT
        # Check that actual invocation lines use the variable
        invocations = re.findall(
            r'`\$\{TOOLS_ROOT\}/[^`]+`', content)
        self.assertGreater(len(invocations), 0,
                           'Should have tool invocations using ${TOOLS_ROOT}')

    def test_config_file_exists(self):
        self.assertTrue(os.path.isfile(CONFIG_FILE))

    def test_config_has_tools_root(self):
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        self.assertIn('tools_root', config)


class TestTransitivePrerequisiteMapWalksFullAncestorChain(unittest.TestCase):
    """Scenario: Transitive prerequisite map walks full ancestor chain"""

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


class TestAnchorConstraintCollectionExtractsForbiddenPatterns(
        unittest.TestCase):
    """Scenario: Anchor constraint collection extracts FORBIDDEN patterns"""

    def test_command_describes_forbidden_extraction(self):
        content = _read_command()
        self.assertIn('FORBIDDEN', content)
        self.assertIn('pattern', content.lower())

    def test_constraint_output_format(self):
        content = _read_command()
        self.assertIn('forbidden', content.lower())
        self.assertIn('invariants', content.lower())
        self.assertIn('constraints', content.lower())


class TestAnchorConstraintCollectionExtractsInvariants(unittest.TestCase):
    """Scenario: Anchor constraint collection extracts invariants"""

    def test_command_describes_invariant_extraction(self):
        content = _read_command()
        self.assertIn('invariant', content.lower())

    def test_command_reads_numbered_subsections(self):
        content = _read_command()
        self.assertIn('numbered', content.lower())


class TestTriageModeChecksSpecCompleteness(unittest.TestCase):
    """Scenario: Triage mode checks spec completeness across all gap
    dimensions"""

    def test_gap_dimensions_table_present(self):
        content = _read_command()
        self.assertIn('Gap Dimensions Table', content)

    def test_all_gap_dimensions_listed(self):
        content = _read_command()
        dimensions = [
            'Spec completeness', 'Policy anchoring', 'Traceability',
            'Engineer decisions', 'User testing', 'Dependency currency',
            'Spec-reality alignment', 'Notes depth', 'Code divergence',
            'Anchor invariant drift', 'Requirement hygiene',
            'Code ownership',
        ]
        for dim in dimensions:
            self.assertIn(dim, content,
                          f'Missing gap dimension: {dim}')


class TestTriageModePerformsLightCodeScanForForbiddenPatterns(
        unittest.TestCase):
    """Scenario: Triage mode performs light code scan for FORBIDDEN patterns"""

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


class TestTriageModeSkipsScenarioByScenarioComparison(unittest.TestCase):
    """Scenario: Triage mode skips scenario-by-scenario comparison"""

    def test_skip_instruction_present(self):
        content = _read_command()
        self.assertIn(
            'Skip scenario-by-scenario deep comparison', content)


class TestDeepModeClassifiesAnchorNodesIntoSpecOnlyTrack(unittest.TestCase):
    """Scenario: Deep mode classifies anchor nodes into spec-only track"""

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


class TestDeepModeBatchesFeaturesByScenarioCount(unittest.TestCase):
    """Scenario: Deep mode batches features by scenario count"""

    def test_scenario_range_per_batch(self):
        content = _read_command()
        self.assertIn('50-75 scenarios', content)

    def test_first_fit_decreasing(self):
        content = _read_command()
        self.assertIn('first-fit-decreasing', content)

    def test_max_features_per_batch(self):
        content = _read_command()
        self.assertIn('max 4-5 features per batch', content)


class TestDeepModeCreatesSoloBatchForLargeFeatures(unittest.TestCase):
    """Scenario: Deep mode creates solo batch for large features"""

    def test_solo_batch_rule(self):
        content = _read_command()
        self.assertIn('Solo batch', content)
        self.assertIn('50+ scenarios', content)


class TestDeepModeLimitsConcurrentSubagentsTo5PerWave(unittest.TestCase):
    """Scenario: Deep mode limits concurrent subagents to 5 per wave"""

    def test_wave_limit_described(self):
        content = _read_command()
        self.assertIn('up to 5 concurrent subagents', content)


class TestDeepModeSubagentsReceiveTransitiveConstraintPayload(
        unittest.TestCase):
    """Scenario: Deep mode subagents receive transitive constraint payload"""

    def test_payload_included_in_prompt(self):
        content = _read_command()
        self.assertIn('transitive prerequisite map', content)
        self.assertIn('anchor constraints', content)

    def test_subagents_dont_recompute(self):
        content = _read_command()
        self.assertIn("don't need to re-derive", content)


class TestDeepModeSubagentsPerformScenarioByScenarioComparison(
        unittest.TestCase):
    """Scenario: Deep mode subagents perform scenario-by-scenario comparison"""

    def test_scenario_comparison_protocol(self):
        content = _read_command()
        self.assertIn('Scenario-by-scenario comparison', content)

    def test_traces_to_code_path(self):
        content = _read_command()
        self.assertIn('Trace to the code path', content)

    def test_flags_contradictions(self):
        content = _read_command()
        self.assertIn('contradictions', content)


class TestSpecOnlySubagentsCheckCrossAnchorConsistency(unittest.TestCase):
    """Scenario: Spec-only subagents check cross-anchor consistency"""

    def test_cross_anchor_consistency_described(self):
        content = _read_command()
        self.assertIn('Cross-anchor consistency', content)

    def test_checks_contradictions_between_anchors(self):
        content = _read_command()
        self.assertIn('contradictions', content.lower())


class TestSubagentReturnsStructuredOutputFormat(unittest.TestCase):
    """Scenario: Subagent returns structured output format"""

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


class TestWaveResultsSavedToAuditStateFile(unittest.TestCase):
    """Scenario: Wave results saved to audit state file"""

    def test_state_file_path(self):
        content = _read_command()
        self.assertIn('.purlin/cache/audit_state.json', content)

    def test_saved_after_each_wave(self):
        content = _read_command()
        self.assertIn('save accumulated results', content.lower())


class TestFailedSubagentBatchIsRequeued(unittest.TestCase):
    """Scenario: Failed subagent batch is re-queued"""

    def test_requeue_on_failure(self):
        content = _read_command()
        self.assertIn('re-queue', content.lower())

    def test_rescue_batch_for_incomplete(self):
        content = _read_command()
        self.assertIn('rescue batch', content)


class TestSynthesisDeduplicatesOverlappingGaps(unittest.TestCase):
    """Scenario: Synthesis deduplicates overlapping gaps"""

    def test_deduplication_instruction_present(self):
        content = _read_command()
        self.assertIn('Deduplicate gaps', content)

    def test_overlapping_batches_handled(self):
        content = _read_command()
        self.assertIn('overlapping feature batches', content)

    def test_transitive_anchor_overlap_handled(self):
        content = _read_command()
        self.assertIn('transitive anchors', content)


class TestAuditTableIncludesEvidenceAndAnchorSourceColumns(unittest.TestCase):
    """Scenario: Audit table includes Evidence and Anchor Source columns"""

    def test_evidence_column_in_table(self):
        content = _read_command()
        self.assertIn('Evidence', content)

    def test_anchor_source_column_in_table(self):
        content = _read_command()
        self.assertIn('Anchor Source', content)

    def test_table_has_all_required_columns(self):
        content = _read_command()
        columns = [
            'Feature', 'Severity', 'Dimension', 'Gap Description',
            'Evidence', 'Anchor Source', 'Action', 'Planned Remediation',
        ]
        for col in columns:
            self.assertIn(col, content,
                          f'Missing audit table column: {col}')


class TestArchitectRemediationPlanDescribesOnlySpecEdits(unittest.TestCase):
    """Scenario: PM remediation plan describes only spec edits"""

    def test_architect_fix_targets_specs_and_anchors(self):
        content = _read_command()
        self.assertIn(
            'PM FIX edits', content)
        self.assertIn('feature specs', content)
        self.assertIn('anchor nodes', content)


class TestBuilderRemediationPlanDescribesOnlyCodeEdits(unittest.TestCase):
    """Scenario: Engineer remediation plan describes only code edits"""

    def test_builder_fix_targets_code_and_tests(self):
        content = _read_command()
        self.assertIn('Engineer FIX edits', content)
        self.assertIn('source code and tests', content)


class TestCrossSessionResumeFromInterruptedDeepModeWave(unittest.TestCase):
    """Scenario: Cross-session resume from interrupted deep mode wave"""

    def test_resume_state_file_documented(self):
        content = _read_command()
        self.assertIn('audit_state.json', content)

    def test_resume_skips_completed_waves(self):
        content = _read_command()
        self.assertIn('resume', content.lower())

    def test_state_file_tracks_required_fields(self):
        content = _read_command()
        for field in ('mode', 'role', 'timestamp',
                      'transitive_map', 'anchor_constraints',
                      'dispatch_manifest', 'accumulated_gaps',
                      'scan_failures', 'code_inventory',
                      'ownership_map_complete'):
            self.assertIn(field, content,
                          f'State file missing field: {field}')


class TestCrossSessionResumeFromCompletedTriageScan(unittest.TestCase):
    """Scenario: Cross-session resume from completed triage scan"""

    def test_triage_resume_skips_to_phase2(self):
        content = _read_command()
        self.assertIn('Phase 2', content)
        # Verify resume mentions skipping to synthesis
        self.assertIn('resume from phase 2 synthesis', content.lower())


class TestAuditStateFileDeletedAfterRemediation(unittest.TestCase):
    """Scenario: Audit state file deleted after remediation"""

    def test_cleanup_documented(self):
        content = _read_command()
        self.assertIn('Delete', content)
        self.assertIn('audit_state.json', content)

    def test_scan_run_after_remediation(self):
        content = _read_command()
        self.assertIn('${TOOLS_ROOT}/cdd/scan.sh', content)


class TestNoGapsProducesCleanReportAndExitsPlanMode(unittest.TestCase):
    """Scenario: No gaps produces clean report and exits plan mode"""

    def test_clean_output_message(self):
        content = _read_command()
        self.assertIn(
            'No spec-code gaps detected across all', content)

    def test_exits_plan_mode(self):
        content = _read_command()
        self.assertIn('ExitPlanMode', content)


class TestForbiddenPatternViolationClassifiedAsHighSeverity(
        unittest.TestCase):
    """Scenario: FORBIDDEN pattern violation classified as HIGH severity"""

    def test_forbidden_is_high_severity(self):
        content = _read_command()
        # Severity table should show FORBIDDEN -> HIGH
        self.assertIn('FORBIDDEN pattern violation', content)

    def test_severity_table_present(self):
        content = _read_command()
        self.assertIn('CRITICAL', content)
        self.assertIn('HIGH', content)
        self.assertIn('MEDIUM', content)
        self.assertIn('LOW', content)


class TestMissingPrerequisiteLinkClassifiedAsMediumSeverity(
        unittest.TestCase):
    """Scenario: Missing prerequisite link classified as MEDIUM severity"""

    def test_missing_prereq_is_medium(self):
        content = _read_command()
        # MEDIUM row should mention prerequisite
        self.assertIn('Missing prerequisite link', content)


class TestArchitectEscalatesCodeSideGapViaCompanionFile(unittest.TestCase):
    """Scenario: PM escalates code-side gap via companion file"""

    def test_architect_escalation_format(self):
        content = _read_command()
        self.assertIn('[DISCOVERY]', content)
        self.assertIn('**Source:** /pl-spec-code-audit', content)
        self.assertIn('**Severity:**', content)
        self.assertIn('**Details:**', content)
        self.assertIn('**Suggested fix:**', content)

    def test_architect_escalation_targets_companion(self):
        content = _read_command()
        self.assertIn('companion file', content.lower())


class TestBuilderEscalatesSpecSideGapViaCompanionFile(unittest.TestCase):
    """Scenario: Engineer escalates spec-side gap via companion file"""

    def test_builder_escalation_format(self):
        content = _read_command()
        self.assertIn('[SPEC_PROPOSAL]', content)

    def test_builder_escalation_targets_companion(self):
        content = _read_command()
        self.assertIn('**Suggested spec change:**', content)


class TestDuplicateRequirementsDetectedAcrossFeatures(unittest.TestCase):
    """Scenario: Duplicate requirements detected across features"""

    def test_cross_feature_duplicate_detection_described(self):
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
        # Severity table MEDIUM row should reference duplicate requirements
        self.assertIn(
            'duplicate requirements across features', content.lower())

    def test_dimension_is_requirement_hygiene(self):
        content = _read_command()
        self.assertIn('Requirement hygiene', content)


class TestConflictingRequirementsDetectedAcrossFeatures(unittest.TestCase):
    """Scenario: Conflicting requirements detected across features"""

    def test_cross_feature_conflict_detection_described(self):
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
        # Severity table HIGH row should reference conflicting requirements
        self.assertIn(
            'conflicting requirements across features', content.lower())


class TestUnusedFeatureSpecDetected(unittest.TestCase):
    """Scenario: Unused feature spec detected"""

    def test_cross_feature_unused_detection_described(self):
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
        # Severity table LOW row should reference orphaned specs
        self.assertIn('unused/orphaned feature spec', content.lower())

    def test_unused_flagged_as_orphaned(self):
        content = _read_command()
        self.assertIn('orphaned specs', content.lower())


class TestScopeConfirmationAutoDetectsCodeDirectories(unittest.TestCase):
    """Scenario: Scope confirmation auto-detects existing code directories"""

    def test_scope_confirmation_section_exists(self):
        content = _read_command()
        self.assertIn('Scope Confirmation', content)

    def test_auto_detects_common_patterns(self):
        content = _read_command()
        for pattern in ('src/', 'tools/', 'tests/', '.claude/commands/'):
            self.assertIn(pattern, content,
                          f'Missing auto-detect pattern: {pattern}')

    def test_only_existing_directories(self):
        content = _read_command()
        self.assertIn('exist on disk', content)


class TestConfigDefinedScopeOverridesAutoDetection(unittest.TestCase):
    """Scenario: Config-defined scope overrides auto-detection"""

    def test_audit_code_paths_config_key(self):
        content = _read_command()
        self.assertIn('audit_code_paths', content)

    def test_config_overrides_auto_detection(self):
        content = _read_command()
        self.assertIn('instead of auto-detection', content)


class TestUserAcceptsDefaultScope(unittest.TestCase):
    """Scenario: User accepts default scope"""

    def test_default_is_confirm(self):
        content = _read_command()
        self.assertIn('Default is confirm', content)

    def test_proceeds_after_confirmation(self):
        content = _read_command()
        self.assertIn('confirmed scope', content.lower())


class TestUserAdjustsScope(unittest.TestCase):
    """Scenario: User adjusts scope"""

    def test_accepts_additions_removals(self):
        content = _read_command()
        self.assertIn('additions/removals', content)

    def test_redisplays_and_reconfirms(self):
        content = _read_command()
        self.assertIn('re-display', content)
        self.assertIn('re-confirm', content)


class TestConfirmedScopeConstrainsTriageCodeScan(unittest.TestCase):
    """Scenario: Confirmed scope constrains triage code scan"""

    def test_scope_constrains_code_discovery(self):
        content = _read_command()
        self.assertIn(
            'confirmed scope constrains code discovery', content.lower())

    def test_light_code_scan_uses_confirmed_scope(self):
        content = _read_command()
        self.assertIn('within the confirmed scope', content.lower())


class TestCodeInventoryEnumeratesAllFiles(unittest.TestCase):
    """Scenario: Code inventory enumerates all files in confirmed scope"""

    def test_phase_05_section_exists(self):
        content = _read_command()
        self.assertIn('Phase 0.5', content)

    def test_enumerate_code_files_step(self):
        content = _read_command()
        self.assertIn('Step 0.5.1', content)
        self.assertIn('Enumerate Code Files', content)

    def test_code_extensions_listed(self):
        content = _read_command()
        for ext in ('.py', '.sh', '.js', '.ts'):
            self.assertIn(ext, content,
                          f'Missing code extension: {ext}')

    def test_output_includes_path_extension_size(self):
        content = _read_command()
        self.assertIn('path', content.lower())
        self.assertIn('extension', content.lower())
        self.assertIn('size_bytes', content)

    def test_md_files_in_claude_commands(self):
        content = _read_command()
        self.assertIn('.claude/commands/', content)
        self.assertIn('.md', content)


class TestOwnershipMapUsesCompanionToolLocation(unittest.TestCase):
    """Scenario: Ownership map uses companion Tool Location (H1)"""

    def test_h1_heuristic_described(self):
        content = _read_command()
        self.assertIn('H1', content)
        self.assertIn('Companion explicit reference', content)

    def test_h1_uses_tool_location(self):
        content = _read_command()
        self.assertIn('Tool Location', content)

    def test_h1_confidence_is_high(self):
        content = _read_command()
        # H1 row should show HIGH confidence
        self.assertIn('Companion explicit reference | HIGH', content)


class TestOwnershipMapUsesSpecPathReference(unittest.TestCase):
    """Scenario: Ownership map uses spec path reference (H2)"""

    def test_h2_heuristic_described(self):
        content = _read_command()
        self.assertIn('H2', content)
        self.assertIn('Spec explicit reference', content)

    def test_h2_checks_feature_spec(self):
        content = _read_command()
        self.assertIn('Feature spec', content)
        self.assertIn('mentions the file path', content)


class TestOwnershipMapUsesTestImportTracing(unittest.TestCase):
    """Scenario: Ownership map uses test import tracing (H3)"""

    def test_h3_heuristic_described(self):
        content = _read_command()
        self.assertIn('H3', content)
        self.assertIn('Test import trace', content)

    def test_h3_deep_mode_only(self):
        content = _read_command()
        self.assertIn('Deep mode only', content)

    def test_h3_checks_test_imports(self):
        content = _read_command()
        self.assertIn('imports or executes the code file', content)


class TestCommandFileMapsToFeatureByNaming(unittest.TestCase):
    """Scenario: Command file maps to feature by naming convention (H4)"""

    def test_h4_heuristic_described(self):
        content = _read_command()
        self.assertIn('H4', content)
        self.assertIn('Command-to-feature naming', content)

    def test_h4_dash_to_underscore(self):
        content = _read_command()
        self.assertIn('dash-to-underscore', content)

    def test_h4_maps_pl_prefix(self):
        content = _read_command()
        self.assertIn('pl-<name>.md', content)
        self.assertIn('pl_<name>.md', content)


class TestOrphanedCodeFileDetectedAsDimension12(unittest.TestCase):
    """Scenario: Orphaned code file detected and reported as dimension 12"""

    def test_orphaned_executable_classification(self):
        content = _read_command()
        self.assertIn('Orphaned executable', content)

    def test_orphaned_executable_severity_medium(self):
        content = _read_command()
        self.assertIn(
            'orphaned executable code with significant behavior', content.lower())

    def test_code_ownership_dimension_in_table(self):
        content = _read_command()
        self.assertIn('Code ownership', content)


class TestOrphanedSkillFileDetectedAsHighSeverity(unittest.TestCase):
    """Scenario: Orphaned skill file detected as HIGH severity"""

    def test_orphaned_skill_file_classification(self):
        content = _read_command()
        self.assertIn('Orphaned skill file', content)

    def test_orphaned_skill_file_severity_high(self):
        content = _read_command()
        self.assertIn(
            'orphaned skill file', content.lower())
        # Verify it appears in the HIGH severity row
        self.assertIn(
            'orphaned skill file (`.claude/commands/pl-*.md`', content)


class TestDeadCodeCandidateClassifiedAsLowSeverity(unittest.TestCase):
    """Scenario: Dead code candidate classified as LOW severity"""

    def test_dead_code_candidate_classification(self):
        content = _read_command()
        self.assertIn('Dead code candidate', content)

    def test_dead_code_severity_low(self):
        content = _read_command()
        self.assertIn(
            'dead code candidate (zero imports, zero owners)', content.lower())

    def test_dead_code_criteria(self):
        content = _read_command()
        self.assertIn('Zero imports from any file AND zero owners', content)


class TestSharedInfrastructureNotFlaggedAsOrphaned(unittest.TestCase):
    """Scenario: Shared infrastructure not flagged as orphaned"""

    def test_shared_infrastructure_classification(self):
        content = _read_command()
        self.assertIn('Shared infrastructure', content)

    def test_import_fan_in_threshold(self):
        content = _read_command()
        self.assertIn('3+ features', content)

    def test_shared_infra_severity_low(self):
        content = _read_command()
        self.assertIn(
            'shared infrastructure code (3+ importers, no dedicated spec)',
            content.lower())


class TestInfrastructureFilesExcludedFromGapReporting(unittest.TestCase):
    """Scenario: Infrastructure files excluded from gap reporting"""

    def test_infrastructure_file_classification(self):
        content = _read_command()
        self.assertIn('Infrastructure file', content)

    def test_known_patterns_listed(self):
        content = _read_command()
        for pattern in ('__init__.py', 'conftest.py', 'setup.py'):
            self.assertIn(pattern, content,
                          f'Missing infrastructure pattern: {pattern}')

    def test_excluded_from_gap_reporting(self):
        content = _read_command()
        self.assertIn(
            'auto-excluded from gap reporting', content.lower())


class TestTriageModeReportsOrphanCountAsSummaryOnly(unittest.TestCase):
    """Scenario: Triage mode reports orphan count as summary only"""

    def test_triage_lightweight_inventory(self):
        content = _read_command()
        self.assertIn('Lightweight code inventory', content)

    def test_summary_not_per_file(self):
        content = _read_command()
        self.assertIn('summary line', content.lower())
        self.assertIn('not per-file entries', content.lower())

    def test_top_3_by_severity(self):
        content = _read_command()
        self.assertIn('top-3 by severity', content)

    def test_triage_uses_limited_heuristics(self):
        content = _read_command()
        self.assertIn('H1, H2, H4, and H5', content)


class TestOrphanScanSubagentExtractsFunctionSignatures(unittest.TestCase):
    """Scenario: Orphan scan subagent extracts function signatures in deep
    mode"""

    def test_orphan_scan_protocol_exists(self):
        content = _read_command()
        self.assertIn('Orphan Scan Subagent Protocol', content)

    def test_extracts_public_functions(self):
        content = _read_command()
        self.assertIn('public functions', content)

    def test_orphan_header_format(self):
        content = _read_command()
        self.assertIn('=== ORPHAN:', content)

    def test_orphan_footer_format(self):
        content = _read_command()
        self.assertIn('=== END ORPHAN ===', content)

    def test_nearest_feature_suggestion(self):
        content = _read_command()
        self.assertIn('nearest feature', content.lower())


class TestDeepModeFillsAllSubagentSlotsPerWave(unittest.TestCase):
    """Scenario: Deep mode fills all subagent slots per wave"""

    def test_aggressive_parallelism_mandate(self):
        content = _read_command()
        self.assertIn('Aggressive parallelism mandate', content)

    def test_all_5_slots_filled(self):
        content = _read_command()
        self.assertIn('All 5 subagent slots per wave MUST be filled', content)

    def test_tracks_mixed_freely(self):
        content = _read_command()
        self.assertIn('mixed freely within the same wave', content)

    def test_orphan_scan_track_described(self):
        content = _read_command()
        self.assertIn('Orphan scan track', content)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    failed = len(result.failures) + len(result.errors)
    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, 'tests.json'), 'w') as f:
        json.dump({
            'status': 'PASS' if result.wasSuccessful() else 'FAIL',
            'passed': result.testsRun - failed,
            'failed': failed,
            'total': result.testsRun,
        }, f)
    sys.exit(0 if result.wasSuccessful() else 1)
