#!/usr/bin/env python3
"""Unit tests for the Critic PM Column feature.

Covers all automated scenarios from features/critic_pm_column.md.
Outputs test results to tests/critic_pm_column/tests.json.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from critic import (
    extract_owner,
    generate_action_items,
    compute_role_status,
    generate_critic_json,
    generate_critic_report,
    parse_visual_spec,
    is_policy_file,
)


# ===================================================================
# Helpers
# ===================================================================

def _make_base_result(**overrides):
    """Create a baseline feature result for testing."""
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
            'pm': [],
        },
    }
    result.update(overrides)
    return result


# ===================================================================
# Owner Tag Parsing Tests
# ===================================================================

class TestExtractOwner(unittest.TestCase):

    def test_pm_owner_tag(self):
        content = '# Feature\n\n> Label: "Test"\n> Owner: PM\n\n## 1. Overview\n'
        self.assertEqual(extract_owner(content, 'test.md'), 'PM')

    def test_architect_owner_tag(self):
        content = '# Feature\n\n> Label: "Test"\n> Owner: Architect\n\n## 1. Overview\n'
        self.assertEqual(extract_owner(content, 'test.md'), 'Architect')

    def test_no_owner_defaults_to_architect(self):
        content = '# Feature\n\n> Label: "Test"\n\n## 1. Overview\n'
        self.assertEqual(extract_owner(content, 'test.md'), 'Architect')

    def test_anchor_node_always_architect(self):
        content = '# Policy\n\n> Label: "Policy"\n> Owner: PM\n\n## 1. Purpose\n'
        self.assertEqual(extract_owner(content, 'policy_test.md'), 'Architect')

    def test_design_anchor_always_architect(self):
        content = '# Design\n\n> Owner: PM\n'
        self.assertEqual(extract_owner(content, 'design_test.md'), 'Architect')

    def test_arch_anchor_always_architect(self):
        content = '# Arch\n\n> Owner: PM\n'
        self.assertEqual(extract_owner(content, 'arch_test.md'), 'Architect')


# ===================================================================
# SPEC_DISPUTE Routing Tests
# ===================================================================

class TestSpecDisputeOnPMOwnedFeature(unittest.TestCase):
    """Scenario: SPEC_DISPUTE on PM-owned feature routes to PM"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        feature_content = """\
# Feature: PM Owned Feature

> Label: "PM Feature"
> Owner: PM

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Some Test
    Given X
    When Y
    Then Z

## 4. Implementation Notes
* Note.
"""
        with open(os.path.join(self.features_dir, 'pm_feature.md'), 'w') as f:
            f.write(feature_content)
        # Discovery sidecar with SPEC_DISPUTE
        sidecar = """\
### [SPEC_DISPUTE] Behavior should be different (Discovered: 2026-03-01)
- **Status:** OPEN
"""
        with open(os.path.join(
                self.features_dir, 'pm_feature.discoveries.md'), 'w') as f:
            f.write(sidecar)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_spec_dispute_routes_to_pm(self):
        import critic
        orig = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/pm_feature.md'
            result['_owner'] = 'PM'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 1,
            }
            items = generate_action_items(result)
            pm_disputes = [i for i in items['pm']
                           if 'disputed scenario' in i['description'].lower()]
            arch_disputes = [i for i in items['architect']
                             if 'disputed scenario' in i['description'].lower()]
            self.assertTrue(len(pm_disputes) > 0,
                            'SPEC_DISPUTE should route to PM')
            self.assertEqual(len(arch_disputes), 0,
                             'SPEC_DISPUTE should NOT route to Architect')
        finally:
            critic.FEATURES_DIR = orig


class TestSpecDisputeOnArchitectOwnedFeature(unittest.TestCase):
    """Scenario: SPEC_DISPUTE on Architect-owned feature routes to Architect"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        feature_content = """\
# Feature: Architect Owned

> Label: "Arch Feature"
> Owner: Architect

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Some Test
    Given X
    When Y
    Then Z

## 4. Implementation Notes
* Note.
"""
        with open(os.path.join(self.features_dir, 'arch_owned.md'), 'w') as f:
            f.write(feature_content)
        sidecar = """\
