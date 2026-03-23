#!/usr/bin/env python3
"""Tests for the PM First Session Guide feature.

Covers all 8 automated scenarios from features/pm_first_session_guide.md:
- Empty project triggers guided mode
- Non-empty project skips guided mode
- First spec created from text description
- First spec created from Figma design
- Next steps include Builder and CDD
- Figma MCP missing when user shares URL
- Figma MCP present is silent
- Figma MCP missing without visual context is silent

The PM agent's startup behavior is defined in instructions/PM_BASE.md.
These tests verify the instruction file contains the required behavioral
references for each scenario.
"""
import json
import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
PM_BASE_FILE = os.path.join(PROJECT_ROOT, 'instructions', 'PM_BASE.md')

_pm_content = None


def _get_pm_content():
    global _pm_content
    if _pm_content is None:
        with open(PM_BASE_FILE) as f:
            _pm_content = f.read()
    return _pm_content


class TestEmptyProjectTriggersGuidedMode(unittest.TestCase):
    """Scenario: Empty project triggers guided mode

    Given the PM agent launches
    And the startup briefing shows feature_summary.total is 0
    Then the PM enters guided onboarding mode
    And the PM does not display the standard command table
    And the PM asks what the user is building
    """

    def test_pm_base_detects_zero_features(self):
        """PM_BASE checks feature_summary.total for zero features."""
        content = _get_pm_content()
        self.assertIn('feature_summary.total == 0', content)

    def test_pm_base_has_guided_onboarding_section(self):
        """PM_BASE has a guided onboarding mode section."""
        content = _get_pm_content()
        self.assertIn('Guided Onboarding Mode', content)

    def test_pm_base_suppresses_command_table_in_guided_mode(self):
        """PM_BASE instructs suppressing command table in guided mode."""
        content = _get_pm_content()
        self.assertIn('Suppress the standard command table', content)

    def test_pm_base_asks_what_user_is_building(self):
        """PM_BASE instructs asking what the user is building."""
        content = _get_pm_content()
        self.assertIn('Ask what the user is building', content)

    def test_pm_base_runs_startup_briefing(self):
        """PM_BASE instructs running startup briefing to check project state."""
        content = _get_pm_content()
        self.assertIn('cdd/status.sh --startup pm', content)


class TestNonEmptyProjectSkipsGuidedMode(unittest.TestCase):
    """Scenario: Non-empty project skips guided mode

    Given the PM agent launches
    And the startup briefing shows feature_summary.total is greater than 0
    Then the PM follows the standard startup protocol
    And guided onboarding mode is not activated
    """

    def test_pm_base_skips_guided_when_features_exist(self):
        """PM_BASE activates guided mode ONLY when feature_summary.total == 0."""
        content = _get_pm_content()
        self.assertIn(
            'ONLY when `feature_summary.total == 0`', content)

    def test_pm_base_prints_command_table_when_features_exist(self):
        """PM_BASE prints command table when features > 0."""
        content = _get_pm_content()
        self.assertIn(
            'feature_summary.total > 0', content)
        self.assertIn('pm_commands.md', content)


class TestFirstSpecCreatedFromTextDescription(unittest.TestCase):
    """Scenario: First spec created from text description

    Given the PM is in guided onboarding mode
    And the user describes their project
    And the user has no Figma designs
    When the PM processes the description
    Then at least one feature spec is created in features/
    And at least one anchor node is created in features/
    And all created files follow the feature file template
    And the PM commits the created files
    And the PM instructs the user to run ./pl-run-builder.sh
    """

    def test_pm_base_creates_text_spec(self):
        """PM_BASE instructs creating text-based spec without Figma."""
        content = _get_pm_content()
        self.assertIn('text-based feature spec', content.lower())

    def test_pm_base_creates_anchor_node(self):
        """PM_BASE instructs creating at least one anchor node."""
        content = _get_pm_content()
        self.assertIn('anchor node', content.lower())

    def test_pm_base_follows_template(self):
        """PM_BASE requires files follow the feature file template."""
        content = _get_pm_content()
        self.assertIn('feature file template', content.lower())

    def test_pm_base_commits_files(self):
        """PM_BASE instructs committing created files."""
        content = _get_pm_content()
        # In the guided onboarding section
        self.assertIn('Commit all created files', content)

    def test_pm_base_instructs_running_builder(self):
        """PM_BASE instructs user to run ./pl-run-builder.sh."""
        content = _get_pm_content()
        self.assertIn('./pl-run-builder.sh', content)


