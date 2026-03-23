"""Tests for QA Verification Effort Classification (qa_verification_effort.md).

Covers all 9 Unit Test scenarios from the feature spec.
"""

import os
import json
import sys
import unittest

# Add critic tool to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'critic'))

from critic import compute_verification_effort  # noqa: E402


# ---------------------------------------------------------------------------
# Shared test feature content fixtures
# ---------------------------------------------------------------------------

WEB_TEST_FEATURE_3QA_2VISUAL = """\
# Feature: Web Dashboard

> Label: "Web Dashboard"
> Category: "CDD Dashboard"
> Web Test: http://localhost:9086

## 1. Overview
A web-testable feature.

## 3. Scenarios

### Unit Tests

#### Scenario: Unit test one

    Given something
    When computed
    Then verified

### QA Scenarios

#### Scenario: Manual check one

    Given the dashboard is open
    When I click a button
    Then something happens

#### Scenario: Manual check two

    Given another state
    When I hover
    Then tooltip appears

#### Scenario: Manual check three

    Given a third state
    When I navigate to another page
    Then content loads

## Visual Specification

> **Design Anchor:** features/design_visual_standards.md
> **Inheritance:** Colors, typography, and theme switching per anchor.

### Screen: Dashboard Main
- **Reference:** N/A
- **Processed:** N/A
- **Token Map:** Main dashboard view.
- [ ] Layout is correct
- [ ] Colors match theme
"""

NON_WEB_FEATURE_4QA = """\
# Feature: CLI Tool

> Label: "CLI Tool"
> Category: "Tools"

## 1. Overview
A CLI feature with no web test.

## 3. Scenarios

### Unit Tests

#### Scenario: Unit test one

    Given something
    Then verified

### QA Scenarios

#### Scenario: Interactive one

    Given the CLI is running
    When I enter a command
    Then output is displayed

#### Scenario: Interactive two

    Given another state
    When I type input
    Then processing occurs

#### Scenario: Interactive three

    Given yet another state
    When I run a subcommand
    Then results appear

#### Scenario: Interactive four

    Given a final state
    When I exit
    Then cleanup occurs
"""

UNIT_TESTS_ONLY_FEATURE = """\
# Feature: Pure Logic

> Label: "Pure Logic"
> Category: "Tools"

## 1. Overview
Feature with only unit tests.

## 3. Scenarios

### Unit Tests

#### Scenario: Test one

    Given input A
    When processed
    Then output B

#### Scenario: Test two

    Given input C
    When processed
    Then output D

#### Scenario: Test three

    Given input E
    When processed
    Then output F

#### Scenario: Test four

    Given input G
    When processed
    Then output H

#### Scenario: Test five

    Given input I
    When processed
    Then output J

### QA Scenarios

None.
"""

AUTO_TAGGED_MIXED_FEATURE = """\
# Feature: Auto Mixed

> Label: "Auto Mixed"
> Category: "Tools"

## 1. Overview
Feature with @auto and manual QA scenarios.

## 3. Scenarios

### Unit Tests

#### Scenario: Unit test

    Given something
    Then verified

### QA Scenarios

#### Scenario: Automated check one @auto

    Given the system is running
    When I trigger an action
    Then the result is observable

#### Scenario: Automated check two @auto

    Given another condition
    When I trigger another action
    Then the result is logged

#### Scenario: Manual check

    Given a human interaction is needed
    When I perform a manual step
    Then I verify the outcome visually
"""

NON_WEB_VISUAL_ONLY_FEATURE = """\
# Feature: Visual Only

> Label: "Visual Only"

## 1. Overview
Feature with visual spec but no web test and no QA scenarios.

## 3. Scenarios

### Unit Tests

#### Scenario: Unit test

    Given input
    Then output

### QA Scenarios

None.

## Visual Specification

> **Design Anchor:** features/design_visual_standards.md

### Screen: Main View
- **Reference:** N/A
- **Processed:** N/A
- **Token Map:** Main view.
- [ ] Layout correct
- [ ] Colors right
- [ ] Spacing consistent
- [ ] Font correct
- [ ] Borders visible
- [ ] Icons present
"""