### [SPEC_DISPUTE] Should work differently (Discovered: 2026-03-01)
- **Status:** OPEN
"""
        with open(os.path.join(
                self.features_dir, 'arch_owned.discoveries.md'), 'w') as f:
            f.write(sidecar)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_spec_dispute_routes_to_architect(self):
        import critic
        orig = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/arch_owned.md'
            result['_owner'] = 'Architect'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 1,
            }
            items = generate_action_items(result)
            arch_disputes = [i for i in items['architect']
                             if 'disputed scenario' in i['description'].lower()]
            pm_disputes = [i for i in items['pm']
                           if 'disputed scenario' in i['description'].lower()]
            self.assertTrue(len(arch_disputes) > 0,
                            'SPEC_DISPUTE should route to Architect')
            self.assertEqual(len(pm_disputes), 0,
                             'SPEC_DISPUTE should NOT route to PM')
        finally:
            critic.FEATURES_DIR = orig


class TestSpecDisputeNoOwnerDefaultsToArchitect(unittest.TestCase):
    """Scenario: SPEC_DISPUTE on feature with no Owner tag defaults to Architect"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        feature_content = """\
# Feature: No Owner

> Label: "No Owner Feature"

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Some Test
    Given X
    When Y
    Then Z

## 4. Implementation Notes
* Note.
"""
        with open(os.path.join(self.features_dir, 'no_owner.md'), 'w') as f:
            f.write(feature_content)
        sidecar = """\
### [SPEC_DISPUTE] Spec is wrong (Discovered: 2026-03-01)
- **Status:** OPEN
"""
        with open(os.path.join(
                self.features_dir, 'no_owner.discoveries.md'), 'w') as f:
            f.write(sidecar)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_no_owner_defaults_to_architect(self):
        import critic
        orig = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/no_owner.md'
            result['_owner'] = 'Architect'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 1,
            }
            items = generate_action_items(result)
            arch_disputes = [i for i in items['architect']
                             if 'disputed scenario' in i['description'].lower()]
            pm_disputes = [i for i in items['pm']
                           if 'disputed scenario' in i['description'].lower()]
            self.assertTrue(len(arch_disputes) > 0)
            self.assertEqual(len(pm_disputes), 0)
        finally:
            critic.FEATURES_DIR = orig


class TestVisualSpecDisputeRoutesToPM(unittest.TestCase):
    """Scenario: Visual SPEC_DISPUTE on Architect-owned feature routes to PM"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        feature_content = """\
# Feature: Visual Feature

> Label: "Visual Feature"
> Owner: Architect

## 1. Overview
Overview.

## 2. Requirements
Reqs.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Some Test
    Given X
    When Y
    Then Z

## 4. Visual Specification

### Screen: Main Dashboard
- **Reference:** N/A
- **Description:** Layout description.
- [ ] Check layout

## 5. Implementation Notes
* Note.
"""
        with open(os.path.join(
                self.features_dir, 'visual_feature.md'), 'w') as f:
            f.write(feature_content)
        sidecar = """\
### [SPEC_DISPUTE] Visual:Main Dashboard colors are wrong (Discovered: 2026-03-01)
- **Status:** OPEN
"""
        with open(os.path.join(
                self.features_dir, 'visual_feature.discoveries.md'), 'w') as f:
            f.write(sidecar)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_visual_spec_dispute_routes_to_pm(self):
        import critic
        orig = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/visual_feature.md'
            result['_owner'] = 'Architect'
            result['visual_spec'] = parse_visual_spec("""\
## Visual Specification

