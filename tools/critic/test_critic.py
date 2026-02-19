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
    match_scenario_to_tests,
    parse_traceability_overrides,
    run_traceability,
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
    generate_critic_json,
    generate_critic_report,
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
        self.assertEqual(result['status'], 'FAIL')

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
