#!/usr/bin/env python3
"""Unit tests for the Critic Quality Gate Tool.

Covers all automated scenarios from features/critic_tool.md.
Outputs test results to tests/critic_tool/tests.json.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure we can import sibling modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from traceability import (
    extract_keywords,
    extract_test_functions,
    extract_bash_test_scenarios,
    extract_test_entries,
    extract_generic_test_entry,
    match_scenario_to_tests,
    parse_traceability_overrides,
    run_traceability,
    discover_test_files,
)
from policy_check import (
    discover_forbidden_patterns,
    get_feature_prerequisites,
    discover_implementation_files,
    scan_file_for_violations,
    run_policy_check,
)
from critic import (
    parse_sections,
    parse_scenarios,
    get_implementation_notes,
    resolve_impl_notes,
    get_user_testing_section,
    is_policy_file,
    check_section_completeness,
    check_scenario_classification,
    check_policy_anchoring,
    check_prerequisite_integrity,
    check_gherkin_quality,
    run_spec_gate,
    check_structural_completeness,
    check_builder_decisions,
    check_logic_drift,
    run_user_testing_audit,
    generate_action_items,
    generate_critic_json,
    generate_critic_report,
    _policy_exempt_implementation_gate,
    audit_untracked_files,
    compute_role_status,
    parse_builder_decisions,
    parse_visual_spec,
    validate_visual_references,
    compute_regression_set,
    _extract_scope_from_commit,
)
import logic_drift


# ===================================================================
# Traceability Engine Tests
# ===================================================================

class TestKeywordExtraction(unittest.TestCase):
    def test_strips_articles(self):
        kw = extract_keywords('The Bootstrap of a Consumer Project')
        self.assertNotIn('the', kw)
        self.assertNotIn('a', kw)
        self.assertNotIn('of', kw)

    def test_strips_prepositions_conjunctions(self):
        kw = extract_keywords('Send data from X to Y and log via API')
        for word in ('from', 'to', 'and', 'via'):
            self.assertNotIn(word, kw)

    def test_keeps_meaningful_words(self):
        kw = extract_keywords('Bootstrap Consumer Project')
        self.assertIn('bootstrap', kw)
        self.assertIn('consumer', kw)
        self.assertIn('project', kw)

    def test_lowercase(self):
        kw = extract_keywords('Spec Gate Section Completeness Check')
        for w in kw:
            self.assertEqual(w, w.lower())

    def test_empty_string(self):
        kw = extract_keywords('')
        self.assertEqual(kw, set())


class TestTraceabilityMatching(unittest.TestCase):
    def test_match_above_threshold(self):
        keywords = {'bootstrap', 'consumer', 'project'}
        functions = [{'name': 'test_bootstrap_consumer_project', 'body': ''}]
        matches = match_scenario_to_tests(keywords, functions)
        self.assertEqual(matches, ['test_bootstrap_consumer_project'])

    def test_no_match_below_threshold(self):
        keywords = {'bootstrap', 'consumer', 'project'}
        functions = [{'name': 'test_unrelated_feature', 'body': 'something else'}]
        matches = match_scenario_to_tests(keywords, functions)
        self.assertEqual(matches, [])

    def test_match_from_body(self):
        keywords = {'bootstrap', 'consumer'}
        functions = [{
            'name': 'test_something',
            'body': 'def test_something(): bootstrap consumer check',
        }]
        matches = match_scenario_to_tests(keywords, functions)
        self.assertEqual(matches, ['test_something'])


class TestTraceabilityOverrides(unittest.TestCase):
    def test_parse_override(self):
        text = '- traceability_override: "My Scenario" -> test_my_scenario'
        overrides = parse_traceability_overrides(text)
        self.assertEqual(overrides, {'My Scenario': 'test_my_scenario'})

    def test_no_overrides(self):
        overrides = parse_traceability_overrides('No overrides here.')
        self.assertEqual(overrides, {})


class TestExtractTestFunctions(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_extracts_functions(self):
        path = os.path.join(self.test_dir, 'test_sample.py')
        with open(path, 'w') as f:
            f.write(
                'def test_alpha():\n'
                '    assert True\n'
                '\n'
                'def test_beta():\n'
                '    assert False\n'
            )
        funcs = extract_test_functions(path)
        names = [f['name'] for f in funcs]
        self.assertEqual(names, ['test_alpha', 'test_beta'])

    def test_nonexistent_file(self):
        funcs = extract_test_functions('/nonexistent/file.py')
        self.assertEqual(funcs, [])


class TestRunTraceability(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        # Create a test file
        test_dir = os.path.join(self.root, 'tests', 'my_feature')
        os.makedirs(test_dir)
        with open(os.path.join(test_dir, 'test_my.py'), 'w') as f:
            f.write(
                'def test_spec_gate_section_completeness():\n'
                '    assert True\n'
                '\n'
                'def test_spec_gate_missing_section():\n'
                '    assert True\n'
            )

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_full_coverage(self):
        scenarios = [
            {'title': 'Spec Gate Section Completeness Check', 'is_manual': False},
            {'title': 'Spec Gate Missing Section', 'is_manual': False},
        ]
        result = run_traceability(
            scenarios, self.root, 'my_feature', tools_root='tools'
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['coverage'], 1.0)

    def test_manual_exempt(self):
        scenarios = [
            {'title': 'Manual Scenario Check', 'is_manual': True},
        ]
        result = run_traceability(
            scenarios, self.root, 'my_feature', tools_root='tools'
        )
        self.assertEqual(result['status'], 'PASS')

    def test_gap_detection(self):
        scenarios = [
            {'title': 'Spec Gate Section Completeness Check', 'is_manual': False},
            {'title': 'Totally Unrelated Unique Xyzzy Scenario', 'is_manual': False},
        ]
        result = run_traceability(
            scenarios, self.root, 'my_feature', tools_root='tools'
        )
        self.assertIn(result['status'], ('WARN', 'FAIL'))
        self.assertGreater(len(result['unmatched']), 0)


# ===================================================================
# Policy Check Tests
# ===================================================================

class TestForbiddenPatternDiscovery(unittest.TestCase):
    def setUp(self):
        self.features_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.features_dir)

    def test_discovers_forbidden(self):
        path = os.path.join(self.features_dir, 'arch_test.md')
        with open(path, 'w') as f:
            f.write('# Policy\n\nFORBIDDEN: hardcoded_port\n')
        patterns = discover_forbidden_patterns(self.features_dir)
        self.assertIn('arch_test.md', patterns)
        self.assertEqual(patterns['arch_test.md'][0]['pattern'], 'hardcoded_port')

    def test_skips_non_arch_files(self):
        path = os.path.join(self.features_dir, 'regular_feature.md')
        with open(path, 'w') as f:
            f.write('FORBIDDEN: should_be_ignored\n')
        patterns = discover_forbidden_patterns(self.features_dir)
        self.assertEqual(patterns, {})

    def test_empty_dir(self):
        patterns = discover_forbidden_patterns(self.features_dir)
        self.assertEqual(patterns, {})


class TestPrerequisiteParsing(unittest.TestCase):
    def test_extracts_arch_prereq(self):
        content = '> Prerequisite: features/arch_critic_policy.md\n'
        prereqs = get_feature_prerequisites(content)
        self.assertIn('arch_critic_policy.md', prereqs)

    def test_no_prereqs(self):
        content = '# Feature without prereqs\n'
        prereqs = get_feature_prerequisites(content)
        self.assertEqual(prereqs, [])


class TestPolicyViolationScanning(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_finds_violation(self):
        fpath = os.path.join(self.test_dir, 'code.py')
        with open(fpath, 'w') as f:
            f.write('PORT = 8086  # hardcoded_port\n')
        violations = scan_file_for_violations(fpath, ['hardcoded_port'])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]['pattern'], 'hardcoded_port')

    def test_no_violation(self):
        fpath = os.path.join(self.test_dir, 'clean.py')
        with open(fpath, 'w') as f:
            f.write('PORT = config.get("port")\n')
        violations = scan_file_for_violations(fpath, ['hardcoded_port'])
        self.assertEqual(violations, [])

    def test_regex_pattern(self):
        fpath = os.path.join(self.test_dir, 'code.py')
        with open(fpath, 'w') as f:
            f.write('import os\neval("code")\n')
        violations = scan_file_for_violations(fpath, [r'eval\('])
        self.assertEqual(len(violations), 1)


class TestRunPolicyCheck(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        # Create an arch policy with FORBIDDEN pattern
        with open(os.path.join(self.features_dir, 'arch_test.md'), 'w') as f:
            f.write('# Policy\n\nFORBIDDEN: hardcoded_port\n')
        # Create tool directory with implementation file
        tool_dir = os.path.join(self.root, 'tools', 'my')
        os.makedirs(tool_dir)
        with open(os.path.join(tool_dir, 'impl.py'), 'w') as f:
            f.write('PORT = 8086  # hardcoded_port\n')

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_violation_detected(self):
        content = '> Prerequisite: features/arch_test.md\n'
        result = run_policy_check(
            content, self.root, 'my_feature',
            features_dir=self.features_dir, tools_root='tools',
        )
        self.assertEqual(result['status'], 'FAIL')
        self.assertGreater(len(result['violations']), 0)

    def test_no_prereqs_pass(self):
        content = '# Feature without policy\n'
        result = run_policy_check(
            content, self.root, 'my_feature',
            features_dir=self.features_dir, tools_root='tools',
        )
        self.assertEqual(result['status'], 'PASS')


# ===================================================================
# Spec Gate Tests (Scenarios from spec)
# ===================================================================

COMPLETE_FEATURE = """\
# Feature: Test Feature

> Label: "Tool: Test"
> Category: "Testing"
> Prerequisite: features/arch_critic_policy.md

## 1. Overview
This is the overview.

## 2. Requirements
These are the requirements.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Test Something
    Given a precondition
    When an action happens
    Then a result occurs

### Manual Scenarios (Human Verification Required)

#### Scenario: Visual Check
    Given the UI is running
    When the user looks
    Then they see something

## 4. Implementation Notes
* Some implementation note here.
"""

INCOMPLETE_FEATURE = """\
# Feature: Incomplete Feature

> Label: "Tool: Incomplete"

## 1. Overview
This is the overview.
"""


class TestSpecGateSectionCompleteness(unittest.TestCase):
    """Scenario: Spec Gate Section Completeness Check"""

    def test_all_sections_present(self):
        sections = parse_sections(COMPLETE_FEATURE)
        result = check_section_completeness(COMPLETE_FEATURE, sections)
        self.assertEqual(result['status'], 'PASS')

    def test_missing_requirements(self):
        sections = parse_sections(INCOMPLETE_FEATURE)
        result = check_section_completeness(INCOMPLETE_FEATURE, sections)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('Requirements', result['detail'])

    def test_empty_impl_notes_warns(self):
        content = COMPLETE_FEATURE.replace(
            '* Some implementation note here.', ''
        )
        sections = parse_sections(content)
        result = check_section_completeness(content, sections)
        self.assertEqual(result['status'], 'WARN')


class TestSpecGateMissingSection(unittest.TestCase):
    """Scenario: Spec Gate Missing Section"""

    def test_missing_section_causes_fail(self):
        sections = parse_sections(INCOMPLETE_FEATURE)
        result = check_section_completeness(INCOMPLETE_FEATURE, sections)
        self.assertEqual(result['status'], 'FAIL')


class TestSpecGatePolicyAnchoring(unittest.TestCase):
    """Scenario: Spec Gate Policy Anchoring"""

    def test_has_policy_prereq(self):
        result = check_policy_anchoring(COMPLETE_FEATURE, 'test_feature.md')
        self.assertEqual(result['status'], 'PASS')

    def test_no_prereq_on_non_policy(self):
        content = '# Feature: No Prereq\n\n## Overview\n'
        result = check_policy_anchoring(content, 'test_feature.md')
        self.assertEqual(result['status'], 'WARN')
        self.assertIn('No prerequisite link found', result['detail'])

    def test_policy_file_exempt(self):
        content = '# Policy: Test\n'
        result = check_policy_anchoring(content, 'arch_test.md')
        self.assertEqual(result['status'], 'PASS')

    def test_design_anchor_node_exempt(self):
        content = '# Design: Test\n'
        result = check_policy_anchoring(content, 'design_test.md')
        self.assertEqual(result['status'], 'PASS')

    def test_policy_prefix_anchor_node_exempt(self):
        content = '# Policy: Test\n'
        result = check_policy_anchoring(content, 'policy_critic.md')
        self.assertEqual(result['status'], 'PASS')


class TestSpecGatePrerequisiteIntegrity(unittest.TestCase):
    """Scenario: Spec Gate Prerequisite Integrity"""

    def setUp(self):
        self.features_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.features_dir)

    def test_existing_prereqs_pass(self):
        with open(os.path.join(self.features_dir, 'arch_test.md'), 'w') as f:
            f.write('# Policy\n')
        content = '> Prerequisite: arch_test.md\n'
        result = check_prerequisite_integrity(content, self.features_dir)
        self.assertEqual(result['status'], 'PASS')

    def test_missing_prereq_fails(self):
        content = '> Prerequisite: arch_nonexistent.md\n'
        result = check_prerequisite_integrity(content, self.features_dir)
        self.assertEqual(result['status'], 'FAIL')


class TestSpecGateGherkinQuality(unittest.TestCase):
    """Scenarios: Gherkin Quality"""

    def test_complete_scenarios(self):
        scenarios = parse_scenarios(COMPLETE_FEATURE)
        result = check_gherkin_quality(scenarios)
        self.assertEqual(result['status'], 'PASS')

    def test_incomplete_scenario(self):
        content = """\
## 3. Scenarios

### Automated Scenarios

#### Scenario: No Steps
    This scenario has no Gherkin steps.