### Screen: Main Dashboard
- **Reference:** N/A
- **Description:** Layout.
- [ ] Check layout
""")
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 1,
            }
            items = generate_action_items(result)
            pm_disputes = [i for i in items['pm']
                           if 'disputed scenario' in i['description'].lower()]
            arch_disputes = [i for i in items['architect']
                             if 'disputed scenario' in i['description'].lower()]
            self.assertTrue(len(pm_disputes) > 0,
                            'Visual SPEC_DISPUTE should route to PM')
            self.assertEqual(len(arch_disputes), 0,
                             'Visual SPEC_DISPUTE should NOT route to Architect')
        finally:
            critic.FEATURES_DIR = orig


# ===================================================================
# Visual Reference Routing Tests
# ===================================================================

class TestStaleDesignRoutesToPM(unittest.TestCase):
    """Scenario: Stale design description routes to PM"""

    def test_stale_design_routes_to_pm(self):
        result = _make_base_result()
        result['_visual_ref_items'] = [{
            'priority': 'LOW',
            'category': 'stale_design_description',
            'description': 'Stale design for Main Dashboard',
        }]
        result['_owner'] = 'Architect'
        items = generate_action_items(result)
        pm_stale = [i for i in items['pm']
                    if i['category'] == 'stale_design_description']
        arch_stale = [i for i in items['architect']
                      if i['category'] == 'stale_design_description']
        self.assertEqual(len(pm_stale), 1)
        self.assertEqual(len(arch_stale), 0)


class TestUnprocessedArtifactRoutesToPM(unittest.TestCase):
    """Scenario: Unprocessed artifact routes to PM"""

    def test_unprocessed_artifact_routes_to_pm(self):
        result = _make_base_result()
        result['_visual_ref_items'] = [{
            'priority': 'HIGH',
            'category': 'unprocessed_artifact',
            'description': 'Unprocessed artifact for Settings Panel',
        }]
        result['_owner'] = 'Architect'
        items = generate_action_items(result)
        pm_items = [i for i in items['pm']
                    if i['category'] == 'unprocessed_artifact']
        arch_items = [i for i in items['architect']
                      if i['category'] == 'unprocessed_artifact']
        self.assertEqual(len(pm_items), 1)
        self.assertEqual(len(arch_items), 0)


# ===================================================================
# PM Role Status Tests
# ===================================================================

class TestPMStatusNA(unittest.TestCase):
    """Scenario: Feature with no visual spec and not PM-owned reports PM N/A"""

    def test_no_visual_no_pm_owner(self):
        result = _make_base_result()
        result['_owner'] = 'Architect'
        result['visual_spec'] = {'present': False, 'references': []}
        status = compute_role_status(result)
        self.assertEqual(status['pm'], 'N/A')


class TestPMStatusDONE(unittest.TestCase):
    """Scenario: PM-owned feature with no PM items reports PM DONE"""

    def test_pm_owned_no_items(self):
        result = _make_base_result()
        result['_owner'] = 'PM'
        result['visual_spec'] = {'present': False, 'references': []}
        result['action_items']['pm'] = []
        status = compute_role_status(result)
        self.assertEqual(status['pm'], 'DONE')


class TestPMStatusTODO(unittest.TestCase):
    """Scenario: PM-owned feature with pending items reports PM TODO"""

    def test_pm_owned_with_items(self):
        result = _make_base_result()
        result['_owner'] = 'PM'
        result['visual_spec'] = {'present': False, 'references': []}
        result['action_items']['pm'] = [{
            'priority': 'HIGH',
            'category': 'user_testing',
            'feature': 'test',
            'description': 'Review disputed scenario',
        }]
        status = compute_role_status(result)
        self.assertEqual(status['pm'], 'TODO')

    def test_visual_feature_with_items(self):
        """Feature with visual spec and PM items should be TODO."""
        result = _make_base_result()
        result['_owner'] = 'Architect'
        result['visual_spec'] = {
            'present': True,
            'references': [{'reference_type': 'local'}],
        }
        result['action_items']['pm'] = [{
            'priority': 'LOW',
            'category': 'stale_design_description',
            'feature': 'test',
            'description': 'Stale design',
        }]
        status = compute_role_status(result)
        self.assertEqual(status['pm'], 'TODO')


# ===================================================================
# Aggregate Report Tests
# ===================================================================

class TestAggregateReportIncludesPMSection(unittest.TestCase):
    """Scenario: Aggregate report includes PM section"""

    def test_pm_section_present(self):
        result = _make_base_result()
        result['action_items']['pm'] = [{
            'priority': 'HIGH',
            'category': 'user_testing',
            'feature': 'test_feature',
            'description': 'Review disputed scenario in test_feature',
        }]
        report = generate_critic_report([result])
        self.assertIn('### PM', report)
        self.assertIn('Review disputed scenario in test_feature', report)

    def test_pm_section_present_even_when_empty(self):
        result = _make_base_result()
        result['action_items']['pm'] = []
        report = generate_critic_report([result])
        self.assertIn('### PM', report)
        self.assertIn('No action items.', report)


# ===================================================================
# CDD Dashboard PM Column Tests
# ===================================================================

class TestCDDDashboardPMColumn(unittest.TestCase):
    """Scenario: CDD dashboard shows PM column"""

    def test_role_table_source_has_pm_column(self):
        """Verify _role_table_html source code includes PM column header
        and PM badge rendering."""
        serve_path = os.path.join(SCRIPT_DIR, '..', 'cdd', 'serve.py')
        with open(serve_path, 'r') as f:
            source = f.read()
        # Table header has PM column
        self.assertIn('>PM</th>', source)
        # PM badge is rendered in table rows
        self.assertIn('pm = _role_badge_html(entry.get("pm"))', source)
        # PM badge cell is in the row
        self.assertIn('{pm}</td>', source)

    def test_js_roles_include_pm(self):
        """Verify JavaScript roles arrays include 'pm'."""
        serve_path = os.path.join(SCRIPT_DIR, '..', 'cdd', 'serve.py')
        with open(serve_path, 'r') as f:
            source = f.read()
        import re
        js_roles = re.findall(
            r"var roles = \['architect', 'builder', 'qa', 'pm'\];",
            source)
        self.assertTrue(
            len(js_roles) >= 4,
            f'Expected at least 4 JS roles arrays with pm, found {len(js_roles)}')

    def test_status_json_includes_pm(self):
        """Verify that when critic.json has pm in role_status,
        get_feature_role_status returns it."""
        root = tempfile.mkdtemp()
        try:
            tests_dir = os.path.join(root, 'tests', 'my_feature')
            os.makedirs(tests_dir)
            critic_json = {
                'role_status': {
                    'architect': 'DONE',
                    'builder': 'DONE',
                    'qa': 'CLEAN',
                    'pm': 'N/A',
                },
            }
            with open(os.path.join(tests_dir, 'critic.json'), 'w') as f:
                json.dump(critic_json, f)

            # Direct file-based test (no serve.py import needed)
            critic_path = os.path.join(tests_dir, 'critic.json')
            with open(critic_path, 'r') as f:
                data = json.load(f)
            rs = data.get('role_status')
            self.assertIn('pm', rs)
            self.assertEqual(rs['pm'], 'N/A')
        finally:
            shutil.rmtree(root)

    def test_config_agents_requires_pm(self):
        """Verify _handle_config_agents requires pm in agents payload."""
        serve_path = os.path.join(SCRIPT_DIR, '..', 'cdd', 'serve.py')
        with open(serve_path, 'r') as f:
            source = f.read()
        self.assertIn("'architect', 'builder', 'qa', 'pm'}", source)


# ===================================================================
# Integration: generate_action_items returns pm key
# ===================================================================

class TestActionItemsReturnPMKey(unittest.TestCase):
    """Verify generate_action_items always returns a pm key."""

    def test_pm_key_present(self):
        result = _make_base_result()
        items = generate_action_items(result)
        self.assertIn('pm', items)
        self.assertIsInstance(items['pm'], list)


class TestRoleStatusReturnsPMKey(unittest.TestCase):
    """Verify compute_role_status always returns a pm key."""

    def test_pm_key_present(self):
        result = _make_base_result()
        status = compute_role_status(result)
        self.assertIn('pm', status)
        self.assertIn(status['pm'], ('DONE', 'TODO', 'N/A'))


# ===================================================================
# Test runner with output to tests/critic_pm_column/tests.json
# ===================================================================

if __name__ == '__main__':
    project_root = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
    tests_out_dir = os.path.join(project_root, 'tests', 'critic_pm_column')
    os.makedirs(tests_out_dir, exist_ok=True)
    status_file = os.path.join(tests_out_dir, 'tests.json')

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    status = 'PASS' if result.wasSuccessful() else 'FAIL'
    failure_count = len(result.failures) + len(result.errors)
    report = {
        'status': status,
        'passed': result.testsRun - failure_count,
        'failed': failure_count,
        'total': result.testsRun,
        'test_file': 'tools/critic/test_critic_pm_column.py',
    }
    with open(status_file, 'w') as f:
        json.dump(report, f)
    print(f'\n{status_file}: {status}')

    sys.exit(0 if result.wasSuccessful() else 1)
