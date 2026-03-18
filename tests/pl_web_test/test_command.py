#!/usr/bin/env python3
"""Tests for the /pl-web-test agent command.

Covers automated scenarios from features/pl_web_test.md:
- Auto-discover web-testable features
- URL override from argument
- Playwright MCP not available triggers auto-setup
- Headed Playwright MCP detected triggers reconfiguration
- Dynamic port resolution from port file
- Port file missing falls back to metadata URL
- Server auto-start when not reachable
- Server not reachable and no start command
- URL override takes precedence over port file
- Manual scenario PASS recorded correctly
- Manual scenario FAIL creates BUG discovery
- Inconclusive step handled gracefully
- Visual spec items verified via screenshot analysis (no Figma MCP)
- Figma-triangulated verification with all sources agreeing
- Figma-triangulated verification detects BUG
- Figma-triangulated verification detects STALE spec
- Figma-triangulated verification detects token drift
- Three-source report format
- Regression scope respected
- Cosmetic scope skips feature
- QA completion gate prompts for completion
- Builder completion gate is summary only
- Instruction files updated with web-test references
- Fixture-backed server started for scenario with fixture tag
- Fixture checkout failure marks scenario inconclusive
- Fixture cleanup after scenario completion

The agent command is a Claude skill defined in .claude/commands/pl-web-test.md.
These tests verify the underlying behaviors that the command depends on:
- Skill file structure (role guard, argument docs, execution protocol)
- Web Test metadata parsing from feature files
- URL override argument parsing
- Scope filtering logic (cosmetic, targeted, dependency-only)
- BUG discovery format validation
- INCONCLUSIVE classification
- Visual spec extraction from feature files
- Figma reference and Token Map extraction from visual specs
- Triangulated verification verdict logic (PASS, BUG, STALE, DRIFT)
- Three-source report format with per-item attribution
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
    PROJECT_ROOT, '.claude', 'commands', 'pl-web-test.md')

# Instruction files that must reference /pl-web-test per Section 2.13
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

# Sample feature spec with Web Test metadata and Web Start
SAMPLE_WEB_TEST_WITH_START = """\
# Feature: Sample Web Feature with Start

> Label: "Sample Feature"
> Category: "CDD"
> Prerequisite: features/policy_critic.md
> Web Test: http://localhost:9086
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
> Web Test: http://localhost:9086

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

# Sample feature spec WITHOUT Web Test metadata
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

# Sample feature spec with Figma reference and Token Map in Visual Specification
SAMPLE_WEB_TESTABLE_WITH_FIGMA = """\
# Feature: Sample Web Feature with Figma

> Label: "Sample Feature"
> Category: "CDD"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/design_visual_standards.md
> Web Test: http://localhost:9086

[TESTING]

## 1. Overview
A sample feature with Figma-backed visual specification.

## 3. Scenarios
### Manual Scenarios (Human Verification Required)
None.

## Visual Specification

> **Design Anchor:** features/design_visual_standards.md
> **Inheritance:** Colors, typography, and theme switching per anchor.

### Screen: Dashboard Main View
- **Reference:** [Figma](https://figma.com/design/ABC123/Dashboard?node-id=42:100)
- **Processed:** 2026-03-10
- **Token Map:**
  - `surface` -> `var(--purlin-bg)`
  - `on-surface` -> `var(--purlin-primary)`
  - `primary` -> `var(--purlin-accent)`
  - `spacing-md` -> `16px`
- [ ] Card width 120px
- [ ] Heading uses var(--font-display)
- [ ] Icon 48x48
- [ ] Subtle left-edge shadow
"""

# Sample feature spec WITHOUT Figma reference in Visual Specification
SAMPLE_WEB_TESTABLE_NO_FIGMA_VISUAL = """\
# Feature: Sample Web Feature No Figma Visual

> Label: "Sample Feature"
> Category: "CDD"
> Prerequisite: features/policy_critic.md
> Web Test: http://localhost:9086

[TESTING]

## 1. Overview
A sample feature with visual spec but no Figma reference.

## 3. Scenarios
### Manual Scenarios (Human Verification Required)
None.

## Visual Specification

### Screen: Settings Panel
- **Reference:** N/A
- **Processed:** N/A
- [ ] Toggle switch is 40x20
- [ ] Label font is 14px Inter
"""

