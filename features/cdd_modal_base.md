# Feature: CDD Modal Base

> Label: "CDD Modal Base"
> Category: "CDD Dashboard"
> Prerequisite: features/design_modal_standards.md
> Prerequisite: features/design_visual_standards.md
> AFT Web: http://localhost:9086
> AFT Start: /pl-cdd

[TODO]

## 1. Overview

The CDD Modal Base provides the shared modal infrastructure that all text-based CDD modals inherit. It implements the constraints defined in `design_modal_standards.md`: viewport-relative width, font size adjustment control with session persistence, title sizing, close behavior, scrollable body, and theme integration. Consumer features (Feature Detail, Tombstone, What's Different, Step Detail, Spec Map modal) declare a prerequisite on this feature and add only their unique behavior.

---

## 2. Requirements

### 2.1 Modal Dimensions

- Width: 70% of viewport width (`70vw`).
- Fallback: 90% of viewport width on viewports narrower than 500px.
- Max-height: 80vh.
- Scrollable body when content exceeds available height.

### 2.2 Modal Title

- Title renders 4 points larger than the modal's default body font size.
- Title uses `var(--purlin-primary)` color.

### 2.3 Font Size Control

- Control positioned in the modal header area (between title and close button, or in a dedicated controls row).
- Layout: decrease button (minus sign), horizontal slider, increase button (plus sign).
- Range: -4 to +30 points relative to the default body font size.
- All text within the modal scales together preserving relative size differences between elements. This includes the title, metadata rows, tabs, body content (headings, paragraphs, lists, code, pre blocks), tags, and any inline-styled text in consumer modals (e.g., Step Detail section labels, source badges, content values).
- Text wraps correctly at all slider positions without horizontal overflow or clipping.
- Selected size persists for the browser session (reopening any text-based modal retains the last setting). Uses `sessionStorage` or equivalent browser-session-scoped mechanism.

### 2.3.1 Font Control Position Stability

- The font size control widget (buttons and slider) MUST maintain a fixed position in the modal header regardless of the current font size adjustment value.
- The modal title MUST be constrained so that changes to the title's rendered size do not displace the font controls or close button. The title truncates with ellipsis if it would otherwise overflow its allocated space.

### 2.3.2 Smooth Slider Scaling

- The slider MUST use sub-integer step granularity (step <= 0.5) so that dragging produces visually smooth, continuous scaling without perceptible discrete jumps.
- The `--modal-font-adjust` custom property MUST accept fractional values and all `calc()` expressions using it MUST produce correct results with fractional inputs.

### 2.3.3 Rapid Button Click Stability

- Each button click increments or decrements by exactly 1 unit.
- Rapid clicking MUST produce sequential, visually distinct increments. Each click MUST result in one visible repaint before the next increment takes effect. Visual batching (where multiple clicks appear as a single large jump) MUST NOT occur.

### 2.4 Close Behavior

- X button in the modal header.
- Escape key.
- Click outside the modal overlay.

### 2.5 Theme Integration

- All modal elements use CSS custom properties from `design_visual_standards.md` and update on theme toggle.

### 2.6 Web-Verify Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/cdd_modal_base/standard` | Project with features having varied metadata for modal rendering verification |

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Modal Width Is 70% of Viewport

    Given the CDD Dashboard is open in a browser
    When the User opens a text-based modal (e.g., clicks a feature name)
    Then the modal container occupies 70% of the viewport width

#### Scenario: Font Size Control Present

    Given the User has opened a text-based modal
    When the modal is displayed
    Then a decrease button (minus sign), horizontal slider, and increase button (plus sign) are visible in the modal header area

#### Scenario: Font Size Increase Scales All Text

    Given the User has opened a text-based modal
    When the User moves the font size slider to the maximum position (+30)
    Then all text elements in the modal (title, metadata, tabs, body h1/h2/h3/p/li/code/pre, tags, inline-styled content) are larger than their default size
    And the relative size differences between text elements are preserved

#### Scenario: Font Size Scales Non-Body Modal Elements

    Given the User has opened a text-based modal
    When the User moves the font size slider to a non-default position
    Then the modal title font size reflects the adjustment
    And metadata rows, tab labels, and tag elements scale by the same adjustment
    And consumer modals with inline-styled text (e.g., Step Detail labels and content) also scale

#### Scenario: Font Size Decrease Scales All Text

    Given the User has opened a text-based modal
    When the User moves the font size slider to the minimum position (-4)
    Then all text elements in the modal body are smaller than their default size
    And all text remains legible

#### Scenario: Text Wraps at All Slider Positions

    Given the User has opened a text-based modal
    When the User moves the font size slider to the maximum position (+30)
    Then no horizontal overflow occurs in the modal body
    And all text wraps correctly within the modal width

#### Scenario: Font Controls Position Stable During Adjustment

    Given the User has opened a text-based modal
    When the User moves the font size slider from the minimum to the maximum position
    Then the font size control widget (buttons and slider) remains at the same screen coordinates throughout the drag
    And the close button remains at the same screen coordinates

#### Scenario: Slider Drag Produces Smooth Scaling

    Given the User has opened a text-based modal
    When the User drags the font size slider continuously from one end to the other
    Then the text scales smoothly without perceptible discrete jumps between positions
    And the slider step granularity is 0.5 or finer

#### Scenario: Rapid Button Clicks Produce Sequential Increments

    Given the User has opened a text-based modal at the default font size (0)
    When the User clicks the increase button 5 times in rapid succession
    Then the font size adjustment value is exactly 5
    And each click produces a visible repaint before the next increment
    And the final state matches the result of 5 sequential single clicks

#### Scenario: Title Truncation Prevents Layout Shift

    Given the User has opened a text-based modal with a long title
    When the User adjusts the font size to the maximum position
    Then the title truncates with an ellipsis rather than overflowing
    And the font controls and close button remain in their original positions

#### Scenario: Font Size Persists Across Modal Opens

    Given the User has opened a text-based modal and adjusted the font size slider
    When the User closes the modal
    And the User opens any text-based modal (same or different content)
    Then the font size slider position is retained at the previously set value

#### Scenario: Close via X Button

    Given the User has opened a text-based modal
    When the User clicks the X button in the modal header
    Then the modal closes

#### Scenario: Close via Escape

    Given the User has opened a text-based modal
    When the User presses the Escape key
    Then the modal closes

#### Scenario: Close via Overlay Click

    Given the User has opened a text-based modal
    When the User clicks outside the modal container (on the overlay)
    Then the modal closes

#### Scenario: Theme Toggle Updates Modal

    Given the User has opened a text-based modal
    When the User toggles the theme (Blueprint to Architect or vice versa)
    Then all modal colors update to reflect the new theme
    And no manual refresh is required

#### Scenario: Title Size Larger Than Body Text

    Given the User has opened a text-based modal
    When the modal is displayed with default font size settings
    Then the modal title computed font size is 4 points larger than the default body font size

### Manual Scenarios (Human Verification Required)

None.

## Visual Specification

> **Design Anchor:** features/design_modal_standards.md
> **Inheritance:** Colors, typography, and theme switching per design_visual_standards.md.

### Screen: CDD Text-Based Modal

- **Reference:** N/A
- **Processed:** N/A
- [ ] Modal occupies 70% viewport width (not fixed pixel width)
- [ ] Modal falls back to 90% width on viewports narrower than 500px
- [ ] Modal title is 4pts larger than body text default
- [ ] Modal title uses `var(--purlin-primary)` color
- [ ] Font size control (minus button, slider, plus button) visible in modal header
- [ ] Font controls and close button remain at fixed screen position during font adjustment (no layout shift)
- [ ] Title truncates with ellipsis when enlarged, never displaces controls
- [ ] Slider drag produces visually smooth continuous scaling (no discrete jumps)
- [ ] Rapid button clicks produce sequential increments (no batched jumps)
- [ ] Slider at min (-4pts): text slightly smaller but fully legible
- [ ] Slider at max (+30pts): text substantially larger, wraps correctly, no horizontal overflow
- [ ] All text elements in the modal (title, metadata, tabs, body content, tags) scale together preserving relative size differences
- [ ] Font size persists when closing and reopening a modal
- [ ] X button visible in header for close
- [ ] Escape key closes modal
- [ ] Clicking outside modal closes it
- [ ] Modal body scrolls vertically for long content
- [ ] Max-height is 80vh
- [ ] All modal elements theme-correct in both Blueprint and Architect themes
- [ ] Theme toggle updates modal colors immediately without closing/reopening
