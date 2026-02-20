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
        self.cache_dir = tempfile.mkdtemp()
        self._orig_cache = logic_drift.CACHE_DIR
        logic_drift.CACHE_DIR = self.cache_dir
        self.pairs = [{
            'scenario_title': 'Test Scenario',
            'scenario_body': 'Given X\nWhen Y\nThen Z',
            'test_functions': [{
                'name': 'test_scenario',
                'body': 'def test_scenario():\n    assert True',
            }],
        }]

    def tearDown(self):
        logic_drift.CACHE_DIR = self._orig_cache
        shutil.rmtree(self.cache_dir, ignore_errors=True)

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
            self.pairs, '/tmp', 'test', 'tools', 'claude-sonnet-4-20250514',
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
            self.pairs, '/tmp', 'test', 'tools', 'claude-sonnet-4-20250514',
        )
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['pairs'][0]['verdict'], 'DIVERGENT')

    @patch('logic_drift.HAS_ANTHROPIC', True)
    @patch('logic_drift.anthropic')
    def test_cache_hit_no_api_call(self, mock_anthropic_mod):
        mock_client = MagicMock()
        mock_anthropic_mod.Anthropic.return_value = mock_client

        # Pre-populate cache
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
            self.pairs, '/tmp', 'test', 'tools', 'claude-sonnet-4-20250514',
        )
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['pairs'][0]['verdict'], 'ALIGNED')
        self.assertEqual(result['pairs'][0]['reasoning'], 'Cached result')
        # API should NOT have been called
        mock_client.messages.create.assert_not_called()

    @patch('logic_drift.HAS_ANTHROPIC', False)
    def test_no_anthropic_graceful_skip(self):
        result = logic_drift.run_logic_drift(
            self.pairs, '/tmp', 'test', 'tools', 'claude-sonnet-4-20250514',
        )
        self.assertEqual(result['status'], 'WARN')
        self.assertIn('not installed', result['detail'])
        self.assertEqual(result['pairs'], [])


class TestCheckLogicDriftEnabled(unittest.TestCase):
    """Integration test: check_logic_drift when LLM is enabled."""

    @patch('critic.discover_test_files')
    @patch('critic.extract_test_functions')
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
- [BUG] (OPEN) Something broken
- [DISCOVERY] (SPEC_UPDATED) New behavior found
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
- [BUG] (RESOLVED) Fixed the thing
"""
        result = run_user_testing_audit(content)
        self.assertEqual(result['status'], 'CLEAN')
        self.assertEqual(result['bugs'], 1)

    def test_intent_drift_open(self):
        content = """\
