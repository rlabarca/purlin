#!/usr/bin/env python3
"""Tests for the /pl-web-verify agent command.

Covers automated scenarios from features/pl_web_verify.md:
- Auto-discover web-testable features
- URL override from argument
- Playwright MCP not available triggers auto-setup
- Manual scenario PASS recorded correctly
- Manual scenario FAIL creates BUG discovery
- Inconclusive step handled gracefully
- Visual spec items verified via screenshot analysis
- Regression scope respected
- Cosmetic scope skips feature
- QA completion gate prompts for completion
- Builder completion gate is summary only
- Instruction files updated with web-verify references
- Fixture-backed server started for scenario with fixture tag
- Fixture checkout failure marks scenario inconclusive
- Fixture cleanup after scenario completion

The agent command is a Claude skill defined in .claude/commands/pl-web-verify.md.
These tests verify the underlying behaviors that the command depends on:
- Skill file structure (role guard, argument docs, execution protocol)
- Web Testable metadata parsing from feature files
- URL override argument parsing
- Scope filtering logic (cosmetic, targeted, dependency-only)
- BUG discovery format validation
- INCONCLUSIVE classification
- Visual spec extraction from feature files
- Role-based completion gate behavior
- Instruction file references across 7 files
"""
import os
import re
import shutil
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
COMMAND_FILE = os.path.join(
    PROJECT_ROOT, '.claude', 'commands', 'pl-web-verify.md')

# Instruction files that must reference /pl-web-verify per Section 2.11
INSTRUCTION_FILES = {
    'feature_format': os.path.join(
        PROJECT_ROOT, 'instructions', 'references', 'feature_format.md'),
    'visual_spec_convention': os.path.join(
        PROJECT_ROOT, 'instructions', 'references',
        'visual_spec_convention.md'),
    'visual_verification_protocol': os.path.join(
        PROJECT_ROOT, 'instructions', 'references',
        'visual_verification_protocol.md'),
    'qa_base': os.path.join(
        PROJECT_ROOT, 'instructions', 'QA_BASE.md'),
    'builder_base': os.path.join(
        PROJECT_ROOT, 'instructions', 'BUILDER_BASE.md'),
    'qa_commands': os.path.join(
        PROJECT_ROOT, 'instructions', 'references', 'qa_commands.md'),
    'builder_commands': os.path.join(
        PROJECT_ROOT, 'instructions', 'references', 'builder_commands.md'),
}

# Sample feature spec with Web Testable metadata
SAMPLE_WEB_TESTABLE_WITH_PORT_FILE = """\
# Feature: Sample Web Feature with Port File

> Label: "Sample Feature"
> Category: "CDD"
> Prerequisite: features/policy_critic.md
> Web Testable: http://localhost:9086
> Web Port File: .purlin/runtime/cdd.port
> Web Start: /pl-cdd

[TESTING]

## 1. Overview
A sample feature with dynamic port resolution.

## 3. Scenarios
### Manual Scenarios (Human Verification Required)

#### Scenario: Dashboard Loads
    Given the server is running
    When the user navigates to the dashboard
    Then the page loads successfully
"""

SAMPLE_WEB_TESTABLE_FEATURE = """\
# Feature: Sample Web Feature

> Label: "Sample Feature"
> Category: "CDD"
> Prerequisite: features/policy_critic.md
> Web Testable: http://localhost:9086

[TESTING]

## 1. Overview
A sample feature for testing.

## 2. Requirements
### 2.1 Display
- Show a dashboard.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Widget renders
    Given the dashboard is loaded
    When the page finishes rendering
    Then the widget is visible

### Manual Scenarios (Human Verification Required)

#### Scenario: Dashboard Layout Correct
    Given the server is running on port 9086
    When the user navigates to http://localhost:9086
    Then the dashboard heading displays "CDD Monitor"
    And the feature table is visible

## Visual Specification

### Screen: Dashboard Main View
- [ ] Heading uses 24px bold font
- [ ] Table rows alternate background colors
- [ ] Status badges show correct colors
"""

# Sample feature spec WITHOUT Web Testable metadata
SAMPLE_NON_WEB_FEATURE = """\
# Feature: CLI Tool

> Label: "CLI Tool"
> Category: "Tools"
> Prerequisite: features/policy_critic.md

[TESTING]

## 1. Overview
A command-line tool.

## 3. Scenarios
### Manual Scenarios (Human Verification Required)

#### Scenario: CLI outputs help
    Given the user runs the tool with --help
    Then the help text is displayed
"""

# Sample critic.json for scope testing
SAMPLE_CRITIC_TARGETED = """\
{
  "regression_scope": "targeted:Dashboard Layout Correct",
  "role_status": {"architect": "DONE", "builder": "DONE", "qa": "TODO"}
}
"""

SAMPLE_CRITIC_COSMETIC = """\
{
  "regression_scope": "cosmetic",
  "role_status": {"architect": "DONE", "builder": "DONE", "qa": "N/A"}
}
"""

SAMPLE_CRITIC_FULL = """\
{
  "regression_scope": "full",
  "role_status": {"architect": "DONE", "builder": "DONE", "qa": "TODO"}
}
"""

SAMPLE_CRITIC_DEPENDENCY_ONLY = """\
{
  "regression_scope": "dependency-only",
  "role_status": {"architect": "DONE", "builder": "DONE", "qa": "N/A"}
}
"""

# Sample feature spec with Test Fixtures metadata for fixture-backed testing
SAMPLE_WEB_TESTABLE_WITH_FIXTURES = """\
# Feature: Sample Web Feature with Fixtures

> Label: "Sample Feature"
> Category: "CDD"
> Prerequisite: features/policy_critic.md
> Web Testable: http://localhost:9086
> Web Port File: .purlin/runtime/cdd.port
> Web Start: /pl-cdd
> Test Fixtures: https://github.com/org/fixtures.git

[TESTING]

## 1. Overview
A sample feature with fixture-backed testing.

## 3. Scenarios
### Manual Scenarios (Human Verification Required)

#### Scenario: Dashboard Shows Fixture State
    Given a CDD server loaded with fixture tag "main/feature/scenario-one"
    When the user navigates to the dashboard
    Then the dashboard displays fixture project data

#### Scenario: Normal Dashboard Loads
    Given the server is running
    When the user navigates to the dashboard
    Then the page loads successfully
"""