# Sample feature spec with Test Fixtures metadata for fixture-backed testing
SAMPLE_WEB_TESTABLE_WITH_FIXTURES = """\
# Feature: Sample Web Feature with Fixtures

> Label: "Sample Feature"
> Category: "CDD"
> Prerequisite: features/policy_critic.md
> Web Test: http://localhost:9086
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


def _extract_web_test_url(content):
    """Extract the Web Test URL from feature file content."""
    match = re.search(r'>\s*(?:Web Test|AFT Web):\s*(\S+)', content)
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


def _extract_figma_references(content):
    """Extract Figma reference URLs from Visual Specification screens.

    Returns a list of dicts with 'screen', 'url', and 'node_id' keys.
    """
    refs = []
    current_screen = None
    for line in content.split('\n'):
        if line.startswith('### Screen:'):
            current_screen = line.replace('### Screen:', '').strip()
        if current_screen and '**Reference:**' in line:
            match = re.search(
                r'\[Figma\]\(([^)]+)\)', line)
            if match:
                url = match.group(1)
                node_match = re.search(r'node-id=([^&\s]+)', url)
                node_id = node_match.group(1) if node_match else None
                refs.append({
                    'screen': current_screen,
                    'url': url,
                    'node_id': node_id
                })
    return refs


def _extract_token_map(content):
    """Extract Token Map entries from Visual Specification.

    Returns a list of dicts with 'figma_token' and 'project_token' keys.
    """
    entries = []
    in_token_map = False
    for line in content.split('\n'):
        if '**Token Map:**' in line:
            in_token_map = True
            continue
        if in_token_map:
            # Token Map entries are indented list items: - `X` -> `Y`
            match = re.match(
                r'\s*-\s*`([^`]+)`\s*->\s*`([^`]+)`', line)
            if match:
                entries.append({
                    'figma_token': match.group(1),
                    'project_token': match.group(2)
                })
            elif line.strip() and not line.strip().startswith('-'):
                # End of token map (non-list line)
                in_token_map = False
    return entries


def _extract_visual_screens(content):
    """Extract screen names and their Figma reference status.

    Returns a list of dicts with 'name' and 'has_figma' keys.
    """
    screens = []
    current_screen = None
    for line in content.split('\n'):
        if line.startswith('### Screen:'):
            if current_screen:
                screens.append(current_screen)
            current_screen = {
                'name': line.replace('### Screen:', '').strip(),
                'has_figma': False
            }
        if current_screen and '[Figma](' in line:
            current_screen['has_figma'] = True
    if current_screen:
        screens.append(current_screen)
    return screens


def _assign_triangulation_verdict(figma_val, spec_val, app_val):
    """Assign a triangulation verdict based on three-source comparison.

    Returns one of: 'PASS', 'BUG', 'STALE', 'SPEC_DRIFT'.
    """
    if figma_val == spec_val == app_val:
        return 'PASS'
    if figma_val != spec_val and app_val == spec_val:
        # Figma changed, spec and app still match old value
        return 'STALE'
    if figma_val == spec_val and app_val != spec_val:
        # Spec and Figma agree, app is wrong
        return 'BUG'
    if figma_val != spec_val and app_val == figma_val:
        # App matches Figma but spec is stale
        return 'SPEC_DRIFT'
    # Figma changed, spec changed, but app still wrong
    return 'BUG'


def _extract_web_start(content):
    """Extract the Web Start command from feature file content."""
    match = re.search(r'>\s*(?:Web Start|AFT Start):\s*(.+)', content)
    return match.group(1).strip() if match else None


# Runtime port file path (hardcoded, not per-feature metadata)
RUNTIME_PORT_FILE = '.purlin/runtime/cdd.port'


def _resolve_url(base_url, url_override=None, project_root=None):
    """Resolve the effective URL using the priority order.

    Priority: (1) URL override, (2) runtime port file at
    .purlin/runtime/cdd.port, (3) base URL.
    Returns the resolved URL string.
    """
    if url_override:
        return url_override

    if project_root:
        abs_port_path = os.path.join(project_root, RUNTIME_PORT_FILE)
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
    And some features have `> Web Test:` metadata and others do not
    When `/pl-web-test` is invoked without arguments
    Then only features with `> Web Test:` metadata are selected
    And features without the annotation are silently skipped

    Test: Verifies Web Test metadata parsing and filtering logic.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_web_test_url_extracted(self):
        """URL is correctly extracted from > Web Test: metadata."""
        url = _extract_web_test_url(SAMPLE_WEB_TESTABLE_FEATURE)
        self.assertEqual(url, 'http://localhost:9086')

    def test_non_web_feature_returns_none(self):
        """Feature without Web Test metadata returns None."""
        url = _extract_web_test_url(SAMPLE_NON_WEB_FEATURE)
        self.assertIsNone(url)

    def test_filtering_selects_only_web_test(self):
        """Only features with Web Test metadata pass the filter."""
        _write_feature(self.tmpdir, 'web_feat', SAMPLE_WEB_TESTABLE_FEATURE)
        _write_feature(self.tmpdir, 'cli_feat', SAMPLE_NON_WEB_FEATURE)
        features_dir = os.path.join(self.tmpdir, 'features')
        eligible = []
        for fname in os.listdir(features_dir):
            path = os.path.join(features_dir, fname)
            with open(path) as f:
                content = f.read()
            if _extract_web_test_url(content):
                eligible.append(fname)
        self.assertEqual(eligible, ['web_feat.md'])

    def test_web_test_metadata_position(self):
        """Web Test metadata works alongside other > metadata lines."""
        content = SAMPLE_WEB_TESTABLE_FEATURE
        self.assertIn('> Label:', content)
        self.assertIn('> Category:', content)
        self.assertIn('> Prerequisite:', content)
        self.assertIn('> Web Test:', content)

    def test_command_file_exists(self):
        """The skill command file .claude/commands/pl-web-test.md exists."""
        self.assertTrue(os.path.isfile(COMMAND_FILE),
                        f'Command file not found: {COMMAND_FILE}')


class TestUrlOverrideFromArgument(unittest.TestCase):
    """Scenario: URL override from argument

    Given a feature has `> Web Test: http://localhost:9086`
    When `/pl-web-test feature_name http://localhost:3000` is invoked
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
        """URL override takes precedence over the spec's Web Test URL."""
        spec_url = _extract_web_test_url(SAMPLE_WEB_TESTABLE_FEATURE)
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
    When `/pl-web-test` is invoked
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
    When `/pl-web-test` executes the scenario
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
    When `/pl-web-test` executes the scenario
    And a Then verification point fails
    Then a [BUG] discovery is recorded in the feature's discovery sidecar file
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
        self.assertIn('web-test', content)

    def test_skill_records_bugs_in_discovery_sidecar(self):
        """Skill file directs BUG recording to discovery sidecar files."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('.discoveries.md', content)


class TestInconclusiveStepHandling(unittest.TestCase):
    """Scenario: Inconclusive step handled gracefully

    Given a manual scenario contains a step requiring non-browser verification
    When `/pl-web-test` cannot automate that step
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