## User Testing Discoveries
- [INTENT_DRIFT] (OPEN) Behavior is technically correct but misses intent
"""
        result = run_user_testing_audit(content)
        self.assertEqual(result['status'], 'HAS_OPEN_ITEMS')
        self.assertEqual(result['intent_drifts'], 1)


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
        self.assertEqual(sc_class['detail'], 'N/A - policy file')

    def test_policy_file_gherkin_quality_skipped(self):
        result = run_spec_gate(
            POLICY_FILE_CONTENT, 'arch_test_policy.md', self.features_dir)
        gq = result['checks']['gherkin_quality']
        self.assertEqual(gq['status'], 'PASS')
        self.assertEqual(gq['detail'], 'N/A - policy file')

    def test_policy_file_overall_passes(self):
        result = run_spec_gate(
            POLICY_FILE_CONTENT, 'arch_test_policy.md', self.features_dir)
        self.assertEqual(result['status'], 'PASS')


class TestImplementationGatePolicyFileExempt(unittest.TestCase):
    """Scenario: Implementation Gate Policy File Exempt"""

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

    def test_exempt_gate_returns_pass(self):
        gate = _policy_exempt_implementation_gate()
        self.assertEqual(gate['status'], 'PASS')

    def test_exempt_gate_all_checks_pass(self):
        gate = _policy_exempt_implementation_gate()
        for check_name, check_result in gate['checks'].items():
            self.assertEqual(
                check_result['status'], 'PASS',
                f'{check_name} should be PASS for policy file')

    def test_exempt_gate_detail_says_exempt(self):
        gate = _policy_exempt_implementation_gate()
        for check_name, check_result in gate['checks'].items():
            self.assertIn(
                'N/A - policy file exempt', check_result['detail'],
                f'{check_name} detail should say exempt')

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
# Bash Test File Discovery and Scenario Parsing Tests
# ===================================================================

class TestBashTestFileDiscovery(unittest.TestCase):
    """Scenario: Bash Test File Discovery"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.test_dir = os.path.join(self.root, 'tests', 'my_feature')
        os.makedirs(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_discovers_both_py_and_sh(self):
        with open(os.path.join(self.test_dir, 'test_feature.py'), 'w') as f:
            f.write('def test_something(): pass\n')
        with open(os.path.join(self.test_dir, 'test_feature.sh'), 'w') as f:
            f.write('echo "[Scenario] Test Something"\n')
        files = discover_test_files(self.root, 'my_feature', tools_root='tools')
        extensions = {os.path.splitext(f)[1] for f in files}
        self.assertIn('.py', extensions)
        self.assertIn('.sh', extensions)

    def test_discovers_sh_only(self):
        with open(os.path.join(self.test_dir, 'test_feature.sh'), 'w') as f:
            f.write('echo "[Scenario] Test Something"\n')
        files = discover_test_files(self.root, 'my_feature', tools_root='tools')
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith('.sh'))


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

    def test_unknown_extension(self):
        path = os.path.join(self.test_dir, 'test_sample.rb')
        with open(path, 'w') as f:
            f.write('# ruby test\n')
        entries = extract_test_entries(path)
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
    def test_excludes_agentic_devops(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='?? .agentic_devops/config.json\n?? real_file.py\n',
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
- [SPEC_DISPUTE] (OPEN) User disagrees with expected behavior
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
- [SPEC_DISPUTE] (OPEN) First dispute
- [SPEC_DISPUTE] (OPEN) Second dispute
- [BUG] (OPEN) A bug too
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
- [SPEC_DISPUTE] (OPEN) User disagrees with Auto Test expected behavior
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
- [SPEC_DISPUTE] (OPEN) User disagrees with behavior
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
- [BUG] (OPEN) Something is broken
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
- [SPEC_DISPUTE] (OPEN) Scenario expected wrong behavior
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
- [SPEC_DISPUTE] (OPEN) User disagrees with behavior
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


class TestRoleStatusQATODOForSpecUpdatedItems(unittest.TestCase):
    """Scenario: Role Status QA TODO for SPEC_UPDATED Items

    SPEC_UPDATED items trigger QA TODO regardless of lifecycle state.
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

    def test_spec_updated_makes_qa_todo_in_todo_lifecycle(self):
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
            self.assertEqual(status['qa'], 'TODO')
        finally:
            critic.FEATURES_DIR = orig_features


class TestRoleStatusQATODOForHasOpenItems(unittest.TestCase):
    """Scenario: Role Status QA TODO for HAS_OPEN_ITEMS

    HAS_OPEN_ITEMS with OPEN discoveries (not BUGs/SPEC_DISPUTEs)
    triggers QA TODO regardless of lifecycle state.
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

    def test_has_open_items_makes_qa_todo_in_todo_lifecycle(self):
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
            status = compute_role_status(result, cdd_status)
            self.assertEqual(status['qa'], 'TODO')
        finally:
            critic.FEATURES_DIR = orig_features


class TestRoleStatusQANAForTestingNoManualScenarios(unittest.TestCase):
    """Scenario: Role Status QA N/A for TESTING Feature with No Manual Scenarios

    A feature in TESTING state with 0 manual scenarios and CLEAN user
    testing should have QA = N/A (nothing for QA to verify).
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
