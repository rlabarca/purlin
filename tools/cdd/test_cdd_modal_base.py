"""Unit tests for CDD Modal Base (cdd_modal_base.md).

Covers automated scenarios from features/cdd_modal_base.md.
Tests verify the generated HTML/CSS/JS infrastructure for shared text-based modals.
Results written to tests/cdd_modal_base/tests.json.
"""
import json
import os
import re
import sys
import unittest
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import serve


def _generate_html():
    """Generate dashboard HTML with mocked feature data."""
    with patch('serve.get_feature_status', return_value=([], [], [])), \
         patch('serve.run_command', return_value=""):
        return serve.generate_html()


class TestModalWidthIs70PercentOfViewport(unittest.TestCase):
    """Scenario: Modal Width Is 70% of Viewport

    Given the CDD Dashboard is open in a browser
    When the User opens a text-based modal
    Then the modal container occupies 70% of the viewport width
    """

    def test_modal_content_uses_70vw_width(self):
        html = _generate_html()
        # CSS should set width:70vw on .modal-content
        self.assertIn('width:70vw', html)
        # Should NOT have the old fixed 700px width
        self.assertNotIn('width:700px', html)

    def test_narrow_viewport_fallback_to_90vw(self):
        html = _generate_html()
        # Media query for viewports narrower than 500px
        self.assertRegex(html, r'@media\s*\(max-width:\s*500px\)')
        # Should contain 90vw fallback
        self.assertIn('width:90vw', html)


class TestFontSizeControlPresent(unittest.TestCase):
    """Scenario: Font Size Control Present

    Given the User has opened a text-based modal
    When the modal is displayed
    Then a decrease button, horizontal slider, and increase button are visible
    """

    def test_feature_modal_has_font_controls(self):
        html = _generate_html()
        # Feature detail modal (modal-overlay) should have font controls
        modal_section = html[html.index('id="modal-overlay"'):]
        modal_section = modal_section[:modal_section.index('</div>\n</div>') + 20]
        self.assertIn('modal-font-controls', modal_section)
        self.assertIn('modal-font-slider', modal_section)
        self.assertIn('modal-font-btn', modal_section)

    def test_whats_different_modal_has_font_controls(self):
        html = _generate_html()
        modal_section = html[html.index('id="wd-modal-overlay"'):]
        modal_section = modal_section[:modal_section.index('</div>\n</div>') + 20]
        self.assertIn('modal-font-controls', modal_section)
        self.assertIn('modal-font-slider', modal_section)

    def test_step_modal_has_font_controls(self):
        html = _generate_html()
        modal_section = html[html.index('id="step-modal-overlay"'):]
        modal_section = modal_section[:modal_section.index('</div>\n</div>') + 20]
        self.assertIn('modal-font-controls', modal_section)
        self.assertIn('modal-font-slider', modal_section)

    def test_branch_collab_modal_has_no_font_controls(self):
        html = _generate_html()
        bc_start = html.index('id="bc-op-modal-overlay"')
        bc_end = html.index('</div>\n</div>', bc_start) + 20
        bc_section = html[bc_start:bc_end]
        self.assertNotIn('modal-font-controls', bc_section)
        self.assertNotIn('modal-font-slider', bc_section)

    def test_slider_has_correct_range(self):
        html = _generate_html()
        # Slider min=-4, max=30
        self.assertRegex(html, r'min="-4"')
        self.assertRegex(html, r'max="30"')

    def test_decrease_button_has_minus_sign(self):
        html = _generate_html()
        # Decrease button should have minus entity or character
        self.assertTrue(
            '&minus;' in html or '\u2212' in html,
            "Decrease button should contain minus sign"
        )

    def test_increase_button_has_plus_sign(self):
        html = _generate_html()
        # Increase button should have plus sign
        # Look for the pattern: font-btn...+
        self.assertRegex(html, r'modal-font-btn.*?>\+<')