class TestFirstSpecCreatedFromFigmaDesign(unittest.TestCase):
    """Scenario: First spec created from Figma design

    Given the PM is in guided onboarding mode
    And Figma MCP is available
    And the user provides a Figma design URL
    When the PM processes the design
    Then the PM calls get_design_context with the parsed fileKey and nodeId
    And a feature spec with a Visual Specification section is created
    And the visual spec references the Figma source
    And at least one anchor node is created
    """

    def test_pm_base_calls_get_design_context(self):
        """PM_BASE instructs calling get_design_context with Figma URL."""
        content = _get_pm_content()
        self.assertIn('get_design_context', content)

    def test_pm_base_creates_visual_spec(self):
        """PM_BASE instructs creating spec with Visual Specification section."""
        content = _get_pm_content()
        self.assertIn('Visual Specification', content)

    def test_pm_base_asks_about_figma_designs(self):
        """PM_BASE asks if user has Figma designs."""
        content = _get_pm_content()
        self.assertIn('Figma designs', content)


class TestNextStepsIncludeBuilderAndCDD(unittest.TestCase):
    """Scenario: Next steps include Builder and CDD

    Given the PM has completed the guided onboarding flow
    Then the PM output includes "./pl-run-builder.sh"
    And the PM output includes "./pl-cdd-start.sh"
    And the PM output includes a one-sentence explanation of what the Builder does
    """

    def test_pm_base_mentions_builder_command(self):
        """PM_BASE includes ./pl-run-builder.sh in next steps."""
        content = _get_pm_content()
        self.assertIn('./pl-run-builder.sh', content)

    def test_pm_base_mentions_cdd_command(self):
        """PM_BASE includes ./pl-cdd-start.sh in next steps."""
        content = _get_pm_content()
        self.assertIn('./pl-cdd-start.sh', content)

    def test_pm_base_explains_builder_role(self):
        """PM_BASE explains what the Builder does."""
        content = _get_pm_content()
        self.assertIn(
            'Builder reads your specs and writes the code and tests',
            content)


class TestFigmaMCPMissingWhenUserSharesURL(unittest.TestCase):
    """Scenario: Figma MCP missing when user shares URL

    Given the PM agent is running (any project state)
    And Figma MCP tools are not available
    And the user shares a Figma URL
    Then the PM offers to guide through Figma MCP setup
    And the guidance includes typing /mcp and selecting figma
    And the guidance includes completing browser authentication
    """

    def test_pm_base_has_figma_setup_guidance(self):
        """PM_BASE includes Figma MCP setup guidance."""
        content = _get_pm_content()
        self.assertIn('/mcp', content)

    def test_pm_base_mentions_figma_selection(self):
        """PM_BASE guidance includes selecting figma."""
        content = _get_pm_content()
        self.assertIn('Select "figma"', content)

    def test_pm_base_mentions_browser_auth(self):
        """PM_BASE guidance includes browser authentication."""
        content = _get_pm_content()
        self.assertIn('browser', content.lower())

    def test_pm_base_triggers_on_url_or_visual_spec(self):
        """PM_BASE triggers setup guidance when user shares URL or has visual specs."""
        content = _get_pm_content()
        self.assertIn('user mentions Figma or shares a Figma URL', content)


class TestFigmaMCPPresentIsSilent(unittest.TestCase):
    """Scenario: Figma MCP present is silent

    Given the PM agent launches
    And Figma MCP tools are available
    Then no Figma health check message is displayed
    """

    def test_pm_base_silent_when_figma_available(self):
        """PM_BASE states health check is silent when Figma MCP is available."""
        content = _get_pm_content()
        self.assertIn(
            'health check MUST be silent', content)


class TestFigmaMCPMissingWithoutVisualContextIsSilent(unittest.TestCase):
    """Scenario: Figma MCP missing without visual context is silent

    Given the PM agent launches
    And Figma MCP tools are not available
    And no features have Visual Specification sections
    And the user has not mentioned Figma
    Then no Figma health check message is displayed
    """

    def test_pm_base_conditional_figma_warning(self):
        """PM_BASE only warns about Figma when visual context exists."""
        content = _get_pm_content()
        # The health check should only trigger when visual specs exist
        # or user mentions Figma
        self.assertIn('Visual Specification', content)

    def test_pm_base_does_not_block_startup(self):
        """PM_BASE states health check must not block startup."""
        content = _get_pm_content()
        self.assertIn(
            'health check MUST NOT block startup', content)


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
    print(f"\ntests.json: {'PASS' if result.wasSuccessful() else 'FAIL'}")
    sys.exit(0 if result.wasSuccessful() else 1)
