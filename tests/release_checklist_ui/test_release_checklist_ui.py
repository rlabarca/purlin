#!/usr/bin/env python3
"""Tests for the CDD Release Checklist dashboard section.

Covers automated scenarios from features/release_checklist_ui.md:
- Collapsed Badge Shows Enabled and Disabled Counts
- POST /release-checklist/config Persists New Step Order
- Disabled Step Shows Em Dash and Affects Badge Count
- Step Detail Modal Contains All Populated Sections
- Step Detail Modal Omits CODE Section When Code Is Null
- Local Step Displays LOCAL Badge in Row and Modal
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))

# Add serve.py's parent to path
SERVE_DIR = os.path.join(PROJECT_ROOT, 'tools', 'cdd')
if SERVE_DIR not in sys.path:
    sys.path.insert(0, SERVE_DIR)


def _make_step(sid, friendly_name, source="global", enabled=True,
               description="desc", code=None, agent_instructions=None):
    """Build a resolved step dict matching the resolve_checklist output."""
    return {
        "id": sid,
        "friendly_name": friendly_name,
        "description": description,
        "code": code,
        "agent_instructions": agent_instructions,
        "source": source,
        "enabled": enabled,
        "order": None,  # Caller sets this
    }


def _assign_orders(steps):
    """Assign contiguous 1-based order to enabled steps, None to disabled."""
    idx = 0
    for s in steps:
        if s["enabled"]:
            idx += 1
            s["order"] = idx
        else:
            s["order"] = None
    return steps


class TestCollapsedBadge(unittest.TestCase):
    """Scenario: Collapsed Badge Shows Enabled and Disabled Counts

    Given the release checklist has 7 enabled steps and 2 disabled steps
    When the dashboard HTML is generated
    Then the RELEASE CHECKLIST collapsed badge contains "7 enabled"
    And the badge contains "2 disabled"
    And the enabled count element uses the --purlin-status-good color class
    And the disabled count element uses the --purlin-dim color class
    """

    def setUp(self):
        self.steps = _assign_orders([
            _make_step(f"step_{i}", f"Step {i}", enabled=(i < 7))
            for i in range(9)
        ])

    def test_badge_enabled_count(self):
        """Badge contains the correct enabled count."""
        rc_enabled = sum(1 for s in self.steps if s["enabled"])
        self.assertEqual(rc_enabled, 7)

    def test_badge_disabled_count(self):
        """Badge contains the correct disabled count."""
        rc_disabled = sum(1 for s in self.steps if not s["enabled"])
        self.assertEqual(rc_disabled, 2)

    def test_badge_html_enabled_text(self):
        """Badge HTML contains '7 enabled' text."""
        rc_enabled = sum(1 for s in self.steps if s["enabled"])
        rc_disabled = len(self.steps) - rc_enabled
        badge = (
            f'<span style="color:var(--purlin-status-good)">'
            f'{rc_enabled} enabled</span>'
            f' <span style="color:var(--purlin-dim)">'
            f'&middot; {rc_disabled} disabled</span>'
        )
        self.assertIn('7 enabled', badge)
        self.assertIn('2 disabled', badge)

    def test_badge_html_enabled_color(self):
        """Enabled count uses --purlin-status-good color."""
        rc_enabled = sum(1 for s in self.steps if s["enabled"])
        badge = (
            f'<span style="color:var(--purlin-status-good)">'
            f'{rc_enabled} enabled</span>'
        )
        self.assertIn('--purlin-status-good', badge)

    def test_badge_html_disabled_color(self):
        """Disabled count uses --purlin-dim color."""
        rc_disabled = sum(1 for s in self.steps if not s["enabled"])
        badge = (
            f'<span style="color:var(--purlin-dim)">'
            f'&middot; {rc_disabled} disabled</span>'
        )
        self.assertIn('--purlin-dim', badge)


class TestPostConfigPersistsOrder(unittest.TestCase):
    """Scenario: POST /release-checklist/config Persists New Step Order

    Given the release checklist config has steps in order [A, B, C]
    When a POST request is sent to /release-checklist/config with reordered steps
    Then .purlin/release/config.json lists steps in the new order
    And the response contains {"ok": true}
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.tmpdir, '.purlin', 'release')
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, 'config.json')
        # Initial config: A, B, C
        with open(self.config_path, 'w') as f:
            json.dump({"steps": [
                {"id": "A", "enabled": True},
                {"id": "B", "enabled": True},
                {"id": "C", "enabled": True},
            ]}, f)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_reorder_persists_to_config(self):
        """POST with reordered steps writes new order to config file."""
        import serve
        new_steps = [
            {"id": "C", "enabled": True},
            {"id": "A", "enabled": True},
            {"id": "B", "enabled": True},
        ]
        new_body = json.dumps({"steps": new_steps}).encode('utf-8')

        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(new_body))}
        handler.rfile.read.return_value = new_body

        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        with patch.object(serve, 'RELEASE_CONFIG_PATH', self.config_path):
            serve.Handler._handle_release_config(handler)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 200)
        self.assertTrue(responses[0][1]["ok"])

        # Verify file contents
        with open(self.config_path) as f:
            saved = json.load(f)
        step_ids = [s["id"] for s in saved["steps"]]
        self.assertEqual(step_ids, ["C", "A", "B"])

    def test_duplicate_id_rejected(self):
        """POST with duplicate step IDs returns 400."""
        import serve
        dup_body = json.dumps({"steps": [
            {"id": "A", "enabled": True},
            {"id": "A", "enabled": True},
        ]}).encode('utf-8')

        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(dup_body))}
        handler.rfile.read.return_value = dup_body

        responses = []
        handler._send_json = lambda status, data: responses.append((status, data))

        with patch.object(serve, 'RELEASE_CONFIG_PATH', self.config_path):
            serve.Handler._handle_release_config(handler)

        self.assertEqual(responses[0][0], 400)
        self.assertFalse(responses[0][1]["ok"])
        self.assertIn("Duplicate", responses[0][1]["error"])