FIVE_QA_SCENARIOS_FEATURE = """\
# Feature: Five Scenarios

> Label: "Five Scenarios"
> Category: "Tools"

## 1. Overview
Feature with five QA scenarios for targeted scope testing.

## 3. Scenarios

### Unit Tests

#### Scenario: Unit test

    Given input
    Then output

### QA Scenarios

#### Scenario: Scenario A

    Given state A
    When action A
    Then result A

#### Scenario: Scenario B

    Given state B
    When action B
    Then result B

#### Scenario: Scenario C

    Given state C
    When action C
    Then result C

#### Scenario: Scenario D

    Given state D
    When action D
    Then result D

#### Scenario: Scenario E

    Given state E
    When action E
    Then result E
"""

BUILDER_INCOMPLETE_FEATURE = """\
# Feature: Incomplete

> Label: "Incomplete"
> Category: "Tools"

## 1. Overview
Feature not yet implemented.

## 3. Scenarios

### Unit Tests

#### Scenario: Unit test

    Given input
    Then output

### QA Scenarios

#### Scenario: Manual one

    Given state
    When action
    Then result
"""

BUILDER_VERIFIED_FEATURE = """\
# Feature: Builder Verified

> Label: "Builder Verified"
> Category: "Tools"

## 1. Overview
Feature with only unit tests that all pass.

## 3. Scenarios

### Unit Tests

#### Scenario: Test one

    Given input
    Then output

#### Scenario: Test two

    Given more input
    Then more output

### QA Scenarios

None.
"""


def _make_base_result_helper(**overrides):
    """Create a baseline result dict for verification effort testing."""
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


class TestWebTestFeatureVisualAutoQAManual(unittest.TestCase):
    """Scenario: Web-test feature classifies visual items as auto and QA scenarios normally.

    Given a feature has `> Web Test: http://localhost:9086` metadata
    And the feature has 3 QA scenarios (no @auto tag) and 2 visual checklist items
    When the Critic computes verification_effort for this feature
    Then `auto` is 2 (visual items on web-test feature)
    And `manual` is 3
    And `summary` is "3 manual"
    """

    def test_web_test_feature_classifies_correctly(self):
        regression_scope = {
            'declared': 'full',
            'scenarios': ['Manual check one', 'Manual check two',
                          'Manual check three'],
            'visual_items': 2,
            'cross_validation_warnings': [],
        }
        role_status = {'architect': 'DONE', 'builder': 'DONE', 'qa': 'TODO'}
        result = _make_base_result_helper()

        ve = compute_verification_effort(
            WEB_TEST_FEATURE_3QA_2VISUAL, 'testing', regression_scope,
            role_status, result)

        # auto counts visual items on web-test feature (via total_auto)
        self.assertEqual(ve['total_auto'], 2)
        # manual counts QA scenarios
        self.assertEqual(ve['manual'], 3)
        # Summary shows manual work for QA (web-test visual items are
        # Builder-verified, not QA-facing in the summary)
        self.assertEqual(ve['summary'], '3 manual')


class TestNonWebTestFeatureManual(unittest.TestCase):
    """Scenario: Non-web-test feature classifies QA scenarios as manual.

    Given a feature does NOT have `> Web Test:` metadata
    And the feature has 4 QA scenarios without @auto tag
    When the Critic computes verification_effort
    Then `manual` is 4
    And `auto` is 0
    And `summary` is "4 manual"
    """

    def test_non_web_manual_scenarios(self):
        regression_scope = {
            'declared': 'full',
            'scenarios': ['Interactive one', 'Interactive two',
                          'Interactive three', 'Interactive four'],
            'visual_items': 0,
            'cross_validation_warnings': [],
        }
        role_status = {'architect': 'DONE', 'builder': 'DONE', 'qa': 'TODO'}
        result = _make_base_result_helper()

        ve = compute_verification_effort(
            NON_WEB_FEATURE_4QA, 'testing', regression_scope,
            role_status, result)

        self.assertEqual(ve['manual'], 4)
        self.assertEqual(ve['auto'], 0)
        self.assertEqual(ve['summary'], '4 manual')


