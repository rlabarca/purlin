"""Automated tests for CDD Release Checklist UI (release_checklist_ui.md).

Tests all automated scenarios from features/release_checklist_ui.md.
Results written to tests/release_checklist_ui/tests.json.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import serve


def _make_steps(overrides=None):
    """Build a default list of resolved release steps for testing."""
    base = [
        {"id": "purlin.record_version_notes", "friendly_name": "Record Version & Release Notes",
         "description": "Gathers suggested release notes.", "code": None,
         "agent_instructions": "1. Determine the last release tag.",
         "source": "global", "enabled": True, "order": 1},
        {"id": "purlin.verify_zero_queue", "friendly_name": "Verify Zero-Queue Status",
         "description": "Verifies all features are satisfied.", "code": None,
         "agent_instructions": "Run tools/cdd/status.sh.",
         "source": "global", "enabled": True, "order": 2},
        {"id": "purlin.push_to_remote", "friendly_name": "Push to Remote Repository",
         "description": "Pushes the release commits and tags.",
         "code": "git push && git push --tags",
         "agent_instructions": "Confirm branch and remote config.",
         "source": "global", "enabled": True, "order": 3},
    ]
    if overrides:
        for i, step in enumerate(base):
            if step["id"] in overrides:
                base[i].update(overrides[step["id"]])
    return base


def _make_steps_with_disabled():
    """Steps where push_to_remote is disabled."""
    steps = _make_steps()
    steps[2]["enabled"] = False
    steps[2]["order"] = None
    # Renumber enabled steps contiguously
    idx = 1
    for s in steps:
        if s["enabled"]:
            s["order"] = idx
            idx += 1
    return steps


def _make_steps_with_local():
    """Steps including a local step."""
    steps = _make_steps()
    steps.append({
        "id": "myproject.deploy", "friendly_name": "Deploy to Staging",
        "description": "Deploy artifacts to staging.", "code": "make deploy",
        "agent_instructions": None,
        "source": "local", "enabled": True, "order": 4,
    })
    return steps


def _generate_html_with_steps(steps):
    """Generate dashboard HTML with mocked release checklist steps."""
    with patch('serve.get_release_checklist', return_value=(steps, [], [])), \
         patch('serve.get_feature_status', return_value=([], [], [])), \
         patch('serve.run_command', return_value=""):
        return serve.generate_html()


class TestCollapsedBadgeShowsEnabledAndDisabledCounts(unittest.TestCase):
    """Scenario: Collapsed Badge Shows Enabled and Disabled Counts

    Given the release checklist has 7 enabled steps and 2 disabled steps
    When the dashboard HTML is generated
    Then the RELEASE CHECKLIST collapsed badge contains "7 enabled"
    And the badge contains "2 disabled"
    And the enabled count element uses the --purlin-status-good color class
    And the disabled count element uses the --purlin-dim color class
    """

    def test_badge_counts_all_enabled(self):
        steps = _make_steps()
        html = _generate_html_with_steps(steps)
        self.assertIn('3 enabled', html)
        self.assertIn('0 disabled', html)

    def test_badge_counts_with_disabled(self):
        steps = _make_steps_with_disabled()
        html = _generate_html_with_steps(steps)
        self.assertIn('2 enabled', html)
        self.assertIn('1 disabled', html)

    def test_enabled_count_uses_status_good_color(self):
        steps = _make_steps()
        html = _generate_html_with_steps(steps)
        # Badge format: <span style="color:var(--purlin-status-good)">N enabled</span>
        self.assertIn('color:var(--purlin-status-good)">3 enabled</span>', html)

    def test_disabled_count_uses_dim_color(self):
        steps = _make_steps_with_disabled()
        html = _generate_html_with_steps(steps)
        self.assertIn('color:var(--purlin-dim)">&middot; 1 disabled</span>', html)


class TestPostReleaseChecklistConfigPersistsNewStepOrder(unittest.TestCase):
    """Scenario: POST /release-checklist/config Persists New Step Order

    Given the release checklist config has steps in order [A, B, C]
    When a POST request is sent to /release-checklist/config with reordered steps
    Then .purlin/release/config.json lists steps in the new order
    And the response contains {"ok": true}
    """

    def _make_handler(self, body_dict, config_path):
        from serve import Handler
        handler = Handler.__new__(Handler)
        body = json.dumps(body_dict).encode('utf-8')
        handler.path = '/release-checklist/config'
        handler.requestline = 'POST /release-checklist/config HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'POST'
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        return handler

    def test_reorder_persists_to_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            # Initial config: A, B, C
            initial = {"steps": [
                {"id": "A", "enabled": True},
                {"id": "B", "enabled": True},
                {"id": "C", "enabled": True},
            ]}
            with open(config_path, 'w') as f:
                json.dump(initial, f)

            # POST reordered: C, A, B
            handler = self._make_handler({
                "steps": [
                    {"id": "C", "enabled": True},
                    {"id": "A", "enabled": True},
                    {"id": "B", "enabled": True},
                ]
            }, config_path)

            with patch('serve.RELEASE_CONFIG_PATH', config_path):
                handler.do_POST()

            handler.send_response.assert_called_with(200)
            body = handler.wfile.getvalue()
            data = json.loads(body)
            self.assertTrue(data["ok"])

            # Verify file on disk
            with open(config_path) as f:
                saved = json.load(f)
            self.assertEqual(saved["steps"][0]["id"], "C")
            self.assertEqual(saved["steps"][1]["id"], "A")
            self.assertEqual(saved["steps"][2]["id"], "B")

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            with open(config_path, 'w') as f:
                json.dump({"steps": []}, f)

            handler = self._make_handler({
                "steps": [
                    {"id": "A", "enabled": True},
                    {"id": "A", "enabled": False},
                ]
            }, config_path)

            with patch('serve.RELEASE_CONFIG_PATH', config_path):
                handler.do_POST()

            handler.send_response.assert_called_with(400)
            body = handler.wfile.getvalue()
            data = json.loads(body)
            self.assertIn("Duplicate", data["error"])


class TestDisabledStepShowsEmDashAndAffectsBadgeCount(unittest.TestCase):
    """Scenario: Disabled Step Shows Em Dash and Affects Badge Count

    Given the release checklist config has step "purlin.push_to_remote" set to enabled false
    When the dashboard HTML is generated
    Then the row for "purlin.push_to_remote" displays an em dash in the step number column
    And the row for "purlin.push_to_remote" has dimmed styling
    And the collapsed badge disabled count reflects the disabled step
    And enabled steps have contiguous 1-based step numbers
    """

    def test_disabled_step_shows_em_dash(self):
        steps = _make_steps_with_disabled()
        html = _generate_html_with_steps(steps)
        # Find the push_to_remote row - it should contain &mdash;
        import re
        row_match = re.search(
            r'<tr[^>]*data-step-id="purlin\.push_to_remote"[^>]*>.*?</tr>',
            html, re.DOTALL)
        self.assertIsNotNone(row_match, "push_to_remote row not found")
        row_html = row_match.group()
        self.assertIn('&mdash;', row_html)

    def test_disabled_step_has_dim_color(self):
        steps = _make_steps_with_disabled()
        html = _generate_html_with_steps(steps)
        import re
        row_match = re.search(
            r'<tr[^>]*data-step-id="purlin\.push_to_remote"[^>]*>.*?</tr>',
            html, re.DOTALL)
        self.assertIsNotNone(row_match)
        row_html = row_match.group()
        # Number cell should use --purlin-dim for disabled
        self.assertIn('color:var(--purlin-dim)', row_html)

    def test_disabled_step_has_rc_disabled_class(self):
        steps = _make_steps_with_disabled()
        html = _generate_html_with_steps(steps)
        import re
        row_match = re.search(
            r'<tr[^>]*data-step-id="purlin\.push_to_remote"[^>]*>',
            html)
        self.assertIsNotNone(row_match)
        self.assertIn('rc-disabled', row_match.group())

    def test_enabled_steps_contiguous_numbering(self):
        steps = _make_steps_with_disabled()
        html = _generate_html_with_steps(steps)
        import re
        # First enabled step: order 1
        row1 = re.search(
            r'<tr[^>]*data-step-id="purlin\.record_version_notes"[^>]*>.*?</tr>',
            html, re.DOTALL)
        self.assertIsNotNone(row1)
        self.assertIn('>1</td>', row1.group())
        # Second enabled step: order 2
        row2 = re.search(
            r'<tr[^>]*data-step-id="purlin\.verify_zero_queue"[^>]*>.*?</tr>',
            html, re.DOTALL)
        self.assertIsNotNone(row2)
        self.assertIn('>2</td>', row2.group())

    def test_badge_reflects_disabled_count(self):
        steps = _make_steps_with_disabled()
        html = _generate_html_with_steps(steps)
        self.assertIn('1 disabled', html)


class TestStepDetailModalContainsAllPopulatedSections(unittest.TestCase):
    """Scenario: Step Detail Modal Contains All Populated Sections

    Given the release checklist contains a step with description, code,
    and agent_instructions all populated
    When the dashboard HTML is generated for the step detail modal of that step
    Then the modal contains a DESCRIPTION section with the step's description text
    And the modal contains a CODE section with a monospace code block
    And the modal contains an AGENT INSTRUCTIONS section
    """

    def test_modal_js_renders_description_section(self):
        html = _generate_html_with_steps(_make_steps())
        # openStepModal JS checks step.description
        self.assertIn('step.description', html)
        self.assertIn('DESCRIPTION', html)

    def test_modal_js_renders_code_section(self):
        html = _generate_html_with_steps(_make_steps())
        # openStepModal JS checks step.code !== null
        self.assertIn('step.code !== null', html)
        self.assertIn('CODE</div>', html)

    def test_modal_js_renders_agent_instructions_section(self):
        html = _generate_html_with_steps(_make_steps())
        self.assertIn('step.agent_instructions !== null', html)
        self.assertIn('AGENT INSTRUCTIONS</div>', html)

    def test_modal_code_uses_pre_with_surface_bg(self):
        html = _generate_html_with_steps(_make_steps())
        self.assertIn('<pre style="background:var(--purlin-surface)', html)


class TestStepDetailModalOmitsCodeSectionWhenCodeIsNull(unittest.TestCase):
    """Scenario: Step Detail Modal Omits CODE Section When Code Is Null

    Given the release checklist contains a step where code is null
    and description and agent_instructions are populated
    When the dashboard HTML is generated for the step detail modal of that step
    Then the modal contains a DESCRIPTION section
    And the modal contains an AGENT INSTRUCTIONS section
    And the modal does not contain a CODE section
    """

    def test_modal_js_guards_code_with_null_check(self):
        html = _generate_html_with_steps(_make_steps())
        # The JS conditionally renders CODE only when non-null
        self.assertIn('step.code !== null && step.code !== undefined', html)

    def test_modal_js_guards_agent_instructions_with_null_check(self):
        html = _generate_html_with_steps(_make_steps())
        self.assertIn('step.agent_instructions !== null && step.agent_instructions !== undefined', html)

    def test_step_with_null_code_no_checkbox_in_row(self):
        """Steps with code=null still render correctly in the row."""
        steps = [
            {"id": "s1", "friendly_name": "Step One",
             "description": "Desc", "code": None,
             "agent_instructions": "Do stuff.",
             "source": "global", "enabled": True, "order": 1},
        ]
        html = _generate_html_with_steps(steps)
        import re
        row = re.search(r'<tr[^>]*data-step-id="s1"[^>]*>.*?</tr>', html, re.DOTALL)
        self.assertIsNotNone(row)
        self.assertIn('Step One', row.group())


class TestLocalStepDisplaysLocalBadgeInRowAndModal(unittest.TestCase):
    """Scenario: Local Step Displays LOCAL Badge in Row and Modal

    Given the release checklist contains a step with source "local"
    When the dashboard HTML is generated
    Then that step's row contains a "LOCAL" badge element
    And the step detail modal header for that step contains a "LOCAL" source badge
    """

    def test_local_step_row_has_local_badge(self):
        steps = _make_steps_with_local()
        html = _generate_html_with_steps(steps)
        import re
        row = re.search(
            r'<tr[^>]*data-step-id="myproject\.deploy"[^>]*>.*?</tr>',
            html, re.DOTALL)
        self.assertIsNotNone(row, "local step row not found")
        self.assertIn('LOCAL</span>', row.group())

    def test_global_step_row_has_global_badge(self):
        steps = _make_steps_with_local()
        html = _generate_html_with_steps(steps)
        import re
        row = re.search(
            r'<tr[^>]*data-step-id="purlin\.record_version_notes"[^>]*>.*?</tr>',
            html, re.DOTALL)
        self.assertIsNotNone(row)
        self.assertIn('GLOBAL</span>', row.group())

    def test_modal_js_renders_source_badge(self):
        html = _generate_html_with_steps(_make_steps_with_local())
        # openStepModal JS builds source badge from step.source
        self.assertIn("(step.source || '').toUpperCase()", html)
        self.assertIn('--purlin-tag-fill', html)

    def test_local_badge_styling(self):
        steps = _make_steps_with_local()
        html = _generate_html_with_steps(steps)
        import re
        row = re.search(
            r'<tr[^>]*data-step-id="myproject\.deploy"[^>]*>.*?</tr>',
            html, re.DOTALL)
        self.assertIsNotNone(row)
        row_html = row.group()
        self.assertIn('--purlin-tag-fill', row_html)
        self.assertIn('--purlin-tag-outline', row_html)
        self.assertIn('text-transform:uppercase', row_html)


# =============================================================================
# Test runner: writes results to tests/release_checklist_ui/tests.json
# =============================================================================
if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../..'))
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        project_root = env_root

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    tests_dir = os.path.join(project_root, 'tests', 'release_checklist_ui')
    os.makedirs(tests_dir, exist_ok=True)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    status = 'PASS' if failed == 0 else 'FAIL'
    with open(os.path.join(tests_dir, 'tests.json'), 'w') as f:
        json.dump({
            'status': status,
            'passed': passed,
            'failed': failed,
            'total': result.testsRun
        }, f)
    print(f"\ntests.json: {status}")