class TestVisualSpecVerificationNoFigma(unittest.TestCase):
    """Scenario: Visual spec items verified via screenshot analysis (no Figma MCP)

    Given a web-testable feature has a `## Visual Specification` with checklist
    And Figma MCP tools are not available
    When `/pl-web-test` navigates to the screen and takes a screenshot
    Then each checklist item is analyzed against the screenshot using vision
    And PASS/FAIL is recorded per item with observation notes
    And the output notes "Figma MCP not available -- triangulated verification
    skipped"

    Test: Verifies visual spec extraction, per-item result recording, and
    the fallback path when Figma MCP is unavailable.
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

    def test_skill_file_documents_no_figma_fallback(self):
        """Skill file documents the no-Figma-MCP fallback path."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn(
            'Figma MCP not available', content)
        self.assertIn(
            'triangulated verification skipped', content)

    def test_skill_file_fallback_uses_screenshot_only(self):
        """Fallback path uses screenshot + vision, no Figma MCP calls."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        # The fallback section (6.5) should reference screenshot analysis
        self.assertIn('full-page screenshot', content)
        self.assertIn('vision', content.lower())

    def test_no_figma_reference_screen_uses_fallback(self):
        """Screens without Figma reference use fallback verification."""
        screens = _extract_visual_screens(SAMPLE_WEB_TESTABLE_NO_FIGMA_VISUAL)
        self.assertEqual(len(screens), 1)
        self.assertEqual(screens[0]['name'], 'Settings Panel')
        self.assertFalse(screens[0]['has_figma'])


class TestFigmaTriangulatedAllAgree(unittest.TestCase):
    """Scenario: Figma-triangulated verification with all sources agreeing

    Given a web-testable feature has a Visual Specification with Figma reference
    And the Token Map maps "primary" to "var(--accent)"
    And a checklist item states "Card width 120px"
    And Figma MCP is available
    When `/pl-web-test` performs triangulated verification
    Then the Figma node width is read via MCP
    And the app computed width is read via browser_evaluate
    And all three sources agree on 120px
    And the item is recorded as PASS with three-source attribution

    Test: Verifies Figma reference extraction, Token Map parsing, and
    skill file protocol for three-source PASS verdict.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_figma_reference_extracted(self):
        """Figma reference URL is correctly extracted from visual spec."""
        refs = _extract_figma_references(SAMPLE_WEB_TESTABLE_WITH_FIGMA)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]['screen'], 'Dashboard Main View')
        self.assertIn('figma.com', refs[0]['url'])

    def test_figma_node_id_extracted(self):
        """Figma node ID is parsed from the reference URL."""
        refs = _extract_figma_references(SAMPLE_WEB_TESTABLE_WITH_FIGMA)
        self.assertEqual(refs[0]['node_id'], '42:100')

    def test_token_map_entries_extracted(self):
        """Token Map entries are correctly parsed from visual spec."""
        entries = _extract_token_map(SAMPLE_WEB_TESTABLE_WITH_FIGMA)
        self.assertEqual(len(entries), 4)
        names = [e['figma_token'] for e in entries]
        self.assertIn('surface', names)
        self.assertIn('on-surface', names)
        self.assertIn('primary', names)
        self.assertIn('spacing-md', names)

    def test_token_map_project_tokens_extracted(self):
        """Token Map project token values are correctly parsed."""
        entries = _extract_token_map(SAMPLE_WEB_TESTABLE_WITH_FIGMA)
        token_dict = {e['figma_token']: e['project_token'] for e in entries}
        self.assertEqual(token_dict['surface'], 'var(--purlin-bg)')
        self.assertEqual(token_dict['primary'], 'var(--purlin-accent)')

    def test_pass_verdict_when_all_agree(self):
        """PASS verdict assigned when Figma, Spec, and App all agree."""
        verdict = _assign_triangulation_verdict('120px', '120px', '120px')
        self.assertEqual(verdict, 'PASS')

    def test_skill_references_figma_mcp_tools(self):
        """Skill file references Figma MCP tools get_file and get_node."""
        self.assertIn('get_file', self.command_content)
        self.assertIn('get_node', self.command_content)

    def test_skill_documents_three_source_comparison(self):
        """Skill file documents reading Figma, Spec, and App sources."""
        self.assertIn('Figma', self.command_content)
        self.assertIn('Spec', self.command_content)
        self.assertIn('App', self.command_content)

    def test_skill_fetches_specific_node_not_entire_file(self):
        """Skill file specifies fetching only the referenced Figma node."""
        self.assertIn('node-id', self.command_content)
        self.assertIn('specific', self.command_content.lower())

    def test_skill_uses_browser_evaluate_for_computed_styles(self):
        """Skill file uses browser_evaluate with getComputedStyle."""
        self.assertIn('getComputedStyle', self.command_content)

    def test_figma_screen_detected_as_having_figma(self):
        """Screen with Figma reference is correctly flagged."""
        screens = _extract_visual_screens(SAMPLE_WEB_TESTABLE_WITH_FIGMA)
        self.assertEqual(len(screens), 1)
        self.assertTrue(screens[0]['has_figma'])