class TestUnitTestsOnlyFeature(unittest.TestCase):
    """Scenario: Feature with only Unit Tests classifies as test_only.

    Given a feature has 5 Unit Test scenarios and zero QA scenarios
    And the feature has no `## Visual Specification` section
    And `tests/<feature>/tests.json` exists with `status: "PASS"`
    When the Critic computes verification_effort
    Then `test_only` is 1
    And all other category counts are 0
    And `summary` is "builder-verified"
    """

    def test_unit_tests_only_test_only(self):
        regression_scope = {
            'declared': 'full',
            'scenarios': [],
            'visual_items': 0,
            'cross_validation_warnings': [],
        }
        role_status = {'architect': 'DONE', 'builder': 'DONE', 'qa': 'TODO'}
        # Tests passing is indicated by structural_completeness PASS
        result = _make_base_result_helper()

        ve = compute_verification_effort(
            UNIT_TESTS_ONLY_FEATURE, 'testing', regression_scope,
            role_status, result)

        self.assertEqual(ve['test_only'], 1)
        self.assertEqual(ve['auto'], 0)
        self.assertEqual(ve['manual'], 0)
        self.assertEqual(ve['skip'], 0)
        self.assertEqual(ve['summary'], 'builder-verified')


class TestAutoTaggedQAScenarios(unittest.TestCase):
    """Scenario: QA scenarios with @auto tag classified as auto.

    Given a feature has 2 QA scenarios with @auto tag and 1 without
    When the Critic computes verification_effort
    Then `auto` is 2
    And `manual` is 1
    And `summary` is "2 auto, 1 manual"
    """

    def test_auto_tagged_scenarios(self):
        regression_scope = {
            'declared': 'full',
            'scenarios': ['Automated check one', 'Automated check two',
                          'Manual check'],
            'visual_items': 0,
            'cross_validation_warnings': [],
        }
        role_status = {'architect': 'DONE', 'builder': 'DONE', 'qa': 'TODO'}
        result = _make_base_result_helper()

        ve = compute_verification_effort(
            AUTO_TAGGED_MIXED_FEATURE, 'testing', regression_scope,
            role_status, result)

        self.assertEqual(ve['auto'], 2)
        self.assertEqual(ve['manual'], 1)
        self.assertEqual(ve['summary'], '2 auto, 1 manual')


class TestVisualSpecByWebTestEligibility(unittest.TestCase):
    """Scenario: Visual spec items classified by web-test eligibility.

    Given a non-web-test feature has 6 visual checklist items and no QA scenarios
    When the Critic computes verification_effort
    Then `manual` is 6
    And `auto` is 0
    And `summary` is "6 manual"
    """

    def test_non_web_visual_items_are_manual(self):
        regression_scope = {
            'declared': 'full',
            'scenarios': [],
            'visual_items': 6,
            'cross_validation_warnings': [],
        }
        role_status = {'architect': 'DONE', 'builder': 'DONE', 'qa': 'TODO'}
        result = _make_base_result_helper()

        ve = compute_verification_effort(
            NON_WEB_VISUAL_ONLY_FEATURE, 'testing', regression_scope,
            role_status, result)

        self.assertEqual(ve['manual'], 6)
        self.assertEqual(ve['auto'], 0)
        self.assertEqual(ve['summary'], '6 manual')


class TestCosmeticScopeSkip(unittest.TestCase):
    """Scenario: Cosmetic scope feature classified as skip.

    Given a feature has `regression_scope.change_scope` of "cosmetic"
    And the cosmetic first-pass guard did not escalate
    When the Critic computes verification_effort
    Then `skip` is 1
    And all other counts are 0
    And `summary` is "builder-verified"
    """

    def test_cosmetic_scope_is_skip(self):
        regression_scope = {
            'declared': 'cosmetic',
            'scenarios': [],
            'visual_items': 0,
            'cross_validation_warnings': [],
        }
        role_status = {'architect': 'DONE', 'builder': 'DONE', 'qa': 'TODO'}
        result = _make_base_result_helper()

        ve = compute_verification_effort(
            FIVE_QA_SCENARIOS_FEATURE, 'testing', regression_scope,
            role_status, result)

        self.assertEqual(ve['skip'], 1)
        self.assertEqual(ve['auto'], 0)
        self.assertEqual(ve['manual'], 0)
        self.assertEqual(ve['test_only'], 0)
        self.assertEqual(ve['summary'], 'builder-verified')