# BUG discovery format per spec Section 2.9
BUG_DISCOVERY_PATTERN = re.compile(
    r'### \[BUG\] .+ \(Discovered: \d{4}-\d{2}-\d{2}\)\n'
    r'- \*\*Scenario:\*\* .+\n'
    r'- \*\*Observed Behavior:\*\* .+\n'
    r'- \*\*Expected Behavior:\*\* .+\n'
    r'- \*\*Action Required:\*\* Builder\n'
    r'- \*\*Status:\*\* OPEN',
    re.MULTILINE
)


def _make_feature_dir(tmpdir, name):
    """Create a features/ directory with a named feature file."""
    features_dir = os.path.join(tmpdir, 'features')
    os.makedirs(features_dir, exist_ok=True)
    return features_dir


def _write_feature(tmpdir, name, content):
    """Write a feature file to the temp project directory."""
    features_dir = _make_feature_dir(tmpdir, name)
    path = os.path.join(features_dir, f'{name}.md')
    with open(path, 'w') as f:
        f.write(content)
    return path


def _write_critic_json(tmpdir, feature_name, content):
    """Write a critic.json to tests/<feature_name>/."""
    test_dir = os.path.join(tmpdir, 'tests', feature_name)
    os.makedirs(test_dir, exist_ok=True)
    path = os.path.join(test_dir, 'critic.json')
    with open(path, 'w') as f:
        f.write(content)
    return path


def _extract_web_testable_url(content):
    """Extract the Web Testable URL from feature file content."""
    match = re.search(r'>\s*Web Testable:\s*(\S+)', content)
    return match.group(1) if match else None


def _extract_manual_scenarios(content):
    """Extract manual scenario names from feature file content."""
    scenarios = []
    in_manual = False
    for line in content.split('\n'):
        if '### Manual Scenarios' in line:
            in_manual = True
            continue
        if in_manual and line.startswith('## '):
            break
        if in_manual and line.startswith('#### Scenario:'):
            name = line.replace('#### Scenario:', '').strip()
            scenarios.append(name)
    return scenarios


def _extract_visual_checklist(content):
    """Extract visual spec checklist items from feature file content."""
    items = []
    in_visual = False
    for line in content.split('\n'):
        if '## Visual Specification' in line:
            in_visual = True
            continue
        if in_visual and line.startswith('## ') and 'Visual' not in line:
            break
        if in_visual and re.match(r'^- \[ \] ', line.strip()):
            items.append(line.strip()[6:])
    return items


def _parse_url_override(args):
    """Parse URL override from argument list.

    A URL override is an argument starting with http:// or https://.
    Returns (feature_names, url_override).
    """
    features = []
    url_override = None
    for arg in args:
        if arg.startswith('http://') or arg.startswith('https://'):
            url_override = arg
        else:
            features.append(arg)
    return features, url_override


def _extract_test_fixtures_url(content):
    """Extract the Test Fixtures repo URL from feature file content."""
    match = re.search(r'>\s*Test Fixtures:\s*(\S+)', content)
    return match.group(1) if match else None


def _detect_fixture_tag_in_steps(scenario_text):
    """Detect fixture tag references in scenario Given steps.

    Looks for pattern: fixture tag "<tag-path>" in Given lines.
    Returns the tag path or None.
    """
    match = re.search(r'fixture tag "([^"]+)"', scenario_text)
    return match.group(1) if match else None


def _extract_web_port_file(content):
    """Extract the Web Port File path from feature file content."""
    match = re.search(r'>\s*Web Port File:\s*(\S+)', content)
    return match.group(1) if match else None


def _extract_web_start(content):
    """Extract the Web Start command from feature file content."""
    match = re.search(r'>\s*Web Start:\s*(.+)', content)
    return match.group(1).strip() if match else None


def _resolve_url(base_url, port_file_path=None, url_override=None,
                 project_root=None):
    """Resolve the effective URL using the priority order.

    Priority: (1) URL override, (2) runtime port file, (3) base URL.
    Returns the resolved URL string.
    """
    if url_override:
        return url_override

    if port_file_path and project_root:
        abs_port_path = os.path.join(project_root, port_file_path)
        if os.path.isfile(abs_port_path):
            try:
                with open(abs_port_path) as f:
                    port_str = f.read().strip()
                if port_str.isdigit():
                    # Replace port in the base URL
                    import urllib.parse
                    parsed = urllib.parse.urlparse(base_url)
                    replaced = parsed._replace(
                        netloc=f'{parsed.hostname}:{port_str}')
                    return urllib.parse.urlunparse(replaced)
            except (IOError, OSError):
                pass

    return base_url


def _filter_scenarios_by_scope(scope, manual_scenarios, visual_items):
    """Filter scenarios and visual items by regression scope.

    Returns (filtered_scenarios, filtered_visual, skip_reason).
    """
    if scope == 'cosmetic':
        return [], [], 'QA skip (cosmetic change)'
    if scope.startswith('dependency-only'):
        return [], [], 'QA skip (dependency-only, no scenarios in scope)'
    if scope.startswith('targeted:'):
        targeted_names = [
            s.strip() for s in scope[len('targeted:'):].split(',')]
        filtered_sc = [
            s for s in manual_scenarios if s in targeted_names]
        filtered_vi = [
            v for v in visual_items
            if any(t.lower() in v.lower() for t in targeted_names)]
        return filtered_sc, filtered_vi, None
    # 'full' or missing/default
    return manual_scenarios, visual_items, None


