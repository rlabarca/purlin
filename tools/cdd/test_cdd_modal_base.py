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
        # modal-body should use calc() with --modal-font-adjust (14px base per design spec)
        self.assertRegex(
            html,
            r'\.modal-body\s*\{[^}]*font-size:\s*calc\(14px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_h1_uses_calc_with_font_adjust(self):
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-body h1\s*\{[^}]*font-size:\s*calc\(17px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_h2_uses_calc_with_font_adjust(self):
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-body h2\s*\{[^}]*font-size:\s*calc\(15px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_h3_uses_calc_with_font_adjust(self):
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-body h3\s*\{[^}]*font-size:\s*calc\(13px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_code_uses_calc_with_font_adjust(self):
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-body code\s*\{[^}]*font-size:\s*calc\(12px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_relative_differences_preserved(self):
        """All text elements offset by same var, preserving relative sizes.

        With 14px body base: h1=17px (+3), h2=15px (+1), h3=13px (-1), code=12px (-2).
        """
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

        # Verify exact offsets from 14px base per design spec
        self.assertEqual(body_base, 14)
        self.assertEqual(h1_base, 17)
        self.assertEqual(h2_base, 15)
        self.assertEqual(h3_base, 13)
        self.assertEqual(code_base, 12)


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


class TestFontSizeScalesNonBodyModalElements(unittest.TestCase):
    """Scenario: Font Size Scales Non-Body Modal Elements

    Given the User has opened a text-based modal
    When the User moves the font size slider to a non-default position
    Then the modal title font size reflects the adjustment
    And metadata rows, tab labels, and tag elements scale by the same adjustment
    And consumer modals with inline-styled text also scale
    """

    def test_title_uses_calc_with_font_adjust(self):
        """Modal title (.modal-header h2) scales with --modal-font-adjust."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-header h2\s*\{[^}]*font-size:\s*calc\(\d+px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_metadata_uses_calc_with_font_adjust(self):
        """Metadata rows (.modal-metadata) scale with --modal-font-adjust."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-metadata\s*\{[^}]*font-size:\s*calc\(\d+px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_tabs_use_calc_with_font_adjust(self):
        """Tab labels (.modal-tab) scale with --modal-font-adjust."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-tab\s*\{[^}]*font-size:\s*calc\(\d+px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_step_detail_labels_use_calc_with_font_adjust(self):
        """Step Detail section labels (inline-styled) scale with --modal-font-adjust."""
        html = _generate_html()
        # Step Detail JS builds section headers with inline font-size using calc()
        self.assertRegex(
            html,
            r'font-size:calc\(10px \+ var\(--modal-font-adjust\) \* 1px\);font-weight:700;text-transform:uppercase;letter-spacing:0\.1em'
        )

    def test_step_detail_content_uses_calc_with_font_adjust(self):
        """Step Detail content (inline-styled) scales with --modal-font-adjust."""
        html = _generate_html()
        # Step Detail JS builds content divs with inline font-size using calc()
        self.assertRegex(
            html,
            r'font-size:calc\(12px \+ var\(--modal-font-adjust\) \* 1px\);line-height:1\.5'
        )

    def test_step_detail_source_badge_uses_calc(self):
        """Step Detail source badge (inline-styled) scales with --modal-font-adjust."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'font-size:calc\(10px \+ var\(--modal-font-adjust\) \* 1px\);font-weight:700;text-transform:uppercase'
        )


class TestCloseViaEscape(unittest.TestCase):
    """Scenario: Close via Escape

    Given the User has opened a text-based modal
    When the User presses the Escape key
    Then the modal closes
    """

    def test_escape_key_event_listener_registered(self):
        """A keydown event listener checks for the Escape key."""
        html = _generate_html()
        self.assertIn("document.addEventListener('keydown'", html)
        self.assertIn("'Escape'", html)

    def test_escape_closes_feature_modal(self):
        """Escape key calls closeModal() for the feature detail modal overlay."""
        html = _generate_html()
        self.assertIn('closeModal()', html)
        self.assertIn("getElementById('modal-overlay')", html)

    def test_escape_closes_wd_modal(self):
        """Escape key calls closeWdModal() for the What's Different modal overlay."""
        html = _generate_html()
        self.assertIn('closeWdModal()', html)

    def test_escape_closes_step_modal(self):
        """Escape key calls closeStepModal() for the Step Detail modal overlay."""
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
    Then the modal title computed font size is 4 points larger than the default body font size
    """

    def test_title_is_4pts_above_body_default(self):
        html = _generate_html()
        # Title now also uses calc() with --modal-font-adjust: 18px base (14 + 4)
        title_match = re.search(
            r'\.modal-header h2\s*\{[^}]*font-size:\s*calc\((\d+)px', html)
        body_match = re.search(
            r'\.modal-body\s*\{[^}]*font-size:\s*calc\((\d+)px', html)

        self.assertIsNotNone(title_match, "Title font-size not found")
        self.assertIsNotNone(body_match, "Body default font-size not found")

        title_size = int(title_match.group(1))
        body_default = int(body_match.group(1))
        self.assertEqual(title_size - body_default, 4,
                         f"Title ({title_size}px) should be exactly 4pts "
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


class TestFontControlsPositionStableDuringAdjustment(unittest.TestCase):
    """Scenario: Font Controls Position Stable During Adjustment

    Given the User has opened a text-based modal
    When the User moves the font size slider from the minimum to the maximum position
    Then the font size control widget remains at the same screen coordinates
    And the close button remains at the same screen coordinates
    """

    def test_title_has_flex_1_min_width_0(self):
        """Title uses flex:1;min-width:0 to absorb available space without
        pushing controls when it grows."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-header h2\{[^}]*flex:1[^}]*min-width:0'
        )

    def test_title_overflow_hidden(self):
        """Title overflow:hidden prevents layout expansion."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-header h2\{[^}]*overflow:hidden'
        )

    def test_font_controls_flex_shrink_0(self):
        """Font controls have flex-shrink:0 so they never compress."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-font-controls\{[^}]*flex-shrink:0'
        )

    def test_close_button_flex_shrink_0(self):
        """Close button has flex-shrink:0 so it stays in place."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-close\{[^}]*flex-shrink:0'
        )


class TestSliderDragProducesSmoothScaling(unittest.TestCase):
    """Scenario: Slider Drag Produces Smooth Scaling

    Given the User has opened a text-based modal
    When the User drags the font size slider continuously
    Then the text scales smoothly without discrete jumps
    And the slider step granularity is 0.5 or finer
    """

    def test_slider_step_is_half_point_or_finer(self):
        """All sliders use step='0.5' for sub-integer granularity."""
        html = _generate_html()
        # Every modal-font-slider must have step="0.5"
        slider_count = html.count('class="modal-font-slider"')
        step_count = html.count('step="0.5"')
        self.assertGreater(slider_count, 0)
        self.assertEqual(slider_count, step_count,
                         f"Found {slider_count} sliders but {step_count} step attributes")

    def test_oninput_uses_parseFloat(self):
        """Slider oninput uses parseFloat (not parseInt) to preserve fractional values."""
        html = _generate_html()
        self.assertIn('parseFloat(this.value)', html)
        # parseInt should NOT appear in slider oninput
        self.assertNotIn('parseInt(this.value)', html)

    def test_session_storage_load_uses_parseFloat(self):
        """Initial load from sessionStorage uses parseFloat to restore fractional values."""
        html = _generate_html()
        self.assertIn("parseFloat(sessionStorage.getItem", html)

    def test_css_variable_accepts_fractional_values(self):
        """The --modal-font-adjust CSS variable is multiplied by 1px in calc(),
        which correctly handles fractional inputs like 2.5."""
        html = _generate_html()
        # calc(14px + var(--modal-font-adjust) * 1px) works with fractional adjust
        self.assertRegex(
            html,
            r'calc\(\d+px\s*\+\s*var\(--modal-font-adjust\)\s*\*\s*1px\)'
        )


class TestRapidButtonClicksProduceSequentialIncrements(unittest.TestCase):
    """Scenario: Rapid Button Clicks Produce Sequential Increments

    Given the User has opened a text-based modal at the default font size (0)
    When the User clicks the increase button 5 times in rapid succession
    Then the font size adjustment value is exactly 5
    And each click produces a visible repaint before the next increment
    """

    def test_adjust_uses_request_animation_frame(self):
        """adjustModalFont wraps setModalFont in requestAnimationFrame
        so each click produces a visible repaint before the next."""
        html = _generate_html()
        self.assertIn('requestAnimationFrame', html)
        # The rAF should be inside adjustModalFont
        adjust_fn_match = re.search(
            r'function adjustModalFont\(delta\)\s*\{(.*?)\}', html, re.DOTALL)
        self.assertIsNotNone(adjust_fn_match, "adjustModalFont function not found")
        fn_body = adjust_fn_match.group(1)
        self.assertIn('requestAnimationFrame', fn_body)
        self.assertIn('setModalFont', fn_body)

    def test_button_onclick_calls_adjust_with_delta_1(self):
        """Each button click calls adjustModalFont with delta 1 or -1 (integer step)."""
        html = _generate_html()
        increase_count = html.count('adjustModalFont(1)')
        decrease_count = html.count('adjustModalFont(-1)')
        # 3 modals × 1 increase button each
        self.assertEqual(increase_count, 3,
                         f"Expected 3 increase buttons, found {increase_count}")
        self.assertEqual(decrease_count, 3,
                         f"Expected 3 decrease buttons, found {decrease_count}")

    def test_set_modal_font_applies_immediately(self):
        """setModalFont updates _modalFontAdjust and applies CSS property synchronously,
        so rAF-queued calls execute sequentially."""
        html = _generate_html()
        set_fn_match = re.search(
            r'function setModalFont\(value\)\s*\{(.*?)\n\}', html, re.DOTALL)
        self.assertIsNotNone(set_fn_match, "setModalFont function not found")
        fn_body = set_fn_match.group(1)
        self.assertIn('_modalFontAdjust = value', fn_body)
        self.assertIn("setProperty('--modal-font-adjust'", fn_body)


class TestTitleTruncationPreventsLayoutShift(unittest.TestCase):
    """Scenario: Title Truncation Prevents Layout Shift

    Given the User has opened a text-based modal with a long title
    When the User adjusts the font size to the maximum position
    Then the title truncates with an ellipsis rather than overflowing
    And the font controls and close button remain in their original positions
    """

    def test_title_has_text_overflow_ellipsis(self):
        """Title uses text-overflow:ellipsis to truncate long text."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-header h2\{[^}]*text-overflow:ellipsis'
        )

    def test_title_has_white_space_nowrap(self):
        """Title uses white-space:nowrap to prevent wrapping before truncation."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-header h2\{[^}]*white-space:nowrap'
        )

    def test_title_overflow_hidden_for_truncation(self):
        """Title overflow:hidden is required for text-overflow:ellipsis to work."""
        html = _generate_html()
        self.assertRegex(
            html,
            r'\.modal-header h2\{[^}]*overflow:hidden'
        )

    def test_header_layout_prevents_title_pushing_controls(self):
        """Header uses flex layout with title flex:1 and controls flex-shrink:0,
        so enlarging font size causes the title to truncate rather than displacing controls."""
        html = _generate_html()
        # Title takes available space (flex:1)
        self.assertRegex(html, r'\.modal-header h2\{[^}]*flex:1')
        # Controls stay fixed (flex-shrink:0)
        self.assertRegex(html, r'\.modal-font-controls\{[^}]*flex-shrink:0')


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
