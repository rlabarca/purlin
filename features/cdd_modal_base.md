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

- Title renders 8 points larger than the modal's default body font size.
- Title uses `var(--purlin-primary)` color.

### 2.3 Font Size Control

- Control positioned in the modal header area (between title and close button, or in a dedicated controls row).
- Layout: decrease button (minus sign), horizontal slider, increase button (plus sign).
- Range: -4 to +30 points relative to the default body font size.
- All modal body text scales together preserving relative size differences between elements.
- Text wraps correctly at all slider positions without horizontal overflow or clipping.
- Selected size persists for the browser session (reopening any text-based modal retains the last setting). Uses `sessionStorage` or equivalent browser-session-scoped mechanism.

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
    Then all text elements in the modal body (h1, h2, h3, p, li, code, pre) are larger than their default size
    And the relative size differences between text elements are preserved

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
    Then the modal title computed font size is 8 points larger than the default body font size

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
- [ ] Modal title is 8pts larger than body text default
- [ ] Modal title uses `var(--purlin-primary)` color
- [ ] Font size control (minus button, slider, plus button) visible in modal header
- [ ] Slider at min (-4pts): text slightly smaller but fully legible
- [ ] Slider at max (+30pts): text substantially larger, wraps correctly, no horizontal overflow
- [ ] All text elements scale together preserving relative size differences
- [ ] Font size persists when closing and reopening a modal
- [ ] X button visible in header for close
- [ ] Escape key closes modal
- [ ] Clicking outside modal closes it
- [ ] Modal body scrolls vertically for long content
- [ ] Max-height is 80vh
- [ ] All modal elements theme-correct in both Blueprint and Architect themes
- [ ] Theme toggle updates modal colors immediately without closing/reopening