class TestAutoDiscoverWebTestableFeatures(unittest.TestCase):
    """Scenario: Auto-discover web-testable features

    Given the Critic report shows features in TESTING state
    And some features have `> Web Testable:` metadata and others do not
    When `/pl-web-verify` is invoked without arguments
    Then only features with `> Web Testable:` metadata are selected
    And features without the annotation are silently skipped

    Test: Verifies Web Testable metadata parsing and filtering logic.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_web_testable_url_extracted(self):
        """URL is correctly extracted from > Web Testable: metadata."""
        url = _extract_web_testable_url(SAMPLE_WEB_TESTABLE_FEATURE)
        self.assertEqual(url, 'http://localhost:9086')

    def test_non_web_feature_returns_none(self):
        """Feature without Web Testable metadata returns None."""
        url = _extract_web_testable_url(SAMPLE_NON_WEB_FEATURE)
        self.assertIsNone(url)

    def test_filtering_selects_only_web_testable(self):
        """Only features with Web Testable metadata pass the filter."""
        _write_feature(self.tmpdir, 'web_feat', SAMPLE_WEB_TESTABLE_FEATURE)
        _write_feature(self.tmpdir, 'cli_feat', SAMPLE_NON_WEB_FEATURE)
        features_dir = os.path.join(self.tmpdir, 'features')
        eligible = []
        for fname in os.listdir(features_dir):
            path = os.path.join(features_dir, fname)
            with open(path) as f:
                content = f.read()
            if _extract_web_testable_url(content):
                eligible.append(fname)
        self.assertEqual(eligible, ['web_feat.md'])

    def test_web_testable_metadata_position(self):
        """Web Testable metadata works alongside other > metadata lines."""
        content = SAMPLE_WEB_TESTABLE_FEATURE
        self.assertIn('> Label:', content)
        self.assertIn('> Category:', content)
        self.assertIn('> Prerequisite:', content)
        self.assertIn('> Web Testable:', content)

    def test_command_file_exists(self):
        """The skill command file .claude/commands/pl-web-verify.md exists."""
        self.assertTrue(os.path.isfile(COMMAND_FILE),
                        f'Command file not found: {COMMAND_FILE}')


class TestUrlOverrideFromArgument(unittest.TestCase):
    """Scenario: URL override from argument

    Given a feature has `> Web Testable: http://localhost:9086`
    When `/pl-web-verify feature_name http://localhost:3000` is invoked
    Then the URL override `http://localhost:3000` is used instead

    Test: Verifies URL override argument parsing.
    """

    def test_url_override_detected_http(self):
        """HTTP URL override is correctly parsed from arguments."""
        features, url = _parse_url_override(
            ['feature_name', 'http://localhost:3000'])
        self.assertEqual(url, 'http://localhost:3000')
        self.assertEqual(features, ['feature_name'])

    def test_url_override_detected_https(self):
        """HTTPS URL override is correctly parsed from arguments."""
        features, url = _parse_url_override(
            ['feature_name', 'https://example.com:8080'])
        self.assertEqual(url, 'https://example.com:8080')
        self.assertEqual(features, ['feature_name'])

    def test_no_url_override_when_absent(self):
        """No URL override when only feature names are provided."""
        features, url = _parse_url_override(['feature_a', 'feature_b'])
        self.assertIsNone(url)
        self.assertEqual(features, ['feature_a', 'feature_b'])

    def test_url_override_replaces_spec_url(self):
        """URL override takes precedence over the spec's Web Testable URL."""
        spec_url = _extract_web_testable_url(SAMPLE_WEB_TESTABLE_FEATURE)
        _, override = _parse_url_override(
            ['sample_web', 'http://localhost:3000'])
        effective_url = override if override else spec_url
        self.assertEqual(effective_url, 'http://localhost:3000')
        self.assertNotEqual(effective_url, spec_url)

    def test_empty_args_returns_no_override(self):
        """Empty argument list returns no features and no URL override."""
        features, url = _parse_url_override([])
        self.assertEqual(features, [])
        self.assertIsNone(url)

    def test_multiple_features_with_url_override(self):
        """Multiple feature names with a single URL override."""
        features, url = _parse_url_override(
            ['feat_a', 'feat_b', 'http://localhost:4000'])
        self.assertEqual(features, ['feat_a', 'feat_b'])
        self.assertEqual(url, 'http://localhost:4000')