"""
        scenarios = parse_scenarios(content)
        result = check_gherkin_quality(scenarios)
        self.assertEqual(result['status'], 'WARN')


class TestSpecGateFullRun(unittest.TestCase):
    """Scenario: Full Spec Gate run"""

    def setUp(self):
        self.features_dir = tempfile.mkdtemp()
        with open(os.path.join(self.features_dir, 'arch_critic_policy.md'), 'w') as f:
            f.write('# Policy\n')

    def tearDown(self):
        shutil.rmtree(self.features_dir)

    def test_complete_feature_not_fail(self):
        result = run_spec_gate(COMPLETE_FEATURE, 'test_feature.md', self.features_dir)
        self.assertNotEqual(result['status'], 'FAIL')

    def test_incomplete_feature_fails(self):
        result = run_spec_gate(INCOMPLETE_FEATURE, 'test_feature.md', self.features_dir)
        self.assertEqual(result['status'], 'FAIL')


# ===================================================================
# Implementation Gate Tests
# ===================================================================

class TestStructuralCompleteness(unittest.TestCase):
    """Scenario: Structural completeness check"""

    def setUp(self):
        self.orig_tests_dir = None

    def test_missing_tests_json_fails(self):
        import critic
        orig = critic.TESTS_DIR
        critic.TESTS_DIR = tempfile.mkdtemp()
        try:
            result = check_structural_completeness('nonexistent_feature')
            self.assertEqual(result['status'], 'FAIL')
        finally:
            shutil.rmtree(critic.TESTS_DIR)
            critic.TESTS_DIR = orig

    def test_passing_tests_json(self):
        import critic
        orig = critic.TESTS_DIR
        critic.TESTS_DIR = tempfile.mkdtemp()
        try:
            test_dir = os.path.join(critic.TESTS_DIR, 'my_feature')
            os.makedirs(test_dir)
            with open(os.path.join(test_dir, 'tests.json'), 'w') as f:
                json.dump({'status': 'PASS'}, f)
            result = check_structural_completeness('my_feature')
            self.assertEqual(result['status'], 'PASS')
        finally:
            shutil.rmtree(critic.TESTS_DIR)
            critic.TESTS_DIR = orig

    def test_failing_tests_json(self):
        import critic
        orig = critic.TESTS_DIR
        critic.TESTS_DIR = tempfile.mkdtemp()
        try:
            test_dir = os.path.join(critic.TESTS_DIR, 'my_feature')
            os.makedirs(test_dir)
            with open(os.path.join(test_dir, 'tests.json'), 'w') as f:
                json.dump({'status': 'FAIL'}, f)
            result = check_structural_completeness('my_feature')
            self.assertEqual(result['status'], 'WARN')
        finally:
            shutil.rmtree(critic.TESTS_DIR)
            critic.TESTS_DIR = orig


class TestBuilderDecisionAudit(unittest.TestCase):
    """Scenario: Implementation Gate Builder Decision Audit"""

    def test_autonomous_warns(self):
        notes = '* [AUTONOMOUS] Chose X over Y.\n* [CLARIFICATION] Interpreted Z.'
        result = check_builder_decisions(notes)
        self.assertEqual(result['status'], 'WARN')

    def test_deviation_fails(self):
        notes = '* [DEVIATION] Changed the protocol.'
        result = check_builder_decisions(notes)
        self.assertEqual(result['status'], 'FAIL')

    def test_discovery_fails(self):
        notes = '* [DISCOVERY] Found unstated requirement.'
        result = check_builder_decisions(notes)
        self.assertEqual(result['status'], 'FAIL')

    def test_clarification_only_passes(self):
        notes = '* [CLARIFICATION] Interpreted the spec as meaning X.'
        result = check_builder_decisions(notes)
        self.assertEqual(result['status'], 'PASS')

    def test_empty_notes_passes(self):
        result = check_builder_decisions('')
        self.assertEqual(result['status'], 'PASS')


class TestLogicDriftDisabled(unittest.TestCase):
    """Scenario: Logic Drift Engine Disabled"""

    def test_disabled_returns_warn(self):
        result = check_logic_drift()
        self.assertEqual(result['status'], 'WARN')
        self.assertIn('skipped', result['detail'].lower())


class TestLogicDriftEngine(unittest.TestCase):
    """Tests for the logic drift engine (run_logic_drift)."""

    def setUp(self):
        self.project_root = tempfile.mkdtemp()
        self.cache_dir = os.path.join(
            self.project_root, '.purlin', 'cache', 'logic_drift_cache',
        )
        self.pairs = [{
            'scenario_title': 'Test Scenario',
            'scenario_body': 'Given X\nWhen Y\nThen Z',
            'test_functions': [{
                'name': 'test_scenario',
                'body': 'def test_scenario():\n    assert True',
            }],
        }]

    def tearDown(self):
        shutil.rmtree(self.project_root, ignore_errors=True)

    @patch('logic_drift.HAS_ANTHROPIC', True)
    @patch('logic_drift.anthropic')
    def test_aligned_verdict(self, mock_anthropic_mod):
        mock_client = MagicMock()
        mock_anthropic_mod.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(
            text='{"verdict": "ALIGNED", "reasoning": "Test matches scenario"}'
        )]
        mock_client.messages.create.return_value = mock_response

        result = logic_drift.run_logic_drift(
            self.pairs, self.project_root, 'test', 'tools',
            'claude-sonnet-4-20250514',
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['pairs']), 1)
        self.assertEqual(result['pairs'][0]['verdict'], 'ALIGNED')
        self.assertEqual(result['pairs'][0]['scenario'], 'Test Scenario')
        self.assertEqual(result['pairs'][0]['test'], 'test_scenario')
        mock_client.messages.create.assert_called_once()

    @patch('logic_drift.HAS_ANTHROPIC', True)
    @patch('logic_drift.anthropic')
    def test_divergent_verdict(self, mock_anthropic_mod):
        mock_client = MagicMock()
        mock_anthropic_mod.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(
            text='{"verdict": "DIVERGENT", "reasoning": "Test is unrelated"}'
        )]
        mock_client.messages.create.return_value = mock_response

        result = logic_drift.run_logic_drift(
            self.pairs, self.project_root, 'test', 'tools',
            'claude-sonnet-4-20250514',
        )
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['pairs'][0]['verdict'], 'DIVERGENT')

    @patch('logic_drift.HAS_ANTHROPIC', True)
    @patch('logic_drift.anthropic')
    def test_cache_hit_no_api_call(self, mock_anthropic_mod):
        mock_client = MagicMock()
        mock_anthropic_mod.Anthropic.return_value = mock_client

        # Pre-populate cache at the resolved path
        scenario_body = self.pairs[0]['scenario_body']
        test_body = self.pairs[0]['test_functions'][0]['body']
        key = logic_drift._cache_key(scenario_body, test_body)
        os.makedirs(self.cache_dir, exist_ok=True)
        cache_file = os.path.join(self.cache_dir, f'{key}.json')
        with open(cache_file, 'w') as f:
            json.dump({
                'verdict': 'ALIGNED',
                'reasoning': 'Cached result',
            }, f)

        result = logic_drift.run_logic_drift(
            self.pairs, self.project_root, 'test', 'tools',
            'claude-sonnet-4-20250514',
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['pairs'][0]['verdict'], 'ALIGNED')
        self.assertEqual(result['pairs'][0]['reasoning'], 'Cached result')
        # API should NOT have been called
        mock_client.messages.create.assert_not_called()

    @patch('logic_drift.HAS_ANTHROPIC', False)
    def test_no_anthropic_graceful_skip(self):
        result = logic_drift.run_logic_drift(
            self.pairs, self.project_root, 'test', 'tools',
            'claude-sonnet-4-20250514',
        )
        self.assertEqual(result['status'], 'WARN')
        self.assertIn('not installed', result['detail'])
        self.assertEqual(result['pairs'], [])


class TestCheckLogicDriftEnabled(unittest.TestCase):
    """Integration test: check_logic_drift when LLM is enabled."""

    @patch('critic.discover_test_files')
    @patch('critic.extract_test_entries')
    @patch('critic.run_logic_drift')
    def test_enabled_calls_run_logic_drift(self, mock_drift,
                                           mock_extract, mock_discover):
        import critic
        orig_enabled = critic.LLM_ENABLED
        critic.LLM_ENABLED = True
        try:
            mock_discover.return_value = ['/some/test.py']
            mock_extract.return_value = [{
                'name': 'test_foo',
                'body': 'def test_foo(): pass',
            }]
            mock_drift.return_value = {
                'status': 'PASS',
                'pairs': [{
                    'scenario': 'Foo',
                    'test': 'test_foo',
                    'verdict': 'ALIGNED',
                    'reasoning': 'OK',
                }],
                'detail': '1/1 pairs ALIGNED',
            }

            scenarios = [{
                'title': 'Foo',
                'is_manual': False,
                'body': 'Given X\nWhen Y\nThen Z',
            }]
            traceability = {
                'matched': [{
                    'scenario': 'Foo',
                    'tests': ['test_foo'],
                    'via': 'keyword',
                }],
            }

            result = check_logic_drift(scenarios, traceability, 'test_feature')
            self.assertEqual(result['status'], 'PASS')
            mock_drift.assert_called_once()
            # Verify the pairs structure passed to run_logic_drift
            call_pairs = mock_drift.call_args[0][0]
            self.assertEqual(len(call_pairs), 1)
            self.assertEqual(call_pairs[0]['scenario_title'], 'Foo')
            self.assertEqual(call_pairs[0]['test_functions'][0]['name'], 'test_foo')
        finally:
            critic.LLM_ENABLED = orig_enabled


# ===================================================================
# User Testing Audit Tests
# ===================================================================

class TestUserTestingAudit(unittest.TestCase):
    """Scenarios: User Testing Discovery Audit + Clean User Testing"""

    def test_open_items(self):
        content = """\
## User Testing Discoveries

### [BUG] Something broken (Discovered: 2026-01-01)
- **Status:** OPEN

### [DISCOVERY] New behavior found (Discovered: 2026-01-02)
- **Status:** SPEC_UPDATED
"""
        result = run_user_testing_audit(content)
        self.assertEqual(result['status'], 'HAS_OPEN_ITEMS')
        self.assertEqual(result['bugs'], 1)
        self.assertEqual(result['discoveries'], 1)

    def test_clean_section(self):
        content = """\
## User Testing Discoveries
"""
        result = run_user_testing_audit(content)
        self.assertEqual(result['status'], 'CLEAN')
        self.assertEqual(result['bugs'], 0)
        self.assertEqual(result['discoveries'], 0)
        self.assertEqual(result['intent_drifts'], 0)

    def test_no_section(self):
        content = '# Feature\n\n## Overview\n'
        result = run_user_testing_audit(content)
        self.assertEqual(result['status'], 'CLEAN')

    def test_resolved_items_clean(self):
        content = """\
## User Testing Discoveries

### [BUG] Fixed the thing (Discovered: 2026-01-01)
- **Status:** RESOLVED
"""
        result = run_user_testing_audit(content)
        self.assertEqual(result['status'], 'CLEAN')
        self.assertEqual(result['bugs'], 1)

    def test_intent_drift_open(self):
        content = """\
## User Testing Discoveries

### [INTENT_DRIFT] Behavior is technically correct but misses intent (Discovered: 2026-01-01)
- **Status:** OPEN
"""
        result = run_user_testing_audit(content)
        self.assertEqual(result['status'], 'HAS_OPEN_ITEMS')
        self.assertEqual(result['intent_drifts'], 1)

    def test_status_keyword_in_prose_ignored(self):
        """Status Detection Constraint: OPEN in prose must not trigger HAS_OPEN_ITEMS."""
        content = """\
## User Testing Discoveries

### [BUG] Was open, now fixed (Discovered: 2026-01-01)
- **Observed Behavior:** This was OPEN for a while and SPEC_UPDATED too.
- **Status:** RESOLVED
"""
        result = run_user_testing_audit(content)
        self.assertEqual(result['status'], 'CLEAN')
        self.assertEqual(result['bugs'], 1)


# ===================================================================
# Output Tests
# ===================================================================

class TestCriticJsonOutput(unittest.TestCase):
    """Scenario: Per-Feature Critic JSON Output"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        self.feature_path = os.path.join(self.features_dir, 'test_feature.md')
        with open(self.feature_path, 'w') as f:
            f.write(COMPLETE_FEATURE)
        # Create the arch policy prereq
        with open(os.path.join(self.features_dir, 'arch_critic_policy.md'), 'w') as f:
            f.write('# Policy\n')

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_output_structure(self):
        import critic
        orig_features = critic.FEATURES_DIR
        orig_tests = critic.TESTS_DIR
        orig_root = critic.PROJECT_ROOT
        critic.FEATURES_DIR = self.features_dir
        critic.TESTS_DIR = os.path.join(self.root, 'tests')
        critic.PROJECT_ROOT = self.root
        try:
            data = generate_critic_json(self.feature_path)
            self.assertIn('generated_at', data)
            self.assertIn('feature_file', data)
            self.assertIn('spec_gate', data)
            self.assertIn('implementation_gate', data)
            self.assertIn('user_testing', data)
            self.assertIn('status', data['spec_gate'])
            self.assertIn('checks', data['spec_gate'])
            self.assertIn('status', data['implementation_gate'])
            self.assertIn('checks', data['implementation_gate'])
        finally:
            critic.FEATURES_DIR = orig_features
            critic.TESTS_DIR = orig_tests
            critic.PROJECT_ROOT = orig_root


class TestAggregateReport(unittest.TestCase):
    """Scenario: Aggregate Report Generation"""

    def test_report_has_summary_table(self):
        results = [{
            'feature_file': 'features/test.md',
            'spec_gate': {'status': 'PASS', 'checks': {}},
            'implementation_gate': {
                'status': 'WARN',
                'checks': {
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 1, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                    },
                    'policy_adherence': {'status': 'PASS', 'violations': []},
                    'traceability': {'status': 'PASS', 'coverage': 1.0, 'detail': 'OK'},
                },
            },
            'user_testing': {
                'status': 'CLEAN',
                'bugs': 0,
                'discoveries': 0,
                'intent_drifts': 0,
            },
        }]
        report = generate_critic_report(results)
        self.assertIn('# Critic Quality Gate Report', report)
        self.assertIn('| Feature |', report)
        self.assertIn('features/test.md', report)
        self.assertIn('## Builder Decision Audit', report)
        self.assertIn('## Policy Violations', report)
        self.assertIn('## Traceability Gaps', report)
        self.assertIn('## Open User Testing Items', report)

    def test_report_shows_violations(self):
        results = [{
            'feature_file': 'features/bad.md',
            'spec_gate': {'status': 'PASS', 'checks': {}},
            'implementation_gate': {
                'status': 'FAIL',
                'checks': {
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                    },
                    'policy_adherence': {
                        'status': 'FAIL',
                        'violations': [{
                            'pattern': 'hardcoded_port',
                            'file': 'tools/test/code.py',
                            'line': 5,
                        }],
                    },
                    'traceability': {'status': 'PASS', 'coverage': 1.0, 'detail': 'OK'},
                },
            },
            'user_testing': {
                'status': 'CLEAN',
                'bugs': 0,
                'discoveries': 0,
                'intent_drifts': 0,
            },
        }]
        report = generate_critic_report(results)
        self.assertIn('hardcoded_port', report)


# ===================================================================
# Scenario Parsing Tests
# ===================================================================

class TestScenarioParsing(unittest.TestCase):
    def test_parses_automated_and_manual(self):
        scenarios = parse_scenarios(COMPLETE_FEATURE)
        automated = [s for s in scenarios if not s['is_manual']]
        manual = [s for s in scenarios if s['is_manual']]
        self.assertEqual(len(automated), 1)
        self.assertEqual(len(manual), 1)
        self.assertEqual(automated[0]['title'], 'Test Something')
        self.assertEqual(manual[0]['title'], 'Visual Check')

    def test_scenario_body_has_gherkin(self):
        scenarios = parse_scenarios(COMPLETE_FEATURE)
        auto = scenarios[0]
        self.assertIn('Given', auto['body'])
        self.assertIn('When', auto['body'])
        self.assertIn('Then', auto['body'])


class TestScenarioClassification(unittest.TestCase):
    """Scenario: Spec Gate Scenario Classification"""

    def test_both_subsections(self):
        scenarios = parse_scenarios(COMPLETE_FEATURE)
        result = check_scenario_classification(scenarios)
        self.assertEqual(result['status'], 'PASS')

    def test_only_automated(self):
        content = """\
## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Only
    Given something
    When action
    Then result
"""
        scenarios = parse_scenarios(content)
        result = check_scenario_classification(scenarios)
        self.assertEqual(result['status'], 'WARN')

    def test_no_scenarios(self):
        result = check_scenario_classification([])
        self.assertEqual(result['status'], 'FAIL')

    def test_explicit_none_manual_passes(self):
        """Scenario: Scenario Classification Explicit None for Manual"""
        content = """\
## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Only
    Given something
    When action
    Then result

### Manual Scenarios (Human Verification Required)

None
"""
        scenarios = parse_scenarios(content)
        result = check_scenario_classification(scenarios, content)
        self.assertEqual(result['status'], 'PASS')
        self.assertIn('None', result['detail'])

    def test_only_automated_no_explicit_none_still_warns(self):
        """Automated-only without explicit None declaration stays WARN."""
        content = """\
## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Only
    Given something
    When action
    Then result
"""
        scenarios = parse_scenarios(content)
        result = check_scenario_classification(scenarios, content)
        self.assertEqual(result['status'], 'WARN')


class TestPolicyAnchoringNonPolicyPrereq(unittest.TestCase):
    """Scenario: Spec Gate Non-Policy Prerequisite"""

    def test_non_policy_prerequisite_passes(self):
        content = '> Prerequisite: features/submodule_bootstrap.md\n'
        result = check_policy_anchoring(content, 'submodule_sync.md')
        self.assertEqual(result['status'], 'PASS')
        self.assertIn('Grounded', result['detail'])

    def test_no_prerequisite_warns(self):
        """Scenario: Spec Gate No Prerequisite on Non-Policy"""
        content = '# Feature: Standalone\n'
        result = check_policy_anchoring(content, 'standalone_feature.md')
        self.assertEqual(result['status'], 'WARN')

    def test_arch_prerequisite_passes(self):
        content = '> Prerequisite: features/arch_critic_policy.md\n'
        result = check_policy_anchoring(content, 'critic_tool.md')
        self.assertEqual(result['status'], 'PASS')
        self.assertIn('Anchored', result['detail'])


# ===================================================================
# Integration: Full Spec Gate
# ===================================================================

class TestSpecGateIntegration(unittest.TestCase):
    """Integration test: full spec gate run with real-ish feature content."""

    def setUp(self):
        self.features_dir = tempfile.mkdtemp()
        with open(os.path.join(self.features_dir, 'arch_critic_policy.md'), 'w') as f:
            f.write('# Policy\n')

    def tearDown(self):
        shutil.rmtree(self.features_dir)

    def test_complete_feature_passes_spec_gate(self):
        result = run_spec_gate(COMPLETE_FEATURE, 'test_feature.md', self.features_dir)
        self.assertEqual(result['status'], 'PASS')
        for check_name, check_result in result['checks'].items():
            self.assertIn(check_result['status'], ('PASS', 'WARN'))

    def test_policy_file_passes_anchoring(self):
        policy_content = """\
# Architectural Policy: Test

## 1. Overview
Policy overview.

## 2. Requirements
Policy requirements.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Policy Test
    Given a rule
    When checked
    Then enforced

### Manual Scenarios (Human Verification Required)

#### Scenario: Manual Policy
    Given a reviewer
    When they check
    Then policy holds

## Implementation Notes
* Some note.
"""
        result = run_spec_gate(policy_content, 'arch_test_policy.md', self.features_dir)
        anchoring = result['checks']['policy_anchoring']
        self.assertEqual(anchoring['status'], 'PASS')


# ===================================================================
# Policy File Tests (New Scenarios from spec commit 74aced2)
# ===================================================================

POLICY_FILE_CONTENT = """\
# Architectural Policy: Test Policy

> Label: "Policy: Test"
> Category: "Quality Assurance"

## 1. Purpose
This policy defines test constraints.

## 2. Invariants

### 2.1 Some Invariant
All features MUST do something.

## 3. Configuration
Some config info.

## Implementation Notes
* This policy governs test constraints.
"""

POLICY_FILE_NO_PURPOSE = """\
# Architectural Policy: Incomplete

> Label: "Policy: Incomplete"

## 2. Invariants

### 2.1 Some Invariant
All features MUST do something.
"""


class TestSpecGatePolicyFileReducedEvaluation(unittest.TestCase):
    """Scenario: Spec Gate Policy File Reduced Evaluation"""

    def setUp(self):
        self.features_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.features_dir)

    def test_policy_file_checks_purpose_invariants(self):
        result = run_spec_gate(
            POLICY_FILE_CONTENT, 'arch_test_policy.md', self.features_dir)
        sc = result['checks']['section_completeness']
        self.assertEqual(sc['status'], 'PASS')
        self.assertIn('Purpose', sc['detail'])
        self.assertIn('Invariants', sc['detail'])

    def test_policy_file_missing_purpose_fails(self):
        result = run_spec_gate(
            POLICY_FILE_NO_PURPOSE, 'arch_test_policy.md', self.features_dir)
        sc = result['checks']['section_completeness']
        self.assertEqual(sc['status'], 'FAIL')
        self.assertIn('Purpose', sc['detail'])

    def test_policy_file_scenario_classification_skipped(self):
        result = run_spec_gate(
            POLICY_FILE_CONTENT, 'arch_test_policy.md', self.features_dir)
        sc_class = result['checks']['scenario_classification']
        self.assertEqual(sc_class['status'], 'PASS')
        self.assertEqual(sc_class['detail'], 'N/A - anchor node')

    def test_policy_file_gherkin_quality_skipped(self):
        result = run_spec_gate(
            POLICY_FILE_CONTENT, 'arch_test_policy.md', self.features_dir)
        gq = result['checks']['gherkin_quality']
        self.assertEqual(gq['status'], 'PASS')
        self.assertEqual(gq['detail'], 'N/A - anchor node')

    def test_policy_file_overall_passes(self):
        result = run_spec_gate(
            POLICY_FILE_CONTENT, 'arch_test_policy.md', self.features_dir)
        self.assertEqual(result['status'], 'PASS')

    def test_policy_prefix_anchor_node_reduced_eval(self):
        result = run_spec_gate(
            POLICY_FILE_CONTENT, 'policy_critic.md', self.features_dir)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(
            result['checks']['scenario_classification']['detail'],
            'N/A - anchor node')
        self.assertEqual(
            result['checks']['gherkin_quality']['detail'],
            'N/A - anchor node')

    def test_design_prefix_anchor_node_reduced_eval(self):
        result = run_spec_gate(
            POLICY_FILE_CONTENT, 'design_visual.md', self.features_dir)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(
            result['checks']['scenario_classification']['detail'],
            'N/A - anchor node')