class TestFontSizeIncreaseScalesAllText(unittest.TestCase):
    """Scenario: Font Size Increase Scales All Text

    Given the User has opened a text-based modal
    When the User moves the font size slider to the maximum position (+30)
    Then all text elements in the modal body are larger than their default size
    And the relative size differences between text elements are preserved
    """

    def test_body_text_uses_calc_with_font_adjust(self):
        html = _generate_html()
        # modal-body should use calc() with --modal-font-adjust
        self.assertRegex(
            html,
            r'\.modal-body\s*\{[^}]*font-size:\s*calc\(13px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_h1_uses_calc_with_font_adjust(self):
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-body h1\s*\{[^}]*font-size:\s*calc\(16px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_h2_uses_calc_with_font_adjust(self):
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-body h2\s*\{[^}]*font-size:\s*calc\(14px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_h3_uses_calc_with_font_adjust(self):
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-body h3\s*\{[^}]*font-size:\s*calc\(12px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_code_uses_calc_with_font_adjust(self):
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-body code\s*\{[^}]*font-size:\s*calc\(11px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_relative_differences_preserved(self):
        """All text elements offset by same var, preserving relative sizes."""
        html = _generate_html()
        # Extract the base sizes used in calc() for body, h1, h2, h3, code
        body_match = re.search(
            r'\.modal-body\s*\{[^}]*font-size:\s*calc\((\d+)px', html)
        h1_match = re.search(
            r'\.modal-body h1\s*\{[^}]*font-size:\s*calc\((\d+)px', html)
        h2_match = re.search(
            r'\.modal-body h2\s*\{[^}]*font-size:\s*calc\((\d+)px', html)
        h3_match = re.search(
            r'\.modal-body h3\s*\{[^}]*font-size:\s*calc\((\d+)px', html)
        code_match = re.search(
            r'\.modal-body code\s*\{[^}]*font-size:\s*calc\((\d+)px', html)

        self.assertIsNotNone(body_match)
        self.assertIsNotNone(h1_match)
        body_base = int(body_match.group(1))
        h1_base = int(h1_match.group(1))
        h2_base = int(h2_match.group(1))
        h3_base = int(h3_match.group(1))
        code_base = int(code_match.group(1))

        # Verify relative differences: h1 > h2 > body, h3 <= body, code < body
        self.assertGreater(h1_base, body_base)
        self.assertGreater(h2_base, body_base)
        self.assertLessEqual(h3_base, body_base)
        self.assertLess(code_base, body_base)


class TestFontSizeDecreaseScalesAllText(unittest.TestCase):
    """Scenario: Font Size Decrease Scales All Text

    Given the User has opened a text-based modal
    When the User moves the font size slider to the minimum position (-4)
    Then all text elements in the modal body are smaller than their default size
    And all text remains legible
    """

    def test_slider_min_is_negative_four(self):
        html = _generate_html()
        self.assertIn('min="-4"', html)

    def test_js_clamps_to_negative_four(self):
        html = _generate_html()
        # The JS setModalFont function should clamp to -4
        self.assertIn('Math.max(-4', html)


class TestTextWrapsAtAllSliderPositions(unittest.TestCase):
    """Scenario: Text Wraps at All Slider Positions

    Given the User has opened a text-based modal at max font size (+30)
    Then no horizontal overflow occurs and all text wraps correctly
    """

    def test_modal_body_has_overflow_y_auto(self):
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-body\s*\{[^}]*overflow-y:\s*auto'
        )

    def test_modal_uses_viewport_relative_width(self):
        """70vw width ensures text can wrap within viewport bounds."""
        html = _generate_html()
        self.assertIn('width:70vw', html)

    def test_modal_body_has_overflow_wrap_break_word(self):
        """overflow-wrap:break-word prevents horizontal overflow at large font sizes."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-body\s*\{[^}]*overflow-wrap:\s*break-word'
        )

    def test_modal_body_has_overflow_x_hidden(self):
        """overflow-x:hidden prevents horizontal scrollbar in modal body."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-body\s*\{[^}]*overflow-x:\s*hidden'
        )


class TestFontSizePersistsAcrossModalOpens(unittest.TestCase):
    """Scenario: Font Size Persists Across Modal Opens

    Given the User has adjusted the font size slider
    When the User closes and reopens a modal
    Then the font size slider position is retained
    """

    def test_session_storage_key_defined(self):
        html = _generate_html()
        self.assertIn('purlin-modal-font-adjust', html)

    def test_session_storage_set_on_change(self):
        html = _generate_html()
        self.assertIn('sessionStorage.setItem', html)

    def test_session_storage_read_on_load(self):
        html = _generate_html()
        self.assertIn('sessionStorage.getItem', html)


class TestCloseViaXButton(unittest.TestCase):
    """Scenario: Close via X Button

    Given the User has opened a text-based modal
    When the User clicks the X button
    Then the modal closes
    """

    def test_feature_modal_has_close_button(self):
        html = _generate_html()
        self.assertIn('id="modal-close"', html)
        self.assertIn('modal-close', html)

    def test_close_button_wired_to_handler(self):
        html = _generate_html()
        # Feature detail modal close button has click listener
        self.assertIn("getElementById('modal-close').addEventListener('click'", html)


class TestCloseViaEscape(unittest.TestCase):
    """Scenario: Close via Escape

    Given the User has opened a text-based modal
    When the User presses the Escape key
    Then the modal closes
    """

    def test_escape_handler_for_feature_modal(self):
        html = _generate_html()
        self.assertIn("'Escape'", html)
        self.assertIn('closeModal()', html)

    def test_escape_handler_for_wd_modal(self):
        html = _generate_html()
        self.assertIn('closeWdModal()', html)

    def test_escape_handler_for_step_modal(self):
        html = _generate_html()
        self.assertIn('closeStepModal()', html)


class TestCloseViaOverlayClick(unittest.TestCase):
    """Scenario: Close via Overlay Click

    Given the User has opened a text-based modal
    When the User clicks outside the modal container
    Then the modal closes
    """

    def test_feature_modal_overlay_click_closes(self):
        html = _generate_html()
        # Overlay click handler: if (e.target === this) closeModal()
        self.assertIn("getElementById('modal-overlay').addEventListener('click'", html)

    def test_wd_modal_overlay_click_closes(self):
        html = _generate_html()
        self.assertIn("getElementById('wd-modal-overlay').addEventListener('click'", html)


class TestThemeToggleUpdatesModal(unittest.TestCase):
    """Scenario: Theme Toggle Updates Modal

    Given the User has opened a text-based modal
    When the User toggles the theme
    Then all modal colors update to reflect the new theme
    """

    def test_modal_uses_css_custom_properties(self):
        html = _generate_html()
        self.assertIn('var(--purlin-surface)', html)
        self.assertIn('var(--purlin-border)', html)
        self.assertIn('var(--purlin-primary)', html)
        self.assertIn('var(--purlin-muted)', html)
        self.assertIn('var(--purlin-accent)', html)


class TestTitleSizeLargerThanBodyText(unittest.TestCase):
    """Scenario: Title Size Larger Than Body Text

    Given the User has opened a text-based modal
    When the modal is displayed with default font size settings
    Then the modal title computed font size is 8 points larger than the default body font size
    """

    def test_title_is_8pts_above_body_default(self):
        html = _generate_html()
        # Body default is 13px, title should be 21px (13 + 8)
        title_match = re.search(
            r'\.modal-header h2\s*\{[^}]*font-size:\s*(\d+)px', html)
        body_match = re.search(
            r'\.modal-body\s*\{[^}]*font-size:\s*calc\((\d+)px', html)

        self.assertIsNotNone(title_match, "Title font-size not found")
        self.assertIsNotNone(body_match, "Body default font-size not found")

        title_size = int(title_match.group(1))
        body_default = int(body_match.group(1))
        self.assertEqual(title_size - body_default, 8,
                         f"Title ({title_size}px) should be exactly 8pts "
                         f"larger than body default ({body_default}px)")

    def test_title_uses_purlin_primary_color(self):
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-header h2\s*\{[^}]*color:\s*var\(--purlin-primary\)'
        )


# =============================================================================
# Font control JS functions exist
# =============================================================================
class TestFontControlJavaScript(unittest.TestCase):
    """Verify shared font control JS infrastructure."""

    def test_set_modal_font_function_exists(self):
        html = _generate_html()
        self.assertIn('function setModalFont(', html)

    def test_adjust_modal_font_function_exists(self):
        html = _generate_html()
        self.assertIn('function adjustModalFont(', html)

    def test_clamp_range_in_set_function(self):
        html = _generate_html()
        # Should clamp to [-4, 30]
        self.assertIn('Math.max(-4', html)
        self.assertIn('Math.min(30', html)

    def test_css_variable_applied_to_modal_content(self):
        html = _generate_html()
        self.assertIn("setProperty('--modal-font-adjust'", html)

    def test_all_sliders_synced(self):
        html = _generate_html()
        self.assertIn("querySelectorAll('.modal-font-slider')", html)


# =============================================================================
# Test runner: writes results to tests/cdd_modal_base/tests.json
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

    tests_dir = os.path.join(project_root, 'tests', 'cdd_modal_base')
    os.makedirs(tests_dir, exist_ok=True)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    status = 'PASS' if failed == 0 else 'FAIL'
    with open(os.path.join(tests_dir, 'tests.json'), 'w') as f:
        json.dump({
            'status': status,
            'passed': passed,
            'failed': failed,
            'total': result.testsRun,
            'test_file': 'tools/cdd/test_cdd_modal_base.py'
        }, f)
    print(f"\ntests.json: {status}")