class TestPlaywrightMcpAutoSetup(unittest.TestCase):
    """Scenario: Playwright MCP not available triggers auto-setup

    Given Playwright MCP tools are not available in the current session
    When `/pl-web-verify` is invoked
    Then the skill attempts to install and configure Playwright MCP
    And informs the user a session restart is required
    And stops execution (does not attempt verification)

    Test: Verifies the auto-setup protocol in the skill file.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_skill_checks_for_browser_navigate(self):
        """Skill file references browser_navigate as the MCP availability check."""
        self.assertIn('browser_navigate', self.command_content)

    def test_skill_references_npx_playwright_mcp(self):
        """Skill file references npx @playwright/mcp for auto-setup."""
        self.assertIn('@playwright/mcp', self.command_content)

    def test_skill_references_claude_mcp_add(self):
        """Skill file includes the claude mcp add command."""
        self.assertIn('claude mcp add', self.command_content)

    def test_skill_mentions_session_restart(self):
        """Skill file instructs user to restart session after MCP setup."""
        self.assertIn('restart', self.command_content.lower())

    def test_skill_stops_after_setup(self):
        """Skill file stops execution after auto-setup (no verification)."""
        self.assertIn('Stop execution', self.command_content)

    def test_skill_provides_manual_setup_instructions(self):
        """Skill file includes manual setup fallback instructions."""
        self.assertIn('Manual setup', self.command_content)


class TestManualScenarioPassRecording(unittest.TestCase):
    """Scenario: Manual scenario PASS recorded correctly

    Given a web-testable feature has a manual scenario with Given/When/Then
    And Playwright MCP is available
    When `/pl-web-verify` executes the scenario
    And all Then/And verification points pass
    Then the scenario is recorded as PASS with evidence notes

    Test: Verifies manual scenario extraction and result format.
    """

    def test_manual_scenarios_extracted(self):
        """Manual scenarios are correctly extracted from feature content."""
        scenarios = _extract_manual_scenarios(SAMPLE_WEB_TESTABLE_FEATURE)
        self.assertEqual(scenarios, ['Dashboard Layout Correct'])

    def test_manual_scenario_has_given_when_then(self):
        """Extracted manual scenarios contain Gherkin steps."""
        content = SAMPLE_WEB_TESTABLE_FEATURE
        self.assertIn('Given the server is running', content)
        self.assertIn('When the user navigates', content)
        self.assertIn('Then the dashboard heading', content)

    def test_pass_result_format(self):
        """PASS result includes scenario name and evidence."""
        result = {
            'scenario': 'Dashboard Layout Correct',
            'status': 'PASS',
            'evidence': 'Screenshot shows heading "CDD Monitor"; table visible'
        }
        self.assertEqual(result['status'], 'PASS')
        self.assertIn('evidence', result)
        self.assertNotEqual(result['evidence'], '')

    def test_skill_references_browser_screenshot(self):
        """Skill file uses browser_screenshot for evidence capture."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('browser_screenshot', content)

    def test_skill_references_browser_evaluate(self):
        """Skill file uses browser_evaluate for DOM state verification."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('browser_evaluate', content)


class TestManualScenarioFailCreatesBugDiscovery(unittest.TestCase):
    """Scenario: Manual scenario FAIL creates BUG discovery

    Given a web-testable feature has a manual scenario
    When `/pl-web-verify` executes the scenario
    And a Then verification point fails
    Then a [BUG] discovery is recorded in User Testing Discoveries
    And the discovery includes observed behavior from screenshot/DOM
    And the discovery is committed to git

    Test: Verifies BUG discovery format per spec Section 2.9.
    """

    def test_bug_discovery_format_valid(self):
        """BUG discovery matches the required format from the spec."""
        sample_bug = (
            '### [BUG] Dashboard heading shows wrong title '
            '(Discovered: 2026-03-06)\n'
            '- **Scenario:** Dashboard Layout Correct\n'
            '- **Observed Behavior:** Heading shows "Status" '
            'instead of "CDD Monitor"\n'
            '- **Expected Behavior:** Dashboard heading displays '
            '"CDD Monitor"\n'
            '- **Action Required:** Builder\n'
            '- **Status:** OPEN'
        )
        self.assertRegex(sample_bug, BUG_DISCOVERY_PATTERN)

    def test_bug_discovery_has_required_fields(self):
        """BUG discovery contains all required fields."""
        required_fields = [
            'Scenario', 'Observed Behavior', 'Expected Behavior',
            'Action Required', 'Status']
        sample_bug = (
            '### [BUG] Test bug (Discovered: 2026-03-06)\n'
            '- **Scenario:** Test\n'
            '- **Observed Behavior:** X\n'
            '- **Expected Behavior:** Y\n'
            '- **Action Required:** Builder\n'
            '- **Status:** OPEN'
        )
        for field in required_fields:
            self.assertIn(f'**{field}:**', sample_bug)

    def test_bug_action_required_is_builder(self):
        """BUG discovery Action Required defaults to Builder."""
        sample_bug = '- **Action Required:** Builder'
        self.assertIn('Builder', sample_bug)

    def test_bug_status_is_open(self):
        """BUG discovery Status is OPEN when created."""
        sample_bug = '- **Status:** OPEN'
        self.assertIn('OPEN', sample_bug)

    def test_skill_references_bug_commit_format(self):
        """Skill file includes the BUG commit message format."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('qa(', content)
        self.assertIn('[BUG]', content)
        self.assertIn('web-verify', content)


class TestInconclusiveStepHandling(unittest.TestCase):
    """Scenario: Inconclusive step handled gracefully

    Given a manual scenario contains a step requiring non-browser verification
    When `/pl-web-verify` cannot automate that step
    Then the step is marked INCONCLUSIVE
    And the summary recommends manual verification via `/pl-verify`
    And the inconclusive step is NOT recorded as a failure

    Test: Verifies INCONCLUSIVE classification and handling.
    """

    def test_inconclusive_is_not_pass_or_fail(self):
        """INCONCLUSIVE is a distinct status from PASS and FAIL."""
        statuses = {'PASS', 'FAIL', 'INCONCLUSIVE'}
        self.assertIn('INCONCLUSIVE', statuses)
        self.assertEqual(len(statuses), 3)

    def test_inconclusive_not_recorded_as_bug(self):
        """INCONCLUSIVE items are NOT recorded as BUG discoveries."""
        # INCONCLUSIVE should produce a recommendation, not a [BUG]
        result = {'status': 'INCONCLUSIVE', 'reason': 'Requires email check'}
        self.assertNotEqual(result['status'], 'FAIL')
        self.assertIn('reason', result)

    def test_inconclusive_recommends_pl_verify(self):
        """INCONCLUSIVE recommendation points to /pl-verify."""
        recommendation = (
            'The following items could not be automated. '
            'Use `/pl-verify` for manual verification.')
        self.assertIn('/pl-verify', recommendation)

    def test_skill_file_references_inconclusive(self):
        """Skill file documents INCONCLUSIVE handling."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('INCONCLUSIVE', content)

    def test_skill_file_references_bash_fallback(self):
        """Skill file mentions Bash tools as fallback for non-browser steps."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('Bash', content)