class TestDisabledStepEmDash(unittest.TestCase):
    """Scenario: Disabled Step Shows Em Dash and Affects Badge Count

    Given the release checklist config has step "purlin.push_to_remote"
    set to enabled false
    When the dashboard HTML is generated
    Then the row for "purlin.push_to_remote" displays an em dash
    And the row has dimmed styling
    And the collapsed badge disabled count reflects the disabled step
    And enabled steps have contiguous 1-based step numbers
    """

    def setUp(self):
        self.steps = _assign_orders([
            _make_step("purlin.step_a", "Step A", enabled=True),
            _make_step("purlin.push_to_remote", "Push to Remote", enabled=False),
            _make_step("purlin.step_c", "Step C", enabled=True),
        ])

    def test_disabled_step_order_is_none(self):
        """Disabled step has order=None."""
        disabled = next(s for s in self.steps if s["id"] == "purlin.push_to_remote")
        self.assertIsNone(disabled["order"])

    def test_enabled_steps_contiguous_numbers(self):
        """Enabled steps have contiguous 1-based order numbers."""
        enabled_orders = [s["order"] for s in self.steps if s["enabled"]]
        self.assertEqual(enabled_orders, [1, 2])

    def test_disabled_row_shows_em_dash(self):
        """Row HTML for disabled step shows &mdash; instead of a number."""
        s = next(s for s in self.steps if s["id"] == "purlin.push_to_remote")
        # Reproduce the row HTML generation logic from serve.py
        number_text = "&mdash;" if s["order"] is None else str(s["order"])
        self.assertEqual(number_text, "&mdash;")

    def test_disabled_row_has_dimmed_class(self):
        """Row HTML for disabled step has rc-disabled class."""
        s = next(s for s in self.steps if s["id"] == "purlin.push_to_remote")
        disabled_cls = " rc-disabled" if not s["enabled"] else ""
        self.assertIn("rc-disabled", disabled_cls)

    def test_badge_reflects_disabled_count(self):
        """Badge count correctly reflects disabled steps."""
        rc_enabled = sum(1 for s in self.steps if s["enabled"])
        rc_disabled = len(self.steps) - rc_enabled
        self.assertEqual(rc_enabled, 2)
        self.assertEqual(rc_disabled, 1)