class TestImplementationGatePolicyFileExempt(unittest.TestCase):
    """Scenario: Implementation Gate Anchor Node Exempt"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        self.policy_path = os.path.join(
            self.features_dir, 'arch_test_policy.md')
        with open(self.policy_path, 'w') as f:
            f.write(POLICY_FILE_CONTENT)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_exempt_gate_returns_pass_no_decisions(self):
        gate = _policy_exempt_implementation_gate(
            POLICY_FILE_CONTENT, self.policy_path)
        self.assertEqual(gate['status'], 'PASS')

    def test_exempt_gate_non_decision_checks_pass(self):
        gate = _policy_exempt_implementation_gate(
            POLICY_FILE_CONTENT, self.policy_path)
        for check_name, check_result in gate['checks'].items():
            if check_name == 'builder_decisions':
                continue  # builder_decisions is audited, not exempt
            self.assertEqual(
                check_result['status'], 'PASS',
                f'{check_name} should be PASS for anchor node')

    def test_exempt_gate_non_decision_detail_says_exempt(self):
        gate = _policy_exempt_implementation_gate(
            POLICY_FILE_CONTENT, self.policy_path)
        for check_name, check_result in gate['checks'].items():
            if check_name == 'builder_decisions':
                continue  # builder_decisions is audited, not exempt
            self.assertIn(
                'N/A - anchor node exempt', check_result['detail'],
                f'{check_name} detail should say exempt')

    def test_exempt_gate_builder_decisions_audited(self):
        """Builder Decision Audit runs on anchor nodes (Section 2.3)."""
        gate = _policy_exempt_implementation_gate(
            POLICY_FILE_CONTENT, self.policy_path)
        bd = gate['checks']['builder_decisions']
        # No decision tags in POLICY_FILE_CONTENT → PASS with zero counts
        self.assertEqual(bd['status'], 'PASS')
        self.assertEqual(bd['summary']['DEVIATION'], 0)
        self.assertEqual(bd['summary']['DISCOVERY'], 0)

    def test_exempt_gate_detects_deviation_in_anchor_node(self):
        """Anchor node with [DEVIATION] entry → FAIL builder_decisions."""
        content = POLICY_FILE_CONTENT.rstrip() + \
            '\n* **[DEVIATION]** Test deviation (Severity: HIGH)\n'
        with open(self.policy_path, 'w') as f:
            f.write(content)
        gate = _policy_exempt_implementation_gate(content, self.policy_path)
        bd = gate['checks']['builder_decisions']
        self.assertEqual(bd['status'], 'FAIL')
        self.assertEqual(bd['summary']['DEVIATION'], 1)
        # Overall gate FAIL when builder_decisions FAIL
        self.assertEqual(gate['status'], 'FAIL')

    def test_exempt_gate_detects_discovery_in_anchor_node(self):
        """Anchor node with [DISCOVERY] entry → FAIL builder_decisions."""
        content = POLICY_FILE_CONTENT.rstrip() + \
            '\n* **[DISCOVERY]** Found unstated req (Severity: HIGH)\n'
        with open(self.policy_path, 'w') as f:
            f.write(content)
        gate = _policy_exempt_implementation_gate(content, self.policy_path)
        bd = gate['checks']['builder_decisions']
        self.assertEqual(bd['status'], 'FAIL')
        self.assertEqual(bd['summary']['DISCOVERY'], 1)

    def test_exempt_gate_autonomous_returns_warn(self):
        """Anchor node with [AUTONOMOUS] entry → WARN builder_decisions."""
        content = POLICY_FILE_CONTENT.rstrip() + \
            '\n* **[AUTONOMOUS]** Gap fill (Severity: WARN)\n'
        with open(self.policy_path, 'w') as f:
            f.write(content)
        gate = _policy_exempt_implementation_gate(content, self.policy_path)
        bd = gate['checks']['builder_decisions']
        self.assertEqual(bd['status'], 'WARN')
        # Overall gate still PASS (WARN doesn't escalate for anchor nodes)
        self.assertEqual(gate['status'], 'PASS')

    def test_generate_critic_json_uses_exempt_for_policy(self):
        import critic
        orig_features = critic.FEATURES_DIR
        orig_tests = critic.TESTS_DIR
        orig_root = critic.PROJECT_ROOT
        critic.FEATURES_DIR = self.features_dir
        critic.TESTS_DIR = os.path.join(self.root, 'tests')
        critic.PROJECT_ROOT = self.root
        try:
            data = generate_critic_json(self.policy_path)
            self.assertEqual(
                data['implementation_gate']['status'], 'PASS')
            for check_name, check_result in \
                    data['implementation_gate']['checks'].items():
                self.assertEqual(check_result['status'], 'PASS')
        finally:
            critic.FEATURES_DIR = orig_features
            critic.TESTS_DIR = orig_tests
            critic.PROJECT_ROOT = orig_root


class TestPolicyAnchoringMissingPrereqFile(unittest.TestCase):
    """Verify FAIL only when referenced prerequisite file doesn't exist."""

    def setUp(self):
        self.features_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.features_dir)

    def test_missing_prereq_file_fails_integrity(self):
        content = '> Prerequisite: features/arch_nonexistent.md\n'
        result = check_prerequisite_integrity(content, self.features_dir)
        self.assertEqual(result['status'], 'FAIL')

    def test_existing_prereq_file_passes_integrity(self):
        with open(os.path.join(self.features_dir, 'arch_test.md'), 'w') as f:
            f.write('# Policy\n')
        content = '> Prerequisite: arch_test.md\n'
        result = check_prerequisite_integrity(content, self.features_dir)
        self.assertEqual(result['status'], 'PASS')

    def test_no_prereq_warns_not_fails(self):
        content = '# Feature: No Prereq\n'
        result = check_policy_anchoring(content, 'some_feature.md')
        self.assertEqual(result['status'], 'WARN')


# ===================================================================
# Language-Agnostic Test File Discovery and Scenario Parsing Tests
# ===================================================================

class TestLanguageAgnosticTestFileDiscovery(unittest.TestCase):
    """Scenario: Language-Agnostic Test File Discovery"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.test_dir = os.path.join(self.root, 'tests', 'my_feature')
        os.makedirs(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_discovers_py_sh_and_ts(self):
        """Discovery includes .py, .sh, and .ts files based on 'test' prefix."""
        with open(os.path.join(self.test_dir, 'test_feature.py'), 'w') as f:
            f.write('def test_something(): pass\n')
        with open(os.path.join(self.test_dir, 'test_feature.sh'), 'w') as f:
            f.write('echo "[Scenario] Test Something"\n')
        with open(os.path.join(self.test_dir, 'test_feature.ts'), 'w') as f:
            f.write('describe("feature", () => { it("works", () => {}); });\n')
        files = discover_test_files(self.root, 'my_feature', tools_root='tools')
        extensions = {os.path.splitext(f)[1] for f in files}
        self.assertIn('.py', extensions)
        self.assertIn('.sh', extensions)
        self.assertIn('.ts', extensions)
        self.assertEqual(len(files), 3)

    def test_discovers_sh_only(self):
        with open(os.path.join(self.test_dir, 'test_feature.sh'), 'w') as f:
            f.write('echo "[Scenario] Test Something"\n')
        files = discover_test_files(self.root, 'my_feature', tools_root='tools')
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith('.sh'))

    def test_discovery_based_on_prefix_not_extension(self):
        """Any file starting with 'test' is discovered, regardless of extension."""
        with open(os.path.join(self.test_dir, 'test_feature.go'), 'w') as f:
            f.write('package main\n')
        with open(os.path.join(self.test_dir, 'test_feature.rs'), 'w') as f:
            f.write('#[test]\nfn it_works() {}\n')
        with open(os.path.join(self.test_dir, 'helper.py'), 'w') as f:
            f.write('# not a test file\n')
        files = discover_test_files(self.root, 'my_feature', tools_root='tools')
        basenames = {os.path.basename(f) for f in files}
        self.assertIn('test_feature.go', basenames)
        self.assertIn('test_feature.rs', basenames)
        self.assertNotIn('helper.py', basenames)


class TestBashScenarioExtraction(unittest.TestCase):
    """Scenario: Bash Scenario Keyword Matching"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_extracts_scenarios(self):
        path = os.path.join(self.test_dir, 'test_bootstrap.sh')
        with open(path, 'w') as f:
            f.write(
                '#!/bin/bash\n'
                'echo "[Scenario] Bootstrap Consumer Project"\n'
                'setup_sandbox\n'
                'run_test\n'
                '\n'
                'echo "[Scenario] Re-Bootstrap Existing Project"\n'
                'setup_again\n'
                'run_again\n'
            )
        entries = extract_bash_test_scenarios(path)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]['name'], 'Bootstrap Consumer Project')
        self.assertEqual(entries[1]['name'], 'Re-Bootstrap Existing Project')
        self.assertIn('setup_sandbox', entries[0]['body'])
        self.assertIn('setup_again', entries[1]['body'])

    def test_single_scenario(self):
        path = os.path.join(self.test_dir, 'test_single.sh')
        with open(path, 'w') as f:
            f.write(
                '#!/bin/bash\n'
                'echo "[Scenario] Single Test"\n'
                'do_something\n'
                'assert_result\n'
            )
        entries = extract_bash_test_scenarios(path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['name'], 'Single Test')
        self.assertIn('assert_result', entries[0]['body'])

    def test_no_scenarios(self):
        path = os.path.join(self.test_dir, 'test_empty.sh')
        with open(path, 'w') as f:
            f.write('#!/bin/bash\necho "Just a script"\n')
        entries = extract_bash_test_scenarios(path)
        self.assertEqual(entries, [])

    def test_nonexistent_file(self):
        entries = extract_bash_test_scenarios('/nonexistent/file.sh')
        self.assertEqual(entries, [])

    def test_keyword_matching_with_bash_entry(self):
        """Verify bash scenario entries can match feature scenario keywords."""
        keywords = {'bootstrap', 'consumer', 'project'}
        entries = [{'name': 'Bootstrap Consumer Project',
                    'body': 'echo "[Scenario] Bootstrap Consumer Project"\nsetup\n'}]
        matches = match_scenario_to_tests(keywords, entries)
        self.assertEqual(len(matches), 1)