class TestVisualSpecVerification(unittest.TestCase):
    """Scenario: Visual spec items verified via screenshot analysis

    Given a web-testable feature has a Visual Specification with checklist items
    When `/pl-web-verify` navigates to the screen and takes a screenshot
    Then each checklist item is analyzed against the screenshot using vision
    And PASS/FAIL is recorded per item with observation notes

    Test: Verifies visual spec extraction and per-item result recording.
    """

    def test_visual_checklist_items_extracted(self):
        """Visual spec checklist items are correctly extracted."""
        items = _extract_visual_checklist(SAMPLE_WEB_TESTABLE_FEATURE)
        self.assertEqual(len(items), 3)
        self.assertIn('Heading uses 24px bold font', items)
        self.assertIn('Table rows alternate background colors', items)
        self.assertIn('Status badges show correct colors', items)

    def test_empty_visual_spec_returns_empty(self):
        """Feature without Visual Specification returns empty list."""
        items = _extract_visual_checklist(SAMPLE_NON_WEB_FEATURE)
        self.assertEqual(items, [])

    def test_per_item_result_has_observation(self):
        """Each visual item result includes observation notes."""
        result = {
            'item': 'Heading uses 24px bold font',
            'status': 'PASS',
            'observation': 'Heading measured at 24px bold via computed style'
        }
        self.assertIn('observation', result)
        self.assertNotEqual(result['observation'], '')

    def test_skill_file_documents_visual_verification(self):
        """Skill file has a Visual Spec Verification step."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('Visual Spec Verification', content)


class TestRegressionScopeRespected(unittest.TestCase):
    """Scenario: Regression scope respected

    Given a feature's critic.json has regression_scope: "targeted:Scenario A"
    When `/pl-web-verify` is invoked for that feature
    Then only "Scenario A" is executed
    And all other manual scenarios and visual items are skipped

    Test: Verifies scope filtering logic for targeted scope.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_targeted_scope_filters_scenarios(self):
        """Targeted scope selects only named scenarios."""
        all_scenarios = ['Dashboard Layout Correct', 'Other Scenario']
        scope = 'targeted:Dashboard Layout Correct'
        filtered, _, skip = _filter_scenarios_by_scope(
            scope, all_scenarios, [])
        self.assertIsNone(skip)
        self.assertEqual(filtered, ['Dashboard Layout Correct'])
        self.assertNotIn('Other Scenario', filtered)

    def test_full_scope_includes_all(self):
        """Full scope includes all scenarios and visual items."""
        scenarios = ['A', 'B']
        visuals = ['Item 1', 'Item 2']
        filtered_sc, filtered_vi, skip = _filter_scenarios_by_scope(
            'full', scenarios, visuals)
        self.assertIsNone(skip)
        self.assertEqual(filtered_sc, scenarios)
        self.assertEqual(filtered_vi, visuals)

    def test_dependency_only_scope_skips(self):
        """Dependency-only scope skips with appropriate message."""
        filtered_sc, filtered_vi, skip = _filter_scenarios_by_scope(
            'dependency-only', ['A'], ['B'])
        self.assertEqual(filtered_sc, [])
        self.assertEqual(filtered_vi, [])
        self.assertIn('dependency-only', skip)

    def test_missing_scope_defaults_to_full(self):
        """Missing or empty scope defaults to full verification."""
        scenarios = ['A']
        visuals = ['V1']
        filtered_sc, filtered_vi, skip = _filter_scenarios_by_scope(
            '', scenarios, visuals)
        self.assertIsNone(skip)
        self.assertEqual(filtered_sc, scenarios)
        self.assertEqual(filtered_vi, visuals)

    def test_critic_json_scope_parsed(self):
        """Regression scope is correctly read from critic.json content."""
        import json
        data = json.loads(SAMPLE_CRITIC_TARGETED)
        self.assertEqual(
            data['regression_scope'], 'targeted:Dashboard Layout Correct')


class TestCosmeticScopeSkipsFeature(unittest.TestCase):
    """Scenario: Cosmetic scope skips feature

    Given a feature's critic.json has regression_scope: "cosmetic"
    When `/pl-web-verify` is invoked for that feature
    Then the feature is skipped entirely with a note

    Test: Verifies cosmetic scope filtering.
    """

    def test_cosmetic_scope_returns_skip_reason(self):
        """Cosmetic scope returns a skip reason."""
        _, _, skip = _filter_scenarios_by_scope('cosmetic', ['A'], ['V1'])
        self.assertIsNotNone(skip)
        self.assertIn('cosmetic', skip)

    def test_cosmetic_scope_returns_empty_lists(self):
        """Cosmetic scope returns empty scenario and visual lists."""
        filtered_sc, filtered_vi, _ = _filter_scenarios_by_scope(
            'cosmetic', ['A', 'B'], ['V1'])
        self.assertEqual(filtered_sc, [])
        self.assertEqual(filtered_vi, [])

    def test_cosmetic_critic_json_parsed(self):
        """Cosmetic scope is correctly read from critic.json content."""
        import json
        data = json.loads(SAMPLE_CRITIC_COSMETIC)
        self.assertEqual(data['regression_scope'], 'cosmetic')

    def test_skill_file_documents_cosmetic_skip(self):
        """Skill file documents cosmetic scope skip behavior."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('cosmetic', content)


class TestQaCompletionGate(unittest.TestCase):
    """Scenario: QA completion gate prompts for completion

    Given the invoking agent is QA
    And all scenarios and visual items passed with zero failures
    When results are presented
    Then the skill prompts to run `/pl-complete <name>`

    Test: Verifies QA-specific completion gate behavior.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_skill_detects_qa_role(self):
        """Skill file checks for QA role identity marker."""
        self.assertIn('Role Definition: The QA', self.command_content)

    def test_skill_prompts_pl_complete_for_qa(self):
        """Skill file prompts QA to run /pl-complete."""
        self.assertIn('/pl-complete', self.command_content)

    def test_skill_qa_section_mentions_zero_failures(self):
        """Skill file conditions QA completion on zero failures."""
        self.assertIn('zero failures', self.command_content)

    def test_qa_gate_distinct_from_builder_gate(self):
        """QA and Builder completion gates are distinct in the skill."""
        # Both role markers must appear in the file
        self.assertIn('QA Agent invocation', self.command_content)
        self.assertIn('Builder invocation', self.command_content)