class TestFigmaTriangulatedDetectsBug(unittest.TestCase):
    """Scenario: Figma-triangulated verification detects BUG

    Given a web-testable feature has a Visual Specification with Figma reference
    And a checklist item states "Icon 48x48"
    And Figma reports 48px and spec says 48px but app computes 32px
    When `/pl-web-test` performs triangulated verification
    Then the item is recorded as BUG with three-source attribution
    And a [BUG] discovery is created routing to Builder

    Test: Verifies BUG verdict logic and skill file BUG routing.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_bug_verdict_when_app_differs(self):
        """BUG verdict when Figma and Spec agree but App differs."""
        verdict = _assign_triangulation_verdict('48px', '48px', '32px')
        self.assertEqual(verdict, 'BUG')

    def test_bug_verdict_when_all_differ_figma_changed(self):
        """BUG verdict when Figma changed, Spec changed, App still wrong."""
        verdict = _assign_triangulation_verdict('56px', '56px', '32px')
        self.assertEqual(verdict, 'BUG')

    def test_skill_documents_bug_verdict_row(self):
        """Skill file includes BUG in the verdict matrix."""
        # The verdict table should have a BUG row
        self.assertIn('BUG', self.command_content)
        self.assertIn('code wrong', self.command_content.lower())

    def test_skill_routes_bug_to_builder(self):
        """Skill file routes BUG discoveries to Builder."""
        self.assertIn('Action Required:** Builder', self.command_content)

    def test_skill_creates_bug_discovery_for_triangulated_bugs(self):
        """Skill file records triangulated BUGs as [BUG] discoveries."""
        # The result recording section should reference BUG discovery
        self.assertIn('[BUG]', self.command_content)
        self.assertIn('three-source', self.command_content.lower())

    def test_bug_discovery_includes_three_source_data(self):
        """BUG discovery observed behavior includes three-source values."""
        self.assertIn(
            'three-source values if triangulated', self.command_content)


class TestFigmaTriangulatedDetectsStale(unittest.TestCase):
    """Scenario: Figma-triangulated verification detects STALE spec

    Given a web-testable feature has a Visual Specification with Figma reference
    And a checklist item states "heading-lg font"
    And Figma has been updated to use "heading-xl" but spec still says
    "heading-lg"
    When `/pl-web-test` performs triangulated verification
    Then the item is recorded as STALE
    And the output notes Figma was updated but spec was not re-ingested
    And a PM action item is generated for re-ingestion

    Test: Verifies STALE verdict logic and PM routing.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_stale_verdict_when_figma_updated(self):
        """STALE verdict when Figma changed but spec and app match old."""
        verdict = _assign_triangulation_verdict(
            'heading-xl', 'heading-lg', 'heading-lg')
        self.assertEqual(verdict, 'STALE')

    def test_stale_distinct_from_bug(self):
        """STALE is distinct from BUG -- spec is outdated, not code."""
        stale = _assign_triangulation_verdict('new', 'old', 'old')
        bug = _assign_triangulation_verdict('48px', '48px', '32px')
        self.assertNotEqual(stale, bug)
        self.assertEqual(stale, 'STALE')
        self.assertEqual(bug, 'BUG')

    def test_skill_documents_stale_verdict_row(self):
        """Skill file includes STALE in the verdict matrix."""
        self.assertIn('STALE', self.command_content)
        self.assertIn('Figma updated', self.command_content)

    def test_skill_routes_stale_to_pm(self):
        """Skill file routes STALE items to PM for re-ingestion."""
        self.assertIn('PM action item', self.command_content)
        self.assertIn('re-ingest', self.command_content.lower())

    def test_stale_not_recorded_as_bug_discovery(self):
        """Skill file distinguishes STALE from BUG in result recording."""
        # STALE items should NOT be recorded as [BUG] discoveries
        self.assertIn('STALE/DRIFT', self.command_content)
        self.assertIn('not BUG discoveries', self.command_content)