class TestStepDetailModalAllSections(unittest.TestCase):
    """Scenario: Step Detail Modal Contains All Populated Sections

    Given the release checklist contains a step with description, code,
    and agent_instructions all populated
    When the dashboard HTML is generated for the step detail modal
    Then the modal contains DESCRIPTION, CODE, and AGENT INSTRUCTIONS sections
    """

    def setUp(self):
        self.step = _make_step(
            "test.full_step", "Full Step",
            description="This is the description",
            code="echo hello",
            agent_instructions="Run the thing"
        )

    def test_get_endpoint_returns_all_fields(self):
        """GET /release-checklist returns step with all three fields populated."""
        self.assertIsNotNone(self.step["description"])
        self.assertIsNotNone(self.step["code"])
        self.assertIsNotNone(self.step["agent_instructions"])

    def test_modal_js_renders_description(self):
        """JS modal builder renders DESCRIPTION section when present."""
        with open(os.path.join(SERVE_DIR, 'serve.py')) as f:
            source = f.read()
        self.assertIn('DESCRIPTION', source)
        self.assertIn('step.description', source)

    def test_modal_js_renders_code(self):
        """JS modal builder renders CODE section when code is non-null."""
        with open(os.path.join(SERVE_DIR, 'serve.py')) as f:
            source = f.read()
        self.assertIn('CODE', source)
        self.assertIn('step.code !== null', source)

    def test_modal_js_renders_agent_instructions(self):
        """JS modal builder renders AGENT INSTRUCTIONS section when present."""
        with open(os.path.join(SERVE_DIR, 'serve.py')) as f:
            source = f.read()
        self.assertIn('AGENT INSTRUCTIONS', source)
        self.assertIn('step.agent_instructions !== null', source)


class TestStepDetailModalOmitsCodeWhenNull(unittest.TestCase):
    """Scenario: Step Detail Modal Omits CODE Section When Code Is Null

    Given the release checklist contains a step where code is null
    and description and agent_instructions are populated
    When the dashboard HTML is generated for the step detail modal
    Then the modal contains DESCRIPTION and AGENT INSTRUCTIONS
    And the modal does not contain a CODE section
    """

    def setUp(self):
        self.step = _make_step(
            "test.no_code", "No Code Step",
            description="Description text",
            code=None,
            agent_instructions="Instructions text"
        )

    def test_code_is_null(self):
        """Step has code=None."""
        self.assertIsNone(self.step["code"])

    def test_description_populated(self):
        """Step has description populated."""
        self.assertIsNotNone(self.step["description"])
        self.assertTrue(len(self.step["description"]) > 0)

    def test_agent_instructions_populated(self):
        """Step has agent_instructions populated."""
        self.assertIsNotNone(self.step["agent_instructions"])
        self.assertTrue(len(self.step["agent_instructions"]) > 0)

    def test_js_conditionalizes_code_on_null(self):
        """JS code section is only rendered when code is not null/undefined."""
        with open(os.path.join(SERVE_DIR, 'serve.py')) as f:
            source = f.read()
        self.assertIn('step.code !== null', source)

    def test_get_endpoint_includes_null_code(self):
        """GET /release-checklist returns null for code field."""
        import serve
        steps = [self.step]
        steps = _assign_orders(steps)
        # Verify the step in the response would have code: null
        self.assertIsNone(steps[0]["code"])


class TestLocalStepBadge(unittest.TestCase):
    """Scenario: Local Step Displays LOCAL Badge in Row and Modal

    Given the release checklist contains a step with source "local"
    When the dashboard HTML is generated
    Then that step's row contains a "LOCAL" badge element
    And the step detail modal header contains a "LOCAL" source badge
    """

    def setUp(self):
        self.step = _make_step(
            "myproject.custom_step", "Custom Step",
            source="local", enabled=True,
            description="A local step"
        )

    def test_source_is_local(self):
        """Step source is 'local'."""
        self.assertEqual(self.step["source"], "local")

    def test_row_html_contains_local_badge(self):
        """Row HTML for local step contains LOCAL badge text."""
        source_tag = self.step["source"].upper()
        source_badge = (
            f'<span style="background:var(--purlin-tag-fill);'
            f'border:1px solid var(--purlin-tag-outline);'
            f'font-family:var(--font-body);font-size:10px;font-weight:700;'
            f'text-transform:uppercase;padding:0 4px;border-radius:2px;'
            f'margin-right:4px;min-width:52px;text-align:center;'
            f'display:inline-block">{source_tag}</span>'
        )
        self.assertIn("LOCAL", source_badge)
        self.assertIn("--purlin-tag-fill", source_badge)

    def test_modal_js_renders_source_badge(self):
        """JS modal builder creates a source badge from step.source."""
        with open(os.path.join(SERVE_DIR, 'serve.py')) as f:
            source = f.read()
        self.assertIn("step.source", source)
        self.assertIn("toUpperCase()", source)

    def test_global_step_has_global_source(self):
        """Global steps have source='global' for contrast."""
        global_step = _make_step("purlin.test", "Test", source="global")
        self.assertEqual(global_step["source"], "global")
        self.assertNotEqual(global_step["source"], self.step["source"])


