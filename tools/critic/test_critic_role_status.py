#!/usr/bin/env python3
"""Unit tests for the Critic Role Status & Routing feature.

Covers all automated scenarios from features/critic_role_status.md.
Migrated from test_critic_pm_column.py + new scenarios for the unified model.
Outputs test results to tests/critic_role_status/tests.json.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from critic import (
    extract_owner,
    generate_action_items,
    compute_role_status,
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
# Scenario: Anchor node Owner tag ignored
# ===================================================================

class TestAnchorNodeOwnerTagIgnored(unittest.TestCase):
    """Anchor nodes are always Architect-owned regardless of Owner tag."""

    def test_policy_anchor_always_architect(self):
        content = '# Policy\n\n> Label: "Policy"\n> Owner: PM\n\n## 1. Purpose\n'
        self.assertEqual(extract_owner(content, 'policy_test.md'), 'Architect')

    def test_design_anchor_always_architect(self):
        content = '# Design\n\n> Owner: PM\n'
        self.assertEqual(extract_owner(content, 'design_test.md'), 'Architect')

    def test_arch_anchor_always_architect(self):
        content = '# Arch\n\n> Owner: PM\n'
        self.assertEqual(extract_owner(content, 'arch_test.md'), 'Architect')


# ===================================================================
# Scenario: Owner tag parsing (supporting tests)
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


# ===================================================================
# Scenario: SPEC_DISPUTE on PM-owned feature routes to PM
# ===================================================================

class TestSpecDisputeOnPMOwnedFeature(unittest.TestCase):

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


# ===================================================================
# Scenario: SPEC_DISPUTE on Architect-owned feature routes to Architect
# ===================================================================

class TestSpecDisputeOnArchitectOwnedFeature(unittest.TestCase):

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


# ===================================================================
# Scenario: SPEC_DISPUTE on feature with no Owner tag defaults to Architect
# ===================================================================

class TestSpecDisputeNoOwnerDefaultsToArchitect(unittest.TestCase):

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


# ===================================================================
# Scenario: Visual SPEC_DISPUTE on Architect-owned feature routes to PM
# ===================================================================

class TestVisualSpecDisputeRoutesToPM(unittest.TestCase):

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
# Scenario: Stale design description routes to PM
# ===================================================================

class TestStaleDesignRoutesToPM(unittest.TestCase):

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


# ===================================================================
# Scenario: Unprocessed artifact routes to PM
# ===================================================================

class TestUnprocessedArtifactRoutesToPM(unittest.TestCase):

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
# Scenario: Feature with no visual spec and not PM-owned reports PM N/A
# ===================================================================

class TestPMStatusNA(unittest.TestCase):

    def test_no_visual_no_pm_owner(self):
        result = _make_base_result()
        result['_owner'] = 'Architect'
        result['visual_spec'] = {'present': False, 'references': []}
        status = compute_role_status(result)
        self.assertEqual(status['pm'], 'N/A')


# ===================================================================
# Scenario: PM-owned feature with no PM items reports PM DONE
# ===================================================================

class TestPMStatusDONE(unittest.TestCase):

    def test_pm_owned_no_items(self):
        result = _make_base_result()
        result['_owner'] = 'PM'
        result['visual_spec'] = {'present': False, 'references': []}
        result['action_items']['pm'] = []
        status = compute_role_status(result)
        self.assertEqual(status['pm'], 'DONE')


# ===================================================================
# Scenario: PM-owned feature with pending items reports PM TODO
# ===================================================================

class TestPMStatusTODO(unittest.TestCase):

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
# Scenario: Aggregate report includes PM section
# ===================================================================

class TestAggregateReportIncludesPMSection(unittest.TestCase):

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
# Scenario: Per-feature critic.json includes all four role keys
# ===================================================================

class TestFourRoleKeys(unittest.TestCase):

    def test_action_items_has_all_four_roles(self):
        result = _make_base_result()
        items = generate_action_items(result)
        self.assertIn('architect', items)
        self.assertIn('builder', items)
        self.assertIn('qa', items)
        self.assertIn('pm', items)
        for role in ('architect', 'builder', 'qa', 'pm'):
            self.assertIsInstance(items[role], list)

    def test_role_status_has_all_four_roles(self):
        result = _make_base_result()
        status = compute_role_status(result)
        self.assertIn('architect', status)
        self.assertIn('builder', status)
        self.assertIn('qa', status)
        self.assertIn('pm', status)


# ===================================================================
# Scenario: Architect action item from spec gate FAIL
# ===================================================================

class TestArchitectActionItemFromSpecGateFail(unittest.TestCase):

    def test_spec_gate_fail_creates_architect_item(self):
        result = _make_base_result()
        result['feature_file'] = 'features/broken_feature.md'
        result['spec_gate'] = {
            'status': 'FAIL',
            'checks': {
                'section_completeness': {
                    'status': 'FAIL',
                    'detail': 'Missing sections: Requirements',
                },
                'scenario_classification': {'status': 'PASS', 'detail': 'OK'},
                'policy_anchoring': {'status': 'PASS', 'detail': 'OK'},
                'prerequisite_integrity': {'status': 'PASS', 'detail': 'OK'},
                'gherkin_quality': {'status': 'PASS', 'detail': 'OK'},
            },
        }
        items = generate_action_items(result)
        arch_items = [i for i in items['architect']
                      if i['priority'] == 'HIGH'
                      and i.get('category') == 'spec_gate']
        self.assertTrue(len(arch_items) > 0,
                        'Spec Gate FAIL should create HIGH Architect item')
        self.assertIn('section_completeness', arch_items[0]['description'])
        # Must NOT create a PM item for spec gaps
        pm_spec_items = [i for i in items['pm']
                         if i.get('category') == 'spec_gate']
        self.assertEqual(len(pm_spec_items), 0,
                         'Spec Gate FAIL should NOT create PM item')

    def test_spec_gate_fail_sets_architect_todo(self):
        result = _make_base_result()
        result['spec_gate'] = {
            'status': 'FAIL',
            'checks': {
                'section_completeness': {
                    'status': 'FAIL',
                    'detail': 'Missing sections: Requirements',
                },
                'scenario_classification': {'status': 'PASS', 'detail': 'OK'},
                'policy_anchoring': {'status': 'PASS', 'detail': 'OK'},
                'prerequisite_integrity': {'status': 'PASS', 'detail': 'OK'},
                'gherkin_quality': {'status': 'PASS', 'detail': 'OK'},
            },
        }
        # Inject the action items so compute_role_status can see them
        result['action_items'] = generate_action_items(result)
        status = compute_role_status(result)
        self.assertEqual(status['architect'], 'TODO')


# ===================================================================
# Scenario: Builder action item from lifecycle reset
# ===================================================================

class TestBuilderActionItemFromLifecycleReset(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        feature_content = """\
# Feature: Reset Feature