class TestExtractTestEntries(unittest.TestCase):
    """Test the extract_test_entries dispatcher."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_dispatches_python(self):
        path = os.path.join(self.test_dir, 'test_sample.py')
        with open(path, 'w') as f:
            f.write('def test_alpha():\n    assert True\n')
        entries = extract_test_entries(path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['name'], 'test_alpha')

    def test_dispatches_bash(self):
        path = os.path.join(self.test_dir, 'test_sample.sh')
        with open(path, 'w') as f:
            f.write('echo "[Scenario] Alpha Test"\ndo_thing\n')
        entries = extract_test_entries(path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['name'], 'Alpha Test')

    def test_generic_fallback_for_unknown_extension(self):
        """Generic fallback produces single entry with basename and full content."""
        path = os.path.join(self.test_dir, 'test_sample.rb')
        with open(path, 'w') as f:
            f.write('# ruby test\nRSpec.describe "feature" do\n  it "works" do\n  end\nend\n')
        entries = extract_test_entries(path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['name'], 'test_sample')
        self.assertIn('ruby test', entries[0]['body'])
        self.assertIn('RSpec.describe', entries[0]['body'])

    def test_generic_fallback_ts_file(self):
        """Scenario: Generic Fallback Test Extraction — .ts file."""
        content = 'describe("feature", () => {\n  it("bootstrap consumer project", () => {\n    expect(true).toBe(true);\n  });\n});\n'
        path = os.path.join(self.test_dir, 'test_feature.ts')
        with open(path, 'w') as f:
            f.write(content)
        entries = extract_test_entries(path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['name'], 'test_feature')
        self.assertEqual(entries[0]['body'], content)

    def test_generic_fallback_keyword_matching(self):
        """Generic fallback entries participate in keyword matching."""
        content = 'describe("bootstrap consumer project", () => { it("works", () => {}); });\n'
        path = os.path.join(self.test_dir, 'test_feature.ts')
        with open(path, 'w') as f:
            f.write(content)
        entries = extract_test_entries(path)
        keywords = {'bootstrap', 'consumer', 'project'}
        matches = match_scenario_to_tests(keywords, entries)
        self.assertEqual(len(matches), 1)

    def test_generic_fallback_nonexistent_file(self):
        entries = extract_generic_test_entry('/nonexistent/file.ts')
        self.assertEqual(entries, [])


# ===================================================================
# Action Item Generation Tests
# ===================================================================

class TestActionItemsArchitect(unittest.TestCase):
    """Scenario: Architect Action Items from Spec Gaps"""

    def test_spec_fail_generates_high_item(self):
        result = {
            'feature_file': 'features/test.md',
            'spec_gate': {
                'status': 'FAIL',
                'checks': {
                    'section_completeness': {
                        'status': 'FAIL',
                        'detail': 'Missing sections: Requirements.',
                    },
                    'scenario_classification': {'status': 'PASS', 'detail': 'OK'},
                    'policy_anchoring': {'status': 'PASS', 'detail': 'OK'},
                    'prerequisite_integrity': {'status': 'PASS', 'detail': 'OK'},
                    'gherkin_quality': {'status': 'PASS', 'detail': 'OK'},
                },
            },
            'implementation_gate': {
                'status': 'PASS',
                'checks': {
                    'traceability': {'status': 'PASS', 'coverage': 1.0, 'detail': 'OK'},
                    'policy_adherence': {'status': 'PASS', 'violations': [], 'detail': 'OK'},
                    'structural_completeness': {'status': 'PASS', 'detail': 'OK'},
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                        'detail': 'OK',
                    },
                    'logic_drift': {'status': 'PASS', 'pairs': [], 'detail': 'OK'},
                },
            },
            'user_testing': {'status': 'CLEAN', 'bugs': 0,
                             'discoveries': 0, 'intent_drifts': 0},
        }
        items = generate_action_items(result)
        arch_items = items['architect']
        self.assertTrue(len(arch_items) > 0)
        self.assertEqual(arch_items[0]['priority'], 'HIGH')
        self.assertIn('section_completeness', arch_items[0]['description'])

    def test_spec_warn_generates_low_item(self):
        result = {
            'feature_file': 'features/test.md',
            'spec_gate': {
                'status': 'WARN',
                'checks': {
                    'section_completeness': {
                        'status': 'WARN',
                        'detail': 'Implementation Notes empty.',
                    },
                    'scenario_classification': {'status': 'PASS', 'detail': 'OK'},
                    'policy_anchoring': {'status': 'PASS', 'detail': 'OK'},
                    'prerequisite_integrity': {'status': 'PASS', 'detail': 'OK'},
                    'gherkin_quality': {'status': 'PASS', 'detail': 'OK'},
                },
            },
            'implementation_gate': {
                'status': 'PASS',
                'checks': {
                    'traceability': {'status': 'PASS', 'coverage': 1.0, 'detail': 'OK'},
                    'policy_adherence': {'status': 'PASS', 'violations': [], 'detail': 'OK'},
                    'structural_completeness': {'status': 'PASS', 'detail': 'OK'},
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                        'detail': 'OK',
                    },
                    'logic_drift': {'status': 'PASS', 'pairs': [], 'detail': 'OK'},
                },
            },
            'user_testing': {'status': 'CLEAN', 'bugs': 0,
                             'discoveries': 0, 'intent_drifts': 0},
        }
        items = generate_action_items(result)
        arch_items = items['architect']
        self.assertTrue(len(arch_items) > 0)
        self.assertEqual(arch_items[0]['priority'], 'LOW')


class TestActionItemsBuilder(unittest.TestCase):
    """Scenario: Builder Action Items from Traceability Gaps"""

    def test_traceability_gap_generates_medium_item(self):
        result = {
            'feature_file': 'features/test.md',
            'spec_gate': {'status': 'PASS', 'checks': {}},
            'implementation_gate': {
                'status': 'WARN',
                'checks': {
                    'traceability': {
                        'status': 'WARN',
                        'coverage': 0.5,
                        'detail': '1/2 traced. Unmatched: Zero-Queue Verification',
                    },
                    'policy_adherence': {'status': 'PASS', 'violations': [], 'detail': 'OK'},
                    'structural_completeness': {'status': 'PASS', 'detail': 'OK'},
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                        'detail': 'OK',
                    },
                    'logic_drift': {'status': 'PASS', 'pairs': [], 'detail': 'OK'},
                },
            },
            'user_testing': {'status': 'CLEAN', 'bugs': 0,
                             'discoveries': 0, 'intent_drifts': 0},
        }
        items = generate_action_items(result)
        builder_items = items['builder']
        self.assertTrue(len(builder_items) > 0)
        self.assertEqual(builder_items[0]['priority'], 'MEDIUM')
        self.assertIn('Write tests', builder_items[0]['description'])

    def test_structural_fail_generates_high_item(self):
        result = {
            'feature_file': 'features/test.md',
            'spec_gate': {'status': 'PASS', 'checks': {}},
            'implementation_gate': {
                'status': 'FAIL',
                'checks': {
                    'traceability': {'status': 'PASS', 'coverage': 1.0, 'detail': 'OK'},
                    'policy_adherence': {'status': 'PASS', 'violations': [], 'detail': 'OK'},
                    'structural_completeness': {
                        'status': 'FAIL',
                        'detail': 'Missing tests/test/tests.json.',
                    },
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                        'detail': 'OK',
                    },
                    'logic_drift': {'status': 'PASS', 'pairs': [], 'detail': 'OK'},
                },
            },
            'user_testing': {'status': 'CLEAN', 'bugs': 0,
                             'discoveries': 0, 'intent_drifts': 0},
        }
        items = generate_action_items(result)
        builder_items = items['builder']
        self.assertTrue(len(builder_items) > 0)
        self.assertEqual(builder_items[0]['priority'], 'HIGH')
        self.assertIn('Fix failing tests', builder_items[0]['description'])

    def test_unacknowledged_deviation_generates_high_architect_item(self):
        """Unacknowledged DEVIATION routes to Architect per spec Section 2.10."""
        result = {
            'feature_file': 'features/test.md',
            'spec_gate': {'status': 'PASS', 'checks': {}},
            'implementation_gate': {
                'status': 'FAIL',
                'checks': {
                    'traceability': {'status': 'PASS', 'coverage': 1.0, 'detail': 'OK'},
                    'policy_adherence': {'status': 'PASS', 'violations': [], 'detail': 'OK'},
                    'structural_completeness': {'status': 'PASS', 'detail': 'OK'},
                    'builder_decisions': {
                        'status': 'FAIL',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 1, 'DISCOVERY': 0,
                                    'INFEASIBLE': 0},
                        'detail': 'Has DEVIATION.',
                    },
                    'logic_drift': {'status': 'PASS', 'pairs': [], 'detail': 'OK'},
                },
            },
            'user_testing': {'status': 'CLEAN', 'bugs': 0,
                             'discoveries': 0, 'intent_drifts': 0,
                             'spec_disputes': 0},
        }
        items = generate_action_items(result)
        arch_items = items['architect']
        deviation_items = [i for i in arch_items
                           if 'DEVIATION' in i['description']]
        self.assertTrue(len(deviation_items) > 0)
        self.assertEqual(deviation_items[0]['priority'], 'HIGH')


class TestActionItemsBugRoutingOverride(unittest.TestCase):
    """Scenario: BUG Action Required Architect Override Routing"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        # Feature with an Architect-routed BUG
        architect_bug_content = """\
# Feature: Instruction Bug

> Label: "Tool: Instruction Bug"

## 1. Overview
Overview.

## User Testing Discoveries

### [BUG] Agent ignores startup flags (Discovered: 2026-01-01)
- **Scenario:** Expert Mode Bypasses Orientation
- **Observed Behavior:** Agent runs full orientation despite startup_sequence false.
- **Expected Behavior:** Agent should skip orientation.
- **Action Required:** Architect
- **Status:** OPEN
"""
        with open(os.path.join(self.features_dir, 'instruction_bug.md'),
                  'w') as f:
            f.write(architect_bug_content)
        # Feature with a normal (Builder-routed) BUG
        builder_bug_content = """\
# Feature: Code Bug

> Label: "Tool: Code Bug"

## 1. Overview
Overview.

## User Testing Discoveries

### [BUG] Button does not refresh (Discovered: 2026-01-01)
- **Scenario:** Run Critic Button
- **Observed Behavior:** Dashboard does not refresh after critic run.
- **Expected Behavior:** Dashboard should refresh immediately.
- **Status:** OPEN
"""
        with open(os.path.join(self.features_dir, 'code_bug.md'), 'w') as f:
            f.write(builder_bug_content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_bug_with_action_required_architect_routes_to_architect(self):
        """BUG with Action Required: Architect routes to Architect items."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/instruction_bug.md'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 1, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            items = generate_action_items(result)
            arch_items = items['architect']
            builder_items = items['builder']
            # BUG should route to Architect, not Builder
            bug_arch = [i for i in arch_items
                        if 'instruction-level bug' in i['description']]
            self.assertEqual(len(bug_arch), 1)
            self.assertEqual(bug_arch[0]['priority'], 'HIGH')
            self.assertEqual(bug_arch[0]['category'], 'user_testing')
            # Builder should NOT have this BUG
            bug_builder = [i for i in builder_items
                           if 'instruction_bug' in i.get('feature', '')]
            self.assertEqual(len(bug_builder), 0)
        finally:
            critic.FEATURES_DIR = orig_features

    def test_bug_without_action_required_routes_to_builder(self):
        """BUG without Action Required field routes to Builder (default)."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/code_bug.md'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 1, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            items = generate_action_items(result)
            builder_items = items['builder']
            arch_items = items['architect']
            # BUG should route to Builder
            bug_builder = [i for i in builder_items
                           if 'Fix bug' in i['description']]
            self.assertEqual(len(bug_builder), 1)
            self.assertEqual(bug_builder[0]['priority'], 'HIGH')
            # Architect should NOT have this BUG
            bug_arch = [i for i in arch_items
                        if 'code_bug' in i.get('feature', '')]
            self.assertEqual(len(bug_arch), 0)
        finally:
            critic.FEATURES_DIR = orig_features


class TestActionItemsQA(unittest.TestCase):
    """Scenario: QA Action Items from TESTING Status"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        feature_content = """\
# Feature: Test

> Label: "Tool: Test"

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Test
    Given X
    When Y
    Then Z

### Manual Scenarios (Human Verification Required)

#### Scenario: Manual One
    Given A
    When B
    Then C

#### Scenario: Manual Two
    Given D
    When E
    Then F

## 4. Implementation Notes
* Note.
"""
        with open(os.path.join(self.features_dir, 'test.md'), 'w') as f:
            f.write(feature_content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_testing_status_generates_qa_item(self):
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            cdd_status = {
                'features': {
                    'testing': [{'file': 'features/test.md', 'label': 'Test'}],
                    'todo': [],
                    'complete': [],
                },
            }
            result = {
                'feature_file': 'features/test.md',
                'spec_gate': {'status': 'PASS', 'checks': {}},
                'implementation_gate': {
                    'status': 'PASS',
                    'checks': {
                        'traceability': {'status': 'PASS', 'coverage': 1.0, 'detail': 'OK'},
                        'policy_adherence': {'status': 'PASS', 'violations': [], 'detail': 'OK'},
                        'structural_completeness': {'status': 'PASS', 'detail': 'OK'},
                        'builder_decisions': {
                            'status': 'PASS',
                            'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                        'DEVIATION': 0, 'DISCOVERY': 0},
                            'detail': 'OK',
                        },
                        'logic_drift': {'status': 'PASS', 'pairs': [], 'detail': 'OK'},
                    },
                },
                'user_testing': {'status': 'CLEAN', 'bugs': 0,
                                 'discoveries': 0, 'intent_drifts': 0},
            }
            items = generate_action_items(result, cdd_status=cdd_status)
            qa_items = items['qa']
            self.assertTrue(len(qa_items) > 0)
            self.assertEqual(qa_items[0]['priority'], 'MEDIUM')
            self.assertIn('2 manual', qa_items[0]['description'])
        finally:
            critic.FEATURES_DIR = orig_features

    def test_testing_with_zero_manual_scenarios_skips_qa_item(self):
        """Features with 0 manual scenarios should not generate QA action items."""
        import critic
        orig_features = critic.FEATURES_DIR
        # Create a temp feature with NO manual scenarios
        tmp = tempfile.mkdtemp()
        features_dir = os.path.join(tmp, 'features')
        os.makedirs(features_dir)
        content = """\
# Feature: Auto Only

> Label: "Tool: Auto Only"

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Test
    Given X
    When Y
    Then Z

## 4. Implementation Notes
* Note.
"""
        with open(os.path.join(features_dir, 'auto_only.md'), 'w') as f:
            f.write(content)
        critic.FEATURES_DIR = features_dir
        try:
            cdd_status = {
                'features': {
                    'testing': [{'file': 'features/auto_only.md', 'label': 'Auto Only'}],
                    'todo': [],
                    'complete': [],
                },
            }
            result = {
                'feature_file': 'features/auto_only.md',
                'spec_gate': {'status': 'PASS', 'checks': {}},
                'implementation_gate': {
                    'status': 'PASS',
                    'checks': {
                        'traceability': {'status': 'PASS', 'coverage': 1.0, 'detail': 'OK'},
                        'policy_adherence': {'status': 'PASS', 'violations': [], 'detail': 'OK'},
                        'structural_completeness': {'status': 'PASS', 'detail': 'OK'},
                        'builder_decisions': {
                            'status': 'PASS',
                            'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                        'DEVIATION': 0, 'DISCOVERY': 0},
                            'detail': 'OK',
                        },
                        'logic_drift': {'status': 'PASS', 'pairs': [], 'detail': 'OK'},
                    },
                },
                'user_testing': {'status': 'CLEAN', 'bugs': 0,
                                 'discoveries': 0, 'intent_drifts': 0},
            }
            items = generate_action_items(result, cdd_status=cdd_status)
            qa_items = items['qa']
            self.assertEqual(len(qa_items), 0,
                             "Features with 0 manual scenarios should not generate QA items")
        finally:
            critic.FEATURES_DIR = orig_features
            shutil.rmtree(tmp)

    def test_no_cdd_status_skips_testing_items(self):
        result = {
            'feature_file': 'features/test.md',
            'spec_gate': {'status': 'PASS', 'checks': {}},
            'implementation_gate': {
                'status': 'PASS',
                'checks': {
                    'traceability': {'status': 'PASS', 'coverage': 1.0, 'detail': 'OK'},
                    'policy_adherence': {'status': 'PASS', 'violations': [], 'detail': 'OK'},
                    'structural_completeness': {'status': 'PASS', 'detail': 'OK'},
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                        'detail': 'OK',
                    },
                    'logic_drift': {'status': 'PASS', 'pairs': [], 'detail': 'OK'},
                },
            },
            'user_testing': {'status': 'CLEAN', 'bugs': 0,
                             'discoveries': 0, 'intent_drifts': 0},
        }
        items = generate_action_items(result, cdd_status=None)
        qa_items = items['qa']
        # No QA items since no CDD status and no SPEC_UPDATED
        self.assertEqual(len(qa_items), 0)


class TestActionItemsInCriticJson(unittest.TestCase):
    """Scenario: Action Items in Critic JSON Output"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        self.feature_path = os.path.join(self.features_dir, 'test_feature.md')
        with open(self.feature_path, 'w') as f:
            f.write(COMPLETE_FEATURE)
        with open(os.path.join(self.features_dir, 'arch_critic_policy.md'), 'w') as f:
            f.write('# Policy\n')

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_critic_json_has_action_items(self):
        import critic
        orig_features = critic.FEATURES_DIR
        orig_tests = critic.TESTS_DIR
        orig_root = critic.PROJECT_ROOT
        critic.FEATURES_DIR = self.features_dir
        critic.TESTS_DIR = os.path.join(self.root, 'tests')
        critic.PROJECT_ROOT = self.root
        try:
            data = generate_critic_json(self.feature_path)
            self.assertIn('action_items', data)
            ai = data['action_items']
            self.assertIn('architect', ai)
            self.assertIn('builder', ai)
            self.assertIn('qa', ai)
        finally:
            critic.FEATURES_DIR = orig_features
            critic.TESTS_DIR = orig_tests
            critic.PROJECT_ROOT = orig_root


class TestActionItemsInAggregateReport(unittest.TestCase):
    """Scenario: Action Items in Aggregate Report"""

    def test_report_has_action_items_section(self):
        results = [{
            'feature_file': 'features/test.md',
            'spec_gate': {
                'status': 'FAIL',
                'checks': {
                    'section_completeness': {
                        'status': 'FAIL',
                        'detail': 'Missing sections: Requirements.',
                    },
                },
            },
            'implementation_gate': {
                'status': 'WARN',
                'checks': {
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                    },
                    'policy_adherence': {'status': 'PASS', 'violations': []},
                    'traceability': {
                        'status': 'WARN',
                        'coverage': 0.5,
                        'detail': '1/2 traced',
                    },
                },
            },
            'user_testing': {
                'status': 'CLEAN',
                'bugs': 0, 'discoveries': 0, 'intent_drifts': 0,
            },
            'action_items': {
                'architect': [{
                    'priority': 'HIGH',
                    'category': 'spec_gate',
                    'feature': 'test',
                    'description': 'Fix spec gap: section_completeness -- Missing Requirements',
                }],
                'builder': [{
                    'priority': 'MEDIUM',
                    'category': 'traceability',
                    'feature': 'test',
                    'description': 'Write tests for test: 1/2 traced',
                }],
                'qa': [],
            },
        }]
        report = generate_critic_report(results)
        self.assertIn('## Action Items by Role', report)
        self.assertIn('### Architect', report)
        self.assertIn('### Builder', report)
        self.assertIn('### QA', report)
        self.assertIn('[HIGH]', report)
        self.assertIn('[MEDIUM]', report)
        self.assertIn('Fix spec gap', report)
        self.assertIn('Write tests', report)

    def test_report_items_sorted_by_priority(self):
        results = [{
            'feature_file': 'features/test.md',
            'spec_gate': {'status': 'PASS', 'checks': {}},
            'implementation_gate': {
                'status': 'PASS',
                'checks': {
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                    },
                    'policy_adherence': {'status': 'PASS', 'violations': []},
                    'traceability': {'status': 'PASS', 'coverage': 1.0, 'detail': 'OK'},
                },
            },
            'user_testing': {
                'status': 'CLEAN',
                'bugs': 0, 'discoveries': 0, 'intent_drifts': 0,
            },
            'action_items': {
                'architect': [
                    {'priority': 'LOW', 'category': 'spec_gate',
                     'feature': 'test', 'description': 'Low item'},
                    {'priority': 'HIGH', 'category': 'spec_gate',
                     'feature': 'test', 'description': 'High item'},
                ],
                'builder': [],
                'qa': [],
            },
        }]
        report = generate_critic_report(results)
        high_pos = report.index('[HIGH]')
        low_pos = report.index('[LOW]')
        self.assertLess(high_pos, low_pos, 'HIGH items should appear before LOW items')


# ===================================================================
# Untracked File Audit Tests
# ===================================================================

class TestUntrackedFileDetection(unittest.TestCase):
    """Scenario: Untracked File Detection"""

    @patch('critic.subprocess.run')
    def test_detects_untracked_files(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='?? newfile.py\n?? docs/readme.txt\n',
        )
        items = audit_untracked_files('/fake/root')
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertEqual(item['priority'], 'MEDIUM')
            self.assertEqual(item['category'], 'untracked_file')
        self.assertIn('newfile.py', items[0]['description'])
        self.assertIn('docs/readme.txt', items[1]['description'])

    @patch('critic.subprocess.run')
    def test_excludes_purlin_dir(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='?? .purlin/config.json\n?? real_file.py\n',
        )
        items = audit_untracked_files('/fake/root')
        self.assertEqual(len(items), 1)
        self.assertIn('real_file.py', items[0]['description'])

    @patch('critic.subprocess.run')
    def test_excludes_claude_dir(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='?? .claude/settings.json\n?? keep_me.txt\n',
        )
        items = audit_untracked_files('/fake/root')
        self.assertEqual(len(items), 1)
        self.assertIn('keep_me.txt', items[0]['description'])

    @patch('critic.subprocess.run')
    def test_ignores_tracked_files(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=' M modified.py\nA  staged.py\n?? untracked.py\n',
        )
        items = audit_untracked_files('/fake/root')
        self.assertEqual(len(items), 1)
        self.assertIn('untracked.py', items[0]['description'])

    @patch('critic.subprocess.run')
    def test_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='',
        )
        items = audit_untracked_files('/fake/root')
        self.assertEqual(items, [])

    @patch('critic.subprocess.run')
    def test_git_failure_returns_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128, stdout='')
        items = audit_untracked_files('/fake/root')
        self.assertEqual(items, [])

    @patch('critic.subprocess.run')
    def test_action_item_description_format(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='?? some/path.py\n',
        )
        items = audit_untracked_files('/fake/root')
        self.assertEqual(len(items), 1)
        self.assertIn('Triage untracked file:', items[0]['description'])
        self.assertIn('commit, gitignore, or delegate to Builder',
                       items[0]['description'])


class TestUntrackedFilesInAggregateReport(unittest.TestCase):
    """Scenario: Untracked Files in Aggregate Report"""

    def test_report_includes_untracked_subsection(self):
        results = [{
            'feature_file': 'features/test.md',
            'spec_gate': {'status': 'PASS', 'checks': {}},
            'implementation_gate': {
                'status': 'PASS',
                'checks': {
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                    },
                    'policy_adherence': {'status': 'PASS', 'violations': []},
                    'traceability': {'status': 'PASS', 'coverage': 1.0,
                                     'detail': 'OK'},
                },
            },
            'user_testing': {
                'status': 'CLEAN',
                'bugs': 0, 'discoveries': 0, 'intent_drifts': 0,
            },
        }]
        untracked = [{
            'priority': 'MEDIUM',
            'category': 'untracked_file',
            'feature': 'project',
            'description': 'Triage untracked file: orphan.py '
                           '(commit, gitignore, or delegate to Builder)',
        }]
        report = generate_critic_report(results, untracked_items=untracked)
        self.assertIn('#### Untracked Files', report)
        self.assertIn('orphan.py', report)
        self.assertIn('Triage untracked file', report)

    def test_report_no_untracked_no_subsection(self):
        results = [{
            'feature_file': 'features/test.md',
            'spec_gate': {'status': 'PASS', 'checks': {}},
            'implementation_gate': {
                'status': 'PASS',
                'checks': {
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                    },
                    'policy_adherence': {'status': 'PASS', 'violations': []},
                    'traceability': {'status': 'PASS', 'coverage': 1.0,
                                     'detail': 'OK'},
                },
            },
            'user_testing': {
                'status': 'CLEAN',
                'bugs': 0, 'discoveries': 0, 'intent_drifts': 0,
            },
        }]
        report = generate_critic_report(results, untracked_items=[])
        self.assertNotIn('#### Untracked Files', report)


# ===================================================================
# Spec Dispute in User Testing Audit Tests
# ===================================================================

class TestSpecDisputeCounted(unittest.TestCase):
    """Scenario: Spec Dispute Counted in User Testing Audit"""

    def test_open_spec_dispute_counted(self):
        content = """\
## User Testing Discoveries

### [SPEC_DISPUTE] User disagrees with expected behavior (Discovered: 2026-01-01)
- **Status:** OPEN
"""
        result = run_user_testing_audit(content)
        self.assertEqual(result['status'], 'HAS_OPEN_ITEMS')
        self.assertEqual(result['spec_disputes'], 1)

    def test_spec_disputes_field_present_when_clean(self):
        content = """\
## User Testing Discoveries
"""
        result = run_user_testing_audit(content)
        self.assertEqual(result['status'], 'CLEAN')
        self.assertIn('spec_disputes', result)
        self.assertEqual(result['spec_disputes'], 0)

    def test_no_section_includes_spec_disputes(self):
        content = '# Feature\n\n## Overview\n'
        result = run_user_testing_audit(content)
        self.assertIn('spec_disputes', result)
        self.assertEqual(result['spec_disputes'], 0)

    def test_multiple_spec_disputes(self):
        content = """\
## User Testing Discoveries

### [SPEC_DISPUTE] First dispute (Discovered: 2026-01-01)
- **Status:** OPEN

### [SPEC_DISPUTE] Second dispute (Discovered: 2026-01-02)
- **Status:** OPEN

### [BUG] A bug too (Discovered: 2026-01-03)
- **Status:** OPEN
"""
        result = run_user_testing_audit(content)
        self.assertEqual(result['spec_disputes'], 2)
        self.assertEqual(result['bugs'], 1)


# ===================================================================
# INFEASIBLE Tag Detection Tests
# ===================================================================