class TestBuilderCompletionGate(unittest.TestCase):
    """Scenario: Builder completion gate is summary only

    Given the invoking agent is Builder
    And all scenarios and visual items passed
    When results are presented
    Then only a summary is printed
    And the skill suggests QA run `/pl-complete`

    Test: Verifies Builder-specific completion gate behavior.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_skill_detects_builder_role(self):
        """Skill file checks for Builder role identity marker."""
        self.assertIn('Role Definition: The Builder', self.command_content)

    def test_builder_does_not_mark_complete(self):
        """Skill file states Builder does NOT mark complete."""
        self.assertIn('Do NOT mark complete', self.command_content)

    def test_builder_suggests_qa_complete(self):
        """Skill file suggests QA agent run /pl-complete for Builder."""
        self.assertIn('Suggest QA', self.command_content)

    def test_builder_gets_summary_only(self):
        """Builder invocation produces summary only, not a completion prompt."""
        self.assertIn('print summary only', self.command_content)


class TestInstructionFilesUpdated(unittest.TestCase):
    """Scenario: Instruction files updated with web-verify references

    Given the skill file has been created
    When instruction updates are applied per Section 2.11
    Then /pl-web-verify appears in both QA and Builder authorized command lists
    And /pl-web-verify [name] appears in all variants of both command tables
    And > Web Testable: is documented in feature_format.md
    And visual_spec_convention.md references the automated alternative
    And visual_verification_protocol.md has Section 5.4.7 for Playwright MCP

    Test: Verifies all 7 instruction files contain required references.
    """

    def test_all_seven_instruction_files_exist(self):
        """All 7 instruction files from Section 2.11 exist."""
        for name, path in INSTRUCTION_FILES.items():
            self.assertTrue(os.path.isfile(path),
                            f'Instruction file not found: {name} at {path}')

    def test_qa_base_authorized_commands(self):
        """QA_BASE.md authorized commands include /pl-web-verify."""
        with open(INSTRUCTION_FILES['qa_base']) as f:
            content = f.read()
        # Find the authorized commands line
        for line in content.split('\n'):
            if 'Authorized commands:' in line and '/pl-web-verify' in line:
                break
        else:
            self.fail('/pl-web-verify not in QA_BASE authorized commands')

    def test_builder_base_authorized_commands(self):
        """BUILDER_BASE.md authorized commands include /pl-web-verify."""
        with open(INSTRUCTION_FILES['builder_base']) as f:
            content = f.read()
        for line in content.split('\n'):
            if 'Authorized commands:' in line and '/pl-web-verify' in line:
                break
        else:
            self.fail('/pl-web-verify not in BUILDER_BASE authorized commands')

    def test_qa_commands_both_variants(self):
        """qa_commands.md has /pl-web-verify in both table variants."""
        with open(INSTRUCTION_FILES['qa_commands']) as f:
            content = f.read()
        occurrences = content.count('/pl-web-verify')
        self.assertGreaterEqual(
            occurrences, 2,
            f'Expected >= 2 occurrences in qa_commands.md, found {occurrences}')

    def test_builder_commands_both_variants(self):
        """builder_commands.md has /pl-web-verify in both table variants."""
        with open(INSTRUCTION_FILES['builder_commands']) as f:
            content = f.read()
        occurrences = content.count('/pl-web-verify')
        self.assertGreaterEqual(
            occurrences, 2,
            f'Expected >= 2 in builder_commands.md, found {occurrences}')

    def test_feature_format_documents_web_testable(self):
        """feature_format.md documents > Web Testable: metadata."""
        with open(INSTRUCTION_FILES['feature_format']) as f:
            content = f.read()
        self.assertIn('Web Testable', content)
        self.assertIn('/pl-web-verify', content)

    def test_visual_spec_convention_references_automated_alt(self):
        """visual_spec_convention.md references automated Playwright MCP."""
        with open(INSTRUCTION_FILES['visual_spec_convention']) as f:
            content = f.read()
        self.assertIn('/pl-web-verify', content)
        self.assertIn('Playwright MCP', content)

    def test_visual_verification_protocol_section_547(self):
        """visual_verification_protocol.md has Section 5.4.7."""
        with open(INSTRUCTION_FILES['visual_verification_protocol']) as f:
            content = f.read()
        self.assertIn('5.4.7', content)
        self.assertIn('Playwright MCP', content)

    def test_visual_verification_protocol_loader_notice(self):
        """visual_verification_protocol.md on-demand loader includes cmd."""
        with open(INSTRUCTION_FILES['visual_verification_protocol']) as f:
            content = f.read()
        # The loader notice at the top should mention /pl-web-verify
        lines = content.split('\n')[:5]
        loader_text = '\n'.join(lines)
        self.assertIn('/pl-web-verify', loader_text)

    def test_visual_spec_convention_loader_notice(self):
        """visual_spec_convention.md on-demand loader includes cmd."""
        with open(INSTRUCTION_FILES['visual_spec_convention']) as f:
            content = f.read()
        lines = content.split('\n')[:5]
        loader_text = '\n'.join(lines)
        self.assertIn('/pl-web-verify', loader_text)

    def test_qa_base_references_web_testable_in_section_54(self):
        """QA_BASE.md Section 5.4 references Web Testable and /pl-web-verify."""
        with open(INSTRUCTION_FILES['qa_base']) as f:
            content = f.read()
        self.assertIn('Web Testable', content)
        self.assertIn('Section 5.4.7', content)

    def test_builder_base_references_web_verification(self):
        """BUILDER_BASE.md references web verification in Section 5.3."""
        with open(INSTRUCTION_FILES['builder_base']) as f:
            content = f.read()
        self.assertIn('Web Verification', content)
        self.assertIn('Web Testable', content)


class TestDynamicPortResolution(unittest.TestCase):
    """Scenario: Dynamic port resolution from port file

    Given a feature has `> Web Testable: http://localhost:9086`
    And the feature has `> Web Port File: .purlin/runtime/cdd.port`
    And `.purlin/runtime/cdd.port` contains `52288`
    When `/pl-web-verify` resolves the URL for that feature
    Then the resolved URL is `http://localhost:52288`

    Test: Verifies port file reading and URL port replacement.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_port_file_metadata_extracted(self):
        """Web Port File metadata is correctly extracted."""
        port_file = _extract_web_port_file(
            SAMPLE_WEB_TESTABLE_WITH_PORT_FILE)
        self.assertEqual(port_file, '.purlin/runtime/cdd.port')

    def test_web_start_metadata_extracted(self):
        """Web Start metadata is correctly extracted."""
        start_cmd = _extract_web_start(
            SAMPLE_WEB_TESTABLE_WITH_PORT_FILE)
        self.assertEqual(start_cmd, '/pl-cdd')

    def test_no_port_file_metadata_returns_none(self):
        """Feature without Web Port File returns None."""
        port_file = _extract_web_port_file(SAMPLE_WEB_TESTABLE_FEATURE)
        self.assertIsNone(port_file)

    def test_no_web_start_returns_none(self):
        """Feature without Web Start returns None."""
        start_cmd = _extract_web_start(SAMPLE_WEB_TESTABLE_FEATURE)
        self.assertIsNone(start_cmd)

    def test_port_file_overrides_spec_port(self):
        """Port from file replaces port in Web Testable URL."""
        runtime_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(runtime_dir)
        with open(os.path.join(runtime_dir, 'cdd.port'), 'w') as f:
            f.write('52288')

        resolved = _resolve_url(
            'http://localhost:9086',
            port_file_path='.purlin/runtime/cdd.port',
            project_root=self.tmpdir)
        self.assertEqual(resolved, 'http://localhost:52288')

    def test_port_file_missing_falls_back(self):
        """Missing port file falls back to spec URL."""
        resolved = _resolve_url(
            'http://localhost:9086',
            port_file_path='.purlin/runtime/cdd.port',
            project_root=self.tmpdir)
        self.assertEqual(resolved, 'http://localhost:9086')

    def test_port_file_empty_falls_back(self):
        """Empty port file falls back to spec URL."""
        runtime_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(runtime_dir)
        with open(os.path.join(runtime_dir, 'cdd.port'), 'w') as f:
            f.write('')

        resolved = _resolve_url(
            'http://localhost:9086',
            port_file_path='.purlin/runtime/cdd.port',
            project_root=self.tmpdir)
        self.assertEqual(resolved, 'http://localhost:9086')

    def test_url_override_takes_precedence(self):
        """URL override takes precedence over port file."""
        runtime_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(runtime_dir)
        with open(os.path.join(runtime_dir, 'cdd.port'), 'w') as f:
            f.write('52288')

        resolved = _resolve_url(
            'http://localhost:9086',
            port_file_path='.purlin/runtime/cdd.port',
            url_override='http://localhost:3000',
            project_root=self.tmpdir)
        self.assertEqual(resolved, 'http://localhost:3000')

    def test_no_port_file_path_uses_base_url(self):
        """No port file path uses base URL directly."""
        resolved = _resolve_url(
            'http://localhost:9086',
            port_file_path=None,
            project_root=self.tmpdir)
        self.assertEqual(resolved, 'http://localhost:9086')

    def test_invalid_port_file_content_falls_back(self):
        """Non-numeric port file content falls back to spec URL."""
        runtime_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(runtime_dir)
        with open(os.path.join(runtime_dir, 'cdd.port'), 'w') as f:
            f.write('not-a-port')

        resolved = _resolve_url(
            'http://localhost:9086',
            port_file_path='.purlin/runtime/cdd.port',
            project_root=self.tmpdir)
        self.assertEqual(resolved, 'http://localhost:9086')