> Label: "Reset Feature"

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
"""
        with open(os.path.join(
                self.features_dir, 'reset_feature.md'), 'w') as f:
            f.write(feature_content)
        # CDD status showing this feature in TODO state
        self.cdd_status = {
            'features': {
                'todo': [{'file': 'features/reset_feature.md'}],
                'testing': [],
                'complete': [],
            }
        }

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_lifecycle_reset_creates_builder_item(self):
        """When a feature resets to TODO lifecycle, Builder gets a HIGH item."""
        import critic
        orig = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/reset_feature.md'
            items = generate_action_items(result, cdd_status=self.cdd_status)
            builder_reset = [i for i in items['builder']
                             if i.get('category') == 'lifecycle_reset']
            self.assertTrue(len(builder_reset) > 0,
                            'Lifecycle reset should create Builder action item')
            self.assertEqual(builder_reset[0]['priority'], 'HIGH')
        finally:
            critic.FEATURES_DIR = orig

    def test_lifecycle_reset_sets_builder_todo(self):
        import critic
        orig = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/reset_feature.md'
            result['action_items'] = generate_action_items(
                result, cdd_status=self.cdd_status)
            status = compute_role_status(result, cdd_status=self.cdd_status)
            self.assertEqual(status['builder'], 'TODO')
        finally:
            critic.FEATURES_DIR = orig


# ===================================================================
# Scenario: QA action item from TESTING status with manual scenarios
# ===================================================================

class TestQAActionItemFromTestingWithManualScenarios(unittest.TestCase):

    def setUp(self):
        """Create a temp dir with a feature in TESTING state."""
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)

        feature_content = """\