class TestInfeasibleTagDetection(unittest.TestCase):
    """Scenario: Architect Action Items from Infeasible Feature"""

    def test_infeasible_parsed_in_decisions(self):
        notes = '* **[INFEASIBLE]** Cannot implement due to X (Severity: CRITICAL)'
        decisions = parse_builder_decisions(notes)
        self.assertEqual(len(decisions['INFEASIBLE']), 1)

    def test_infeasible_causes_fail_status(self):
        notes = '* [INFEASIBLE] Cannot implement.'
        result = check_builder_decisions(notes)
        self.assertEqual(result['status'], 'FAIL')
        self.assertGreater(result['summary']['INFEASIBLE'], 0)

    def test_infeasible_generates_critical_architect_item(self):
        result = _make_base_result()
        result['implementation_gate']['checks']['builder_decisions'] = {
            'status': 'FAIL',
            'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                        'DEVIATION': 0, 'DISCOVERY': 0, 'INFEASIBLE': 1},
            'detail': 'Has INFEASIBLE.',
        }
        items = generate_action_items(result)
        arch_items = items['architect']
        infeasible_items = [i for i in arch_items
                            if i['priority'] == 'CRITICAL']
        self.assertTrue(len(infeasible_items) > 0)
        self.assertIn('infeasible', infeasible_items[0]['category'])


# ===================================================================
# Spec Dispute Action Item Tests
# ===================================================================

class TestSpecDisputeActionItems(unittest.TestCase):
    """Scenario: Architect Action Items from Spec Dispute"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        feature_content = """\
# Feature: Disputed Feature

> Label: "Tool: Disputed"

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Test
    Given X
    When Y
    Then Z

## 4. Implementation Notes
* Note.

## User Testing Discoveries

### [SPEC_DISPUTE] User disagrees with Auto Test expected behavior (Discovered: 2026-01-01)
- **Status:** OPEN
"""
        with open(os.path.join(self.features_dir, 'disputed.md'), 'w') as f:
            f.write(feature_content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_open_spec_dispute_generates_high_architect_item(self):
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/disputed.md'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 1,
            }
            items = generate_action_items(result)
            arch_items = items['architect']
            dispute_items = [i for i in arch_items
                             if 'disputed scenario' in i['description'].lower()
                             or 'SPEC_DISPUTE' in i['description']]
            self.assertTrue(len(dispute_items) > 0)
            self.assertEqual(dispute_items[0]['priority'], 'HIGH')
        finally:
            critic.FEATURES_DIR = orig_features


# ===================================================================
# Role Status Computation Tests (Section 2.11)
# ===================================================================

def _make_base_result(**overrides):
    """Create a baseline feature result for role status testing."""
    result = {
        'feature_file': 'features/test.md',
        'spec_gate': {
            'status': 'PASS',
            'checks': {
                'section_completeness': {'status': 'PASS', 'detail': 'OK'},
                'scenario_classification': {'status': 'PASS', 'detail': 'OK'},
                'policy_anchoring': {'status': 'PASS', 'detail': 'OK'},
                'prerequisite_integrity': {'status': 'PASS', 'detail': 'OK'},
                'gherkin_quality': {'status': 'PASS', 'detail': 'OK'},
            },
        },
        'implementation_gate': {
            'status': 'PASS',
            'checks': {
                'traceability': {'status': 'PASS', 'coverage': 1.0,
                                 'detail': 'OK'},
                'policy_adherence': {'status': 'PASS', 'violations': [],
                                     'detail': 'OK'},
                'structural_completeness': {'status': 'PASS', 'detail': 'OK'},
                'builder_decisions': {
                    'status': 'PASS',
                    'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                'DEVIATION': 0, 'DISCOVERY': 0,
                                'INFEASIBLE': 0},
                    'detail': 'OK',
                },
                'logic_drift': {'status': 'PASS', 'pairs': [],
                                'detail': 'OK'},
            },
        },
        'user_testing': {
            'status': 'CLEAN', 'bugs': 0, 'discoveries': 0,
            'intent_drifts': 0, 'spec_disputes': 0,
        },
        'action_items': {
            'architect': [],
            'builder': [],
            'qa': [],
        },
    }
    result.update(overrides)
    return result


class TestRoleStatusArchitectTODO(unittest.TestCase):
    """Scenario: Role Status Architect TODO"""

    def test_spec_fail_makes_architect_todo(self):
        result = _make_base_result()
        result['spec_gate']['status'] = 'FAIL'
        result['spec_gate']['checks']['section_completeness'] = {
            'status': 'FAIL', 'detail': 'Missing Requirements.',
        }
        result['action_items']['architect'] = [{
            'priority': 'HIGH',
            'category': 'spec_gate',
            'feature': 'test',
            'description': 'Fix spec gap.',
        }]
        status = compute_role_status(result)
        self.assertEqual(status['architect'], 'TODO')


class TestRoleStatusArchitectDONE(unittest.TestCase):
    """Scenario: Role Status Architect DONE"""

    def test_no_high_items_makes_architect_done(self):
        result = _make_base_result()
        status = compute_role_status(result)
        self.assertEqual(status['architect'], 'DONE')

    def test_low_items_still_done(self):
        result = _make_base_result()
        result['action_items']['architect'] = [{
            'priority': 'LOW',
            'category': 'spec_gate',
            'feature': 'test',
            'description': 'Improve spec.',
        }]
        status = compute_role_status(result)
        self.assertEqual(status['architect'], 'DONE')


class TestRoleStatusBuilderDONE(unittest.TestCase):
    """Scenario: Role Status Builder DONE"""

    def test_structural_pass_no_bugs_makes_done(self):
        result = _make_base_result()
        status = compute_role_status(result)
        self.assertEqual(status['builder'], 'DONE')


class TestRoleStatusBuilderFAIL(unittest.TestCase):
    """Scenario: Role Status Builder FAIL"""

    def test_structural_warn_makes_builder_fail(self):
        """tests.json exists with status FAIL -> structural WARN -> Builder FAIL."""
        result = _make_base_result()
        result['implementation_gate']['checks']['structural_completeness'] = {
            'status': 'WARN', 'detail': 'tests.json status is FAIL.',
        }
        status = compute_role_status(result)
        self.assertEqual(status['builder'], 'FAIL')

    def test_structural_fail_makes_builder_todo(self):
        """tests.json missing/malformed -> structural FAIL -> Builder TODO."""
        result = _make_base_result()
        result['implementation_gate']['checks']['structural_completeness'] = {
            'status': 'FAIL', 'detail': 'Missing tests.json.',
        }
        result['action_items']['builder'] = [{
            'priority': 'HIGH',
            'category': 'structural_completeness',
            'feature': 'test',
            'description': 'Fix failing tests.',
        }]
        status = compute_role_status(result)
        self.assertEqual(status['builder'], 'TODO')


class TestRoleStatusBuilderINFEASIBLE(unittest.TestCase):
    """Scenario: Role Status Builder INFEASIBLE"""

    def test_infeasible_tag_makes_infeasible(self):
        result = _make_base_result()
        result['implementation_gate']['checks']['builder_decisions'] = {
            'status': 'FAIL',
            'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                        'DEVIATION': 0, 'DISCOVERY': 0, 'INFEASIBLE': 1},
            'detail': 'Has INFEASIBLE.',
        }
        status = compute_role_status(result)
        self.assertEqual(status['builder'], 'INFEASIBLE')

    def test_infeasible_takes_precedence_over_fail(self):
        result = _make_base_result()
        result['implementation_gate']['checks']['builder_decisions'] = {
            'status': 'FAIL',
            'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                        'DEVIATION': 0, 'DISCOVERY': 0, 'INFEASIBLE': 1},
            'detail': 'Has INFEASIBLE.',
        }
        result['implementation_gate']['checks']['structural_completeness'] = {
            'status': 'FAIL', 'detail': 'tests.json FAIL.',
        }
        status = compute_role_status(result)
        self.assertEqual(status['builder'], 'INFEASIBLE')


class TestRoleStatusBuilderBLOCKED(unittest.TestCase):
    """Scenario: Role Status Builder BLOCKED"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        content = """\
# Feature: Blocked Feature

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Test
    Given X
    When Y
    Then Z

## 4. Implementation Notes
* Note.

## User Testing Discoveries

### [SPEC_DISPUTE] User disagrees with behavior (Discovered: 2026-01-01)
- **Status:** OPEN
"""
        with open(os.path.join(self.features_dir, 'blocked.md'), 'w') as f:
            f.write(content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_open_spec_dispute_blocks_builder(self):
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/blocked.md'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 1,
            }
            status = compute_role_status(result)
            self.assertEqual(status['builder'], 'BLOCKED')
        finally:
            critic.FEATURES_DIR = orig_features


class TestRoleStatusQACLEAN(unittest.TestCase):
    """Scenario: Role Status QA CLEAN"""

    def test_clean_testing_in_complete_state(self):
        result = _make_base_result()
        cdd_status = {
            'features': {
                'complete': [{'file': 'features/test.md'}],
                'testing': [], 'todo': [],
            },
        }
        status = compute_role_status(result, cdd_status)
        self.assertEqual(status['qa'], 'CLEAN')


class TestRoleStatusQAFAIL(unittest.TestCase):
    """Scenario: Role Status QA FAIL"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        content = """\
# Feature: Buggy Feature

## 1. Overview
Overview.

## User Testing Discoveries

### [BUG] Something is broken (Discovered: 2026-01-01)
- **Status:** OPEN
"""
        with open(os.path.join(self.features_dir, 'buggy.md'), 'w') as f:
            f.write(content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_open_bugs_makes_qa_fail(self):
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/buggy.md'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 1, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            cdd_status = {
                'features': {
                    'testing': [{'file': 'features/buggy.md'}],
                    'complete': [], 'todo': [],
                },
            }
            status = compute_role_status(result, cdd_status)
            self.assertEqual(status['qa'], 'FAIL')
        finally:
            critic.FEATURES_DIR = orig_features


class TestRoleStatusQADISPUTED(unittest.TestCase):
    """Scenario: Role Status QA DISPUTED"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        content = """\
# Feature: Disputed Feature

## 1. Overview
Overview.

## User Testing Discoveries

### [SPEC_DISPUTE] Scenario expected wrong behavior (Discovered: 2026-01-01)
- **Status:** OPEN
"""
        with open(os.path.join(self.features_dir, 'disputed_qa.md'), 'w') as f:
            f.write(content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_open_spec_dispute_makes_qa_disputed(self):
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/disputed_qa.md'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 1,
            }
            cdd_status = {
                'features': {
                    'testing': [{'file': 'features/disputed_qa.md'}],
                    'complete': [], 'todo': [],
                },
            }
            status = compute_role_status(result, cdd_status)
            self.assertEqual(status['qa'], 'DISPUTED')
        finally:
            critic.FEATURES_DIR = orig_features


class TestRoleStatusQANA(unittest.TestCase):
    """Scenario: Role Status QA N/A"""

    def test_no_tests_makes_qa_na(self):
        result = _make_base_result()
        result['implementation_gate']['checks']['structural_completeness'] = {
            'status': 'FAIL', 'detail': 'Missing tests.json.',
        }
        cdd_status = {
            'features': {
                'todo': [{'file': 'features/test.md'}],
                'testing': [], 'complete': [],
            },
        }
        status = compute_role_status(result, cdd_status)
        self.assertEqual(status['qa'], 'N/A')

    def test_todo_lifecycle_with_passing_tests_makes_qa_clean(self):
        result = _make_base_result()
        cdd_status = {
            'features': {
                'todo': [{'file': 'features/test.md'}],
                'testing': [], 'complete': [],
            },
        }
        status = compute_role_status(result, cdd_status)
        self.assertEqual(status['qa'], 'CLEAN')

    def test_no_cdd_status_with_passing_tests_makes_qa_clean(self):
        result = _make_base_result()
        status = compute_role_status(result, cdd_status=None)
        self.assertEqual(status['qa'], 'CLEAN')


class TestRoleStatusInCriticJson(unittest.TestCase):
    """Scenario: Role Status in Critic JSON Output"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        self.feature_path = os.path.join(self.features_dir, 'test_feature.md')
        with open(self.feature_path, 'w') as f:
            f.write(COMPLETE_FEATURE)
        with open(os.path.join(self.features_dir,
                               'arch_critic_policy.md'), 'w') as f:
            f.write('# Policy\n')

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_critic_json_has_role_status(self):
        import critic
        orig_features = critic.FEATURES_DIR
        orig_tests = critic.TESTS_DIR
        orig_root = critic.PROJECT_ROOT
        critic.FEATURES_DIR = self.features_dir
        critic.TESTS_DIR = os.path.join(self.root, 'tests')
        critic.PROJECT_ROOT = self.root
        try:
            data = generate_critic_json(self.feature_path)
            self.assertIn('role_status', data)
            rs = data['role_status']
            self.assertIn('architect', rs)
            self.assertIn('builder', rs)
            self.assertIn('qa', rs)
            # Verify valid enum values
            self.assertIn(rs['architect'], ('DONE', 'TODO'))
            self.assertIn(rs['builder'],
                          ('DONE', 'TODO', 'FAIL', 'INFEASIBLE', 'BLOCKED'))
            self.assertIn(rs['qa'],
                          ('CLEAN', 'TODO', 'FAIL', 'DISPUTED', 'N/A'))
        finally:
            critic.FEATURES_DIR = orig_features
            critic.TESTS_DIR = orig_tests
            critic.PROJECT_ROOT = orig_root


class TestRoleStatusBuilderTODO(unittest.TestCase):
    """Scenario: Role Status Builder TODO with traceability gaps"""

    def test_traceability_gap_makes_builder_todo(self):
        result = _make_base_result()
        result['action_items']['builder'] = [{
            'priority': 'MEDIUM',
            'category': 'traceability',
            'feature': 'test',
            'description': 'Write tests for test.',
        }]
        status = compute_role_status(result)
        self.assertEqual(status['builder'], 'TODO')


class TestBuilderActionItemsFromLifecycleReset(unittest.TestCase):
    """Scenario: Builder Action Items from Lifecycle Reset

    When a feature is in TODO lifecycle state per feature_status.json,
    the Critic generates a HIGH Builder action item to review spec changes.
    """

    def test_todo_lifecycle_generates_builder_action_item(self):
        result = _make_base_result()
        cdd_status = {
            'features': {
                'todo': [{'file': 'features/test.md'}],
                'testing': [], 'complete': [],
            },
        }
        items = generate_action_items(result, cdd_status)
        builder_items = items['builder']
        lifecycle_items = [
            i for i in builder_items if i['category'] == 'lifecycle_reset'
        ]
        self.assertEqual(len(lifecycle_items), 1)
        self.assertEqual(lifecycle_items[0]['priority'], 'HIGH')
        self.assertIn('Review and implement spec changes', lifecycle_items[0]['description'])

    def test_testing_lifecycle_no_lifecycle_builder_item(self):
        import critic
        root = tempfile.mkdtemp()
        features_dir = os.path.join(root, 'features')
        os.makedirs(features_dir)
        with open(os.path.join(features_dir, 'test.md'), 'w') as f:
            f.write(COMPLETE_FEATURE)
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = features_dir
        try:
            result = _make_base_result()
            cdd_status = {
                'features': {
                    'testing': [{'file': 'features/test.md'}],
                    'todo': [], 'complete': [],
                },
            }
            items = generate_action_items(result, cdd_status)
            lifecycle_items = [
                i for i in items['builder'] if i['category'] == 'lifecycle_reset'
            ]
            self.assertEqual(len(lifecycle_items), 0)
        finally:
            critic.FEATURES_DIR = orig_features
            shutil.rmtree(root)

    def test_no_cdd_status_skips_lifecycle_item(self):
        result = _make_base_result()
        items = generate_action_items(result, cdd_status=None)
        lifecycle_items = [
            i for i in items['builder'] if i['category'] == 'lifecycle_reset'
        ]
        self.assertEqual(len(lifecycle_items), 0)


class TestSpecUpdatedDoesNotGenerateBuilderItems(unittest.TestCase):
    """Scenario: SPEC_UPDATED Discovery Does Not Generate Builder Action Items

    SPEC_UPDATED discoveries do NOT generate Builder action items regardless
    of the 'Action Required' field. Builder signaling comes from the feature
    lifecycle state (TODO), not from discovery routing.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        content = """\
# Feature: Test

## 1. Overview
Overview.

## User Testing Discoveries