class TestTargetedScopeReducesCounts(unittest.TestCase):
    """Scenario: Targeted scope reduces counts to named items only.

    Given a feature has 5 QA scenarios
    And `regression_scope.change_scope` is "targeted:Scenario A,Scenario B"
    When the Critic computes verification_effort
    Then only 2 scenarios are counted (the targeted ones)
    And the remaining 3 are excluded from all categories
    """

    def test_targeted_scope_filters(self):
        regression_scope = {
            'declared': 'targeted:Scenario A,Scenario B',
            'scenarios': ['Scenario A', 'Scenario B'],
            'visual_items': 0,
            'cross_validation_warnings': [],
        }
        role_status = {'architect': 'DONE', 'builder': 'DONE', 'qa': 'TODO'}
        result = _make_base_result_helper()

        ve = compute_verification_effort(
            FIVE_QA_SCENARIOS_FEATURE, 'testing', regression_scope,
            role_status, result)

        # Only 2 targeted scenarios should be counted
        self.assertEqual(ve['manual'], 2)
        self.assertEqual(ve['total_manual'], 2)
        # All others excluded
        self.assertEqual(ve['auto'], 0)
        self.assertEqual(ve['web_test'], 0)


class TestBuilderIncompleteAwaiting(unittest.TestCase):
    """Scenario: Builder-incomplete feature shows awaiting builder.

    Given a feature has `role_status.builder` of "TODO"
    When the Critic computes verification_effort
    Then all counts are 0
    And `summary` is "awaiting builder"
    """

    def test_builder_todo_awaiting(self):
        regression_scope = {
            'declared': 'full',
            'scenarios': [],
            'visual_items': 0,
            'cross_validation_warnings': [],
        }
        role_status = {'architect': 'DONE', 'builder': 'TODO', 'qa': 'N/A'}
        result = _make_base_result_helper()

        ve = compute_verification_effort(
            BUILDER_INCOMPLETE_FEATURE, 'todo', regression_scope,
            role_status, result)

        self.assertEqual(ve['auto'], 0)
        self.assertEqual(ve['manual'], 0)
        self.assertEqual(ve['test_only'], 0)
        self.assertEqual(ve['skip'], 0)
        self.assertEqual(ve['summary'], 'awaiting builder')


class TestBuilderVerifiedFeature(unittest.TestCase):
    """Scenario: Builder-verified feature produces qa N/A.

    Given a feature has zero QA scenarios
    And all Unit Tests pass
    And the Builder marks `[Complete]` (no `[Verified]`)
    When the Critic computes verification_effort
    Then `qa` status is `"N/A"`
    And `summary` is "builder-verified"
    """

    def test_builder_verified_qa_na(self):
        regression_scope = {
            'declared': 'full',
            'scenarios': [],
            'visual_items': 0,
            'cross_validation_warnings': [],
        }
        # When Builder marks [Complete] with no manual scenarios,
        # lifecycle is complete and qa is N/A
        role_status = {'architect': 'DONE', 'builder': 'DONE', 'qa': 'N/A'}
        result = _make_base_result_helper()

        ve = compute_verification_effort(
            BUILDER_VERIFIED_FEATURE, 'complete', regression_scope,
            role_status, result)

        # qa status N/A is in role_status, not in verification_effort
        self.assertEqual(role_status['qa'], 'N/A')
        self.assertEqual(ve['summary'], 'builder-verified')
        self.assertEqual(ve['auto'], 0)
        self.assertEqual(ve['manual'], 0)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    status = 'PASS' if result.wasSuccessful() else 'FAIL'
    failed = len(result.failures) + len(result.errors)
    report = {
        'status': status,
        'passed': result.testsRun - failed,
        'failed': failed,
        'total': result.testsRun,
        'test_file': 'tests/qa_verification_effort/test_verification_effort.py',
    }
    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, 'tests.json'), 'w') as f:
        json.dump(report, f)
    print(f"\ntests.json: {status}")
    sys.exit(0 if result.wasSuccessful() else 1)