# Feature: Manual Feature

> Label: "Manual Feature"

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

#### Scenario: Manual Check One
    Given a running system
    When the user inspects the output
    Then the display is correct

#### Scenario: Manual Check Two
    Given a running system
    When the user clicks submit
    Then the form saves correctly

#### Scenario: Manual Check Three
    Given a running system
    When the user refreshes
    Then data is preserved
"""
        with open(os.path.join(
                self.features_dir, 'manual_feature.md'), 'w') as f:
            f.write(feature_content)

        # CDD status with feature in TESTING
        self.cdd_status = {
            'features': {
                'todo': [],
                'testing': [{'file': 'features/manual_feature.md'}],
                'complete': [],
            }
        }

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_testing_with_manual_creates_qa_item(self):
        import critic
        orig_features = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/manual_feature.md'
            items = generate_action_items(
                result, cdd_status=self.cdd_status)
            qa_items = [i for i in items['qa']
                        if i.get('category') == 'testing_status'
                        and 'manual_feature' in i.get('feature', '')]
            self.assertTrue(len(qa_items) > 0,
                            'TESTING with manual scenarios should create QA item')
            self.assertIn('3 manual scenario', qa_items[0]['description'])
        finally:
            critic.FEATURES_DIR = orig_features


# ===================================================================
# Scenario: QA DISPUTED generates informational action item when
#           dispute routes to PM
# ===================================================================


class TestQADisputedInformationalItemPM(unittest.TestCase):
    """When a PM-owned feature has an OPEN SPEC_DISPUTE, QA status is
    DISPUTED and a LOW-priority informational QA action item must be
    generated referencing PM as the resolver. The HIGH-priority
    resolution item must appear in PM action items."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        feature_content = """\
# Feature: PM Disputed Info

> Label: "PM Disputed Info"
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
        with open(os.path.join(
                self.features_dir, 'pm_disputed_info.md'), 'w') as f:
            f.write(feature_content)
        sidecar = """\
### [SPEC_DISPUTE] Design layout doesn't match (Discovered: 2026-03-01)
- **Status:** OPEN
"""
        with open(os.path.join(
                self.features_dir,
                'pm_disputed_info.discoveries.md'), 'w') as f:
            f.write(sidecar)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_qa_disputed_has_low_informational_item(self):
        import critic
        orig = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/pm_disputed_info.md'
            result['_owner'] = 'PM'
            result['user_testing'] = {
                'status': 'HAS_OPEN_ITEMS',
                'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 1,
            }
            cdd_status = {
                'features': {
                    'testing': [],
                    'complete': [
                        {'file': 'features/pm_disputed_info.md'}],
                    'todo': [],
                },
            }
            # Compute role status to verify QA is DISPUTED
            status = compute_role_status(result, cdd_status)
            self.assertEqual(status['qa'], 'DISPUTED')

            # Generate action items and verify QA has informational item
            items = generate_action_items(result, cdd_status=cdd_status)
            qa_items = items['qa']
            suspended = [
                i for i in qa_items
                if 'suspended' in i['description'].lower()
            ]
            self.assertTrue(
                len(suspended) > 0,
                'QA DISPUTED should have informational action item')
            self.assertEqual(suspended[0]['priority'], 'LOW')
            self.assertIn('PM', suspended[0]['description'])

            # PM should have the HIGH-priority resolution item
            pm_items = items['pm']
            pm_dispute = [
                i for i in pm_items
                if 'disputed' in i['description'].lower()
            ]
            self.assertTrue(
                len(pm_dispute) > 0,
                'PM should have HIGH-priority dispute resolution item')
            self.assertEqual(pm_dispute[0]['priority'], 'HIGH')
        finally:
            critic.FEATURES_DIR = orig