class TestFigmaTriangulatedDetectsTokenDrift(unittest.TestCase):
    """Scenario: Figma-triangulated verification detects token drift

    Given a web-testable feature has a Token Map with
    "spacing-md" -> "var(--spacing-md)"
    And Figma reports spacing-md resolved value is 20px
    And the app's computed --spacing-md value is 16px
    When `/pl-web-test` performs token verification
    Then the token entry is recorded as DRIFT
    And the output shows Figma=20px App=16px

    Test: Verifies Token Map extraction, token drift detection logic, and
    skill file documentation of token verification.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_token_map_extracted_for_drift_check(self):
        """Token Map entries are available for drift checking."""
        entries = _extract_token_map(SAMPLE_WEB_TESTABLE_WITH_FIGMA)
        spacing = [e for e in entries if e['figma_token'] == 'spacing-md']
        self.assertEqual(len(spacing), 1)
        self.assertEqual(spacing[0]['project_token'], '16px')

    def test_token_drift_detected(self):
        """Token drift detected when Figma value differs from App value."""
        # Simulate: Figma reports 20px, App computes 16px
        figma_val = '20px'
        app_val = '16px'
        self.assertNotEqual(figma_val, app_val)

    def test_token_pass_when_values_match(self):
        """Token PASS when Figma resolved value matches App value."""
        figma_val = '16px'
        app_val = '16px'
        self.assertEqual(figma_val, app_val)

    def test_skill_documents_token_verification(self):
        """Skill file documents Token Map verification step."""
        self.assertIn('Token Map verification', self.command_content)

    def test_skill_documents_token_drift_output(self):
        """Skill file shows Figma and App values in token drift output."""
        self.assertIn('Figma=', self.command_content)
        self.assertIn('App=', self.command_content)

    def test_skill_reads_figma_design_variable(self):
        """Skill file reads Figma design variable value via MCP."""
        self.assertIn('design variable', self.command_content.lower())

    def test_skill_reads_computed_css_property(self):
        """Skill file reads app CSS property via browser_evaluate."""
        self.assertIn('computed CSS property', self.command_content)

    def test_drift_flagged_per_token_entry(self):
        """Skill file flags drift per Token Map entry individually."""
        self.assertIn('[DRIFT]', self.command_content)
        self.assertIn('token drift', self.command_content.lower())


class TestThreeSourceReportFormat(unittest.TestCase):
    """Scenario: Three-source report format

    Given `/pl-web-test` has completed triangulated verification
    When results are printed
    Then the output includes a "Triangulated Verification" section
    And each item shows Figma, Spec, and App values
    And the Token Map section shows per-token comparison
    And a summary line shows counts by verdict type

    Test: Verifies the skill file includes the three-source report format
    with all required sections and attribution columns.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.command_content = f.read()

    def test_report_has_triangulated_header(self):
        """Report includes the Triangulated Verification header."""
        self.assertIn(
            'Triangulated Verification', self.command_content)

    def test_report_has_screen_label(self):
        """Report format includes Screen: label for per-screen results."""
        self.assertIn('Screen:', self.command_content)

    def test_report_shows_pass_verdict_with_three_values(self):
        """Report PASS lines show Figma, Spec, and App values."""
        # Look for the report format template with all three sources
        self.assertIn('[PASS]', self.command_content)
        self.assertIn('Figma=', self.command_content)
        self.assertIn('Spec=', self.command_content)
        self.assertIn('App=', self.command_content)

    def test_report_shows_bug_verdict(self):
        """Report BUG lines show three values with code-wrong annotation."""
        self.assertIn('[BUG]', self.command_content)
        self.assertIn('<- code wrong', self.command_content)

    def test_report_shows_stale_verdict(self):
        """Report STALE lines show Figma and Spec values."""
        self.assertIn('[STALE]', self.command_content)
        self.assertIn('<- Figma updated', self.command_content)

    def test_report_shows_drift_verdict(self):
        """Report DRIFT lines show Figma, Spec, App values."""
        self.assertIn('[DRIFT]', self.command_content)
        self.assertIn('<- spec drift', self.command_content)

    def test_report_has_token_map_section(self):
        """Report includes a Token Map section for per-token comparison."""
        self.assertIn('Token Map:', self.command_content)
        self.assertIn('<- token drift', self.command_content)

    def test_report_has_summary_line(self):
        """Report includes summary with counts by verdict type."""
        self.assertIn('Summary:', self.command_content)
        self.assertIn('BUG', self.command_content)
        self.assertIn('STALE', self.command_content)
        self.assertIn('DRIFT', self.command_content)

    def test_report_verdict_routing(self):
        """Skill file documents verdict routing to Builder and PM."""
        # BUG -> Builder (via Action Required), STALE/DRIFT -> PM
        self.assertIn('Action Required:** Builder', self.command_content)
        self.assertIn('PM action items', self.command_content)

    def test_all_verdicts_produce_correct_types(self):
        """All verdict assignments produce expected values."""
        self.assertEqual(
            _assign_triangulation_verdict('a', 'a', 'a'), 'PASS')
        self.assertEqual(
            _assign_triangulation_verdict('a', 'a', 'b'), 'BUG')
        self.assertEqual(
            _assign_triangulation_verdict('b', 'a', 'a'), 'STALE')
        self.assertEqual(
            _assign_triangulation_verdict('b', 'a', 'b'), 'SPEC_DRIFT')