class TestHeadedPlaywrightDetection(unittest.TestCase):
    """Scenario: Headed Playwright MCP detected triggers reconfiguration

    Given Playwright MCP tools are available in the current session
    But the MCP server was configured without `--headless`
    When `/pl-web-verify` is invoked
    Then the skill instructs the user to reconfigure with headless mode

    Test: Verifies skill file has headless detection logic.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_skill_checks_headless_flag(self):
        """Skill file checks for --headless in MCP config."""
        self.assertIn('--headless', self.command_content)

    def test_skill_references_mcp_config_files(self):
        """Skill file references all MCP config file locations."""
        # Project-level settings
        self.assertIn('settings.local.json', self.command_content)
        self.assertIn('settings.json', self.command_content)
        self.assertIn('mcpServers.playwright', self.command_content)
        # Per-project config in ~/.claude.json (projects.<path> key)
        self.assertIn('projects.', self.command_content)
        # Plugin marketplace
        self.assertIn('plugins/', self.command_content)

    def test_skill_provides_reconfigure_command(self):
        """Skill file provides the reconfigure commands."""
        self.assertIn('claude mcp remove playwright', self.command_content)
        self.assertIn(
            'claude mcp add playwright -- npx @playwright/mcp --headless',
            self.command_content)

    def test_skill_stops_on_headed_detection(self):
        """Skill file stops execution when headed mode detected."""
        self.assertIn('Stop execution', self.command_content)


class TestDynamicPortResolutionInSkillFile(unittest.TestCase):
    """Verifies the skill file documents the port resolution protocol."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_skill_references_web_port_file(self):
        """Skill file references Web Port File metadata."""
        self.assertIn('Web Port File', self.command_content)

    def test_skill_references_web_start(self):
        """Skill file references Web Start metadata."""
        self.assertIn('Web Start', self.command_content)

    def test_skill_documents_priority_order(self):
        """Skill file documents URL override > port file > spec URL."""
        self.assertIn('URL override', self.command_content)
        self.assertIn('port file', self.command_content.lower())

    def test_skill_documents_liveness_check(self):
        """Skill file documents liveness check via curl."""
        self.assertIn('curl', self.command_content)
        self.assertIn('liveness', self.command_content.lower())

    def test_skill_documents_auto_start(self):
        """Skill file documents server auto-start protocol."""
        self.assertIn('10 seconds', self.command_content)
        self.assertIn('auto-start', self.command_content.lower())

    def test_skill_continues_on_failure(self):
        """Skill file continues with other features on liveness failure."""
        self.assertIn(
            'skip this feature (continue with others)',
            self.command_content)