# ===================================================================
# Scenario: Builder BLOCKED clears when SPEC_DISPUTE moves to RESOLVED
# ===================================================================


class TestBuilderBlockedClearsOnResolvedDispute(unittest.TestCase):
    """When a feature had an OPEN SPEC_DISPUTE (Builder was BLOCKED)
    and PM resolves it by marking RESOLVED without editing the feature
    file, Builder should NOT be BLOCKED. The feature lifecycle has NOT
    reset to TODO (no spec edit occurred)."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        feature_content = """\
# Feature: Resolved Dispute

> Label: "Resolved Dispute"

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
        with open(os.path.join(
                self.features_dir, 'resolved_dispute.md'), 'w') as f:
            f.write(feature_content)
        sidecar = """\
### [SPEC_DISPUTE] User disagrees with expected behavior (Discovered: 2026-01-01)
- **Status:** RESOLVED
- **Resolution:** Spec is correct as-is. No change needed.
"""
        with open(os.path.join(
                self.features_dir,
                'resolved_dispute.discoveries.md'), 'w') as f:
            f.write(sidecar)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_resolved_dispute_does_not_block_builder(self):
        import critic
        orig = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/resolved_dispute.md'
            result['user_testing'] = {
                'status': 'CLEAN', 'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            cdd_status = {
                'features': {
                    'complete': [
                        {'file': 'features/resolved_dispute.md'}],
                    'testing': [], 'todo': [],
                },
            }
            status = compute_role_status(result, cdd_status)
            self.assertNotEqual(
                status['builder'], 'BLOCKED',
                'RESOLVED dispute should NOT block Builder')
            # With structural_completeness PASS and no lifecycle TODO,
            # builder should be DONE
            self.assertEqual(status['builder'], 'DONE')
        finally:
            critic.FEATURES_DIR = orig

    def test_no_lifecycle_reset_without_spec_edit(self):
        """Feature stays in COMPLETE lifecycle when dispute is resolved
        without editing the feature file."""
        import critic
        orig = critic.FEATURES_DIR
        critic.FEATURES_DIR = self.features_dir
        try:
            result = _make_base_result()
            result['feature_file'] = 'features/resolved_dispute.md'
            result['user_testing'] = {
                'status': 'CLEAN', 'bugs': 0, 'discoveries': 0,
                'intent_drifts': 0, 'spec_disputes': 0,
            }
            cdd_status = {
                'features': {
                    'complete': [
                        {'file': 'features/resolved_dispute.md'}],
                    'testing': [], 'todo': [],
                },
            }
            status = compute_role_status(result, cdd_status)
            # QA should not be TODO -- dispute is resolved
            self.assertNotEqual(status['qa'], 'DISPUTED')
        finally:
            critic.FEATURES_DIR = orig


# ===================================================================
# Test runner with output to tests/critic_role_status/tests.json
# ===================================================================

if __name__ == '__main__':
    project_root = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
    tests_out_dir = os.path.join(project_root, 'tests', 'critic_role_status')
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
        'test_file': 'tools/critic/test_critic_role_status.py',
    }
    with open(status_file, 'w') as f:
        json.dump(report, f)
    print(f'\n{status_file}: {status}')

    sys.exit(0 if result.wasSuccessful() else 1)