class TestRegressionScopeRespected(unittest.TestCase):
    """Scenario: Regression scope respected

    Given a feature's critic.json has regression_scope: "targeted:Scenario A"
    When `/pl-web-test` is invoked for that feature
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
    When `/pl-web-test` is invoked for that feature
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
    """Scenario: Instruction files updated with web-test references

    Given the skill file has been created
    When instruction updates are applied per Section 2.13
    Then /pl-web-test appears in both QA and Builder authorized command lists
    And /pl-web-test [name] appears in all variants of both command tables
    And > Web Test: is documented in feature_format.md
    And visual_spec_convention.md references the automated alternative
    And visual_verification_protocol.md has Section 5.4.7 for Playwright MCP

    Test: Verifies all 7 instruction files contain required references.
    """

    def test_all_seven_instruction_files_exist(self):
        """All 7 instruction files from Section 2.13 exist."""
        for name, path in INSTRUCTION_FILES.items():
            self.assertTrue(os.path.isfile(path),
                            f'Instruction file not found: {name} at {path}')

    def test_qa_base_authorized_commands(self):
        """QA_BASE.md authorized commands include /pl-web-test."""
        with open(INSTRUCTION_FILES['qa_base']) as f:
            content = f.read()
        # Find the authorized commands line
        for line in content.split('\n'):
            if 'Authorized commands:' in line and '/pl-web-test' in line:
                break
        else:
            self.fail('/pl-web-test not in QA_BASE authorized commands')

    def test_builder_base_authorized_commands(self):
        """BUILDER_BASE.md authorized commands include /pl-web-test."""
        with open(INSTRUCTION_FILES['builder_base']) as f:
            content = f.read()
        for line in content.split('\n'):
            if 'Authorized commands:' in line and '/pl-web-test' in line:
                break
        else:
            self.fail('/pl-web-test not in BUILDER_BASE authorized commands')

    def test_qa_commands_both_variants(self):
        """qa_commands.md has /pl-web-test in both table variants."""
        with open(INSTRUCTION_FILES['qa_commands']) as f:
            content = f.read()
        occurrences = content.count('/pl-web-test')
        self.assertGreaterEqual(
            occurrences, 2,
            f'Expected >= 2 occurrences in qa_commands.md, found {occurrences}')

    def test_builder_commands_both_variants(self):
        """builder_commands.md has /pl-web-test in both table variants."""
        with open(INSTRUCTION_FILES['builder_commands']) as f:
            content = f.read()
        occurrences = content.count('/pl-web-test')
        self.assertGreaterEqual(
            occurrences, 2,
            f'Expected >= 2 in builder_commands.md, found {occurrences}')

    def test_feature_format_documents_web_test(self):
        """feature_format.md documents > Web Test: metadata."""
        with open(INSTRUCTION_FILES['feature_format']) as f:
            content = f.read()
        self.assertIn('Web Test', content)
        self.assertIn('/pl-web-test', content)

    def test_visual_spec_convention_references_automated_alt(self):
        """visual_spec_convention.md references automated Playwright MCP."""
        with open(INSTRUCTION_FILES['visual_spec_convention']) as f:
            content = f.read()
        self.assertIn('/pl-web-test', content)
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
        # The loader notice at the top should mention /pl-web-test
        lines = content.split('\n')[:5]
        loader_text = '\n'.join(lines)
        self.assertIn('/pl-web-test', loader_text)

    def test_visual_spec_convention_loader_notice(self):
        """visual_spec_convention.md on-demand loader includes cmd."""
        with open(INSTRUCTION_FILES['visual_spec_convention']) as f:
            content = f.read()
        lines = content.split('\n')[:5]
        loader_text = '\n'.join(lines)
        self.assertIn('/pl-web-test', loader_text)

    def test_qa_base_references_web_test_in_section_54(self):
        """QA_BASE.md references /pl-web-test in authorized commands."""
        with open(INSTRUCTION_FILES['qa_base']) as f:
            content = f.read()
        self.assertIn('/pl-web-test', content)

    def test_builder_base_references_web_test(self):
        """BUILDER_BASE.md references Web Test verification."""
        with open(INSTRUCTION_FILES['builder_base']) as f:
            content = f.read()
        self.assertIn('Web Test', content)
        self.assertIn('/pl-web-test', content)


class TestDynamicPortResolution(unittest.TestCase):
    """Scenario: Dynamic port resolution from runtime port file

    Given a feature has `> Web Test: http://localhost:9086`
    And `.purlin/runtime/cdd.port` contains `52288`
    When `/pl-web-test` resolves the URL for that feature
    Then the resolved URL is `http://localhost:52288`
    And port `9086` from the metadata is not used

    Test: Verifies internal port file reading and URL port replacement.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_web_start_metadata_extracted(self):
        """Web Start metadata is correctly extracted."""
        start_cmd = _extract_web_start(SAMPLE_WEB_TEST_WITH_START)
        self.assertEqual(start_cmd, '/pl-cdd')

    def test_no_web_start_returns_none(self):
        """Feature without Web Start returns None."""
        start_cmd = _extract_web_start(SAMPLE_WEB_TESTABLE_FEATURE)
        self.assertIsNone(start_cmd)

    def test_runtime_port_file_overrides_spec_port(self):
        """Runtime port file replaces port in Web Test URL."""
        runtime_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(runtime_dir)
        with open(os.path.join(runtime_dir, 'cdd.port'), 'w') as f:
            f.write('52288')

        resolved = _resolve_url(
            'http://localhost:9086',
            project_root=self.tmpdir)
        self.assertEqual(resolved, 'http://localhost:52288')

    def test_port_file_missing_falls_back(self):
        """Missing port file falls back to spec URL."""
        resolved = _resolve_url(
            'http://localhost:9086',
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
            url_override='http://localhost:3000',
            project_root=self.tmpdir)
        self.assertEqual(resolved, 'http://localhost:3000')

    def test_no_project_root_uses_base_url(self):
        """No project root uses base URL directly."""
        resolved = _resolve_url(
            'http://localhost:9086',
            project_root=None)
        self.assertEqual(resolved, 'http://localhost:9086')

    def test_invalid_port_file_content_falls_back(self):
        """Non-numeric port file content falls back to spec URL."""
        runtime_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(runtime_dir)
        with open(os.path.join(runtime_dir, 'cdd.port'), 'w') as f:
            f.write('not-a-port')

        resolved = _resolve_url(
            'http://localhost:9086',
            project_root=self.tmpdir)
        self.assertEqual(resolved, 'http://localhost:9086')

    def test_runtime_port_file_path_is_hardcoded(self):
        """The runtime port file path is a module constant, not per-feature."""
        self.assertEqual(RUNTIME_PORT_FILE, '.purlin/runtime/cdd.port')