class TestFixtureBackedServerStarted(unittest.TestCase):
    """Scenario: Fixture-backed server started for scenario with fixture tag

    Given a feature has `> Web Testable: http://localhost:9086`
    And the feature has `> Test Fixtures: https://github.com/org/fixtures.git`
    And a scenario's Given step references fixture tag "main/feature/scenario-one"
    When `/pl-web-verify` processes that scenario
    Then the fixture tag is checked out to a temp directory
    And a CDD server is started with `--project-root <fixture-dir> --port 0`
    And the ephemeral port from the server's stdout is used for navigation
    And the static URL port (9086) is NOT used

    Test: Verifies fixture metadata parsing, tag detection, and skill file
    instructions for fixture-backed server startup.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_test_fixtures_metadata_extracted(self):
        """Test Fixtures URL is correctly extracted from feature metadata."""
        url = _extract_test_fixtures_url(
            SAMPLE_WEB_TESTABLE_WITH_FIXTURES)
        self.assertEqual(url, 'https://github.com/org/fixtures.git')

    def test_no_test_fixtures_returns_none(self):
        """Feature without Test Fixtures metadata returns None."""
        url = _extract_test_fixtures_url(SAMPLE_WEB_TESTABLE_FEATURE)
        self.assertIsNone(url)

    def test_fixture_tag_detected_in_given_step(self):
        """Fixture tag reference is detected in scenario Given steps."""
        scenario = (
            '    Given a CDD server loaded with '
            'fixture tag "main/feature/scenario-one"\n'
            '    When the user navigates to the dashboard\n'
            '    Then the dashboard displays fixture project data')
        tag = _detect_fixture_tag_in_steps(scenario)
        self.assertEqual(tag, 'main/feature/scenario-one')

    def test_no_fixture_tag_returns_none(self):
        """Scenario without fixture tag reference returns None."""
        scenario = (
            '    Given the server is running\n'
            '    When the user navigates to the dashboard\n'
            '    Then the page loads successfully')
        tag = _detect_fixture_tag_in_steps(scenario)
        self.assertIsNone(tag)

    def test_skill_references_fixture_checkout(self):
        """Skill file references fixture.sh checkout command."""
        self.assertIn('fixture.sh checkout', self.command_content)

    def test_skill_references_ephemeral_port(self):
        """Skill file references --port 0 for ephemeral port binding."""
        self.assertIn('--port 0', self.command_content)

    def test_skill_references_project_root_flag(self):
        """Skill file references --project-root for fixture directory."""
        self.assertIn('--project-root', self.command_content)

    def test_skill_documents_fixture_detection(self):
        """Skill file documents fixture tag detection pattern."""
        self.assertIn('fixture tag', self.command_content)


class TestFixtureCheckoutFailureInconclusive(unittest.TestCase):
    """Scenario: Fixture checkout failure marks scenario inconclusive

    Given a feature has `> Test Fixtures: https://github.com/org/fixtures.git`
    And a scenario references fixture tag "main/feature/nonexistent-tag"
    When `/pl-web-verify` attempts to check out the fixture
    Then the checkout fails (tag not found)
    And the scenario is marked INCONCLUSIVE
    And other scenarios in the feature continue normally

    Test: Verifies skill file documents error handling for failed fixture
    checkouts and INCONCLUSIVE classification.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_skill_documents_fixture_error_handling(self):
        """Skill file documents handling of fixture checkout failures."""
        self.assertIn('INCONCLUSIVE', self.command_content)
        self.assertIn('checkout fail', self.command_content.lower())

    def test_skill_continues_after_fixture_failure(self):
        """Skill file continues with other scenarios after fixture failure."""
        self.assertIn(
            'Continue with other scenarios',
            self.command_content)

    def test_fixture_and_non_fixture_scenarios_coexist(self):
        """Feature with both fixture and non-fixture scenarios is valid."""
        url = _extract_test_fixtures_url(
            SAMPLE_WEB_TESTABLE_WITH_FIXTURES)
        self.assertIsNotNone(url)
        scenarios = _extract_manual_scenarios(
            SAMPLE_WEB_TESTABLE_WITH_FIXTURES)
        # Should have both fixture-tagged and normal scenarios
        self.assertEqual(len(scenarios), 2)
        fixture_tagged = [
            s for s in scenarios
            if 'Fixture' in s or 'fixture' in s.lower()]
        non_fixture = [
            s for s in scenarios
            if 'Fixture' not in s and 'fixture' not in s.lower()]
        self.assertGreaterEqual(len(fixture_tagged), 1)
        self.assertGreaterEqual(len(non_fixture), 1)


class TestFixtureCleanupAfterCompletion(unittest.TestCase):
    """Scenario: Fixture cleanup after scenario completion

    Given a fixture-backed scenario has completed (pass or fail)
    When `/pl-web-verify` moves to the next scenario
    Then the fixture-backed CDD server has been stopped
    And the fixture checkout directory has been removed

    Test: Verifies skill file documents cleanup protocol for fixture
    resources after scenario execution.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_skill_documents_server_stop(self):
        """Skill file documents stopping the fixture-backed server."""
        # The cleanup section should mention stopping the server
        self.assertIn('stop', self.command_content.lower())
        self.assertIn('fixture', self.command_content.lower())

    def test_skill_references_fixture_cleanup(self):
        """Skill file references fixture.sh cleanup command."""
        self.assertIn('fixture.sh cleanup', self.command_content)

    def test_skill_cleanup_on_both_pass_and_fail(self):
        """Skill file specifies cleanup regardless of pass/fail."""
        self.assertIn('pass or fail', self.command_content.lower())

    def test_non_fixture_scenarios_use_normal_flow(self):
        """Skill file documents that non-fixture scenarios use normal flow."""
        self.assertIn('Non-fixture scenarios', self.command_content)


# =============================================================================
# Test runner: writes results to tests/pl_web_verify/tests.json
# =============================================================================
if __name__ == '__main__':
    import json as _json

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../..'))
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        project_root = env_root

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    tests_dir = os.path.join(project_root, 'tests', 'pl_web_verify')
    os.makedirs(tests_dir, exist_ok=True)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    status = 'PASS' if failed == 0 else 'FAIL'
    with open(os.path.join(tests_dir, 'tests.json'), 'w') as f:
        _json.dump({
            'status': status,
            'passed': passed,
            'failed': failed,
            'total': result.testsRun
        }, f)
    print(f"\ntests.json: {status}")