### [DISCOVERY] start.sh port binding issue (Discovered: 2026-02-20)
- **Scenario:** Server Start/Stop Lifecycle
- **Observed Behavior:** Port stays in TIME_WAIT after stop.
- **Expected Behavior:** Server starts on first invocation after stop.
- **Action Required:** Builder
- **Status:** SPEC_UPDATED
"""
        with open(os.path.join(self.features_dir, 'test.md'), 'w') as f:
            f.write(content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_spec_updated_does_not_generate_builder_item(self):
        """SPEC_UPDATED discoveries never generate Builder action items."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 1,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            items = generate_action_items(result, cdd_status=None)
            builder_items = [
                i for i in items['builder']
                if 'Implement fix' in i['description']
            ]
            self.assertEqual(len(builder_items), 0)
        finally:
            critic.FEATURES_DIR = orig_features

    def test_spec_updated_builder_done_when_no_lifecycle_todo(self):
        """role_status.builder should be DONE when SPEC_UPDATED exists but
        feature is not in TODO lifecycle (Builder signaling is lifecycle-based)."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 1,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            cdd_status = {
                'features': {
                    'complete': [{'file': 'features/test.md'}],
                    'testing': [], 'todo': [],
                },
            }
            # Generate action items (no Builder items from SPEC_UPDATED)
            result['action_items'] = generate_action_items(
                result, cdd_status=cdd_status)
            status = compute_role_status(result, cdd_status)
            self.assertEqual(status['builder'], 'DONE')
        finally:
            critic.FEATURES_DIR = orig_features


class TestRoleStatusBuilderLifecycleTODO(unittest.TestCase):
    """Scenario: Builder Action Items from Lifecycle Reset (role_status)

    When a feature is in TODO lifecycle state, role_status.builder is TODO
    regardless of passing tests and traceability.
    """

    def test_todo_lifecycle_makes_builder_todo(self):
        result = _make_base_result()
        cdd_status = {
            'features': {
                'todo': [{'file': 'features/test.md'}],
                'testing': [], 'complete': [],
            },
        }
        status = compute_role_status(result, cdd_status)
        self.assertEqual(status['builder'], 'TODO')

    def test_complete_lifecycle_allows_builder_done(self):
        result = _make_base_result()
        cdd_status = {
            'features': {
                'complete': [{'file': 'features/test.md'}],
                'testing': [], 'todo': [],
            },
        }
        status = compute_role_status(result, cdd_status)
        self.assertEqual(status['builder'], 'DONE')


class TestRoleStatusQATODOForTestingFeature(unittest.TestCase):
    """Scenario: Role Status QA TODO for TESTING Feature

    A feature in TESTING state with CLEAN user testing should have
    role_status.qa = TODO (not CLEAN), because QA hasn't verified yet.
    Requires at least one manual scenario.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        # Feature with manual scenarios
        content = """\
# Feature: Test

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Test
    Given X
    When Y
    Then Z

### Manual Scenarios (Human Verification Required)

#### Scenario: Manual Check
    Given A
    When B
    Then C

## 4. Implementation Notes
* Note.
"""
        with open(os.path.join(self.features_dir, 'test.md'), 'w') as f:
            f.write(content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_testing_state_clean_user_testing_makes_qa_todo(self):
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            cdd_status = {
                'features': {
                    'testing': [{'file': 'features/test.md'}],
                    'complete': [], 'todo': [],
                },
            }
            status = compute_role_status(result, cdd_status)
            self.assertEqual(status['qa'], 'TODO')
            self.assertNotEqual(status['qa'], 'CLEAN')
        finally:
            critic.FEATURES_DIR = orig_features

    def test_complete_state_clean_user_testing_makes_qa_clean(self):
        result = _make_base_result()
        cdd_status = {
            'features': {
                'complete': [{'file': 'features/test.md'}],
                'testing': [], 'todo': [],
            },
        }
        status = compute_role_status(result, cdd_status)
        self.assertEqual(status['qa'], 'CLEAN')


class TestRoleStatusQADISPUTEDInNonTestingLifecycle(unittest.TestCase):
    """Scenario: Role Status QA DISPUTED in Non-TESTING Lifecycle

    DISPUTED is lifecycle-independent. A feature in TODO lifecycle state
    with OPEN SPEC_DISPUTEs should have QA = DISPUTED (not N/A).
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        content = """\
# Feature: Disputed

## 1. Overview
Overview.

## User Testing Discoveries

### [SPEC_DISPUTE] User disagrees with behavior (Discovered: 2026-01-01)
- **Status:** OPEN
"""
        with open(os.path.join(self.features_dir, 'disputed_todo.md'), 'w') as f:
            f.write(content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_disputed_overrides_na_in_todo_lifecycle(self):
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/disputed_todo.md'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 1,
            }
            cdd_status = {
                'features': {
                    'todo': [{'file': 'features/disputed_todo.md'}],
                    'testing': [], 'complete': [],
                },
            }
            status = compute_role_status(result, cdd_status)
            self.assertEqual(status['qa'], 'DISPUTED')
        finally:
            critic.FEATURES_DIR = orig_features


class TestRoleStatusQATODOForSpecUpdatedItemsInTesting(unittest.TestCase):
    """Scenario: Role Status QA TODO for SPEC_UPDATED Items in TESTING

    SPEC_UPDATED items trigger QA TODO only when feature is in TESTING
    lifecycle state. In TODO lifecycle, QA is CLEAN (Builder hasn't committed).
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        content = """\
# Feature: Spec Updated

## 1. Overview
Overview.

## User Testing Discoveries

### [DISCOVERY] Something found (Discovered: 2026-01-01)
- **Status:** SPEC_UPDATED
"""
        with open(os.path.join(self.features_dir, 'spec_updated.md'), 'w') as f:
            f.write(content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_spec_updated_makes_qa_todo_in_testing_lifecycle(self):
        """QA=TODO when SPEC_UPDATED + TESTING lifecycle."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/spec_updated.md'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 1,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            cdd_status = {
                'features': {
                    'testing': [{'file': 'features/spec_updated.md'}],
                    'todo': [], 'complete': [],
                },
            }
            status = compute_role_status(result, cdd_status)
            self.assertEqual(status['qa'], 'TODO')
        finally:
            critic.FEATURES_DIR = orig_features

    def test_spec_updated_makes_qa_clean_in_todo_lifecycle(self):
        """QA=CLEAN when SPEC_UPDATED + TODO lifecycle (Builder not done yet)."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/spec_updated.md'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 1,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            cdd_status = {
                'features': {
                    'todo': [{'file': 'features/spec_updated.md'}],
                    'testing': [], 'complete': [],
                },
            }
            status = compute_role_status(result, cdd_status)
            self.assertEqual(status['qa'], 'CLEAN')
        finally:
            critic.FEATURES_DIR = orig_features


class TestRoleStatusQACLEANDespiteOpenDiscoveriesRoutingToArchitect(
        unittest.TestCase):
    """Scenario: Role Status QA CLEAN Despite OPEN Discoveries Routing to Architect

    OPEN discoveries (DISCOVERYs, INTENT_DRIFTs) route to Architect, not QA.
    QA has no actionable work, so QA=CLEAN when tests pass.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        content = """\
# Feature: Open Items

## 1. Overview
Overview.

## User Testing Discoveries

### [DISCOVERY] New behavior found (Discovered: 2026-01-01)
- **Status:** OPEN
"""
        with open(os.path.join(self.features_dir, 'open_items.md'), 'w') as f:
            f.write(content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_open_discovery_routing_to_architect_gives_qa_clean(self):
        """OPEN discoveries route to Architect. QA=CLEAN when tests pass."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/open_items.md'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 1,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            cdd_status = {
                'features': {
                    'todo': [{'file': 'features/open_items.md'}],
                    'testing': [], 'complete': [],
                },
            }
            # Generate action items first (architect gets OPEN DISCOVERY item)
            result['action_items'] = generate_action_items(
                result, cdd_status=cdd_status)
            status = compute_role_status(result, cdd_status)
            self.assertEqual(status['qa'], 'CLEAN')
            self.assertEqual(status['architect'], 'TODO')
        finally:
            critic.FEATURES_DIR = orig_features


class TestResolvedPruningSignal(unittest.TestCase):
    """Scenario: RESOLVED Pruning Signal generates LOW QA action item."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        content = """\
# Feature: Resolved Items

## 1. Overview
Overview.

## User Testing Discoveries

### [BUG] Fixed bug one (Discovered: 2026-01-01)
- **Status:** RESOLVED

### [DISCOVERY] Resolved finding (Discovered: 2026-01-02)
- **Status:** RESOLVED
"""
        with open(os.path.join(self.features_dir, 'resolved.md'), 'w') as f:
            f.write(content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_resolved_entries_generate_low_qa_prune_item(self):
        """RESOLVED entries generate LOW QA action item to prune."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/resolved.md'
            result['user_testing'] = {
                'status': 'CLEAN',
                'bugs': 1, 'discoveries': 1,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            cdd_status = {
                'features': {
                    'testing': [{'file': 'features/resolved.md'}],
                    'todo': [], 'complete': [],
                },
            }
            items = generate_action_items(result, cdd_status=cdd_status)
            prune_items = [
                i for i in items['qa']
                if 'Prune' in i['description']
            ]
            self.assertEqual(len(prune_items), 1)
            self.assertEqual(prune_items[0]['priority'], 'LOW')
            self.assertIn('2 RESOLVED', prune_items[0]['description'])
        finally:
            critic.FEATURES_DIR = orig_features

    def test_no_prune_item_when_no_resolved(self):
        """No pruning signal when no RESOLVED entries exist."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/resolved.md'
            result['user_testing'] = {
                'status': 'CLEAN',
                'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            items = generate_action_items(result, cdd_status=None)
            prune_items = [
                i for i in items['qa']
                if 'Prune' in i['description']
            ]
            self.assertEqual(len(prune_items), 0)
        finally:
            critic.FEATURES_DIR = orig_features


class TestRoleStatusQACLEANForTestingNoManualScenarios(unittest.TestCase):
    """Scenario: Role Status QA CLEAN for Feature with Passing Tests and No Manual Scenarios

    A feature in TESTING state with 0 manual scenarios and passing tests
    should have QA = CLEAN (no manual verification needed, tests pass).
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        # Feature with NO manual scenarios
        content = """\
# Feature: Auto Only

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Test
    Given X
    When Y
    Then Z

## 4. Implementation Notes
* Note.
"""
        with open(os.path.join(self.features_dir, 'auto_only.md'), 'w') as f:
            f.write(content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_testing_no_manual_makes_qa_clean(self):
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/auto_only.md'
            cdd_status = {
                'features': {
                    'testing': [{'file': 'features/auto_only.md'}],
                    'complete': [], 'todo': [],
                },
            }
            status = compute_role_status(result, cdd_status)
            self.assertEqual(status['qa'], 'CLEAN')
        finally:
            critic.FEATURES_DIR = orig_features


# ===================================================================
# Regression Scope Tests (Section 2.12)
# ===================================================================

class TestRegressionScopeFullDefault(unittest.TestCase):
    """Scenario: Regression Scope Full Default

    When no [Scope: ...] trailer exists, declared defaults to 'full' and
    the regression set includes all manual scenarios and visual items.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        self.content = """\
# Feature: Scope Test

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Test
    Given X
    When Y
    Then Z

### Manual Scenarios (Human Verification Required)

#### Scenario: Manual Check A
    Given A
    When B
    Then C

#### Scenario: Manual Check B
    Given D
    When E
    Then F

## Visual Specification

### Screen: Dashboard
- [ ] Check layout
- [ ] Check colors

## 4. Implementation Notes
* Note.
"""
        with open(os.path.join(self.features_dir, 'scope_test.md'), 'w') as f:
            f.write(self.content)

    def tearDown(self):
        shutil.rmtree(self.root)

    @patch('critic._extract_scope_from_commit', return_value='full')
    def test_full_default_includes_all(self, _mock):
        result = compute_regression_set(
            'features/scope_test.md', self.content)
        self.assertEqual(result['declared'], 'full')
        self.assertIn('Manual Check A', result['scenarios'])
        self.assertIn('Manual Check B', result['scenarios'])
        self.assertEqual(result['visual_items'], 2)
        self.assertEqual(result['cross_validation_warnings'], [])


class TestRegressionScopeTargeted(unittest.TestCase):
    """Scenario: Regression Scope Targeted

    [Scope: targeted:Web Dashboard Display,Role Columns on Dashboard]
    yields only the named scenarios; visual is skipped.
    """

    def setUp(self):
        self.content = """\
# Feature: Targeted

## 3. Scenarios

### Manual Scenarios (Human Verification Required)

#### Scenario: Web Dashboard Display
    Given X When Y Then Z

#### Scenario: Role Columns on Dashboard
    Given A When B Then C

#### Scenario: Other Scenario
    Given D When E Then F

## Visual Specification

### Screen: Page
- [ ] Check item

## Implementation Notes
* Note.
"""

    @patch('critic._extract_scope_from_commit',
           return_value='targeted:Web Dashboard Display,Role Columns on Dashboard')
    def test_targeted_scope(self, _mock):
        result = compute_regression_set(
            'features/targeted.md', self.content)
        self.assertEqual(
            result['declared'],
            'targeted:Web Dashboard Display,Role Columns on Dashboard')
        self.assertEqual(
            sorted(result['scenarios']),
            ['Role Columns on Dashboard', 'Web Dashboard Display'])
        # Visual skipped for targeted (no Visual: prefix)
        self.assertEqual(result['visual_items'], 0)
        self.assertEqual(result['cross_validation_warnings'], [])

    @patch('critic._extract_scope_from_commit',
           return_value='targeted:Nonexistent Scenario')
    def test_targeted_unresolvable_name_warns(self, _mock):
        result = compute_regression_set(
            'features/targeted.md', self.content)
        self.assertEqual(len(result['cross_validation_warnings']), 1)
        self.assertIn('Nonexistent Scenario',
                      result['cross_validation_warnings'][0])
        self.assertIn('#### Scenario:',
                      result['cross_validation_warnings'][0])

    @patch('critic._extract_scope_from_commit',
           return_value='targeted:Web Dashboard Display,Bad Name')
    def test_targeted_mixed_valid_and_invalid_names(self, _mock):
        result = compute_regression_set(
            'features/targeted.md', self.content)
        self.assertEqual(result['scenarios'], ['Web Dashboard Display',
                                               'Bad Name'])
        self.assertEqual(len(result['cross_validation_warnings']), 1)
        self.assertIn('Bad Name', result['cross_validation_warnings'][0])

    @patch('critic._extract_scope_from_commit',
           return_value='targeted:Visual:Page')
    def test_targeted_visual_screen_resolved(self, _mock):
        result = compute_regression_set(
            'features/targeted.md', self.content)
        self.assertEqual(result['scenarios'], [])
        self.assertEqual(result['visual_items'], 1)
        self.assertEqual(result['cross_validation_warnings'], [])

    @patch('critic._extract_scope_from_commit',
           return_value='targeted:Visual:Nonexistent Screen')
    def test_targeted_visual_unresolvable_warns(self, _mock):
        result = compute_regression_set(
            'features/targeted.md', self.content)
        self.assertEqual(result['visual_items'], 0)
        self.assertEqual(len(result['cross_validation_warnings']), 1)
        self.assertIn('Visual:Nonexistent Screen',
                      result['cross_validation_warnings'][0])
        self.assertIn('### Screen:',
                      result['cross_validation_warnings'][0])

    @patch('critic._extract_scope_from_commit',
           return_value='targeted:Web Dashboard Display,Visual:Page')
    def test_targeted_mixed_scenario_and_visual(self, _mock):
        result = compute_regression_set(
            'features/targeted.md', self.content)
        self.assertEqual(result['scenarios'], ['Web Dashboard Display'])
        self.assertEqual(result['visual_items'], 1)
        self.assertEqual(result['cross_validation_warnings'], [])


class TestRegressionScopeCosmetic(unittest.TestCase):
    """Scenario: Regression Scope Cosmetic

    [Scope: cosmetic] yields empty regression set.
    """

    def setUp(self):
        self.content = """\
# Feature: Cosmetic

## 3. Scenarios

### Manual Scenarios (Human Verification Required)

#### Scenario: Some Manual
    Given X When Y Then Z

## Implementation Notes
* Note.
"""

    @patch('critic._get_previous_qa_status', return_value='CLEAN')
    @patch('critic._extract_scope_from_commit', return_value='cosmetic')
    @patch('critic._get_commit_changed_files', return_value=set())
    def test_cosmetic_empty_set(self, _mock_files, _mock_scope, _mock_qa):
        result = compute_regression_set(
            'features/cosmetic.md', self.content)
        self.assertEqual(result['declared'], 'cosmetic')
        self.assertEqual(result['scenarios'], [])
        self.assertEqual(result['visual_items'], 0)

    @patch('critic._get_previous_qa_status', return_value='CLEAN')
    @patch('critic._extract_scope_from_commit', return_value='cosmetic')
    @patch('critic._get_commit_changed_files',
           return_value={'tools/cdd/server.py'})
    def test_cosmetic_cross_validation_warning(
            self, _mock_files, _mock_scope, _mock_qa):
        """Cross-validation: cosmetic scope with changed files emits warning."""
        result = compute_regression_set(
            'features/cosmetic.md', self.content)
        self.assertEqual(result['declared'], 'cosmetic')
        self.assertEqual(len(result['cross_validation_warnings']), 1)
        self.assertIn('Cosmetic scope',
                      result['cross_validation_warnings'][0])


class TestRegressionScopeCosmeticFirstPassGuard(unittest.TestCase):
    """Scenario: Cosmetic Scope Does Not Skip First-Time Verification

    When [Scope: cosmetic] is declared but no prior clean QA pass exists,
    the Critic escalates to full verification.
    """

    def setUp(self):
        self.content = """\
# Feature: Cosmetic First Pass

## 3. Scenarios

### Manual Scenarios (Human Verification Required)

#### Scenario: Manual Scenario One
    Given something
    When something
    Then something
"""

    @patch('critic._get_previous_qa_status', return_value=None)
    @patch('critic._extract_scope_from_commit', return_value='cosmetic')
    def test_cosmetic_escalates_when_no_prior_qa(self, _mock_scope, _mock_qa):
        """No prior critic.json → escalate to full."""
        result = compute_regression_set(
            'features/cosmetic_first_pass.md', self.content)
        self.assertEqual(result['declared'], 'full')
        self.assertEqual(len(result['cross_validation_warnings']), 1)
        self.assertIn('no prior clean QA pass',
                      result['cross_validation_warnings'][0])
        self.assertEqual(result['scenarios'], ['Manual Scenario One'])

    @patch('critic._get_previous_qa_status', return_value='TODO')
    @patch('critic._extract_scope_from_commit', return_value='cosmetic')
    def test_cosmetic_escalates_when_qa_todo(self, _mock_scope, _mock_qa):
        """Prior qa=TODO → escalate to full."""
        result = compute_regression_set(
            'features/cosmetic_first_pass.md', self.content)
        self.assertEqual(result['declared'], 'full')
        self.assertIn('no prior clean QA pass',
                      result['cross_validation_warnings'][0])

    @patch('critic._get_previous_qa_status', return_value='CLEAN')
    @patch('critic._get_commit_changed_files', return_value=set())
    @patch('critic._extract_scope_from_commit', return_value='cosmetic')
    def test_cosmetic_suppressed_when_prior_qa_clean(
            self, _mock_scope, _mock_files, _mock_qa):
        """Prior qa=CLEAN → cosmetic suppression applies normally."""
        result = compute_regression_set(
            'features/cosmetic_first_pass.md', self.content)
        self.assertEqual(result['declared'], 'cosmetic')
        self.assertEqual(result['scenarios'], [])
        self.assertEqual(result['visual_items'], 0)
        self.assertEqual(result['cross_validation_warnings'], [])


class TestRegressionScopeDependencyOnly(unittest.TestCase):
    """Scenario: Regression Scope Dependency Only

    [Scope: dependency-only] includes scenarios touching changed dependency.
    """

    def setUp(self):
        self.content = """\
# Feature: Dep Only

> Prerequisite: features/arch_critic_policy.md

## 3. Scenarios

### Manual Scenarios (Human Verification Required)

#### Scenario: Dep Surface A
    Given X When Y Then Z

#### Scenario: Dep Surface B
    Given A When B Then C

## Implementation Notes
* Note.
"""

    @patch('critic._extract_scope_from_commit',
           return_value='dependency-only')
    def test_dependency_only_scope(self, _mock):
        result = compute_regression_set(
            'features/dep_only.md', self.content)
        self.assertEqual(result['declared'], 'dependency-only')
        # Conservative default: includes all manual scenarios
        self.assertIn('Dep Surface A', result['scenarios'])
        self.assertIn('Dep Surface B', result['scenarios'])


class TestRegressionScopeCrossValidationWarning(unittest.TestCase):
    """Scenario: Regression Scope Cross-Validation Warning

    Cosmetic scope + modified files triggers a cross-validation warning
    in both regression_scope.cross_validation_warnings and the report.
    """

    def setUp(self):
        self.content = """\
# Feature: Cross Val

## 3. Scenarios

### Manual Scenarios (Human Verification Required)

#### Scenario: Manual Test
    Given X When Y Then Z

## Implementation Notes
* Note.
"""

    @patch('critic._get_previous_qa_status', return_value='CLEAN')
    @patch('critic._extract_scope_from_commit', return_value='cosmetic')
    @patch('critic._get_commit_changed_files',
           return_value={'tools/cdd/server.py', 'tools/cdd/templates/index.html'})
    def test_cross_validation_warning_emitted(
            self, _mock_files, _mock_scope, _mock_qa):
        result = compute_regression_set(
            'features/cross_val.md', self.content)
        self.assertTrue(len(result['cross_validation_warnings']) > 0)
        warning = result['cross_validation_warnings'][0]
        self.assertIn('Cosmetic scope', warning)
        self.assertIn('tools/cdd/server.py', warning)


class TestBuilderActionItemsFromInvalidTargetedScopeNames(unittest.TestCase):
    """Scenario: Builder Action Items from Invalid Targeted Scope Names

    When a targeted scope references a scenario name that doesn't exist
    in the feature spec, a MEDIUM Builder action item with category
    scope_validation is generated.
    """

    def test_invalid_scope_name_generates_builder_action_item(self):
        result = _make_base_result()
        result['regression_scope'] = {
            'declared': 'targeted:Nonexistent Scenario',
            'scenarios': [],
            'visual_items': 0,
            'cross_validation_warnings': [
                "Targeted scope name 'Nonexistent Scenario' does not match "
                "any #### Scenario: title in the feature spec"
            ],
        }
        items = generate_action_items(result, cdd_status=None)
        scope_items = [
            i for i in items['builder'] if i['category'] == 'scope_validation'
        ]
        self.assertEqual(len(scope_items), 1)
        self.assertEqual(scope_items[0]['priority'], 'MEDIUM')
        self.assertIn('Nonexistent Scenario', scope_items[0]['description'])
        self.assertIn('Fix scope declaration', scope_items[0]['description'])

    def test_no_warnings_no_scope_validation_items(self):
        result = _make_base_result()
        result['regression_scope'] = {
            'declared': 'targeted:Valid Scenario',
            'scenarios': ['Valid Scenario'],
            'visual_items': 0,
            'cross_validation_warnings': [],
        }
        items = generate_action_items(result, cdd_status=None)
        scope_items = [
            i for i in items['builder'] if i['category'] == 'scope_validation'
        ]
        self.assertEqual(len(scope_items), 0)

    def test_no_regression_scope_key_no_scope_validation_items(self):
        result = _make_base_result()
        # No regression_scope key at all (default case)
        items = generate_action_items(result, cdd_status=None)
        scope_items = [
            i for i in items['builder'] if i['category'] == 'scope_validation'
        ]
        self.assertEqual(len(scope_items), 0)

    def test_first_pass_guard_warning_no_builder_item(self):
        """First-pass guard escalation warning must NOT generate a Builder item."""
        result = _make_base_result()
        result['regression_scope'] = {
            'declared': 'full',  # escalated from cosmetic by first-pass guard
            'scenarios': ['Some Scenario'],
            'visual_items': 0,
            'cross_validation_warnings': [
                'Cosmetic scope declared but no prior clean QA pass exists '
                'for this feature. Escalating to full verification.'
            ],
        }
        items = generate_action_items(result, cdd_status=None)
        scope_items = [
            i for i in items['builder'] if i['category'] == 'scope_validation'
        ]
        self.assertEqual(len(scope_items), 0)

    def test_cosmetic_cross_file_warning_no_builder_item(self):
        """Cosmetic scope cross-file warning must NOT generate a Builder item."""
        result = _make_base_result()
        result['regression_scope'] = {
            'declared': 'cosmetic',
            'scenarios': [],
            'visual_items': 0,
            'cross_validation_warnings': [
                'Cosmetic scope commit modifies files: tools/cdd/server.py. '
                'Manual scenarios may be affected.'
            ],
        }
        items = generate_action_items(result, cdd_status=None)
        scope_items = [
            i for i in items['builder'] if i['category'] == 'scope_validation'
        ]
        self.assertEqual(len(scope_items), 0)

class TestNoQAActionItemForTargetedScopeNamingOnlyAutomatedScenarios(
        unittest.TestCase):
    """Scenario: No QA Action Item for Targeted Scope Naming Only Automated
    Scenarios

    When a targeted scope names only automated scenarios (no manual ones),
    no QA verification action item should be generated for the feature.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        # Feature with ONLY automated scenarios (0 manual)
        feature_content = """\
# Feature: AutoOnly

> Label: "Tool: AutoOnly"

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Some Automated Scenario
    Given X
    When Y
    Then Z

### Manual Scenarios

None. All scenarios for this feature are fully automated.

## 4. Implementation Notes
* Note.
"""
        with open(os.path.join(self.features_dir, 'autoonly.md'), 'w') as f:
            f.write(feature_content)
        # Feature with mix of automated and manual scenarios
        mixed_content = """\
# Feature: Mixed

> Label: "Tool: Mixed"

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto One
    Given X When Y Then Z

### Manual Scenarios (Human Verification Required)

#### Scenario: Manual One
    Given A When B Then C

## 4. Implementation Notes
* Note.
"""
        with open(os.path.join(self.features_dir, 'mixed.md'), 'w') as f:
            f.write(mixed_content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_targeted_automated_only_no_qa_item(self):
        """Targeted scope naming only automated scenarios generates no QA item."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            cdd_status = {
                'features': {
                    'testing': [{'file': 'features/autoonly.md',
                                 'label': 'AutoOnly'}],
                    'todo': [],
                    'complete': [],
                },
            }
            result = {
                'feature_file': 'features/autoonly.md',
                'spec_gate': {'status': 'PASS', 'checks': {}},
                'implementation_gate': {
                    'status': 'PASS',
                    'checks': {
                        'traceability': {'status': 'PASS', 'coverage': 1.0,
                                         'detail': 'OK'},
                        'policy_adherence': {'status': 'PASS',
                                             'violations': [],
                                             'detail': 'OK'},
                        'structural_completeness': {'status': 'PASS',
                                                    'detail': 'OK'},
                        'builder_decisions': {
                            'status': 'PASS',
                            'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                        'DEVIATION': 0, 'DISCOVERY': 0},
                            'detail': 'OK',
                        },
                        'logic_drift': {'status': 'PASS', 'pairs': [],
                                        'detail': 'OK'},
                    },
                },
                'user_testing': {'status': 'CLEAN', 'bugs': 0,
                                 'discoveries': 0, 'intent_drifts': 0},
                'regression_scope': {
                    'declared': 'targeted:Some Automated Scenario',
                    'scenarios': ['Some Automated Scenario'],
                    'visual_items': 0,
                    'cross_validation_warnings': [],
                },
            }
            items = generate_action_items(result, cdd_status=cdd_status)
            qa_testing_items = [
                i for i in items['qa']
                if i['category'] == 'testing_status'
            ]
            self.assertEqual(len(qa_testing_items), 0,
                             'No QA item should be generated when all '
                             'targeted scenarios are automated')
        finally:
            critic.FEATURES_DIR = orig_features

    def test_targeted_mixed_keeps_only_manual_in_qa_item(self):
        """Targeted scope with mix of auto+manual keeps only manual in QA."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            cdd_status = {
                'features': {
                    'testing': [{'file': 'features/mixed.md',
                                 'label': 'Mixed'}],
                    'todo': [],
                    'complete': [],
                },
            }
            result = {
                'feature_file': 'features/mixed.md',
                'spec_gate': {'status': 'PASS', 'checks': {}},
                'implementation_gate': {
                    'status': 'PASS',
                    'checks': {
                        'traceability': {'status': 'PASS', 'coverage': 1.0,
                                         'detail': 'OK'},
                        'policy_adherence': {'status': 'PASS',
                                             'violations': [],
                                             'detail': 'OK'},
                        'structural_completeness': {'status': 'PASS',
                                                    'detail': 'OK'},
                        'builder_decisions': {
                            'status': 'PASS',
                            'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                        'DEVIATION': 0, 'DISCOVERY': 0},
                            'detail': 'OK',
                        },
                        'logic_drift': {'status': 'PASS', 'pairs': [],
                                        'detail': 'OK'},
                    },
                },
                'user_testing': {'status': 'CLEAN', 'bugs': 0,
                                 'discoveries': 0, 'intent_drifts': 0},
                'regression_scope': {
                    'declared': 'targeted:Auto One,Manual One',
                    'scenarios': ['Auto One', 'Manual One'],
                    'visual_items': 0,
                    'cross_validation_warnings': [],
                },
            }
            items = generate_action_items(result, cdd_status=cdd_status)
            qa_testing_items = [
                i for i in items['qa']
                if i['category'] == 'testing_status'
            ]
            self.assertEqual(len(qa_testing_items), 1)
            desc = qa_testing_items[0]['description']
            self.assertIn('1 targeted scenario(s)', desc)
            self.assertIn('Manual One', desc)
            self.assertNotIn('Auto One', desc)
        finally:
            critic.FEATURES_DIR = orig_features


# ===================================================================
# Targeted Scope Completeness Tests (Section 2.10)
# ===================================================================

class TestTargetedScopeCompletenessAudit(unittest.TestCase):
    """Scenario: Targeted Scope Completeness Audit

    When a feature has change_scope "targeted:..." and builder "TODO",
    the Critic flags scenarios/screens NOT listed in the targeted scope
    as MEDIUM-priority Architect action items.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        feature_content = """\
# Feature: ScopedFeature

> Label: "Tool: ScopedFeature"

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Alpha
    Given X When Y Then Z

#### Scenario: Auto Beta
    Given A When B Then C

### Manual Scenarios (Human Verification Required)

#### Scenario: Manual Gamma
    Given M When N Then O

#### Scenario: Manual Delta
    Given P When Q Then R

## Visual Specification

### Screen: Dashboard Overview
- [ ] Layout is correct

### Screen: Settings Panel
- [ ] Colors match
"""
        with open(os.path.join(
                self.features_dir, 'scoped_feature.md'), 'w') as f:
            f.write(feature_content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def _make_result(self, change_scope='targeted:Auto Alpha,Manual Gamma'):
        return {
            'feature_file': 'features/scoped_feature.md',
            'spec_gate': {'status': 'PASS', 'checks': {}},
            'implementation_gate': {
                'status': 'PASS',
                'checks': {
                    'traceability': {'status': 'PASS', 'coverage': 1.0,
                                     'detail': 'OK'},
                    'policy_adherence': {'status': 'PASS',
                                         'violations': [],
                                         'detail': 'OK'},
                    'structural_completeness': {'status': 'PASS',
                                                'detail': 'OK'},
                    'builder_decisions': {
                        'status': 'PASS',
                        'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                                    'DEVIATION': 0, 'DISCOVERY': 0},
                        'detail': 'OK',
                    },
                    'logic_drift': {'status': 'PASS', 'pairs': [],
                                    'detail': 'OK'},
                },
            },
            'user_testing': {'status': 'CLEAN', 'bugs': 0,
                             'discoveries': 0, 'intent_drifts': 0,
                             'spec_disputes': 0},
            'regression_scope': {
                'declared': change_scope,
                'scenarios': [],
                'visual_items': 0,
                'cross_validation_warnings': [],
            },
            'visual_spec': {'present': True, 'items': 2,
                            'screen_names': ['Dashboard Overview',
                                             'Settings Panel']},
        }

    def _make_cdd_status(self, lifecycle='todo',
                         change_scope='targeted:Auto Alpha,Manual Gamma'):
        return {
            'features': {
                lifecycle: [{
                    'file': 'features/scoped_feature.md',
                    'label': 'ScopedFeature',
                    'change_scope': change_scope,
                }],
                **{s: [] for s in ('todo', 'testing', 'complete')
                   if s != lifecycle},
            },
        }

    def test_flags_unscoped_scenarios_and_visual(self):
        """Targeted scope missing scenarios/screens generates Architect item."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            scope = 'targeted:Auto Alpha,Manual Gamma'
            result = self._make_result(scope)
            cdd = self._make_cdd_status('todo', scope)
            items = generate_action_items(result, cdd_status=cdd)
            arch_scope = [i for i in items['architect']
                          if i['category'] == 'targeted_scope_gap']
            self.assertEqual(len(arch_scope), 1)
            desc = arch_scope[0]['description']
            # Unscoped scenarios: Auto Beta, Manual Delta
            self.assertIn('Auto Beta', desc)
            self.assertIn('Manual Delta', desc)
            # Unscoped visual screens
            self.assertIn('Visual:Dashboard Overview', desc)
            self.assertIn('Visual:Settings Panel', desc)
            self.assertEqual(arch_scope[0]['priority'], 'MEDIUM')
        finally:
            critic.FEATURES_DIR = orig_features

    def test_no_flag_when_scope_is_full(self):
        """Features with full scope are exempt from completeness audit."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = self._make_result('full')
            cdd = self._make_cdd_status('todo', 'full')
            items = generate_action_items(result, cdd_status=cdd)
            arch_scope = [i for i in items['architect']
                          if i['category'] == 'targeted_scope_gap']
            self.assertEqual(len(arch_scope), 0)
        finally:
            critic.FEATURES_DIR = orig_features

    def test_no_flag_when_lifecycle_is_testing(self):
        """Features in TESTING state are exempt (only TODO is audited)."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            scope = 'targeted:Auto Alpha'
            result = self._make_result(scope)
            cdd = self._make_cdd_status('testing', scope)
            items = generate_action_items(result, cdd_status=cdd)
            arch_scope = [i for i in items['architect']
                          if i['category'] == 'targeted_scope_gap']
            self.assertEqual(len(arch_scope), 0)
        finally:
            critic.FEATURES_DIR = orig_features

    def test_no_flag_when_all_scenarios_covered(self):
        """Targeted scope covering all scenarios generates no item."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            scope = ('targeted:Auto Alpha,Auto Beta,Manual Gamma,'
                     'Manual Delta,Visual:Dashboard Overview,'
                     'Visual:Settings Panel')
            result = self._make_result(scope)
            cdd = self._make_cdd_status('todo', scope)
            items = generate_action_items(result, cdd_status=cdd)
            arch_scope = [i for i in items['architect']
                          if i['category'] == 'targeted_scope_gap']
            self.assertEqual(len(arch_scope), 0)
        finally:
            critic.FEATURES_DIR = orig_features

    def test_visual_only_unscoped(self):
        """Targeted scope with all scenarios but missing visual screens."""
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            scope = ('targeted:Auto Alpha,Auto Beta,Manual Gamma,'
                     'Manual Delta')
            result = self._make_result(scope)
            cdd = self._make_cdd_status('todo', scope)
            items = generate_action_items(result, cdd_status=cdd)
            arch_scope = [i for i in items['architect']
                          if i['category'] == 'targeted_scope_gap']
            self.assertEqual(len(arch_scope), 1)
            desc = arch_scope[0]['description']
            # Only visual screens should be flagged
            self.assertNotIn('Auto Alpha', desc)
            self.assertNotIn('Manual Gamma', desc)
            self.assertIn('Visual:Dashboard Overview', desc)
            self.assertIn('Visual:Settings Panel', desc)
        finally:
            critic.FEATURES_DIR = orig_features


# ===================================================================
# Visual Specification Tests (Section 2.13)
# ===================================================================

class TestVisualSpecificationDetected(unittest.TestCase):
    """Scenario: Visual Specification Detected

    Feature with ## Visual Specification section reports screens and items.
    """

    def test_visual_spec_detected(self):
        content = """\
# Feature: Visual

## 1. Overview
Overview.

## Visual Specification

### Screen: Dashboard
- [ ] Layout is responsive
- [ ] Colors match brand
- [x] Logo is visible

### Screen: Settings
- [ ] Toggle switches align
- [ ] Font sizes correct
- [ ] Spacing consistent
- [ ] Dark mode supported
- [ ] Scrollbar visible

## Implementation Notes
* Note.
"""
        result = parse_visual_spec(content)
        self.assertTrue(result['present'])
        self.assertEqual(result['screens'], 2)
        self.assertEqual(result['items'], 8)

    def test_visual_spec_not_present(self):
        content = """\
# Feature: No Visual

## 1. Overview
Overview.

## Implementation Notes
* Note.
"""
        result = parse_visual_spec(content)
        self.assertFalse(result['present'])
        self.assertEqual(result['screens'], 0)
        self.assertEqual(result['items'], 0)


class TestVisualSpecificationDetectedWithNumberedHeader(unittest.TestCase):
    """Scenario: Visual Specification Detected with Numbered Section Header

    Feature with ## 4. Visual Specification (numbered prefix) reports
    screens and items correctly.
    """

    def test_numbered_header_detected(self):
        content = """\
# Feature: Numbered Visual

## 1. Overview
Overview.

## 4. Visual Specification

### Screen: Main View
- [ ] Layout is correct
- [ ] Colors match tokens
- [x] Logo visible

## Implementation Notes
* Note.
"""
        result = parse_visual_spec(content)
        self.assertTrue(result['present'])
        self.assertEqual(result['screens'], 1)
        self.assertEqual(result['items'], 3)
        self.assertEqual(result['screen_names'], ['Main View'])


class TestVisualSpecificationExemptFromTraceability(unittest.TestCase):
    """Scenario: Visual Specification Exempt from Traceability

    Visual checklist items do not affect traceability coverage.
    The traceability engine only processes scenarios parsed by
    parse_scenarios(), which does not extract visual spec items.
    """

    def test_visual_items_not_parsed_as_scenarios(self):
        """Visual spec items are not returned by parse_scenarios()."""
        content = """\
# Feature: Visual Trace

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Test
    Given X
    When Y
    Then Z

## Visual Specification

### Screen: Dashboard
- [ ] Check layout
- [ ] Check colors
"""
        scenarios = parse_scenarios(content)
        # Only the automated scenario is parsed, not visual items
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0]['title'], 'Auto Test')

    def test_visual_items_excluded_from_traceability(self):
        """Visual items don't produce traceability gaps."""
        content = """\
# Feature: Visual Trace

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto Test
    Given X
    When Y
    Then Z

## Visual Specification

### Screen: Dashboard
- [ ] Check layout
- [ ] Check colors
"""
        scenarios = parse_scenarios(content)
        # Traceability only considers automated scenarios
        automated = [s for s in scenarios if not s.get('is_manual')]
        self.assertEqual(len(automated), 1)
        # Visual items are not in the scenario list at all
        titles = [s['title'] for s in scenarios]
        self.assertNotIn('Check layout', titles)
        self.assertNotIn('Check colors', titles)


# ===================================================================
# Companion File Convention Tests
# ===================================================================

class TestCompanionFileResolution(unittest.TestCase):
    """Scenario: Companion File Resolution for Implementation Gate

    Given a feature file with a stub referencing a companion .impl.md file,
    resolve_impl_notes() should read and return the companion file content.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_resolves_companion_file(self):
        """Stub with companion reference reads the companion file."""
        feature_path = os.path.join(self.tmpdir, 'my_feature.md')
        companion_path = os.path.join(self.tmpdir, 'my_feature.impl.md')

        feature_content = """\
# Feature: My Feature

## Overview
A feature.

## Requirements
Some requirements.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Test
    Given X
    When Y
    Then Z

## Implementation Notes
See [my_feature.impl.md](my_feature.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.
"""
        companion_content = """\
# Implementation Notes: My Feature

*   **Tool Location:** Some tool info.
*   **[CLARIFICATION]** Some clarification. (Severity: INFO)
*   **[DEVIATION]** Some deviation. (Severity: HIGH)
"""
        with open(feature_path, 'w') as f:
            f.write(feature_content)
        with open(companion_path, 'w') as f:
            f.write(companion_content)

        result = resolve_impl_notes(feature_content, feature_path)
        self.assertIn('[CLARIFICATION]', result)
        self.assertIn('[DEVIATION]', result)
        self.assertIn('Tool Location', result)

    def test_backward_compatible_inline_notes(self):
        """Feature with inline notes (no companion) returns inline content."""
        feature_path = os.path.join(self.tmpdir, 'inline_feature.md')

        feature_content = """\
# Feature: Inline

## Overview
A feature.

## Implementation Notes
*   **[CLARIFICATION]** Inline clarification. (Severity: INFO)
*   Some inline knowledge.
"""
        with open(feature_path, 'w') as f:
            f.write(feature_content)

        result = resolve_impl_notes(feature_content, feature_path)
        self.assertIn('[CLARIFICATION]', result)
        self.assertIn('Inline clarification', result)

    def test_companion_missing_returns_stub(self):
        """Stub referencing non-existent companion returns stub text."""
        feature_path = os.path.join(self.tmpdir, 'orphan.md')

        feature_content = """\
# Feature: Orphan

## Implementation Notes
See [orphan.impl.md](orphan.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.
"""
        with open(feature_path, 'w') as f:
            f.write(feature_content)

        result = resolve_impl_notes(feature_content, feature_path)
        # Returns the stub text since companion doesn't exist
        self.assertIn('orphan.impl.md', result)


class TestCompanionStubNotFlaggedAsEmpty(unittest.TestCase):
    """Scenario: Stub With Companion Reference Not Flagged as Empty

    A stub containing a companion file link should not be considered
    'empty notes' by section completeness checks.
    """

    def test_stub_is_not_empty(self):
        """Stub with companion ref has non-empty impl notes."""
        content = """\
# Feature: Stubbed

## Overview
A feature.

## 2. Requirements
Some requirements.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Test
    Given X
    When Y
    Then Z

## Implementation Notes
See [stubbed.impl.md](stubbed.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.
"""
        sections = parse_sections(content)
        result = check_section_completeness(content, sections)
        # Should be PASS, not WARN about empty notes
        self.assertEqual(result['status'], 'PASS')

    def test_truly_empty_notes_warns(self):
        """Empty implementation notes should produce a WARN."""
        content = """\
# Feature: Empty

## Overview
A feature.

## 2. Requirements
Some requirements.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Test
    Given X
    When Y
    Then Z

## Implementation Notes
"""
        sections = parse_sections(content)
        result = check_section_completeness(content, sections)
        self.assertEqual(result['status'], 'WARN')
        self.assertIn('empty', result['detail'].lower())


class TestCompanionFileOnDiskSuppressesWarning(unittest.TestCase):
    """Scenario: Feature With No Implementation Notes Section But Companion On Disk

    When a feature file has no ## Implementation Notes section at all,
    but a companion .impl.md file exists on disk, check_section_completeness
    should return PASS (not WARN) when given the feature_path.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_companion_on_disk_returns_pass(self):
        """Feature with no impl notes section but companion file → PASS."""
        feature_path = os.path.join(self.tmpdir, 'my_feature.md')
        companion_path = os.path.join(self.tmpdir, 'my_feature.impl.md')
        content = """\
# Feature: My Feature

## Overview
A feature.

## 2. Requirements
Some requirements.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Test
    Given X
    When Y
    Then Z
"""
        with open(feature_path, 'w') as f:
            f.write(content)
        with open(companion_path, 'w') as f:
            f.write('# Implementation Notes: My Feature\nSome notes.\n')

        sections = parse_sections(content)
        result = check_section_completeness(content, sections,
                                            feature_path=feature_path)
        self.assertEqual(result['status'], 'PASS')

    def test_no_companion_no_section_warns(self):
        """Feature with no impl notes section and no companion file → WARN."""
        feature_path = os.path.join(self.tmpdir, 'lonely_feature.md')
        content = """\
# Feature: Lonely

## Overview
A feature.

## 2. Requirements
Some requirements.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Test
    Given X
    When Y
    Then Z
"""
        with open(feature_path, 'w') as f:
            f.write(content)

        sections = parse_sections(content)
        result = check_section_completeness(content, sections,
                                            feature_path=feature_path)
        self.assertEqual(result['status'], 'WARN')
        self.assertIn('empty', result['detail'].lower())

    def test_no_feature_path_still_warns(self):
        """Without feature_path, missing impl notes still warns (backward compat)."""
        content = """\
# Feature: NoPath

## Overview
A feature.

## 2. Requirements
Some requirements.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Test
    Given X
    When Y
    Then Z
"""
        sections = parse_sections(content)
        result = check_section_completeness(content, sections)
        self.assertEqual(result['status'], 'WARN')
        self.assertIn('empty', result['detail'].lower())


class TestFeatureScanExcludesCompanionFiles(unittest.TestCase):
    """Scenario: Feature Scanning Excludes Companion Files

    When scanning for feature files, *.impl.md files must not be
    included in the results.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create a feature file and a companion file
        with open(os.path.join(self.tmpdir, 'my_feature.md'), 'w') as f:
            f.write('# Feature: My Feature\n')
        with open(os.path.join(self.tmpdir, 'my_feature.impl.md'), 'w') as f:
            f.write('# Implementation Notes\n')
        with open(os.path.join(self.tmpdir, 'another.md'), 'w') as f:
            f.write('# Feature: Another\n')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_impl_files_excluded_from_scan(self):
        """The *.impl.md filter correctly excludes companion files."""
        feature_files = sorted([
            f for f in os.listdir(self.tmpdir)
            if f.endswith('.md') and not f.endswith('.impl.md')
        ])
        self.assertEqual(feature_files, ['another.md', 'my_feature.md'])
        self.assertNotIn('my_feature.impl.md', feature_files)


# ===================================================================
# Visual Specification Reference Extraction Tests (Section 2.13)
# ===================================================================

class TestVisualSpecReferenceExtraction(unittest.TestCase):
    """Test parse_visual_spec() extracts per-screen reference metadata."""

    def test_local_reference(self):
        content = """\
# Feature: Ref Test

## Visual Specification

> **Design Anchor:** features/design_visual_standards.md
> **Inheritance:** Colors, typography, and theme switching per anchor.

### Screen: Dashboard
- **Reference:** `features/design/my_feature/dashboard-layout.png`
- **Processed:** 2026-02-15
- **Description:** A structured description of the dashboard layout.
- [ ] Layout correct
- [ ] Colors match
"""
        result = parse_visual_spec(content)
        self.assertTrue(result['present'])
        self.assertEqual(result['screens'], 1)
        self.assertEqual(len(result['references']), 1)
        ref = result['references'][0]
        self.assertEqual(ref['screen_name'], 'Dashboard')
        self.assertEqual(ref['reference_path'],
                         'features/design/my_feature/dashboard-layout.png')
        self.assertEqual(ref['reference_type'], 'local')
        self.assertEqual(ref['processed_date'], '2026-02-15')
        self.assertTrue(ref['has_description'])
        self.assertEqual(result['unprocessed_count'], 0)

    def test_figma_reference(self):
        content = """\
# Feature: Figma Test

## Visual Specification

### Screen: Settings
- **Reference:** [Figma](https://figma.com/file/abc123)
- **Processed:** N/A
- **Description:** The settings panel design.
- [ ] Check layout
"""
        result = parse_visual_spec(content)
        ref = result['references'][0]
        self.assertEqual(ref['reference_type'], 'figma')
        self.assertEqual(ref['reference_path'],
                         'https://figma.com/file/abc123')
        self.assertIsNone(ref['processed_date'])
        self.assertTrue(ref['has_description'])

    def test_live_reference(self):
        content = """\
# Feature: Live Test

## Visual Specification

### Screen: Current UI
- **Reference:** [Live](https://example.com/dashboard)
- **Processed:** 2026-01-01
- **Description:** Current dashboard state.
- [ ] Matches design
"""
        result = parse_visual_spec(content)
        ref = result['references'][0]
        self.assertEqual(ref['reference_type'], 'live')
        self.assertEqual(ref['reference_path'],
                         'https://example.com/dashboard')

    def test_no_reference(self):
        content = """\
# Feature: NA Test

## Visual Specification

### Screen: Conceptual
- **Reference:** N/A
- **Processed:** N/A
- **Description:** Conceptual design based on requirements.
- [ ] Layout follows convention
"""
        result = parse_visual_spec(content)
        ref = result['references'][0]
        self.assertEqual(ref['reference_type'], 'none')
        self.assertIsNone(ref['reference_path'])

    def test_unprocessed_artifact_count(self):
        content = """\
# Feature: Unprocessed

## Visual Specification

### Screen: Dashboard
- **Reference:** `features/design/my_feature/mockup.png`
- **Processed:** N/A
"""
        result = parse_visual_spec(content)
        ref = result['references'][0]
        self.assertFalse(ref['has_description'])
        self.assertEqual(result['unprocessed_count'], 1)

    def test_multiple_screens_mixed(self):
        content = """\
# Feature: Multi Screen

## Visual Specification

### Screen: Home
- **Reference:** `features/design/multi/home.png`
- **Processed:** 2026-01-01
- **Description:** Home page layout.
- [ ] Header visible

### Screen: Profile
- **Reference:** [Figma](https://figma.com/file/xyz)
- **Processed:** N/A
- [ ] Avatar renders
"""
        result = parse_visual_spec(content)
        self.assertEqual(result['screens'], 2)
        self.assertEqual(len(result['references']), 2)
        home = result['references'][0]
        profile = result['references'][1]
        self.assertEqual(home['reference_type'], 'local')
        self.assertTrue(home['has_description'])
        self.assertEqual(profile['reference_type'], 'figma')
        self.assertFalse(profile['has_description'])
        self.assertEqual(result['unprocessed_count'], 1)

    def test_no_visual_spec_returns_empty_references(self):
        content = """\
# Feature: Plain

## Overview
Just a feature.
"""
        result = parse_visual_spec(content)
        self.assertFalse(result['present'])
        self.assertEqual(result['references'], [])
        self.assertEqual(result['unprocessed_count'], 0)
        self.assertEqual(result['stale_count'], 0)
        self.assertEqual(result['missing_reference_count'], 0)


class TestValidateVisualReferences(unittest.TestCase):
    """Test validate_visual_references() for integrity, staleness,
    and unprocessed artifact detection."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_local_reference(self):
        visual_spec = {
            'present': True, 'screens': 1, 'items': 2,
            'screen_names': ['Dashboard'],
            'references': [{
                'screen_name': 'Dashboard',
                'reference_path': 'features/design/my_feature/missing.png',
                'reference_type': 'local',
                'processed_date': '2026-01-01',
                'has_description': True,
            }],
            'unprocessed_count': 0, 'stale_count': 0,
            'missing_reference_count': 0,
        }
        items = validate_visual_references(visual_spec, self.tmpdir)
        missing = [i for i in items
                   if i['category'] == 'missing_design_reference']
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]['priority'], 'MEDIUM')
        self.assertEqual(visual_spec['missing_reference_count'], 1)

    def test_unprocessed_artifact(self):
        visual_spec = {
            'present': True, 'screens': 1, 'items': 0,
            'screen_names': ['Dashboard'],
            'references': [{
                'screen_name': 'Dashboard',
                'reference_path': 'features/design/test/mockup.png',
                'reference_type': 'local',
                'processed_date': None,
                'has_description': False,
            }],
            'unprocessed_count': 1, 'stale_count': 0,
            'missing_reference_count': 0,
        }
        items = validate_visual_references(visual_spec, self.tmpdir)
        unprocessed = [i for i in items
                       if i['category'] == 'unprocessed_artifact']
        self.assertEqual(len(unprocessed), 1)
        self.assertEqual(unprocessed[0]['priority'], 'HIGH')

    def test_stale_description(self):
        # Create a local artifact file with a recent mtime
        artifact_dir = os.path.join(
            self.tmpdir, 'features', 'design', 'test')
        os.makedirs(artifact_dir, exist_ok=True)
        artifact_path = os.path.join(artifact_dir, 'layout.png')
        with open(artifact_path, 'w') as f:
            f.write('fake image')
        # Set file mtime to Feb 2026 (well after the processed date)
        import time
        future_ts = time.mktime((2026, 3, 15, 0, 0, 0, 0, 0, 0))
        os.utime(artifact_path, (future_ts, future_ts))

        visual_spec = {
            'present': True, 'screens': 1, 'items': 2,
            'screen_names': ['Dashboard'],
            'references': [{
                'screen_name': 'Dashboard',
                'reference_path': 'features/design/test/layout.png',
                'reference_type': 'local',
                'processed_date': '2026-01-01',
                'has_description': True,
            }],
            'unprocessed_count': 0, 'stale_count': 0,
            'missing_reference_count': 0,
        }
        items = validate_visual_references(visual_spec, self.tmpdir)
        stale = [i for i in items
                 if i['category'] == 'stale_design_description']
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]['priority'], 'LOW')
        self.assertEqual(visual_spec['stale_count'], 1)

    def test_current_description_not_stale(self):
        # Create a local artifact file
        artifact_dir = os.path.join(
            self.tmpdir, 'features', 'design', 'test')
        os.makedirs(artifact_dir, exist_ok=True)
        artifact_path = os.path.join(artifact_dir, 'layout.png')
        with open(artifact_path, 'w') as f:
            f.write('fake image')
        # Set file mtime to Jan 1, 2026
        import time
        old_ts = time.mktime((2026, 1, 1, 0, 0, 0, 0, 0, 0))
        os.utime(artifact_path, (old_ts, old_ts))

        visual_spec = {
            'present': True, 'screens': 1, 'items': 1,
            'screen_names': ['Dashboard'],
            'references': [{
                'screen_name': 'Dashboard',
                'reference_path': 'features/design/test/layout.png',
                'reference_type': 'local',
                'processed_date': '2026-02-01',
                'has_description': True,
            }],
            'unprocessed_count': 0, 'stale_count': 0,
            'missing_reference_count': 0,
        }
        items = validate_visual_references(visual_spec, self.tmpdir)
        stale = [i for i in items
                 if i['category'] == 'stale_design_description']
        self.assertEqual(len(stale), 0)
        self.assertEqual(visual_spec['stale_count'], 0)

    def test_url_references_skip_integrity_check(self):
        visual_spec = {
            'present': True, 'screens': 2, 'items': 4,
            'screen_names': ['Figma View', 'Live View'],
            'references': [
                {
                    'screen_name': 'Figma View',
                    'reference_path': 'https://figma.com/file/abc',
                    'reference_type': 'figma',
                    'processed_date': None,
                    'has_description': True,
                },
                {
                    'screen_name': 'Live View',
                    'reference_path': 'https://example.com',
                    'reference_type': 'live',
                    'processed_date': '2026-01-01',
                    'has_description': True,
                },
            ],
            'unprocessed_count': 0, 'stale_count': 0,
            'missing_reference_count': 0,
        }
        items = validate_visual_references(visual_spec, self.tmpdir)
        # No integrity issues for URL references
        self.assertEqual(len(items), 0)

    def test_clean_visual_spec_no_items(self):
        # Create a valid local artifact
        artifact_dir = os.path.join(
            self.tmpdir, 'features', 'design', 'test')
        os.makedirs(artifact_dir, exist_ok=True)
        artifact_path = os.path.join(artifact_dir, 'layout.png')
        with open(artifact_path, 'w') as f:
            f.write('fake image')
        import time
        old_ts = time.mktime((2026, 1, 1, 0, 0, 0, 0, 0, 0))
        os.utime(artifact_path, (old_ts, old_ts))

        visual_spec = {
            'present': True, 'screens': 1, 'items': 2,
            'screen_names': ['Dashboard'],
            'references': [{
                'screen_name': 'Dashboard',
                'reference_path': 'features/design/test/layout.png',
                'reference_type': 'local',
                'processed_date': '2026-02-01',
                'has_description': True,
            }],
            'unprocessed_count': 0, 'stale_count': 0,
            'missing_reference_count': 0,
        }
        items = validate_visual_references(visual_spec, self.tmpdir)
        self.assertEqual(len(items), 0)
        self.assertEqual(visual_spec['stale_count'], 0)
        self.assertEqual(visual_spec['missing_reference_count'], 0)


# ===================================================================
# Test runner with output to tests/critic_tool/tests.json
# ===================================================================

if __name__ == '__main__':
    project_root = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
    tests_out_dir = os.path.join(project_root, 'tests', 'critic_tool')
    os.makedirs(tests_out_dir, exist_ok=True)
    status_file = os.path.join(tests_out_dir, 'tests.json')

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    status = 'PASS' if result.wasSuccessful() else 'FAIL'
    with open(status_file, 'w') as f:
        json.dump({
            'status': status,
            'tests': result.testsRun,
            'failures': len(result.failures) + len(result.errors),
            'tool': 'critic',
            'runner': 'unittest',
        }, f)
    print(f'\n{status_file}: {status}')

    sys.exit(0 if result.wasSuccessful() else 1)