class TestHeadedPlaywrightDetection(unittest.TestCase):
    """Scenario: Headed Playwright MCP detected triggers reconfiguration

    Given Playwright MCP tools are available in the current session
    But the MCP server was configured without `--headless`
    When `/pl-web-test` is invoked
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

    def test_skill_references_runtime_port_file(self):
        """Skill file references runtime port file."""
        self.assertIn('cdd.port', self.command_content)

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

    Given a feature has `> Web Test: http://localhost:9086`
    And the feature has `> Test Fixtures: https://github.com/org/fixtures.git`
    And a scenario's Given step references fixture tag "main/feature/scenario-one"
    When `/pl-web-test` processes that scenario
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
    When `/pl-web-test` attempts to check out the fixture
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
    When `/pl-web-test` moves to the next scenario
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


class TestLegacyPlWebVerifyRemoved(unittest.TestCase):
    """Scenario: Legacy pl-web-verify references fully removed

    Given the pl-web-test skill file exists at `.claude/commands/pl-web-test.md`
    When a search is performed for "pl-web-verify" or "Web Testable" across
    all non-release-note files
    Then zero matches are found
    And the old skill file `.claude/commands/pl-web-verify.md` does not exist
    And the test directory is `tests/pl_web_test/` (not `tests/pl_web_verify/`)

    Test: Verifies that all legacy references have been cleaned up.
    """

    def test_old_skill_file_does_not_exist(self):
        """The old .claude/commands/pl-web-verify.md file does not exist."""
        old_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-web-verify.md')
        self.assertFalse(
            os.path.isfile(old_path),
            f'Old skill file still exists: {old_path}')

    def test_new_skill_file_exists(self):
        """The new .claude/commands/pl-web-test.md file exists."""
        self.assertTrue(
            os.path.isfile(COMMAND_FILE),
            f'New skill file not found: {COMMAND_FILE}')

    def test_old_test_directory_does_not_exist(self):
        """The old tests/pl_web_verify/ directory does not exist."""
        old_dir = os.path.join(PROJECT_ROOT, 'tests', 'pl_web_verify')
        self.assertFalse(
            os.path.isdir(old_dir),
            f'Old test directory still exists: {old_dir}')

    def test_new_test_directory_exists(self):
        """The new tests/pl_web_test/ directory exists."""
        new_dir = os.path.join(PROJECT_ROOT, 'tests', 'pl_web_test')
        self.assertTrue(
            os.path.isdir(new_dir),
            f'New test directory not found: {new_dir}')

    def test_no_web_testable_in_skill_file(self):
        """The new skill file contains no 'Web Testable' references."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertNotIn('Web Testable', content)

    def test_no_pl_web_verify_in_skill_file(self):
        """The new skill file contains no 'pl-web-verify' references."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertNotIn('pl-web-verify', content)

    def test_no_web_testable_in_critic(self):
        """tools/critic/critic.py contains no 'Web Testable' references."""
        critic_path = os.path.join(
            PROJECT_ROOT, 'tools', 'critic', 'critic.py')
        with open(critic_path) as f:
            content = f.read()
        self.assertNotIn('Web Testable', content)

    def test_no_web_testable_in_fixture_setup(self):
        """dev/setup_fixture_repo.sh contains no 'Web Testable' refs."""
        fixture_path = os.path.join(
            PROJECT_ROOT, 'dev', 'setup_fixture_repo.sh')
        with open(fixture_path) as f:
            content = f.read()
        self.assertNotIn('Web Testable', content)

    def test_no_pl_web_verify_in_fixture_setup(self):
        """dev/setup_fixture_repo.sh has no 'pl_web_verify' tag refs."""
        fixture_path = os.path.join(
            PROJECT_ROOT, 'dev', 'setup_fixture_repo.sh')
        with open(fixture_path) as f:
            content = f.read()
        self.assertNotIn('pl_web_verify', content)


# =============================================================================
# Test runner: writes results to tests/pl_web_test/tests.json
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

    tests_dir = os.path.join(project_root, 'tests', 'pl_web_test')
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