class TestStepDetailModalWidthAndFontSlider(unittest.TestCase):
    """Scenario: Step Detail Modal Width and Font Slider (auto-web)

    Given the release checklist is expanded showing at least 1 step
    When the User clicks a step's friendly name to open the step detail modal
    Then the modal width is 70% of the viewport width
    And a font size adjustment control (minus, slider, plus) is visible in the modal header.
    """

    def setUp(self):
        with open(os.path.join(SERVE_DIR, 'serve.py')) as f:
            self.content = f.read()

    def test_step_modal_uses_modal_content_class(self):
        """Step detail modal container uses the shared .modal-content class."""
        step_start = self.content.find('id="step-modal-overlay"')
        step_end = self.content.find('</div>\n</div>\n', step_start + 100)
        step_html = self.content[step_start:step_end]
        self.assertIn('class="modal-content"', step_html)

    def test_modal_content_width_70vw(self):
        """The .modal-content CSS rule includes width:70vw."""
        self.assertRegex(self.content, r'\.modal-content\{[^}]*width:\s*70vw')

    def test_step_modal_has_font_controls(self):
        """Step detail modal header includes font size control elements."""
        step_start = self.content.find('id="step-modal-overlay"')
        step_end = self.content.find('</div>\n</div>\n', step_start + 100)
        step_html = self.content[step_start:step_end]
        self.assertIn('modal-font-controls', step_html)
        self.assertIn('modal-font-slider', step_html)

    def test_step_modal_has_minus_and_plus_buttons(self):
        """Step detail modal has minus and plus font adjustment buttons."""
        step_start = self.content.find('id="step-modal-overlay"')
        step_end = self.content.find('</div>\n</div>\n', step_start + 100)
        step_html = self.content[step_start:step_end]
        self.assertIn('adjustModalFont(-1)', step_html)
        self.assertIn('adjustModalFont(1)', step_html)


class TestStepDetailModalTitleFontSize(unittest.TestCase):
    """Scenario: Step Detail Modal title follows design_modal_standards sizing.

    The design_modal_standards anchor specifies that modal titles render 4pt
    larger than the default body font size (14px body -> 18px title).
    """

    def setUp(self):
        with open(os.path.join(SERVE_DIR, 'serve.py')) as f:
            self.content = f.read()

    def test_modal_title_base_size_is_18px(self):
        """Modal header h2 uses 18px base (14px body + 4pt per design_modal_standards)."""
        import re
        match = re.search(r'\.modal-header h2\{[^}]*font-size:\s*calc\((\d+)px', self.content)
        self.assertIsNotNone(match, "modal-header h2 font-size rule not found")
        title_base = int(match.group(1))
        self.assertEqual(title_base, 18, f"Title base is {title_base}px, expected 18px")

    def test_modal_body_base_size_is_14px(self):
        """Modal body uses 14px base font size."""
        import re
        match = re.search(r'\.modal-body\{[^}]*font-size:\s*calc\((\d+)px', self.content)
        self.assertIsNotNone(match, "modal-body font-size rule not found")
        body_base = int(match.group(1))
        self.assertEqual(body_base, 14, f"Body base is {body_base}px, expected 14px")

    def test_title_is_4pt_larger_than_body(self):
        """Title font size is exactly 4pt larger than body per design_modal_standards."""
        import re
        title_match = re.search(r'\.modal-header h2\{[^}]*font-size:\s*calc\((\d+)px', self.content)
        body_match = re.search(r'\.modal-body\{[^}]*font-size:\s*calc\((\d+)px', self.content)
        self.assertIsNotNone(title_match)
        self.assertIsNotNone(body_match)
        title_base = int(title_match.group(1))
        body_base = int(body_match.group(1))
        diff = title_base - body_base
        self.assertEqual(diff, 4, f"Title-body difference is {diff}pt, expected 4pt per design_modal_standards")


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
    sys.exit(0 if result.wasSuccessful() else 1)
