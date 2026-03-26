# Feature: <Name>

> Label: "<Category>: <Label>"
> Category: "<Category>"
> Owner: <PM or PM — omit line if PM (default)>
> Prerequisite: features/<anchor_node>.md

## 1. Overview

<One paragraph: what this feature is and why it exists.>

---

## 2. Requirements

### 2.1 <Group Name>

- <Requirement>

<!-- Optional: Uncomment for features with regression tests.
### 2.x Regression Testing

Regression tests verify <describe what is tested>.
- **Approach:** <Agent behavior harness / Web test / API contract check>
- **Scenarios covered:** <which scenarios>
-->

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: <Title>

    Given <precondition>
    When <action>
    Then <expected outcome>
    And <additional assertion>

### Manual Scenarios (Human Verification Required)

None.

<!-- Optional: Uncomment for features with a visual/UI component.
## Visual Specification

> **Design Anchor:** features/design_visual_standards.md
> **Inheritance:** Colors, typography, and theme switching per anchor.

### Screen: <Screen Name>
- **Reference:** N/A
- **Processed:** N/A
- **Token Map:**
  - `<figma-token>` -> `<project-token>`
- [ ] <Visual acceptance criterion>
-->

<!-- Optional: Uncomment to hint QA about regression-worthy behaviors.
## Regression Guidance
- <Behavior description: what to verify and why it is fragile>
-->
